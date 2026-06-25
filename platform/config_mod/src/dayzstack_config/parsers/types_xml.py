"""Parser for DayZ vanilla types.xml — the loot economy master file.

Schema is well-known: <types> root with many <type name="..."> children.
Each <type> may have nominal/lifetime/restock/min, quantmin/quantmax, cost,
flags (count_in_cargo, count_in_hoarder, count_in_map, count_in_player,
crafted, deloot), category, usage, value, tag.

Parser is permissive — captures unknown elements in `extra_elements` to
preserve them on round-trip. Modded types.xml dialects (Expansion, CF mods)
add extra fields; we don't lose them.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from lxml import etree

from ..types import ParsedConfig, TypesItem, ValidationIssue


# Known scalar fields with int values. Keys are XML element names.
_INT_FIELDS = ("nominal", "lifetime", "restock", "min", "quantmin", "quantmax", "cost")
# Known list-of-name-attribute fields (each child has a `name` attribute).
_NAMED_LIST_FIELDS = ("usage", "value", "tag")


class TypesXmlParser:
    config_type: str = "types_xml"

    # ── parse ────────────────────────────────────────────────────────────────

    def parse_string(self, content: str, source_label: str, source_path: str | None = None) -> ParsedConfig:
        # lxml is permissive AND preserves unknown elements via passthrough below
        parser = etree.XMLParser(remove_blank_text=False, recover=True)
        try:
            root = etree.fromstring(content.encode("utf-8"), parser)
        except etree.XMLSyntaxError as e:
            return ParsedConfig(
                config_type=self.config_type,
                source_label=source_label,
                source_path=source_path,
                raw_content=content,
                data={"items": {}},
                issues=[ValidationIssue(severity="error", code="xml_parse_error", message=str(e))],
            )

        if root is None or root.tag != "types":
            return ParsedConfig(
                config_type=self.config_type,
                source_label=source_label,
                source_path=source_path,
                raw_content=content,
                data={"items": {}},
                issues=[ValidationIssue(
                    severity="error",
                    code="root_element",
                    message=f"expected <types>, got {root.tag if root is not None else 'None'}",
                )],
            )

        items: dict[str, dict[str, Any]] = {}
        for type_el in root.iterchildren("type"):
            name = type_el.get("name", "")
            if not name:
                continue
            items[name] = self._parse_type(type_el)

        # Capture root attributes (rare but possible)
        root_attrs = dict(root.attrib)

        return ParsedConfig(
            config_type=self.config_type,
            source_label=source_label,
            source_path=source_path,
            raw_content=content,
            data={
                "root_attrs": root_attrs,
                "items": items,
            },
            metadata={"item_count": len(items)},
        )

    def parse_file(self, path: Path, source_label: str | None = None) -> ParsedConfig:
        content = path.read_text(encoding="utf-8", errors="replace")
        return self.parse_string(
            content,
            source_label=source_label or path.stem,
            source_path=str(path),
        )

    def _parse_type(self, type_el: etree._Element) -> dict[str, Any]:
        item: dict[str, Any] = {
            "name": type_el.get("name", ""),
            "flags": {},
            "usages": [],
            "values": [],
            "tags": [],
            "category": None,
            "extra_elements": [],   # passthrough for forward-compat / modded types
        }

        for child in type_el:
            tag = child.tag
            # Skip lxml Comment / ProcessingInstruction nodes (tag is a cython callable, not str)
            if not isinstance(tag, str):
                continue
            if tag in _INT_FIELDS:
                txt = (child.text or "").strip()
                try:
                    item[tag] = int(txt) if txt else None
                except ValueError:
                    item[tag] = None
            elif tag == "flags":
                # All flag attrs are int-ish (0 or 1 typically)
                flags = {}
                for k, v in child.attrib.items():
                    try:
                        flags[k] = int(v)
                    except (TypeError, ValueError):
                        flags[k] = v
                item["flags"] = flags
            elif tag == "category":
                item["category"] = child.get("name")
            elif tag in _NAMED_LIST_FIELDS:
                key = {"usage": "usages", "value": "values", "tag": "tags"}[tag]
                v = child.get("name")
                if v is not None:
                    item[key].append(v)
            else:
                # Unknown element — capture for round-trip
                item["extra_elements"].append({
                    "tag": tag,
                    "attrib": dict(child.attrib),
                    "text": (child.text or "").strip() or None,
                })

        return item

    # ── serialize (best-effort round-trip) ──────────────────────────────────

    def serialize(self, parsed: ParsedConfig) -> str:
        """Emit a types.xml string from parsed.data. May not be byte-identical
        to original (lxml normalizes attribute quoting, whitespace) but
        semantically equivalent and re-parseable."""
        root_attrs = parsed.data.get("root_attrs", {}) or {}
        items = parsed.data.get("items", {}) or {}

        root = etree.Element("types", attrib=root_attrs)
        for name, item in items.items():
            type_el = etree.SubElement(root, "type", attrib={"name": name})
            for f in _INT_FIELDS:
                v = item.get(f)
                if v is not None:
                    el = etree.SubElement(type_el, f)
                    el.text = str(v)
            cat = item.get("category")
            if cat:
                etree.SubElement(type_el, "category", attrib={"name": cat})
            flags = item.get("flags") or {}
            if flags:
                etree.SubElement(type_el, "flags", attrib={k: str(v) for k, v in flags.items()})
            for u in item.get("usages") or []:
                etree.SubElement(type_el, "usage", attrib={"name": u})
            for v in item.get("values") or []:
                etree.SubElement(type_el, "value", attrib={"name": v})
            for t in item.get("tags") or []:
                etree.SubElement(type_el, "tag", attrib={"name": t})
            for extra in item.get("extra_elements") or []:
                el = etree.SubElement(type_el, extra["tag"], attrib=extra.get("attrib") or {})
                if extra.get("text"):
                    el.text = extra["text"]

        return etree.tostring(
            root, pretty_print=True, xml_declaration=True, encoding="UTF-8"
        ).decode("utf-8")

    # ── validate ────────────────────────────────────────────────────────────

    def validate(self, parsed: ParsedConfig) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        items = parsed.data.get("items", {}) or {}

        for name, item in items.items():
            # Common error: nominal=0 with lifetime > 0 (item exists but never spawns)
            if item.get("nominal") == 0 and item.get("lifetime", 0):
                issues.append(ValidationIssue(
                    severity="warning",
                    code="zero_nominal_with_lifetime",
                    message=f"{name}: nominal=0 but lifetime={item.get('lifetime')} (item won't spawn)",
                    path=name,
                ))
            # Common error: min > nominal (impossible target)
            n, m = item.get("nominal"), item.get("min")
            if n is not None and m is not None and m > n:
                issues.append(ValidationIssue(
                    severity="warning",
                    code="min_exceeds_nominal",
                    message=f"{name}: min={m} > nominal={n}",
                    path=name,
                ))
            # Common error: quantmax < quantmin
            qmin, qmax = item.get("quantmin"), item.get("quantmax")
            if qmin is not None and qmax is not None and qmax < qmin and qmax != -1:
                issues.append(ValidationIssue(
                    severity="error",
                    code="quantmax_below_quantmin",
                    message=f"{name}: quantmax={qmax} < quantmin={qmin}",
                    path=name,
                ))

        return issues


# Convenience extractor — returns TypesItem objects from parsed.data, useful for diff
def items_as_typed(parsed: ParsedConfig) -> dict[str, TypesItem]:
    return {name: TypesItem(**item) for name, item in (parsed.data.get("items") or {}).items()}
