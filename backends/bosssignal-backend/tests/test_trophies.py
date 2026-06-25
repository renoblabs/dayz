"""Tests for Trophy model and trophy endpoints."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest

from app.db.models import Trophy


@pytest.mark.asyncio
async def test_trophy_row_persists(session):
    t = Trophy(
        id=uuid.uuid4(),
        trophy_class="WarlordsCrown",
        boss_type="ExampleBoss_01",
        encounter_id=uuid.uuid4(),
        original_holder_id="p-top",
        original_holder_name="DarkHunter99",
        original_server_id="server_03",
        original_claimed_at=datetime.now(timezone.utc),
        current_holder_id="p-top",
        current_holder_name="DarkHunter99",
        current_server_id="server_03",
    )
    session.add(t)
    await session.commit()
    await session.refresh(t)
    assert t.id is not None
    assert t.trophy_class == "WarlordsCrown"
    assert t.original_holder_id == "p-top"


@pytest.mark.asyncio
async def test_trophy_awarded_ingests_and_persists(client, seeded_encounter):
    payload = {
        "event_type": "trophy.awarded",
        "server_id":  "server_03",
        "server_time": 1000.0,
        "data": {
            "encounter_id":   str(seeded_encounter.id),
            "trophy_class":   "WarlordsCrown",
            "boss_type":      "ExampleBoss_01",
            "holder_id":      "p-top",
            "holder_name":    "DarkHunter99",
        },
    }
    r = await client.post(
        "/api/v1/events",
        json=payload,
        headers={"X-BossSignal-Secret": "test-secret"},
    )
    assert r.status_code == 202

    from sqlalchemy import select
    from app.db.database import AsyncSessionLocal
    from app.db.models import Trophy
    async with AsyncSessionLocal() as s:
        result = await s.scalars(select(Trophy))
        trophies = result.all()
        assert len(trophies) == 1
        assert trophies[0].trophy_class == "WarlordsCrown"
        assert trophies[0].current_holder_id == "p-top"
        assert trophies[0].original_holder_id == "p-top"


@pytest.mark.asyncio
async def test_list_trophies_via_api(client, seeded_encounter):
    payload = {
        "event_type": "trophy.awarded",
        "server_id":  "server_03",
        "server_time": 1000.0,
        "data": {
            "encounter_id": str(seeded_encounter.id),
            "trophy_class": "WarlordsCrown",
            "boss_type":    "ExampleBoss_01",
            "holder_id":    "p-top",
            "holder_name":  "DarkHunter99",
        },
    }
    await client.post("/api/v1/events", json=payload, headers={"X-BossSignal-Secret": "test-secret"})
    r = await client.get("/api/v1/trophies")
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) == 1
    assert rows[0]["trophy_class"] == "WarlordsCrown"


@pytest.mark.asyncio
async def test_trophies_leaderboard(client, seeded_encounter):
    payload = {
        "event_type": "trophy.awarded",
        "server_id":  "server_03",
        "server_time": 1000.0,
        "data": {
            "encounter_id": str(seeded_encounter.id),
            "trophy_class": "WarlordsCrown",
            "boss_type":    "ExampleBoss_01",
            "holder_id":    "p-top",
            "holder_name":  "DarkHunter99",
        },
    }
    await client.post("/api/v1/events", json=payload, headers={"X-BossSignal-Secret": "test-secret"})
    r = await client.get("/api/v1/trophies/leaderboard")
    assert r.status_code == 200
    lb = r.json()
    assert lb["by_player"][0]["player_id"] == "p-top"
    assert lb["by_player"][0]["trophy_count"] == 1


@pytest.mark.asyncio
async def test_trophy_history_empty_for_new(client, seeded_encounter):
    payload = {
        "event_type": "trophy.awarded",
        "server_id":  "server_03",
        "server_time": 1000.0,
        "data": {
            "encounter_id": str(seeded_encounter.id),
            "trophy_class": "WarlordsCrown",
            "boss_type":    "ExampleBoss_01",
            "holder_id":    "p-top",
            "holder_name":  "DarkHunter99",
        },
    }
    await client.post("/api/v1/events", json=payload, headers={"X-BossSignal-Secret": "test-secret"})
    listing = await client.get("/api/v1/trophies")
    tid = listing.json()[0]["id"]
    h = await client.get(f"/api/v1/trophies/{tid}/history")
    assert h.status_code == 200
    assert h.json()["transfer_history"] == []
