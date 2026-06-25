"""
Test fixtures for BossSignal backend.

Uses SQLite in-memory DB per test (fast, isolated). The dialect-portable
JSON_TYPE in models.py + the conditional engine kwargs in database.py
let the same model code run against SQLite here and Postgres in prod.
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio

# Force SQLite + test secret before the app imports settings
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["BOSSSIGNAL_SECRET"] = "test-secret"
os.environ["DEBUG"] = "false"

from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.models import Base, BossEncounter


@pytest_asyncio.fixture
async def engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def session(engine):
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)
    async with SessionLocal() as s:
        yield s


@pytest_asyncio.fixture
async def client(engine, monkeypatch):
    """TestClient bound to the test engine."""
    from app.main import app
    from app.db import database as db_module

    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)
    monkeypatch.setattr(db_module, "engine", engine)
    monkeypatch.setattr(db_module, "AsyncSessionLocal", SessionLocal)

    # NOTE: ASGITransport doesn't trigger lifespan; tables are created by the engine fixture.
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def seeded_encounter(session):
    """Create one killed BossEncounter with 3 participants of varying damage."""
    enc = BossEncounter(
        id=uuid.uuid4(),
        server_id="server_03",
        boss_id="boss-abc-123",
        boss_type="ExampleBoss_01",
        display_name="The Warlord",
        spawned_at=datetime.now(timezone.utc),
        killed_at=datetime.now(timezone.utc),
        status="killed",
        max_health=40000.0,
        time_to_kill_seconds=420.0,
        participants=[
            {"player_id": "p-top", "player_name": "DarkHunter99", "damage_dealt": 12800.0, "kill_shot": True},
            {"player_id": "p-mid", "player_name": "NightWalker",  "damage_dealt":  7200.0, "kill_shot": False},
            {"player_id": "p-low", "player_name": "Vasya",        "damage_dealt":   900.0, "kill_shot": False},
        ],
    )
    session.add(enc)
    await session.commit()
    await session.refresh(enc)
    yield enc
