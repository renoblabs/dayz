"""
KB read-only routes for the dashboard. Proxies the platform/dayz-stack KB
postgres (port 5436) over a separate async engine.

Three endpoints:
  GET /api/v1/kb/sources?type=&page=
  GET /api/v1/kb/search?q=&limit=
  GET /api/v1/kb/source/<id>

DATA NOTES:
  All routes return REAL data when the KB postgres is reachable. If the engine
  isn't configured (KB_DATABASE_URL unset) or the connection fails, every route
  returns an empty-shape response with `kb_available: false` so the dashboard
  can render a graceful "KB offline" state without erroring.

  Search is BM25-only at the FastAPI layer (uses `text_tsv` GIN index). The
  full hybrid (BM25 + vector RRF) lives in dayzstack_kb.search and is exposed
  via the dayz-kb MCP — not here. Reason: replicating the embedding pipeline
  inside this backend is out of scope; BM25 alone is sufficient for the
  dashboard's "browse and skim" use case.
"""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.kb_database import get_kb_db

router = APIRouter(prefix="/api/v1/kb", tags=["kb"])

# Allowed source_type filter values (mirrors the CHECK constraint on sources)
_ALLOWED_TYPES = {
    "bistudio_wiki",
    "yadz_docs",
    "github_mod_file",
    "youtube_transcript",
    "community_doc",
    "manual",
    "local_repo",
}


def _empty_kb_response(extra: dict | None = None) -> dict:
    out = {"kb_available": False, "items": [], "total": 0}
    if extra:
        out.update(extra)
    return out


# ── /kb/sources ───────────────────────────────────────────────────────────────


@router.get("/sources", summary="List KB sources, paginated, optional type filter")
async def list_sources(
    type: Optional[str] = Query(None, description="Filter by source_type"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    kb: Optional[AsyncSession] = Depends(get_kb_db),
) -> dict:
    if kb is None:
        return _empty_kb_response({"page": page, "page_size": page_size})

    if type is not None and type not in _ALLOWED_TYPES:
        raise HTTPException(400, f"unknown source_type '{type}'. Allowed: {sorted(_ALLOWED_TYPES)}")

    where = ""
    params: dict = {"limit": page_size, "offset": (page - 1) * page_size}
    if type is not None:
        where = "WHERE source_type = :stype"
        params["stype"] = type

    rows = (
        await kb.execute(
            text(
                f"""
                SELECT id, url, source_type, title, fetched_at,
                       jsonb_extract_path_text(metadata, 'rel_path') AS rel_path,
                       jsonb_extract_path_text(metadata, 'sub_kind') AS sub_kind,
                       length(cleaned_text) AS text_len
                FROM public.sources
                {where}
                ORDER BY fetched_at DESC
                LIMIT :limit OFFSET :offset
                """
            ),
            params,
        )
    ).all()

    total = (
        await kb.execute(
            text(f"SELECT COUNT(*) FROM public.sources {where}"),
            {k: v for k, v in params.items() if k == "stype"} if type else {},
        )
    ).scalar_one()

    return {
        "kb_available": True,
        "page":         page,
        "page_size":    page_size,
        "total":        total,
        "items": [
            {
                "id":          str(r.id),
                "url":         r.url,
                "source_type": r.source_type,
                "title":       r.title,
                "rel_path":    r.rel_path,
                "sub_kind":    r.sub_kind,
                "text_len":    r.text_len,
                "fetched_at":  r.fetched_at.isoformat() if r.fetched_at else None,
            }
            for r in rows
        ],
    }


# ── /kb/search ────────────────────────────────────────────────────────────────


@router.get("/search", summary="BM25 keyword search over chunks")
async def search_kb(
    q: str = Query(..., min_length=1, max_length=200),
    limit: int = Query(15, ge=1, le=50),
    kb: Optional[AsyncSession] = Depends(get_kb_db),
) -> dict:
    """
    BM25 ranking over the `chunks.text_tsv` generated tsvector index.
    Returns top-N hits with surrounding source attribution.
    """
    if kb is None:
        return _empty_kb_response({"query": q})

    # plainto_tsquery for forgiving query parsing (no operator syntax surprises)
    rows = (
        await kb.execute(
            text(
                """
                SELECT
                    c.id          AS chunk_id,
                    c.source_id   AS source_id,
                    c.chunk_index AS chunk_index,
                    c.text        AS text,
                    c.metadata    AS chunk_metadata,
                    s.url         AS source_url,
                    s.source_type AS source_type,
                    s.title       AS title,
                    ts_rank_cd(c.text_tsv, plainto_tsquery('english', :q)) AS score
                FROM public.chunks c
                JOIN public.sources s ON s.id = c.source_id
                WHERE c.text_tsv @@ plainto_tsquery('english', :q)
                ORDER BY score DESC, c.source_id, c.chunk_index
                LIMIT :limit
                """
            ),
            {"q": q, "limit": limit},
        )
    ).all()

    return {
        "kb_available": True,
        "query":        q,
        "limit":        limit,
        "items": [
            {
                "chunk_id":    str(r.chunk_id),
                "source_id":   str(r.source_id),
                "chunk_index": r.chunk_index,
                "snippet":     (r.text[:600] + "…") if len(r.text) > 600 else r.text,
                "source_url":  r.source_url,
                "source_type": r.source_type,
                "title":       r.title,
                "score":       float(r.score) if r.score is not None else 0.0,
            }
            for r in rows
        ],
    }


# ── /kb/source/<id> ───────────────────────────────────────────────────────────


@router.get("/source/{source_id}", summary="Single source with all chunks")
async def get_source(
    source_id: str,
    kb: Optional[AsyncSession] = Depends(get_kb_db),
) -> dict:
    if kb is None:
        return {"kb_available": False, "source": None, "chunks": []}

    try:
        sid = uuid.UUID(source_id)
    except ValueError:
        raise HTTPException(400, f"source_id is not a valid UUID: {source_id}")

    src_row = (
        await kb.execute(
            text(
                """
                SELECT id, url, source_type, title, fetched_at, content_hash,
                       length(raw_text) AS raw_len, length(cleaned_text) AS cleaned_len,
                       metadata
                FROM public.sources
                WHERE id = :sid
                """
            ),
            {"sid": sid},
        )
    ).first()

    if src_row is None:
        raise HTTPException(404, f"source not found: {source_id}")

    chunk_rows = (
        await kb.execute(
            text(
                """
                SELECT id, chunk_index, text, metadata,
                       (embedding IS NOT NULL) AS has_embedding
                FROM public.chunks
                WHERE source_id = :sid
                ORDER BY chunk_index
                """
            ),
            {"sid": sid},
        )
    ).all()

    return {
        "kb_available": True,
        "source": {
            "id":          str(src_row.id),
            "url":         src_row.url,
            "source_type": src_row.source_type,
            "title":       src_row.title,
            "fetched_at":  src_row.fetched_at.isoformat() if src_row.fetched_at else None,
            "content_hash": src_row.content_hash,
            "raw_len":     src_row.raw_len,
            "cleaned_len": src_row.cleaned_len,
            "metadata":    src_row.metadata,
        },
        "chunks": [
            {
                "id":            str(c.id),
                "chunk_index":   c.chunk_index,
                "text":          c.text,
                "metadata":      c.metadata,
                "has_embedding": c.has_embedding,
            }
            for c in chunk_rows
        ],
        "chunk_count": len(chunk_rows),
    }
