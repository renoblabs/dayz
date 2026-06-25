"""Server snapshotter — fetch top DayZ servers + their mod fingerprints.

Idempotent per (snapshot_date, source, server_id). Re-running on the same
calendar day skips already-captured rows.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, select

from dayzstack_shared.db import session_scope
from dayzstack_shared.logging import get_logger

from .models import ServerMod, ServerSnapshot
from .sources.battlemetrics import BattlemetricsConfig, fetch_top_dayz_servers, parse_server

log = get_logger(__name__)


async def snapshot_battlemetrics(max_servers: int = 200) -> dict[str, int]:
    """Fetch top max_servers DayZ servers from Battlemetrics, persist rows."""
    cfg = BattlemetricsConfig(max_servers=max_servers)
    log.info("server_snapshot.start", source="battlemetrics", max_servers=max_servers)

    items = await fetch_top_dayz_servers(cfg)
    log.info("server_snapshot.fetched", source="battlemetrics", servers=len(items))

    today = datetime.now(timezone.utc).date()
    server_inserted = 0
    mods_inserted = 0
    server_skipped = 0

    async with session_scope() as session:
        for item in items:
            snap_row, mod_rows = parse_server(item, today)

            # Idempotency: (snapshot_date, source, server_id)
            exists = await session.scalar(
                select(func.count())
                .select_from(ServerSnapshot)
                .where(
                    ServerSnapshot.snapshot_date == snap_row["snapshot_date"],
                    ServerSnapshot.source == snap_row["source"],
                    ServerSnapshot.server_id == snap_row["server_id"],
                )
            )
            if exists:
                server_skipped += 1
                continue

            session.add(ServerSnapshot(**snap_row))
            for mod in mod_rows:
                session.add(ServerMod(**mod))
            server_inserted += 1
            mods_inserted += len(mod_rows)

    log.info(
        "server_snapshot.persisted",
        source="battlemetrics",
        servers=server_inserted,
        mods=mods_inserted,
        skipped_dupes=server_skipped,
    )
    return {
        "source": "battlemetrics",
        "servers_inserted": server_inserted,
        "servers_skipped_duplicates": server_skipped,
        "mods_inserted": mods_inserted,
    }
