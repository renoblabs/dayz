"""dayz-stack-intel CLI — snapshot, stats."""

from __future__ import annotations

import asyncio
import json
import sys

import click

from dayzstack_shared.logging import setup_logging


@click.group()
def main() -> None:
    """dayz-stack intel tools."""
    setup_logging()


@main.command("snapshot")
@click.option("--query", "query_type", type=click.Choice(["trend", "recent", "votes", "updated"]), default=None)
@click.option("--all", "all_queries", is_flag=True, help="Run all four query types in sequence")
@click.option("--max-pages", default=10, help="Max pages per query (numperpage=100)")
def snapshot(query_type: str | None, all_queries: bool, max_pages: int) -> None:
    """Fetch a workshop snapshot and persist to intel.workshop_snapshots."""
    from .snapshotter import run_all, run_snapshot

    if all_queries == bool(query_type):  # both or neither
        click.echo("Specify exactly one of --query or --all", err=True)
        sys.exit(2)

    async def _run() -> None:
        if all_queries:
            counts = await run_all(max_pages=max_pages)
            click.echo(json.dumps(counts, indent=2))
        else:
            assert query_type is not None
            n = await run_snapshot(query_type, max_pages=max_pages)
            click.echo(json.dumps({query_type: n}, indent=2))

    try:
        asyncio.run(_run())
    except Exception as e:
        click.echo(f"snapshot failed: {e}", err=True)
        sys.exit(1)


@main.command("snapshot-servers")
@click.option("--source", type=click.Choice(["battlemetrics"]), default="battlemetrics")
@click.option("--max-servers", default=200, help="How many top servers to capture")
def snapshot_servers(source: str, max_servers: int) -> None:
    """Snapshot top DayZ servers + their mod fingerprints."""
    from .server_snapshotter import snapshot_battlemetrics

    async def _run() -> None:
        if source == "battlemetrics":
            result = await snapshot_battlemetrics(max_servers=max_servers)
        else:
            raise click.ClickException(f"unknown source: {source}")
        click.echo(json.dumps(result, indent=2))

    try:
        asyncio.run(_run())
    except Exception as e:
        click.echo(f"server snapshot failed: {e}", err=True)
        sys.exit(1)


@main.command("stats")
def stats() -> None:
    """Print row count per snapshot_date / query_type for sanity."""
    from sqlalchemy import func, select

    from dayzstack_shared.db import session_scope

    from .models import WorkshopSnapshot

    async def _run() -> None:
        async with session_scope() as session:
            rows = (
                await session.execute(
                    select(
                        WorkshopSnapshot.snapshot_date,
                        WorkshopSnapshot.query_type,
                        func.count().label("n"),
                    )
                    .group_by(WorkshopSnapshot.snapshot_date, WorkshopSnapshot.query_type)
                    .order_by(WorkshopSnapshot.snapshot_date.desc(), WorkshopSnapshot.query_type)
                )
            ).all()
        if not rows:
            click.echo("(no snapshots yet)")
            return
        click.echo(f"{'date':<12} {'query':<10} {'count':>8}")
        for r in rows:
            click.echo(f"{str(r.snapshot_date):<12} {r.query_type:<10} {r.n:>8}")

    asyncio.run(_run())


if __name__ == "__main__":
    main()
