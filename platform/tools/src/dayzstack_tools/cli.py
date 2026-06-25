"""dayz-stack CLI — operator-facing stack reports."""

from __future__ import annotations

import asyncio
import os
import sys
from collections import defaultdict
from datetime import date, datetime, timezone

import click
from sqlalchemy import text

from dayzstack_shared.db import session_scope
from dayzstack_shared.logging import setup_logging


STALE_DAYS = 180  # workshop "last updated" threshold for stale-flag


@click.group()
def main() -> None:
    """dayz-stack operator tools."""
    setup_logging()


# ── helpers ──────────────────────────────────────────────────────────────────


async def _latest_snapshot_date() -> date | None:
    async with session_scope() as session:
        row = (await session.execute(
            text("SELECT MAX(snapshot_date) FROM intel.server_snapshots")
        )).scalar_one()
    return row


async def _find_servers(pattern: str, snap_date: date | None = None) -> list[dict]:
    """Resolve a name pattern (case-insensitive substring) to matching servers.

    If snap_date is None, finds the most recent snapshot that has a match for
    the pattern (per server) — top-200 churns day-over-day, so a server may not
    be in literally the latest capture.
    """
    async with session_scope() as session:
        if snap_date is not None:
            rows = (await session.execute(
                text("""
                    SELECT server_id, server_name, player_count, max_players,
                           rank_in_source, snapshot_date
                    FROM intel.server_snapshots
                    WHERE snapshot_date = :d AND server_name ILIKE :p
                    ORDER BY player_count DESC NULLS LAST
                """),
                {"d": snap_date, "p": f"%{pattern}%"},
            )).mappings().all()
        else:
            rows = (await session.execute(
                text("""
                    SELECT DISTINCT ON (server_id)
                        server_id, server_name, player_count, max_players,
                        rank_in_source, snapshot_date
                    FROM intel.server_snapshots
                    WHERE server_name ILIKE :p
                    ORDER BY server_id, snapshot_date DESC
                """),
                {"p": f"%{pattern}%"},
            )).mappings().all()
    return [dict(r) for r in rows]


async def _server_mods(server_id: str, snap_date: date) -> list[dict]:
    """Get all mods on a server at a snapshot."""
    async with session_scope() as session:
        rows = (await session.execute(
            text("""
                SELECT mod_name, workshop_id, raw_mod_string
                FROM intel.server_mods
                WHERE server_id = :s AND snapshot_date = :d
                ORDER BY mod_name
            """),
            {"s": server_id, "d": snap_date},
        )).mappings().all()
    return [dict(r) for r in rows]


async def _global_deployment(snap_date: date) -> dict[str, int]:
    """workshop_id → server count across the snapshot."""
    async with session_scope() as session:
        rows = (await session.execute(
            text("""
                SELECT workshop_id, COUNT(DISTINCT server_id) AS n
                FROM intel.server_mods
                WHERE snapshot_date = :d AND workshop_id IS NOT NULL
                GROUP BY workshop_id
            """),
            {"d": snap_date},
        )).all()
    return {r[0]: r[1] for r in rows}


async def _workshop_meta(workshop_ids: list[str]) -> dict[str, dict]:
    """Latest workshop snapshot row per workshop_id (title, updated_at, subs)."""
    if not workshop_ids:
        return {}
    async with session_scope() as session:
        rows = (await session.execute(
            text("""
                SELECT DISTINCT ON (workshop_id)
                    workshop_id, title, subscriptions, updated_at, created_at
                FROM intel.workshop_snapshots
                WHERE workshop_id = ANY(:ids)
                ORDER BY workshop_id, snapshot_date DESC
            """),
            {"ids": workshop_ids},
        )).mappings().all()
    return {r["workshop_id"]: dict(r) for r in rows}


def _days_since(d: datetime | None) -> int | None:
    if d is None:
        return None
    if d.tzinfo is None:
        d = d.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - d).days


def _pick_one_server(servers: list[dict], pattern: str) -> dict | None:
    """If exactly one match, return it. Otherwise show options and return None."""
    if not servers:
        click.echo(f"No server in latest snapshot matched '{pattern}'.", err=True)
        return None
    if len(servers) == 1:
        return servers[0]
    click.echo(f"{len(servers)} servers matched '{pattern}'. Be more specific:", err=True)
    for s in servers[:10]:
        click.echo(f"  [{s['player_count']:>3} pop] {s['server_name'][:80]}", err=True)
    if len(servers) > 10:
        click.echo(f"  ... and {len(servers) - 10} more", err=True)
    return None


# ── command: health ──────────────────────────────────────────────────────────


@main.command("health")
@click.argument("pattern")
def health(pattern: str) -> None:
    """Single-server stack health check.

    Usage: dayz-stack health "<substring of server name>"

    Reports against the latest intel snapshot:
      - Top deployed mods present (rank in our top-200 dataset)
      - Stale mods (workshop last-updated > 180 days ago)
      - Rare mods (deployed on <5 servers, may be bespoke)
      - Framework footprint (CF, Dabs, Expansion-Core)
    """
    asyncio.run(_health(pattern))


async def _health(pattern: str) -> None:
    snap = await _latest_snapshot_date()
    if snap is None:
        click.echo("No server snapshots found. Run `dayz-stack-intel snapshot-servers` first.", err=True)
        sys.exit(1)

    # Resolve server across all snapshots (top-200 churns day-over-day)
    matches = await _find_servers(pattern, snap_date=None)
    server = _pick_one_server(matches, pattern)
    if server is None:
        sys.exit(1)

    server_snap_date = server.get("snapshot_date") or snap
    mods = await _server_mods(server["server_id"], server_snap_date)
    if not mods:
        click.echo(f"Server matched but no mod data captured for {server_snap_date}.")
        return

    # Global-deployment baseline always uses the latest snapshot for ranking
    global_dep = await _global_deployment(snap)
    workshop_ids = [m["workshop_id"] for m in mods if m["workshop_id"]]
    ws_meta = await _workshop_meta(workshop_ids)

    # Header
    click.echo("-" * 72)
    click.echo(f"  {server['server_name']}")
    click.echo(f"  pop {server['player_count']}/{server['max_players']}  "
               f"rank #{server['rank_in_source']} in top-populated  "
               f"snapshot {server_snap_date}")
    click.echo("-" * 72)
    click.echo(f"  {len(mods)} mods total  "
               f"({sum(1 for m in mods if m['workshop_id'])} matched to workshop ids)")
    click.echo()

    # Framework footprint
    fwk = {
        "1559212036": "Community Framework",
        "2545327648": "Dabs Framework",
        "2291785308": "DayZ-Expansion-Core",
    }
    present_fwk = [name for wid, name in fwk.items() if any(m["workshop_id"] == wid for m in mods)]
    if present_fwk:
        click.echo(f"  Frameworks: {', '.join(present_fwk)}")
    else:
        click.echo("  Frameworks: (none of CF / Dabs / Expansion-Core present)")
    click.echo()

    # Top deployed mods present (sorted by global rank)
    ranked = sorted(
        [(m, global_dep.get(m["workshop_id"], 0)) for m in mods if m["workshop_id"]],
        key=lambda x: -x[1],
    )
    click.echo(f"  Top deployed mods present (rank by deployment in top-200 sample):")
    for m, n in ranked[:8]:
        title = (ws_meta.get(m["workshop_id"], {}).get("title") or m["mod_name"])[:46]
        click.echo(f"    {n:>3} servers  {title}")
    if len(ranked) > 8:
        click.echo(f"    ... and {len(ranked) - 8} more")
    click.echo()

    # Stale flag
    stale = []
    for m in mods:
        wid = m["workshop_id"]
        if not wid:
            continue
        meta = ws_meta.get(wid)
        if not meta:
            continue
        age = _days_since(meta.get("updated_at"))
        if age is not None and age > STALE_DAYS:
            stale.append((meta.get("title") or m["mod_name"], age, global_dep.get(wid, 0)))
    if stale:
        click.echo(f"  Stale flag (workshop last-updated > {STALE_DAYS} days ago):")
        for title, age, n in sorted(stale, key=lambda x: -x[1])[:6]:
            click.echo(f"    {age:>4}d stale  on {n} top-200 servers - {title[:50]}")
        click.echo("    (note: Steam Web API last-updated; sample limited to top-1k pages we pulled)")
    else:
        click.echo("  Stale flag: nothing flagged (or workshop metadata missing for these mods)")
    click.echo()

    # Rare mods (deployed on <5 servers in top-200)
    rare = [(m, global_dep.get(m["workshop_id"], 0)) for m in mods if m["workshop_id"]]
    rare = [(m, n) for m, n in rare if 0 < n < 5]
    if rare:
        click.echo(f"  Rare/bespoke mods (deployed on <5 of top-200):")
        for m, n in sorted(rare, key=lambda x: x[1])[:8]:
            title = (ws_meta.get(m["workshop_id"], {}).get("title") or m["mod_name"])[:50]
            click.echo(f"    on {n} servers  {title}")
        if len(rare) > 8:
            click.echo(f"    ... and {len(rare) - 8} more")
    click.echo()

    # Caveat footer
    click.echo("  -- caveats --")
    click.echo("  - 'top-200' = Battlemetrics top-populated DayZ servers; biased toward heavy-PvE/quest niches")
    click.echo("  - workshop metadata limited to mods we've pulled (~30% overlap with deployment-only IDs)")
    click.echo("  - one snapshot point - rank/staleness is a single observation, not a trend")
    click.echo()


# ── command: compare ────────────────────────────────────────────────────────


@main.command("compare")
@click.argument("patterns", nargs=-1, required=True)
@click.option("--limit", default=15, help="How many shared/unique mods to show per server")
def compare(patterns: tuple[str, ...], limit: int) -> None:
    """Cross-server stack comparator.

    Usage: dayz-stack compare "<pattern1>" "<pattern2>" [<pattern3> ...]

    For each pattern, picks the highest-pop matching server and compares stacks:
      - Mods shared across ALL servers (the common foundation)
      - Mods unique to each server (the differentiators)
      - Rare-elsewhere mods on each server (low-deployment in top-200)
    """
    if len(patterns) < 2:
        click.echo("compare needs at least two server patterns.", err=True)
        sys.exit(2)
    asyncio.run(_compare(patterns, limit))


async def _compare(patterns: tuple[str, ...], limit: int) -> None:
    snap = await _latest_snapshot_date()
    if snap is None:
        click.echo("No server snapshots found.", err=True)
        sys.exit(1)

    selected: list[dict] = []
    for p in patterns:
        matches = await _find_servers(p, snap_date=None)
        if not matches:
            click.echo(f"No server matched '{p}' across any snapshot.", err=True)
            sys.exit(1)
        # Take the highest-pop match if multiple
        if len(matches) > 1:
            click.echo(f"  '{p}' matched {len(matches)} servers - picking highest-pop", err=True)
        selected.append(matches[0])

    # Fetch mod sets and ranks (each from the snapshot in which the server appeared)
    server_mods: list[set[str]] = []
    server_mods_named: list[dict[str, str]] = []  # workshop_id → mod_name
    for s in selected:
        mods = await _server_mods(s["server_id"], s.get("snapshot_date") or snap)
        wids = {m["workshop_id"] for m in mods if m["workshop_id"]}
        server_mods.append(wids)
        named = {m["workshop_id"]: m["mod_name"] for m in mods if m["workshop_id"]}
        server_mods_named.append(named)

    global_dep = await _global_deployment(snap)
    all_wids = set().union(*server_mods)
    ws_meta = await _workshop_meta(list(all_wids))

    def _title(wid: str, fallback: str) -> str:
        m = ws_meta.get(wid)
        if m and m.get("title"):
            return m["title"]
        return fallback

    # Header
    click.echo("-" * 72)
    click.echo(f"  Comparing {len(selected)} servers (latest snapshot {snap})")
    click.echo("-" * 72)
    for i, s in enumerate(selected):
        click.echo(f"  [{i+1}] pop {s['player_count']:>3}  {len(server_mods[i]):>3} mods   {s['server_name'][:55]}")
    click.echo()

    # Combined mod_name lookup across all servers (fallback for missing workshop meta)
    all_named: dict[str, str] = {}
    for named in server_mods_named:
        for wid, mname in named.items():
            all_named.setdefault(wid, mname)

    # Shared across all
    shared = set.intersection(*server_mods) if server_mods else set()
    click.echo(f"  Shared by all {len(selected)} servers ({len(shared)} mods):")
    shared_ranked = sorted(shared, key=lambda w: -global_dep.get(w, 0))
    for wid in shared_ranked[:limit]:
        n = global_dep.get(wid, 0)
        title = _title(wid, all_named.get(wid, "(unknown)"))[:50]
        click.echo(f"    {n:>3}srv  {title}")
    if len(shared_ranked) > limit:
        click.echo(f"    ... and {len(shared_ranked) - limit} more")
    click.echo()

    # Unique to each
    for i, (s, wids) in enumerate(zip(selected, server_mods, strict=False)):
        others = set().union(*[w for j, w in enumerate(server_mods) if j != i])
        only_here = wids - others
        click.echo(f"  Unique to [{i+1}] '{s['server_name'][:50]}' ({len(only_here)} mods):")
        # Sort by ascending deployment — rarer first (more interesting)
        unique_ranked = sorted(only_here, key=lambda w: global_dep.get(w, 0))
        for wid in unique_ranked[:limit]:
            n = global_dep.get(wid, 0)
            title = _title(wid, server_mods_named[i].get(wid, "(unknown)"))[:50]
            tag = "BESPOKE" if n < 5 else f"{n}srv"
            click.echo(f"    {tag:>7}  {title}")
        if len(unique_ranked) > limit:
            click.echo(f"    ... and {len(unique_ranked) - limit} more")
        click.echo()

    # Caveat footer
    click.echo("  -- caveats --")
    click.echo("  - workshop_id-based comparison; mods returned without IDs aren't compared")
    click.echo("  - 'BESPOKE' flag = on <5 of top-200; not a quality signal, just rarity")
    click.echo("  - one snapshot point per server; stacks change between server restarts")
    click.echo()


# ── command: lessons ─────────────────────────────────────────────────────────

NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://localhost:6703")
# Credentials come from the environment. Set NEO4J_PASSWORD before running;
# the placeholder default below is intentionally non-functional.
NEO4J_AUTH = (
    os.environ.get("NEO4J_USER", "neo4j"),
    os.environ.get("NEO4J_PASSWORD", "<your-neo4j-password>"),
)

# Read-only: this query only MATCHes and RETURNs. The lessons CLI never writes
# to the graph — capture is auto_capture's job, this is pure retrieval.
_LESSONS_CYPHER = """
MATCH (e:DayZError)
WHERE toLower(e.message)            CONTAINS toLower($kw)
   OR toLower(coalesce(e.root_cause, ''))        CONTAINS toLower($kw)
   OR toLower(coalesce(e.error_signature, ''))   CONTAINS toLower($kw)
   OR toLower(coalesce(e.mod_name, ''))          CONTAINS toLower($kw)
   OR toLower(coalesce(e.error_type, ''))        CONTAINS toLower($kw)
OPTIONAL MATCH (s:Solution)-[:SOLVES]->(e)
RETURN e.message            AS message,
       e.root_cause         AS root_cause,
       e.fix_applied        AS fix_applied,
       e.resolution_status  AS status,
       e.resolved           AS resolved,
       e.seen_count         AS seen_count,
       e.troubleshoot_doc   AS doc,
       coalesce(e.timestamp, '') AS ts,
       collect(DISTINCT s.description) AS solutions
ORDER BY ts DESC
LIMIT $limit
"""


@main.command("lessons")
@click.argument("keyword")
@click.option("--limit", default=10, help="Max matching lessons to show")
def lessons(keyword: str, limit: int) -> None:
    """Query the Neo4j memory graph for past errors matching a keyword.

    Usage: dayz-stack lessons "<keyword>"

    Read-only. Returns, for each match: the error, its root cause, the fix
    that worked, resolution status, how many times it's been seen, and a
    link to the troubleshoot doc. This is the retrieval half of the
    capture loop (auto_capture writes; this reads).
    """
    from neo4j import GraphDatabase

    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=NEO4J_AUTH)
        with driver.session() as session:
            rows = list(session.run(_LESSONS_CYPHER, kw=keyword, limit=limit))
        driver.close()
    except Exception as exc:  # noqa: BLE001 - operator CLI, surface the cause plainly
        click.echo(f"Could not query memory graph at {NEO4J_URI}: {exc}", err=True)
        click.echo("Is the dayz-memory-neo4j container up? (docker ps | grep neo4j)", err=True)
        sys.exit(1)

    if not rows:
        click.echo(f"No lessons matched '{keyword}'.")
        return

    click.echo("-" * 72)
    click.echo(f"  {len(rows)} lesson(s) matching '{keyword}'")
    click.echo("-" * 72)
    for r in rows:
        seen = r["seen_count"]
        seen_str = f" (seen {seen}x)" if seen else ""
        status = r["status"] or ("resolved" if r["resolved"] else "open")
        click.echo()
        click.echo(f"  ERROR     {r['message']}{seen_str}")
        click.echo(f"  STATUS    {status}")
        if r["root_cause"]:
            click.echo(f"  CAUSE     {r['root_cause']}")
        fix = r["fix_applied"]
        sols = [s for s in (r["solutions"] or []) if s]
        if fix:
            click.echo(f"  FIX       {fix}")
        for s in sols:
            click.echo(f"  SOLUTION  {s}")
        if not fix and not sols:
            click.echo("  FIX       (none recorded yet)")
        if r["doc"]:
            click.echo(f"  DOC       {r['doc']}")
    click.echo()


# ── entry ───────────────────────────────────────────────────────────────────


if __name__ == "__main__":
    main()
