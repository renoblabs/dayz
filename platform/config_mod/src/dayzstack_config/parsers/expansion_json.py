"""Parser for DayZ Expansion JSON configs.

Permissive — Expansion settings shapes have shifted across versions.
We parse the JSON, capture the top-level shape, and mark which "well-known"
config family this looks like.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..types import ParsedConfig, ValidationIssue


# Well-known top-level keys per Expansion config flavor — used as heuristics
# to label what kind of config we're looking at.
_FLAVOR_HINTS: dict[str, tuple[str, ...]] = {
    "general_settings":   ("EnableGlobalChat", "EnableTransportChat", "VehicleSyncTimer"),
    "market_settings":    ("DefaultDealerMaxPriceThreshold", "MarketSystemEnabled"),
    "quest_settings":     ("EnableQuests", "QuestModuleEnabled"),
    "vehicle_settings":   ("VehiclePhysicsEnabled", "VehicleRequireKeyToStart"),
    "ai_settings":        ("Enabled", "AIPatrolEnabled"),
    "credits":            ("Authors", "Contributors", "Translators"),
    "loadout":            ("Slots", "Quickbar"),
    "skin":               ("DefaultSkinName", "Skins"),
}


def _detect_flavor(top_keys: list[str]) -> str:
    keys_set = set(top_keys)
    for flavor, hints in _FLAVOR_HINTS.items():
        if any(h in keys_set for h in hints):
            return flavor
    return "unknown"


class ExpansionJsonParser:
    config_type: str = "expansion_json"

    def parse_string(self, content: str, source_label: str, source_path: str | None = None) -> ParsedConfig:
        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            return ParsedConfig(
                config_type=self.config_type,
                source_label=source_label,
                source_path=source_path,
                raw_content=content,
                data={},
                issues=[ValidationIssue(severity="error", code="json_parse_error", message=str(e))],
            )

        if not isinstance(data, dict):
            return ParsedConfig(
                config_type=self.config_type,
                source_label=source_label,
                source_path=source_path,
                raw_content=content,
                data={},
                issues=[ValidationIssue(
                    severity="error", code="not_object",
                    message=f"top-level not an object (got {type(data).__name__})",
                )],
            )

        top_keys = list(data.keys())
        flavor = _detect_flavor(top_keys)

        return ParsedConfig(
            config_type=self.config_type,
            source_label=source_label,
            source_path=source_path,
            raw_content=content,
            data=data,
            metadata={
                "flavor": flavor,
                "top_level_keys": top_keys,
                "key_count": len(top_keys),
            },
        )

    def parse_file(self, path: Path, source_label: str | None = None) -> ParsedConfig:
        return self.parse_string(
            path.read_text(encoding="utf-8", errors="replace"),
            source_label=source_label or path.stem,
            source_path=str(path),
        )

    def serialize(self, parsed: ParsedConfig) -> str:
        # 4-space indent matches Expansion's own writer convention
        return json.dumps(parsed.data, indent=4, ensure_ascii=False)

    def validate(self, parsed: ParsedConfig) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        if (parsed.metadata or {}).get("flavor") == "unknown":
            issues.append(ValidationIssue(
                severity="info",
                code="unknown_flavor",
                message="JSON shape doesn't match any known Expansion config flavor — captured as raw",
            ))
        return issues
