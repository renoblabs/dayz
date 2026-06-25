"""Tests for event ingestion idempotency."""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy.exc import IntegrityError

from app.db.models import Event
from app.routers.events import ingest_event


class _Request:
    async def json(self):
        return {
            "event_type": "server.heartbeat",
            "server_id": "server_01",
            "server_time": 123,
            "data": {},
        }


class _RaceDb:
    def __init__(self) -> None:
        self.existing = Event(
            id=uuid.uuid4(),
            server_id="server_01",
            event_type="server.heartbeat",
            payload={},
            idempotency_key="already-inserted",
        )
        self.scalar_calls = 0
        self.rolled_back = False

    async def scalar(self, _query):
        self.scalar_calls += 1
        if self.scalar_calls < 3:
            return None
        return self.existing

    def add(self, _event) -> None:
        pass

    async def commit(self) -> None:
        raise IntegrityError("insert", {}, Exception("duplicate"))

    async def rollback(self) -> None:
        self.rolled_back = True


@pytest.mark.asyncio
async def test_ingest_event_returns_duplicate_when_unique_key_races():
    db = _RaceDb()

    result = await ingest_event(_Request(), db=db)

    assert result == {"status": "duplicate", "event_id": str(db.existing.id)}
    assert db.rolled_back is True
