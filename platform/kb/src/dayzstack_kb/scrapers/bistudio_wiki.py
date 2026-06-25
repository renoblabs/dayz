"""bistudio_wiki — Scrape DayZ:Modding wiki via Wayback Machine and CDX API.

Uses Wayback CDX API to discover all unique archived DayZ wiki pages,
and fetches cached HTML content, converting it to markdown via markdownify.
Reads from the public Wayback Machine archive rather than the live origin,
which sits behind Cloudflare. Requests are rate-limited and respectful.
"""

from __future__ import annotations

import asyncio
import json
import time
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any, ClassVar

from .base import FetchedSource, ScrapeTarget

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
RATE_LIMIT_S = 1.0

# Canonical and highly-used DayZ wiki pages fallback
SEED_WIKI_PAGES = [
    "DayZ:Central_Economy",
    "DayZ:Central_Economy_Configuration",
    "DayZ:Central_Economy_mission_files_modding",
    "DayZ:Central_Economy_setup_for_custom_terrains",
    "DayZ:Enforce_Script_Syntax",
    "DayZ:Modding_Basics",
    "DayZ:Scripting_Basics",
    "DayZ:Server_Configuration",
    "DayZ:Administration_Logs",
    "DayZ:Buldozer_for_Object_Builder",
    "DayZ:Buldozer_for_Terrain_Builder",
    "DayZ:CE:_Ambient_Spawner",
    "DayZ:Contaminated_Areas_Configuration",
    "DayZ:Configuring_2D_Map",
    "DayZ:Diag_Menu",
]


class BistudioWikiScraper:
    """Crawls DayZ:Modding category via Wayback Machine and ingests as markdown."""

    source_type: ClassVar[str] = "bistudio_wiki"

    def __init__(self, cache_dir: Path | None = None, max_pages: int | None = None):
        self.cache_dir = (cache_dir or Path("scraper-cache/bistudio")).resolve()
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.max_pages = max_pages
        self._last_call_at: float = 0.0

    async def discover_targets(self) -> AsyncIterator[ScrapeTarget]:
        """Discover unique archived DayZ wiki pages via Wayback CDX API or fallback list."""
        url = "https://web.archive.org/cdx/search/cdx?url=community.bistudio.com/wiki/DayZ:*&output=json&collapse=urlkey"
        headers = {"User-Agent": USER_AGENT}
        page_count = 0
        pages: list[str] = list(SEED_WIKI_PAGES)

        try:
            import requests
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                for row in data[1:]:
                    orig_url = row[2]
                    if "?" in orig_url or "%20" in orig_url or ".png" in orig_url or ".jpg" in orig_url:
                        continue
                    parts = orig_url.split("/wiki/")
                    if len(parts) > 1:
                        identifier = parts[1]
                        if not identifier or identifier.lower() == "dayz":
                            continue
                        if identifier not in pages:
                            pages.append(identifier)
        except Exception:
            pass

        for p in pages:
            page_count += 1
            yield ScrapeTarget(
                identifier=p,
                metadata={"category_path": "Category:DayZ:Modding"},
            )
            if self.max_pages and page_count >= self.max_pages:
                return

    async def fetch(self, target: ScrapeTarget) -> FetchedSource | None:
        title = target.identifier
        safe_title = title.replace(":", "_").replace("/", "_").replace("\\", "_")
        cache_file = self.cache_dir / f"{safe_title}.json"

        # Check cache
        if cache_file.exists():
            try:
                cached = json.loads(cache_file.read_text(encoding="utf-8"))
                return FetchedSource(
                    url=cached["url"],
                    source_type=self.source_type,
                    title=cached["title"],
                    raw_text=cached["raw_text"],
                    cleaned_text=cached["cleaned_text"],
                    metadata=cached["metadata"],
                )
            except Exception:
                pass

        try:
            import requests
            from bs4 import BeautifulSoup
            import markdownify

            url = f"https://web.archive.org/web/https://community.bistudio.com/wiki/{title}"
            headers = {"User-Agent": USER_AGENT}

            elapsed = time.time() - self._last_call_at
            if elapsed < RATE_LIMIT_S:
                await asyncio.sleep(RATE_LIMIT_S - elapsed)
            self._last_call_at = time.time()

            resp = requests.get(url, headers=headers, timeout=15)
            if resp.status_code != 200:
                return None

            soup = BeautifulSoup(resp.text, 'html.parser')
            content_div = soup.find(id="mw-content-text")
            if not content_div:
                return None

            cleaned_text = markdownify.markdownify(str(content_div), heading_style="ATX")

            cached_data = {
                "url": f"https://community.bistudio.com/wiki/{title}",
                "title": title,
                "raw_text": resp.text,
                "cleaned_text": cleaned_text,
                "metadata": {
                    "category_path": target.metadata.get("category_path", "Category:DayZ:Modding"),
                    "wiki": "bistudio",
                    "format": "markdown",
                }
            }
            cache_file.write_text(json.dumps(cached_data), encoding="utf-8")

            return FetchedSource(
                url=cached_data["url"],
                source_type=self.source_type,
                title=cached_data["title"],
                raw_text=cached_data["raw_text"],
                cleaned_text=cached_data["cleaned_text"],
                metadata=cached_data["metadata"],
            )
        except Exception:
            return None


async def collect_all(
    cache_dir: Path | None = None,
    max_pages: int | None = None,
) -> list[FetchedSource]:
    scraper = BistudioWikiScraper(cache_dir, max_pages)
    out: list[FetchedSource] = []
    async for target in scraper.discover_targets():
        result = await scraper.fetch(target)
        if result is not None:
            out.append(result)
    return out
