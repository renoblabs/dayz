"""Hybrid retrieval — BM25 (Postgres FTS) + vector cosine, fused via RRF.

RRF (Reciprocal Rank Fusion) is robust to score-scale differences between
the two retrievers and consistently outperforms either alone for code search.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import bindparam, text
from sqlalchemy.ext.asyncio import AsyncSession

from dayzstack_shared.db import session_scope

from .embeddings import embed_query


@dataclass(slots=True)
class SearchHit:
    chunk_id: str
    source_id: str
    source_url: str
    source_type: str
    title: str | None
    snippet: str
    chunk_metadata: dict
    score: float
    bm25_rank: int | None
    vector_rank: int | None

    def as_dict(self) -> dict[str, Any]:
        return {
            "chunk_id": str(self.chunk_id),
            "source_id": str(self.source_id),
            "source_url": self.source_url,
            "source_type": self.source_type,
            "title": self.title,
            "snippet": self.snippet,
            "chunk_metadata": self.chunk_metadata,
            "score": self.score,
            "bm25_rank": self.bm25_rank,
            "vector_rank": self.vector_rank,
        }


# How aggressively RRF discounts later ranks. Standard k=60 from the paper.
RRF_K = 60


async def _bm25_search(
    session: AsyncSession,
    query: str,
    limit: int,
    source_type_filter: list[str] | None,
) -> list[tuple[str, str, str, str, str | None, str, dict, float]]:
    """Returns rows of (chunk_id, source_id, url, source_type, title, snippet, metadata, score)."""
    sql = """
    SELECT c.id::text, c.source_id::text, s.url, s.source_type, s.title,
           c.text, c.metadata,
           ts_rank_cd(c.text_tsv, websearch_to_tsquery('english', :q)) AS rank
    FROM chunks c JOIN sources s ON s.id = c.source_id
    WHERE c.text_tsv @@ websearch_to_tsquery('english', :q)
    """
    params: dict[str, Any] = {"q": query, "lim": limit}
    if source_type_filter:
        sql += " AND s.source_type = ANY(:source_types)"
        params["source_types"] = source_type_filter
    sql += " ORDER BY rank DESC LIMIT :lim"

    res = await session.execute(text(sql), params)
    return list(res.fetchall())


async def _vector_search(
    session: AsyncSession,
    query_vec: list[float],
    limit: int,
    source_type_filter: list[str] | None,
) -> list[tuple[str, str, str, str, str | None, str, dict, float]]:
    """Cosine similarity against pgvector HNSW index."""
    sql = """
    SELECT c.id::text, c.source_id::text, s.url, s.source_type, s.title,
           c.text, c.metadata,
           1 - (c.embedding <=> CAST(:qvec AS vector)) AS sim
    FROM chunks c JOIN sources s ON s.id = c.source_id
    WHERE c.embedding IS NOT NULL
    """
    params: dict[str, Any] = {"qvec": str(query_vec), "lim": limit}
    if source_type_filter:
        sql += " AND s.source_type = ANY(:source_types)"
        params["source_types"] = source_type_filter
    sql += " ORDER BY c.embedding <=> CAST(:qvec AS vector) ASC LIMIT :lim"

    res = await session.execute(text(sql), params)
    return list(res.fetchall())


def _make_snippet(text_: str, max_chars: int = 280) -> str:
    text_ = text_.strip()
    if len(text_) <= max_chars:
        return text_
    return text_[:max_chars].rsplit(" ", 1)[0] + "…"


async def hybrid_search(
    query: str,
    limit: int = 8,
    fetch_per_retriever: int = 25,
    source_type_filter: list[str] | None = None,
) -> list[SearchHit]:
    """Hybrid search via Reciprocal Rank Fusion."""

    qvec_task = embed_query(query)

    async with session_scope() as session:
        bm25_rows = await _bm25_search(session, query, fetch_per_retriever, source_type_filter)

        try:
            qvec = await qvec_task
            vec_rows = await _vector_search(session, qvec, fetch_per_retriever, source_type_filter)
        except Exception:
            # If embeddings unavailable, fall back to BM25-only
            vec_rows = []

    # RRF fuse
    scores: dict[str, dict[str, Any]] = {}

    for rank, row in enumerate(bm25_rows, start=1):
        cid = row[0]
        scores.setdefault(cid, {"row": row, "bm25_rank": None, "vec_rank": None, "score": 0.0})
        scores[cid]["bm25_rank"] = rank
        scores[cid]["score"] += 1.0 / (RRF_K + rank)

    for rank, row in enumerate(vec_rows, start=1):
        cid = row[0]
        scores.setdefault(cid, {"row": row, "bm25_rank": None, "vec_rank": None, "score": 0.0})
        scores[cid]["vec_rank"] = rank
        scores[cid]["score"] += 1.0 / (RRF_K + rank)

    # Sort + materialize
    fused = sorted(scores.values(), key=lambda s: s["score"], reverse=True)[:limit]

    hits: list[SearchHit] = []
    for s in fused:
        row = s["row"]
        cid, sid, url, stype, title, text_, meta, _ = row
        hits.append(
            SearchHit(
                chunk_id=cid,
                source_id=sid,
                source_url=url,
                source_type=stype,
                title=title,
                snippet=_make_snippet(text_),
                chunk_metadata=meta or {},
                score=s["score"],
                bm25_rank=s["bm25_rank"],
                vector_rank=s["vec_rank"],
            )
        )
    return hits
