"""Embeddings via Ollama (default: nomic-embed-text, 768 dim).

Background batch worker pattern: chunks insert with embedding=NULL, this
module fills them in batches. Keeps insertion path fast.
"""

from __future__ import annotations

import asyncio
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from dayzstack_shared.config import get_settings


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
async def _embed_one(client: httpx.AsyncClient, text: str, model: str) -> list[float]:
    """Single embed call. Retries with backoff."""
    resp = await client.post(
        "/api/embeddings",
        json={"model": model, "prompt": text},
        timeout=60.0,
    )
    resp.raise_for_status()
    data = resp.json()
    return data["embedding"]


async def embed_batch(texts: list[str], model: str | None = None) -> list[list[float]]:
    """Embed a list of texts. Ollama's embedding endpoint is single-request,
    so we parallelize with a small concurrency cap."""
    settings = get_settings()
    model = model or settings.embed_model

    # Ollama serves embeddings serially per model; parallel requests just queue
    # and time out under load. Lesson from session 2's stall (160/7041 done):
    # use concurrency=1 with a long timeout so we trade speed for completion.
    async with httpx.AsyncClient(base_url=settings.ollama_url, timeout=300.0) as client:
        sem = asyncio.Semaphore(1)

        async def with_sem(t: str) -> list[float]:
            async with sem:
                return await _embed_one(client, t, model)

        return await asyncio.gather(*(with_sem(t) for t in texts))


async def embed_query(text: str) -> list[float]:
    """Single-query embed for search."""
    out = await embed_batch([text])
    return out[0]


async def health_check() -> dict[str, Any]:
    """Verify Ollama is reachable + the embed model is pulled."""
    settings = get_settings()
    async with httpx.AsyncClient(base_url=settings.ollama_url, timeout=5.0) as client:
        try:
            r = await client.get("/api/tags")
            r.raise_for_status()
            tags = r.json().get("models", [])
            model_present = any(m.get("name", "").startswith(settings.embed_model) for m in tags)
            return {
                "ok": True,
                "model_present": model_present,
                "available": [m.get("name") for m in tags],
                "configured_model": settings.embed_model,
            }
        except Exception as e:
            return {"ok": False, "error": str(e)}
