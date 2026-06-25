"""Base types for scrapers — Protocol + Pydantic dataclasses."""

from __future__ import annotations

import hashlib
from collections.abc import AsyncIterator
from typing import ClassVar, Protocol

from pydantic import BaseModel, ConfigDict, Field


class ScrapeTarget(BaseModel):
    """One thing a scraper plans to fetch (URL, file path, video id, etc.)."""

    model_config = ConfigDict(extra="allow")

    identifier: str  # Stable identifier (URL, abs path, etc.) for idempotency.
    metadata: dict = Field(default_factory=dict)


class FetchedSource(BaseModel):
    """One fetched, cleaned source ready for DB insertion."""

    model_config = ConfigDict(extra="forbid")

    url: str
    source_type: str
    title: str | None = None
    raw_text: str
    cleaned_text: str
    metadata: dict = Field(default_factory=dict)

    @property
    def content_hash(self) -> str:
        """sha256 of cleaned_text — versioning key."""
        return hashlib.sha256(self.cleaned_text.encode("utf-8")).hexdigest()


class Scraper(Protocol):
    """Each scraper produces a stream of FetchedSources."""

    source_type: ClassVar[str]

    async def discover_targets(self) -> AsyncIterator[ScrapeTarget]:
        """Yield targets the scraper would fetch. Generator, may be unbounded."""
        ...

    async def fetch(self, target: ScrapeTarget) -> FetchedSource | None:
        """Fetch + clean a target. Return None to skip."""
        ...
