"""Ingest pipeline — fetch sources, dedupe via content_hash, chunk, embed, persist.

The ingest worker is the "rails" all scrapers run on. Scrapers produce
FetchedSource; this module persists + chunks + embeds.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from dayzstack_shared.db import session_scope
from dayzstack_shared.logging import get_logger

from .chunking import chunk_source
from .embeddings import embed_batch
from .models import Chunk, ScrapeRun, Source
from .scrapers.base import FetchedSource

log = get_logger(__name__)


async def _persist_source(session: AsyncSession, fetched: FetchedSource) -> tuple[Source, bool]:
    """Insert source if (url, content_hash) is new; return (Source, was_new)."""
    existing = await session.scalar(
        select(Source).where(
            Source.url == fetched.url,
            Source.content_hash == fetched.content_hash,
        )
    )
    if existing is not None:
        return existing, False

    src = Source(
        url=fetched.url,
        source_type=fetched.source_type,
        title=fetched.title,
        raw_text=fetched.raw_text,
        cleaned_text=fetched.cleaned_text,
        metadata_=fetched.metadata,
        content_hash=fetched.content_hash,
    )
    session.add(src)
    await session.flush()
    return src, True


async def _chunk_and_persist(session: AsyncSession, source: Source) -> int:
    """Chunk + persist (without embeddings — those come in a second pass)."""
    suffix = source.metadata_.get("file_suffix") if source.metadata_ else None
    chunks = chunk_source(source.cleaned_text, source.metadata_ or {}, file_suffix=suffix)

    for idx, c in enumerate(chunks):
        session.add(
            Chunk(
                source_id=source.id,
                chunk_index=idx,
                text_=c.text,
                metadata_=c.metadata,
                embedding=None,  # Filled in pass 2
            )
        )
    await session.flush()
    return len(chunks)


async def ingest_sources(sources: list[FetchedSource], scraper_type: str) -> dict:
    """Bulk-ingest a list of FetchedSources. Returns counts dict."""
    sources_added = 0
    sources_seen = 0
    chunks_added = 0
    error: str | None = None

    async with session_scope() as session:
        run = ScrapeRun(scraper_type=scraper_type, status="running")
        session.add(run)
        await session.flush()
        run_id = run.id

    try:
        for fetched in sources:
            async with session_scope() as session:
                src, was_new = await _persist_source(session, fetched)
                sources_seen += 1
                if was_new:
                    sources_added += 1
                    n = await _chunk_and_persist(session, src)
                    chunks_added += n
                    log.info("ingest.persisted", url=fetched.url, chunks=n)
                else:
                    log.debug("ingest.duplicate", url=fetched.url)
    except Exception as e:
        error = repr(e)
        log.error("ingest.failed", error=error)

    async with session_scope() as session:
        await session.execute(
            update(ScrapeRun)
            .where(ScrapeRun.id == run_id)
            .values(
                finished_at=datetime.now(timezone.utc),
                status="succeeded" if error is None else ("partial" if sources_added > 0 else "failed"),
                sources_added=sources_added,
                sources_updated=sources_seen - sources_added,
                chunks_added=chunks_added,
                error_message=error,
            )
        )

    return {
        "sources_added": sources_added,
        "sources_skipped_duplicates": sources_seen - sources_added,
        "chunks_added": chunks_added,
        "error": error,
    }


async def fill_missing_embeddings(batch_size: int = 32) -> int:
    """Find chunks without embeddings, batch-compute, write back. Returns count filled."""
    total_filled = 0
    while True:
        async with session_scope() as session:
            rows = (
                await session.execute(
                    select(Chunk.id, Chunk.text_)
                    .where(Chunk.embedding.is_(None))
                    .limit(batch_size)
                )
            ).all()

        if not rows:
            break

        ids = [r[0] for r in rows]
        texts = [r[1] for r in rows]

        try:
            vecs = await embed_batch(texts)
        except Exception as e:
            log.error("embed.batch_failed", error=repr(e), batch_size=len(texts))
            break

        async with session_scope() as session:
            for chunk_id, vec in zip(ids, vecs, strict=True):
                await session.execute(
                    update(Chunk).where(Chunk.id == chunk_id).values(embedding=vec)
                )
        total_filled += len(rows)
        log.info("embed.batch_filled", count=len(rows), total=total_filled)

    return total_filled
