"""Battlemetrics public API client — server lists + mod fingerprints.

Endpoint: https://api.battlemetrics.com/servers
- No auth required for read queries
- DayZ filter: filter[game]=dayz
- attributes.details.modIds gives Workshop IDs per server
- attributes.details.modNames gives parallel name list

Pagination via JSON:API standard (page[size], next link in meta).
Per-server mod count averages 10-30 for popular servers.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

API_BASE = "https://api.battlemetrics.com"
USER_AGENT = "dayz-stack-intel/0.1 (+https://github.com/dayz-stack)"


@dataclass(slots=True)
class BattlemetricsConfig:
    page_size: int = 100
    max_servers: int = 200          # top N by player count is plenty for trend purposes
    sleep_between_pages_s: float = 1.0   # polite — they ban scrapers
    timeout_s: float = 30.0


@retry(
    retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.TimeoutException)),
    stop=stop_after_attempt(4),
    wait=wait_exponential(min=2, max=30),
    reraise=True,
)
async def _get(client: httpx.AsyncClient, url: str, params: dict | None = None) -> dict:
    resp = await client.get(url, params=params, timeout=30.0)
    if resp.status_code == 429:
        await asyncio.sleep(15)  # back way off — BM bans
        resp.raise_for_status()
    resp.raise_for_status()
    return resp.json()


async def fetch_top_dayz_servers(cfg: BattlemetricsConfig) -> list[dict]:
    """Paginated fetch of top DayZ servers by player count. Returns flat list of items."""
    items: list[dict] = []
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}

    async with httpx.AsyncClient(headers=headers) as client:
        # First page
        url = f"{API_BASE}/servers"
        params: dict = {
            "filter[game]": "dayz",
            "sort": "-players",
            "page[size]": cfg.page_size,
        }
        rank_offset = 0

        while url and len(items) < cfg.max_servers:
            page = await _get(client, url, params)
            data = page.get("data") or []
            for rank_in_page, item in enumerate(data):
                item["_rank"] = rank_offset + rank_in_page
                items.append(item)
                if len(items) >= cfg.max_servers:
                    break
            rank_offset += len(data)

            # Follow `next` link if present
            next_url = page.get("links", {}).get("next")
            if not next_url:
                break
            url = next_url
            params = None  # next link already has cursor params encoded

            await asyncio.sleep(cfg.sleep_between_pages_s)

    return items


def _sanitize_json(obj):
    """Recursively strip null bytes from any string values in a dict/list tree.

    Postgres JSONB rejects \\u0000 in string values (not just root TEXT columns).
    """
    if isinstance(obj, str):
        return obj.replace("\x00", "")
    if isinstance(obj, dict):
        return {k: _sanitize_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize_json(v) for v in obj]
    return obj


def _sanitize_text(s) -> str | None:
    """Strip nulls and control bytes that some BM responses leak from raw query data.

    Battlemetrics sometimes returns binary-encoded mod blobs (concatenated names with
    delimiter bytes) when the source server's protocol response wasn't cleanly parsed.
    Postgres TEXT rejects 0x00; we also drop other C0 control chars except tab/lf/cr.
    """
    if s is None:
        return None
    s = str(s)
    cleaned = "".join(c for c in s if c in ("\t", "\n", "\r") or ord(c) >= 0x20)
    cleaned = cleaned.replace("\x00", "")
    return cleaned.strip() or None


def parse_server(item: dict, snapshot_date) -> tuple[dict, list[dict]]:
    """Extract a server_snapshots row + its mod rows from one BM item."""
    a = item.get("attributes", {}) or {}
    details = a.get("details") or {}

    server_id = str(item.get("id", ""))
    snap_row = {
        "snapshot_date": snapshot_date,
        "source": "battlemetrics",
        "server_id": server_id,
        "server_name": _sanitize_text(a.get("name")) or "(unnamed)",
        "map_name": _sanitize_text(details.get("map") or details.get("Map")),
        "player_count": a.get("players"),
        "max_players": a.get("maxPlayers"),
        "queue_count": a.get("queue") or details.get("queue"),
        "rank_in_source": item.get("_rank"),
        "ip": _sanitize_text(a.get("ip")),
        "port": a.get("port"),
        "raw_response": _sanitize_json(item),
    }

    mod_rows: list[dict] = []
    mod_ids_raw = details.get("modIds") or []
    mod_names_raw = details.get("modNames") or []

    # If either is a list, treat it as such; if a string slipped through (BM
    # sometimes returns garbage-encoded blobs), reject the whole mod set for
    # this server — better to lose the mod fingerprint than poison the table.
    if not isinstance(mod_ids_raw, list):
        mod_ids_raw = []
    if not isinstance(mod_names_raw, list):
        mod_names_raw = []

    # Filter out any non-scalar items (sometimes nested lists slip through)
    mod_ids = [m for m in mod_ids_raw if isinstance(m, (str, int))]
    mod_names = [m for m in mod_names_raw if isinstance(m, str)]

    n = max(len(mod_ids), len(mod_names))
    for i in range(n):
        wid_raw = mod_ids[i] if i < len(mod_ids) else None
        name_raw = mod_names[i] if i < len(mod_names) else None
        wid = _sanitize_text(wid_raw)
        name = _sanitize_text(name_raw)
        if wid is None and name is None:
            continue
        mod_rows.append({
            "snapshot_date": snapshot_date,
            "server_id": server_id,
            "source": "battlemetrics",
            "mod_name": (name or f"id:{wid}")[:1000],  # cap excessively long names
            "workshop_id": wid if wid else None,
            "raw_mod_string": _sanitize_text(name or wid) or "?",
        })

    return snap_row, mod_rows
