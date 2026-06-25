"""github_mods — clone curated DayZ mod repos via git, ingest source files.

Curated to top community/foundational mods. Each repo is `git clone --depth 1`
into scraper-cache/github/<owner>__<repo>/ then walked for .c, .h, .cpp,
config.cpp, README.md.

Tagged source_type='github_mod_file' (existing) with metadata.kind='open_source_mod'
so future filters can target the curated open-source corpus specifically.
"""

from __future__ import annotations

import asyncio
import shutil
import subprocess
from collections.abc import AsyncIterator
from pathlib import Path
from typing import ClassVar

from .base import FetchedSource, ScrapeTarget


# Curated list. Stable, foundational, community-recommended modder repos.
# Add to this list judiciously — each one ingests hundreds of files.
CURATED_REPOS: list[tuple[str, str]] = [
    # (owner, repo)
    # === Foundational frameworks ===
    ("Arkensor", "DayZ-CommunityFramework"),
    ("salutesh", "DayZ-Expansion-Scripts"),
    # === Mod templates / vendor-prefix conventions ===
    ("InclementDab", "DayZ-Mod-Template"),
    ("InclementDab", "DayZ-Dabs-Framework"),
    ("Jacob-Mango", "DayZ-CommunityOnlineTools"),
    ("Jacob-Mango", "DayZ-SampleMod"),
    # === OFFICIAL Bohemia Interactive repos — partial substitute for the
    #     CF-blocked BI wiki. DayZ-Central-Economy is especially critical
    #     for the server-modder pivot (types.xml, mission files, CE configs).
    ("BohemiaInteractive", "DayZ-Samples"),
    ("BohemiaInteractive", "DayZ-Misc"),
    ("BohemiaInteractive", "DayZ-Central-Economy"),
]

# Extension globs for the BohemiaInteractive repos that have server-config
# rather than script content — types.xml, JSON, etc.
SERVER_CONFIG_GLOBS: list[str] = ["**/*.xml", "**/*.json"]

INGEST_GLOBS: list[str] = ["**/*.c", "**/*.cpp", "**/*.h", "**/*.hpp", "**/config.cpp", "**/*.md"]
SKIP_DIR_PREFIXES: tuple[str, ...] = (".git", "node_modules", "__pycache__", ".vs", ".vscode", ".idea")
MAX_FILE_BYTES = 200_000


def _git_shallow_clone(url: str, dest: Path) -> bool:
    """Synchronous shallow clone via subprocess.run with arg list (no shell, safe).

    Returns True on success, False otherwise. Cleans up on failure.
    """
    try:
        result = subprocess.run(
            ["git", "clone", "--depth", "1", url, str(dest)],
            capture_output=True,
            text=True,
            timeout=120,
            shell=False,
            check=False,
        )
    except (subprocess.TimeoutExpired, OSError):
        if dest.exists():
            shutil.rmtree(dest, ignore_errors=True)
        return False

    if result.returncode != 0:
        if dest.exists():
            shutil.rmtree(dest, ignore_errors=True)
        return False
    return True


class GithubModsScraper:
    """Shallow-clones a curated set of repos and ingests source files."""

    source_type: ClassVar[str] = "github_mod_file"

    def __init__(
        self,
        cache_dir: Path | None = None,
        repos: list[tuple[str, str]] | None = None,
    ):
        self.cache_dir = (cache_dir or Path("scraper-cache/github")).resolve()
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.repos = repos or CURATED_REPOS

    async def _ensure_clone(self, owner: str, repo: str) -> Path | None:
        """Clone repo if not already present. Returns path or None on failure."""
        target = self.cache_dir / f"{owner}__{repo}"
        if (target / ".git").exists():
            return target
        url = f"https://github.com/{owner}/{repo}.git"
        ok = await asyncio.to_thread(_git_shallow_clone, url, target)
        return target if ok else None

    async def discover_targets(self) -> AsyncIterator[ScrapeTarget]:
        seen: set[Path] = set()
        for owner, repo in self.repos:
            repo_root = await self._ensure_clone(owner, repo)
            if repo_root is None:
                continue

            # BI repos include critical XML/JSON configs (types.xml etc.) — pull those too
            globs = INGEST_GLOBS + SERVER_CONFIG_GLOBS if owner == "BohemiaInteractive" else INGEST_GLOBS
            for glob in globs:
                for path in repo_root.glob(glob):
                    if not path.is_file():
                        continue
                    if any(part.startswith(SKIP_DIR_PREFIXES) for part in path.parts):
                        continue
                    if path in seen:
                        continue
                    seen.add(path)
                    yield ScrapeTarget(
                        identifier=str(path),
                        metadata={
                            "owner": owner,
                            "repo": repo,
                            "kind": "open_source_mod",
                            "repo_root": str(repo_root),
                        },
                    )

    async def fetch(self, target: ScrapeTarget) -> FetchedSource | None:
        path = Path(target.identifier)
        try:
            stat = path.stat()
            if stat.st_size > MAX_FILE_BYTES:
                return None
            raw = path.read_text(encoding="utf-8", errors="replace")
        except (OSError, UnicodeError):
            return None

        if not raw.strip():
            return None

        owner = target.metadata.get("owner", "")
        repo = target.metadata.get("repo", "")
        repo_root = Path(target.metadata.get("repo_root", path.parent))
        rel = path.relative_to(repo_root) if path.is_relative_to(repo_root) else path

        url = f"https://github.com/{owner}/{repo}/blob/HEAD/{rel.as_posix()}"

        return FetchedSource(
            url=url,
            source_type=self.source_type,
            title=f"{owner}/{repo}: {rel.as_posix()}",
            raw_text=raw,
            cleaned_text=raw,
            metadata={
                "owner": owner,
                "repo": repo,
                "rel_path": rel.as_posix(),
                "file_suffix": path.suffix,
                "file_size": stat.st_size,
                "kind": "open_source_mod",
            },
        )


async def collect_all(
    cache_dir: Path | None = None,
    repos: list[tuple[str, str]] | None = None,
) -> list[FetchedSource]:
    scraper = GithubModsScraper(cache_dir, repos)
    out: list[FetchedSource] = []
    async for target in scraper.discover_targets():
        result = await scraper.fetch(target)
        if result is not None:
            out.append(result)
    return out
