"""Shared types for parsers, diff, persistence."""

from __future__ import annotations

import hashlib
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


# Recognized config types — used in DB CHECK + dispatch tables
CONFIG_TYPES = (
    "types_xml",
    "cfgspawnabletypes_xml",
    "cfgeventspawns_xml",
    "expansion_json",
    "traderplus_json",
    "mission_init_c",
    "server_cfg",
)


class ValidationIssue(BaseModel):
    """A single problem found during config validation."""

    severity: str = Field(default="warning", pattern="^(error|warning|info)$")
    code: str
    message: str
    path: str | None = None  # XPath / dotted JSON path / file:line


class ParsedConfig(BaseModel):
    """Result of parsing a config file. Format-specific data lives in `data`."""

    model_config = ConfigDict(extra="forbid")

    config_type: str
    source_label: str           # human-readable label, e.g. "vanilla_chernarus_2025"
    source_path: str | None = None
    raw_content: str            # original text, kept for round-trip + diff
    data: dict[str, Any]        # normalized parsed structure
    metadata: dict[str, Any] = Field(default_factory=dict)
    issues: list[ValidationIssue] = Field(default_factory=list)

    @property
    def file_hash(self) -> str:
        return hashlib.sha256(self.raw_content.encode("utf-8", errors="replace")).hexdigest()


# A type-xml item for diff convenience
class TypesItem(BaseModel):
    """One <type name="..."> entry from types.xml. Pydantic for easy compare."""

    model_config = ConfigDict(extra="allow")

    name: str
    nominal: int | None = None
    lifetime: int | None = None
    restock: int | None = None
    min: int | None = None
    quantmin: int | None = None
    quantmax: int | None = None
    cost: int | None = None
    flags: dict[str, int] = Field(default_factory=dict)   # count_in_cargo etc. (1/0)
    category: str | None = None
    usages: list[str] = Field(default_factory=list)
    values: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class TypesDiffEntry(BaseModel):
    """One row of a types.xml diff."""

    name: str
    change: str  # 'added' | 'removed' | 'modified'
    field_changes: dict[str, tuple[Any, Any]] = Field(default_factory=dict)
