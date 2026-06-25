"""Tests for top-damager lookup endpoints."""
from __future__ import annotations

import uuid

import pytest


@pytest.mark.asyncio
async def test_top_damager_by_encounter(client, seeded_encounter):
    r = await client.get(f"/api/v1/encounters/{seeded_encounter.id}/top-damager")
    assert r.status_code == 200
    body = r.json()
    assert body["player_id"] == "p-top"
    assert body["player_name"] == "DarkHunter99"
    assert body["damage_dealt"] == 12800.0
    assert body["rank"] == 1


@pytest.mark.asyncio
async def test_top_damager_skip_excludes_held(client, seeded_encounter):
    r = await client.get(
        f"/api/v1/encounters/{seeded_encounter.id}/top-damager"
        f"?skip_holders=p-top"
    )
    assert r.status_code == 200
    assert r.json()["player_id"] == "p-mid"


@pytest.mark.asyncio
async def test_top_damager_404_on_missing_encounter(client):
    fake = uuid.uuid4()
    r = await client.get(f"/api/v1/encounters/{fake}/top-damager")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_top_damager_by_boss_id_alias(client, seeded_encounter):
    r = await client.get(
        f"/api/v1/servers/{seeded_encounter.server_id}"
        f"/active-boss/{seeded_encounter.boss_id}/top-damager"
    )
    assert r.status_code == 200
    assert r.json()["player_id"] == "p-top"
