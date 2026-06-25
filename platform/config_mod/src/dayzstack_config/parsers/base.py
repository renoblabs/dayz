"""Parser Protocol — every config parser implements this."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from ..types import ParsedConfig, ValidationIssue


@runtime_checkable
class ConfigParser(Protocol):
    config_type: str  # 'types_xml', etc.

    def parse_string(self, content: str, source_label: str, source_path: str | None = None) -> ParsedConfig: ...

    def parse_file(self, path: Path, source_label: str | None = None) -> ParsedConfig:
        """Default impl reads file then dispatches to parse_string."""
        ...

    def serialize(self, parsed: ParsedConfig) -> str:
        """Round-trip — emit original-format text from parsed.data. Best-effort byte match."""
        ...

    def validate(self, parsed: ParsedConfig) -> list[ValidationIssue]:
        """Check for common errors. Empty list = clean."""
        ...
