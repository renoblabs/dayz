"""dayz-stack-kb CLI — ingest, search, embed-fill, status."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import click

from dayzstack_shared.config import get_settings
from dayzstack_shared.logging import get_logger, setup_logging

log = get_logger(__name__)


@click.group()
def main() -> None:
    """dayz-stack KB tools."""
    setup_logging()


# ── ingest-local ─────────────────────────────────────────────────────────────
@main.command("ingest-local")
@click.option(
    "--repo",
    "repo_path",
    default=None,
    help="Path to local repo (default: settings.dayzapi_root)",
)
def ingest_local(repo_path: str | None) -> None:
    """Cold-start ingest from a sibling local repo (e.g. dayzAPI)."""
    from .ingest import ingest_sources
    from .scrapers.local_repo import collect_all

    settings = get_settings()
    root = Path(repo_path) if repo_path else Path(settings.dayzapi_root)

    async def _run() -> None:
        click.echo(f"[ingest-local] scanning {root.resolve()}…")
        sources = await collect_all(root)
        click.echo(f"[ingest-local] discovered {len(sources)} sources")
        if not sources:
            click.echo("nothing to ingest")
            return
        result = await ingest_sources(sources, scraper_type="local_repo")
        click.echo(json.dumps(result, indent=2))
        click.echo("[ingest-local] done. Run `dayz-stack-kb embed-fill` to populate embeddings.")

    asyncio.run(_run())


# ── ingest-bistudio ──────────────────────────────────────────────────────────
@main.command("ingest-bistudio")
@click.option("--max-pages", default=None, type=int, help="Cap number of wiki pages (testing)")
@click.option("--cache-dir", default=None)
def ingest_bistudio(max_pages: int | None, cache_dir: str | None) -> None:
    """Scrape DayZ:Modding wiki via MediaWiki API."""
    from .ingest import ingest_sources
    from .scrapers.bistudio_wiki import collect_all

    async def _run() -> None:
        cd = Path(cache_dir) if cache_dir else None
        click.echo(f"[ingest-bistudio] crawling DayZ:Modding (max_pages={max_pages or 'unlimited'})…")
        sources = await collect_all(cd, max_pages)
        click.echo(f"[ingest-bistudio] discovered {len(sources)} pages")
        if not sources:
            click.echo("nothing fetched (check network / API access)")
            return
        result = await ingest_sources(sources, scraper_type="bistudio_wiki")
        click.echo(json.dumps(result, indent=2))

    asyncio.run(_run())


# ── ingest-github-mods ───────────────────────────────────────────────────────
@main.command("ingest-github-mods")
@click.option("--cache-dir", default=None)
def ingest_github_mods(cache_dir: str | None) -> None:
    """Clone curated DayZ mod repos and ingest their source files."""
    from .ingest import ingest_sources
    from .scrapers.github_mods import collect_all

    async def _run() -> None:
        cd = Path(cache_dir) if cache_dir else None
        click.echo("[ingest-github-mods] cloning + walking curated mod repos…")
        sources = await collect_all(cd)
        click.echo(f"[ingest-github-mods] discovered {len(sources)} files")
        if not sources:
            click.echo("nothing fetched (check git availability + network)")
            return
        result = await ingest_sources(sources, scraper_type="github_mod_file")
        click.echo(json.dumps(result, indent=2))

    asyncio.run(_run())


# ── ingest-workshop ──────────────────────────────────────────────────────────
@main.command("ingest-workshop")
@click.option("--workshop-root", default=None, help="Steam workshop content/221100 dir")
@click.option("--mod-id", "mod_ids", multiple=True, type=int, help="Specific workshop mod IDs (default: known)")
def ingest_workshop(workshop_root: str | None, mod_ids: tuple[int, ...]) -> None:
    """Ingest source from locally-installed Steam Workshop mods (CF, etc.)."""
    from .ingest import ingest_sources
    from .scrapers.workshop_local import collect_all

    async def _run() -> None:
        root = Path(workshop_root) if workshop_root else None
        sources = await collect_all(root, list(mod_ids) or None)
        click.echo(f"[ingest-workshop] discovered {len(sources)} sources")
        if not sources:
            click.echo("nothing to ingest (no known mods present?)")
            return
        result = await ingest_sources(sources, scraper_type="workshop_local")
        click.echo(json.dumps(result, indent=2))

    asyncio.run(_run())


# ── embed-fill ───────────────────────────────────────────────────────────────
@main.command("embed-fill")
@click.option("--batch-size", default=32)
def embed_fill(batch_size: int) -> None:
    """Compute embeddings for any chunks missing them."""
    from .ingest import fill_missing_embeddings

    async def _run() -> None:
        n = await fill_missing_embeddings(batch_size=batch_size)
        click.echo(f"[embed-fill] populated {n} chunk embeddings")

    asyncio.run(_run())


# ── search ───────────────────────────────────────────────────────────────────
@main.command("search")
@click.argument("query")
@click.option("--limit", default=8)
@click.option("--source-type", "source_types", multiple=True, help="Filter source_type (repeatable)")
@click.option("--full", is_flag=True, help="Print full chunk text, not just snippet")
def search(query: str, limit: int, source_types: tuple[str, ...], full: bool) -> None:
    """Hybrid search the KB."""
    from .search import hybrid_search

    async def _run() -> None:
        hits = await hybrid_search(query, limit=limit, source_type_filter=list(source_types) or None)
        if not hits:
            click.echo("no hits")
            return
        for i, h in enumerate(hits, start=1):
            click.echo(f"\n#{i}  [{h.source_type}]  {h.title or '(no title)'}")
            click.echo(f"      score={h.score:.4f}  bm25={h.bm25_rank}  vec={h.vector_rank}")
            click.echo(f"      url: {h.source_url}")
            if full:
                click.echo(f"      ---\n{h.snippet}\n      ---")
            else:
                click.echo(f"      {h.snippet}")

    asyncio.run(_run())


# ── status ───────────────────────────────────────────────────────────────────
@main.command("status")
def status() -> None:
    """Print row counts + recent scrape runs + embedding health."""
    from sqlalchemy import func, select

    from dayzstack_shared.db import session_scope

    from .embeddings import health_check
    from .models import Chunk, ScrapeRun, Source

    async def _run() -> None:
        async with session_scope() as session:
            n_sources = await session.scalar(select(func.count()).select_from(Source))
            n_chunks = await session.scalar(select(func.count()).select_from(Chunk))
            n_unembed = await session.scalar(
                select(func.count()).select_from(Chunk).where(Chunk.embedding.is_(None))
            )
            recent_runs = (
                await session.execute(
                    select(ScrapeRun).order_by(ScrapeRun.started_at.desc()).limit(5)
                )
            ).scalars().all()

        click.echo(f"sources:       {n_sources}")
        click.echo(f"chunks:        {n_chunks}")
        click.echo(f"  unembedded:  {n_unembed}")
        click.echo("\nrecent scrape runs:")
        for r in recent_runs:
            click.echo(
                f"  {r.started_at.strftime('%Y-%m-%d %H:%M')}  "
                f"{r.scraper_type:<14} {r.status:<10} +{r.sources_added}src +{r.chunks_added}chunks"
            )

        click.echo("\nollama:")
        h = await health_check()
        click.echo(json.dumps(h, indent=2))

    asyncio.run(_run())


if __name__ == "__main__":
    main()
