"""local_repo scraper — cold-start ingest from dayzAPI's curated content.

This is the day-1 KB seed. Reads:
- dayzAPI/docs/*.md            — session notes, gotcha catalogs
- dayzAPI/research/**/*.md      — research artifacts
- dayzAPI/_cf_unpacked/**/*.c   — CommunityFramework decompiled source

These are higher-signal than scraped wiki pages for the agent's first 100 queries.
Read-only against dayzAPI; we never modify the  other repo.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from pathlib import Path
from typing import ClassVar

from .base import FetchedSource, ScrapeTarget


class LocalRepoScraper:
    """Walks a sibling repo's docs/code and ingests select files."""

    source_type: ClassVar[str] = "local_repo"

    # Patterns describing what to ingest, mapped to (sub-source-type, treat-as).
    # Tuple is (glob_pattern, sub_kind, doc_or_code).
    PATTERNS: ClassVar[list[tuple[str, str, str]]] = [
        ("docs/*.md", "session_doc", "doc"),
        ("docs/superpowers/specs/*.md", "spec", "doc"),
        ("docs/superpowers/plans/*.md", "plan", "doc"),
        ("research/**/*.md", "research", "doc"),
        ("_cf_unpacked/**/*.c", "cf_source", "code"),
        ("_cf_unpacked/**/*.cpp", "cf_source", "code"),
        # The gotcha catalog is THE highest-value seed.
        ("docs/dayz-modding-patterns.md", "gotcha_catalog", "doc"),
    ]

    def __init__(self, repo_root: Path):
        self.root = repo_root.resolve()
        if not self.root.exists():
            raise FileNotFoundError(f"local_repo scraper: {self.root} does not exist")

    async def discover_targets(self) -> AsyncIterator[ScrapeTarget]:
        seen: set[Path] = set()
        for pattern, sub_kind, doc_or_code in self.PATTERNS:
            for path in self.root.glob(pattern):
                if not path.is_file():
                    continue
                if path in seen:
                    continue
                seen.add(path)
                yield ScrapeTarget(
                    identifier=str(path),
                    metadata={"sub_kind": sub_kind, "doc_or_code": doc_or_code},
                )

    async def fetch(self, target: ScrapeTarget) -> FetchedSource | None:
        path = Path(target.identifier)
        try:
            raw = path.read_text(encoding="utf-8", errors="replace")
        except (OSError, UnicodeError):
            return None

        if not raw.strip():
            return None

        # No HTML cleaning needed — these are already markdown/source.
        # Cleaned == raw for local repo files.
        rel = path.relative_to(self.root) if path.is_relative_to(self.root) else path
        title = path.stem
        if path.suffix == ".md":
            # First H1 if present
            for line in raw.splitlines()[:30]:
                if line.startswith("# "):
                    title = line.lstrip("#").strip()
                    break

        return FetchedSource(
            url=f"local://{rel.as_posix()}",
            source_type=self.source_type,
            title=title,
            raw_text=raw,
            cleaned_text=raw,
            metadata={
                "repo_root": str(self.root),
                "rel_path": rel.as_posix(),
                "sub_kind": target.metadata.get("sub_kind"),
                "doc_or_code": target.metadata.get("doc_or_code"),
                "file_suffix": path.suffix,
                "file_size": path.stat().st_size,
            },
        )


async def collect_all(repo_root: Path) -> list[FetchedSource]:
    """Convenience helper — drains discover_targets + fetches in series."""
    scraper = LocalRepoScraper(repo_root)
    out: list[FetchedSource] = []
    async for target in scraper.discover_targets():
        result = await scraper.fetch(target)
        if result is not None:
            out.append(result)
    return out
