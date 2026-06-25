"""Parser for cfgeventspawns.xml — coordinates where dynamic events spawn.

Schema: <eventposdef> root containing <event name="EventName"> children with
<pos x="..." z="..." a="..."/> children (a = optional rotation).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from lxml import etree

from ..types import ParsedConfig, ValidationIssue


class CfgEventSpawnsXmlParser:
    config_type: str = "cfgeventspawns_xml"

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
                data={"events": {}},
                issues=[ValidationIssue(severity="error", code="xml_parse_error", message=str(e))],
            )

        events: dict[str, list[dict[str, Any]]] = {}
        if root is not None:
            for ev in root.iterchildren("event"):
                name = ev.get("name", "")
                if not name:
                    continue
                positions: list[dict[str, Any]] = []
                for pos in ev.iterchildren("pos"):
                    positions.append({
                        "x": _maybe_float(pos.get("x")),
                        "y": _maybe_float(pos.get("y")),
                        "z": _maybe_float(pos.get("z")),
                        "a": _maybe_float(pos.get("a")),
                        "group": pos.get("group"),
                    })
                events[name] = positions

        return ParsedConfig(
            config_type=self.config_type,
            source_label=source_label,
            source_path=source_path,
            raw_content=content,
            data={
                "root_tag": root.tag if root is not None else None,
                "events": events,
            },
            metadata={
                "event_count": len(events),
                "total_positions": sum(len(v) for v in events.values()),
            },
        )

    def parse_file(self, path: Path, source_label: str | None = None) -> ParsedConfig:
        return self.parse_string(
            path.read_text(encoding="utf-8", errors="replace"),
            source_label=source_label or path.stem,
            source_path=str(path),
        )

    def serialize(self, parsed: ParsedConfig) -> str:
        root_tag = parsed.data.get("root_tag") or "eventposdef"
        root = etree.Element(root_tag)
        for name, positions in (parsed.data.get("events") or {}).items():
            ev = etree.SubElement(root, "event", attrib={"name": name})
            for p in positions:
                attrib: dict[str, str] = {}
                for k in ("x", "y", "z", "a"):
                    if p.get(k) is not None:
                        attrib[k] = f"{p[k]:.6g}"
                if p.get("group"):
                    attrib["group"] = p["group"]
                etree.SubElement(ev, "pos", attrib=attrib)
        return etree.tostring(root, pretty_print=True, xml_declaration=True, encoding="UTF-8").decode("utf-8")

    def validate(self, parsed: ParsedConfig) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        for name, positions in (parsed.data.get("events") or {}).items():
            if not positions:
                issues.append(ValidationIssue(
                    severity="warning",
                    code="empty_event",
                    message=f"event '{name}' has no <pos> entries",
                    path=name,
                ))
        return issues


def _maybe_float(s: str | None) -> float | None:
    if s is None:
        return None
    try:
        return float(s)
    except ValueError:
        return None
