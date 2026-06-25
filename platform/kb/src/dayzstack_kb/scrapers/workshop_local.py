"""workshop_local scraper — pulls Enforce source from a locally-installed Steam Workshop mod.

Same shape as LocalRepoScraper but targets the Steam workshop content dir.
Default target: CommunityFramework (workshop ID 1559212036) since it's the most-cited
example corpus in DayZ modding.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path
from typing import ClassVar

from .base import FetchedSource, ScrapeTarget

# Sensible defaults for a typical Steam install. Override via constructor.
DEFAULT_WORKSHOP_ROOT = Path("C:/Program Files (x86)/Steam/steamapps/workshop/content/221100")

# Workshop ID -> friendly name mapping. Extend as needed.
KNOWN_MODS: dict[int, str] = {
    1559212036: "CommunityFramework",
    1828439124: "VPPAdminTools",
}


class WorkshopLocalScraper:
    """Walks one or more locally-installed Workshop mods, ingests script files."""

    source_type: ClassVar[str] = "github_mod_file"  # treat workshop source like github source

    SCRIPT_GLOBS: ClassVar[list[str]] = ["**/*.c", "**/*.cpp", "**/*.h", "**/*.hpp", "**/config.cpp"]
    DOC_GLOBS: ClassVar[list[str]] = ["**/README*", "**/readme*", "**/*.md"]

    def __init__(self, workshop_root: Path | None = None, mod_ids: list[int] | None = None):
        self.workshop_root = (workshop_root or DEFAULT_WORKSHOP_ROOT).resolve()
        # Default = all known mods present on disk
        if mod_ids is None:
            self.mod_ids = [mid for mid in KNOWN_MODS if (self.workshop_root / str(mid)).exists()]
        else:
            self.mod_ids = mod_ids

    async def discover_targets(self) -> AsyncIterator[ScrapeTarget]:
        seen: set[Path] = set()
        for mod_id in self.mod_ids:
            mod_root = self.workshop_root / str(mod_id)
            if not mod_root.exists():
                continue
            mod_name = KNOWN_MODS.get(mod_id, f"workshop_{mod_id}")

            for glob in self.SCRIPT_GLOBS + self.DOC_GLOBS:
                for path in mod_root.glob(glob):
                    if not path.is_file():
                        continue
                    if path in seen:
                        continue
                    seen.add(path)
                    yield ScrapeTarget(
                        identifier=str(path),
                        metadata={
                            "mod_id": mod_id,
                            "mod_name": mod_name,
                            "is_doc": path.suffix.lower() in (".md", "") and "readme" in path.stem.lower(),
                        },
                    )

    async def fetch(self, target: ScrapeTarget) -> FetchedSource | None:
        path = Path(target.identifier)
        try:
            raw = path.read_text(encoding="utf-8", errors="replace")
        except (OSError, UnicodeError):
            return None

        if not raw.strip():
            return None

        # Skip enormous files (>200KB of source is usually generated/binary)
        if len(raw) > 200_000:
            return None

        mod_id = target.metadata.get("mod_id")
        mod_name = target.metadata.get("mod_name")
        rel = path.relative_to(self.workshop_root / str(mod_id)) if mod_id else path

        return FetchedSource(
            url=f"workshop://{mod_id}/{rel.as_posix()}",
            source_type=self.source_type,
            title=f"{mod_name}: {rel.as_posix()}",
            raw_text=raw,
            cleaned_text=raw,
            metadata={
                "mod_id": mod_id,
                "mod_name": mod_name,
                "rel_path": rel.as_posix(),
                "file_suffix": path.suffix,
                "file_size": path.stat().st_size,
                "is_doc": target.metadata.get("is_doc", False),
            },
        )


async def collect_all(workshop_root: Path | None = None, mod_ids: list[int] | None = None) -> list[FetchedSource]:
    scraper = WorkshopLocalScraper(workshop_root, mod_ids)
    out: list[FetchedSource] = []
    async for target in scraper.discover_targets():
        result = await scraper.fetch(target)
        if result is not None:
            out.append(result)
    return out
