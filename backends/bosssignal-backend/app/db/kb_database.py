"""
Read-only async SQLAlchemy engine for the KB postgres (dayz-stack platform).

Lives in a separate database than the BossSignal events DB. Connection is
optional — if KB_DATABASE_URL isn't set, or the engine can't connect, the
KB routers return empty results rather than 500'ing.
"""
from __future__ import annotations

import logging
from typing import AsyncIterator, Optional

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings

log = logging.getLogger(__name__)

_settings = get_settings()
_engine: Optional[AsyncEngine] = None
_SessionFactory: Optional[async_sessionmaker[AsyncSession]] = None


def _get_engine() -> Optional[AsyncEngine]:
    global _engine, _SessionFactory
    if _engine is not None:
        return _engine
    if not _settings.kb_database_url:
        return None
    try:
        _engine = create_async_engine(
            _settings.kb_database_url,
            echo=_settings.debug,
            pool_size=4,
            max_overflow=4,
            pool_pre_ping=True,
            pool_recycle=300,
        )
        _SessionFactory = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)
    except Exception as exc:
        log.warning("KB engine init failed: %s", exc)
        _engine = None
    return _engine


async def get_kb_db() -> AsyncIterator[Optional[AsyncSession]]:
    """FastAPI dependency: yields an AsyncSession or None if KB is unreachable."""
    eng = _get_engine()
    if eng is None or _SessionFactory is None:
        yield None
        return
    async with _SessionFactory() as session:
        yield session
