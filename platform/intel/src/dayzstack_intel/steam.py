"""Steam Web API client — IPublishedFileService/QueryFiles for DayZ workshop.

Steam's QueryFiles is the canonical endpoint for ranked workshop content.
Verified field names + query type integers against the Steam Web API docs.

DayZ appid is 221100. Each query type returns ranked items.
"""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from typing import Any

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

DAYZ_APPID = 221100
QUERYFILES_URL = "https://api.steampowered.com/IPublishedFileService/QueryFiles/v1/"

# Steam query type integers — see EPublishedFileQueryType in steamworks docs
QUERY_TYPE_INTS: dict[str, int] = {
    "votes": 0,         # RankedByVote
    "recent": 1,        # RankedByPublicationDate
    "trend": 12,        # RankedByTrend (uses days param)
    "updated": 21,      # RankedByLastUpdatedDate
}


@dataclass(slots=True)
class SteamQueryConfig:
    api_key: str
    appid: int = DAYZ_APPID
    numperpage: int = 100
    days_for_trend: int = 7
    sleep_between_pages_s: float = 0.5
    timeout_s: float = 30.0


class SteamApiError(Exception):
    """Raised when the Steam API returns a non-200 or unparseable response."""


def get_api_key() -> str:
    """Read STEAM_API_KEY from env. Raises if absent — caller decides how to surface."""
    key = os.environ.get("STEAM_API_KEY")
    if not key:
        raise SteamApiError(
            "STEAM_API_KEY not in env. Add it to Doppler under the dayz-stack project, "
            "OR export STEAM_API_KEY=<your key> before running. "
            "Get a free key at https://steamcommunity.com/dev/apikey"
        )
    return key


@retry(
    retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.TimeoutException, SteamApiError)),
    stop=stop_after_attempt(4),
    wait=wait_exponential(min=2, max=30),
    reraise=True,
)
async def _query_page(client: httpx.AsyncClient, params: dict[str, Any]) -> dict:
    """Single QueryFiles page. Retries on 5xx / timeout / 429."""
    resp = await client.get(QUERYFILES_URL, params=params, timeout=30.0)
    if resp.status_code == 429:
        # Be nice to Steam — back off
        raise SteamApiError(f"429 from Steam, will back off: {resp.text[:200]}")
    resp.raise_for_status()
    body = resp.json()
    if "response" not in body:
        raise SteamApiError(f"unexpected Steam response shape: {body}")
    return body["response"]


async def query_files(
    cfg: SteamQueryConfig,
    query_type: str,
    max_pages: int = 10,
) -> list[dict]:
    """Fetch up to max_pages × numperpage workshop items for one query_type.

    Returns a flat list of `publishedfiledetails` dicts in API rank order
    across all pages.
    """
    if query_type not in QUERY_TYPE_INTS:
        raise ValueError(f"unknown query_type {query_type!r}; allowed: {list(QUERY_TYPE_INTS)}")

    base_params: dict[str, Any] = {
        "key": cfg.api_key,
        "appid": cfg.appid,
        "numperpage": cfg.numperpage,
        "query_type": QUERY_TYPE_INTS[query_type],
        "return_metadata": "true",
        "return_tags": "true",
        "return_details": "true",
        "return_short_description": "true",
        "return_vote_data": "true",
        "match_all_tags": "false",
    }
    if query_type == "trend":
        base_params["days"] = cfg.days_for_trend

    items: list[dict] = []
    cursor: str = "*"  # initial cursor

    async with httpx.AsyncClient() as client:
        for page_idx in range(max_pages):
            params = dict(base_params)
            params["cursor"] = cursor

            page = await _query_page(client, params)
            details = page.get("publishedfiledetails") or []
            next_cursor = page.get("next_cursor") or ""

            for rank_in_page, item in enumerate(details):
                # Annotate with absolute rank across pages
                item["_rank_in_query"] = page_idx * cfg.numperpage + rank_in_page
                items.append(item)

            if not details or not next_cursor or next_cursor == cursor:
                break

            cursor = next_cursor
            await asyncio.sleep(cfg.sleep_between_pages_s)

    return items
