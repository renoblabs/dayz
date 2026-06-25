"""Snapshotter — fetch Steam Workshop ranked queries, persist to intel.workshop_snapshots.

Idempotency: each (snapshot_date, query_type, workshop_id) is recorded once per day.
Re-running the snapshotter on the same calendar day will skip already-captured rows.
"""

from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import select, func
from sqlalchemy.dialects.postgresql import insert as pg_insert

from dayzstack_shared.db import session_scope
from dayzstack_shared.logging import get_logger

from .models import WorkshopSnapshot
from .steam import SteamQueryConfig, get_api_key, query_files

log = get_logger(__name__)


def _parse_steam_ts(value: int | str | None) -> datetime | None:
    """Steam returns Unix epoch seconds for created/updated."""
    if value is None or value == 0 or value == "0":
        return None
    try:
        return datetime.fromtimestamp(int(value), tz=timezone.utc)
    except (TypeError, ValueError):
        return None


def _coerce_int(value) -> int | None:
    """Steam returns numeric fields as either int or str — coerce or drop."""
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _row_from_item(snapshot_date: date, query_type: str, item: dict) -> dict:
    """Map one Steam publishedfiledetails item to a workshop_snapshots row."""
    return {
        "snapshot_date": snapshot_date,
        "query_type": query_type,
        "workshop_id": str(item.get("publishedfileid", "")),
        "title": item.get("title") or "(untitled)",
        "author_id": str(item.get("creator")) if item.get("creator") else None,
        "author_name": item.get("creator_appid_name") or item.get("creator_name"),
        "subscriptions": _coerce_int(item.get("lifetime_subscriptions")),
        "favorites": _coerce_int(item.get("lifetime_favorited")),
        "views": _coerce_int(item.get("views")),
        "file_size": _coerce_int(item.get("file_size")),
        "tags": [t.get("tag") for t in item.get("tags", []) if t.get("tag")],
        # Model attrs are *_ts to avoid clash with the captured_at semantics; DB column names are still "created_at"/"updated_at"
        "created_at_ts": _parse_steam_ts(item.get("time_created")),
        "updated_at_ts": _parse_steam_ts(item.get("time_updated")),
        "rank_in_query": item.get("_rank_in_query"),
        "raw_response": item,
    }


async def run_snapshot(query_type: str, max_pages: int = 10) -> int:
    """Fetch a single query_type, persist rows. Returns rows inserted."""
    cfg = SteamQueryConfig(api_key=get_api_key())

    log.info("snapshot.start", query_type=query_type, max_pages=max_pages)
    items = await query_files(cfg, query_type, max_pages=max_pages)
    log.info("snapshot.fetched", query_type=query_type, items=len(items))

    if not items:
        return 0

    today = datetime.now(timezone.utc).date()
    rows = [_row_from_item(today, query_type, item) for item in items]

    inserted = 0
    async with session_scope() as session:
        # Bulk insert; on conflict on the natural key (date+qtype+wid), skip
        for row in rows:
            stmt = (
                pg_insert(WorkshopSnapshot.__table__)
                .values(**row)
                .on_conflict_do_nothing(
                    index_elements=None,
                    constraint=None,
                    # No unique constraint defined yet — we rely on day-level idempotency
                    # by checking if this date+query_type already has rows for this id
                )
            )
            # Manual idempotency check (cheaper than a constraint for this volume)
            existing = await session.scalar(
                select(func.count())
                .select_from(WorkshopSnapshot)
                .where(
                    WorkshopSnapshot.snapshot_date == row["snapshot_date"],
                    WorkshopSnapshot.query_type == row["query_type"],
                    WorkshopSnapshot.workshop_id == row["workshop_id"],
                )
            )
            if existing:
                continue
            session.add(WorkshopSnapshot(**row))
            inserted += 1

    log.info("snapshot.persisted", query_type=query_type, inserted=inserted, skipped=len(rows) - inserted)
    return inserted


async def run_all(max_pages: int = 10) -> dict[str, int]:
    """Run all four query types in sequence, returning per-type insert counts."""
    counts: dict[str, int] = {}
    for q in ("trend", "recent", "votes", "updated"):
        try:
            counts[q] = await run_snapshot(q, max_pages=max_pages)
        except Exception as e:
            log.error("snapshot.failed", query_type=q, error=repr(e))
            counts[q] = -1
    return counts
