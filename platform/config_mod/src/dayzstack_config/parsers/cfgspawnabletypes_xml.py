"""Parser for cfgspawnabletypes.xml — controls cargo + attachment spawn rules.

Schema: <spawnabletypes> root with many <type name="ItemClass"> children.
Each type may have <attachments chance="..."> blocks containing <item name="..." chance="..."/>
or <cargo chance="..."> blocks containing <item name="..." chance=".."/> with the same shape.
Some types also have <hoarder> blocks.

Permissive parser — same passthrough strategy as types_xml.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from lxml import etree

from ..types import ParsedConfig, ValidationIssue


_GROUP_TAGS = ("attachments", "cargo", "hoarder")


class CfgSpawnableTypesXmlParser:
    config_type: str = "cfgspawnabletypes_xml"

    def parse_string(self, content: str, source_label: str, source_path: str | None = None) -> ParsedConfig:
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

        if root is None or root.tag != "spawnabletypes":
            return ParsedConfig(
                config_type=self.config_type,
                source_label=source_label,
                source_path=source_path,
                raw_content=content,
                data={"items": {}},
                issues=[ValidationIssue(
                    severity="error", code="root_element",
                    message=f"expected <spawnabletypes>, got {root.tag if root is not None else 'None'}",
                )],
            )

        items: dict[str, dict[str, Any]] = {}
        for type_el in root.iterchildren("type"):
            name = type_el.get("name", "")
            if not name:
                continue
            items[name] = self._parse_type(type_el)

        return ParsedConfig(
            config_type=self.config_type,
            source_label=source_label,
            source_path=source_path,
            raw_content=content,
            data={"items": items},
            metadata={"item_count": len(items)},
        )

    def parse_file(self, path: Path, source_label: str | None = None) -> ParsedConfig:
        return self.parse_string(
            path.read_text(encoding="utf-8", errors="replace"),
            source_label=source_label or path.stem,
            source_path=str(path),
        )

    def _parse_type(self, type_el: etree._Element) -> dict[str, Any]:
        out: dict[str, Any] = {"name": type_el.get("name", ""), "groups": []}
        for child in type_el:
            # Skip XML comments and processing instructions — their .tag is a
            # cython callable (e.g. lxml's Comment factory), not a string,
            # which breaks JSON serialization downstream.
            if not isinstance(child.tag, str):
                continue
            if child.tag in _GROUP_TAGS:
                grp = {
                    "kind": child.tag,
                    "chance": _maybe_float(child.get("chance")),
                    "items": [
                        {"name": item.get("name"), "chance": _maybe_float(item.get("chance"))}
                        for item in child.iterchildren("item")
                        if item.get("name")
                    ],
                }
                out["groups"].append(grp)
            else:
                out.setdefault("extra_elements", []).append({
                    "tag": child.tag,
                    "attrib": dict(child.attrib),
                    "text": (child.text or "").strip() or None,
                })
        return out

    def serialize(self, parsed: ParsedConfig) -> str:
        root = etree.Element("spawnabletypes")
        for name, item in (parsed.data.get("items") or {}).items():
            type_el = etree.SubElement(root, "type", attrib={"name": name})
            for grp in item.get("groups") or []:
                attrib: dict[str, str] = {}
                if grp.get("chance") is not None:
                    attrib["chance"] = _format_float(grp["chance"])
                grp_el = etree.SubElement(type_el, grp["kind"], attrib=attrib)
                for it in grp.get("items") or []:
                    item_attrib: dict[str, str] = {"name": it["name"]}
                    if it.get("chance") is not None:
                        item_attrib["chance"] = _format_float(it["chance"])
                    etree.SubElement(grp_el, "item", attrib=item_attrib)
            for extra in item.get("extra_elements") or []:
                el = etree.SubElement(type_el, extra["tag"], attrib=extra.get("attrib") or {})
                if extra.get("text"):
                    el.text = extra["text"]

        return etree.tostring(root, pretty_print=True, xml_declaration=True, encoding="UTF-8").decode("utf-8")

    def validate(self, parsed: ParsedConfig) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        for name, item in (parsed.data.get("items") or {}).items():
            for grp in item.get("groups") or []:
                ch = grp.get("chance")
                if ch is not None and (ch < 0 or ch > 1):
                    issues.append(ValidationIssue(
                        severity="warning",
                        code="chance_out_of_range",
                        message=f"{name}/{grp['kind']}: chance={ch} not in [0,1]",
                        path=f"{name}.{grp['kind']}",
                    ))
        return issues


def _maybe_float(s: str | None) -> float | None:
    if s is None:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _format_float(f: float) -> str:
    """Match DayZ's typical chance formatting (e.g. '0.30' not '0.3000000001')."""
    return f"{f:.4g}"
