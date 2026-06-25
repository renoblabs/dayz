"""
Tests for the server_status.loaded_mods plumbing:
  - heartbeat carrying loaded_mods persists it
  - server.started carrying loaded_mods persists it
  - heartbeat WITHOUT loaded_mods doesn't blank out a previously-set manifest
  - /server/status normalizes the stored manifest to {name, version, status}
  - /server/status omits no field when loaded_mods is null/empty
"""
from __future__ import annotations

import pytest


SECRET = "test-secret"
HEADERS = {"X-BossSignal-Secret": SECRET}


@pytest.mark.asyncio
async def test_heartbeat_with_loaded_mods_persists_and_normalizes(client):
    payload = {
        "event_type": "server.heartbeat",
        "server_id":  "server_01",
        "server_time": 100.0,
        "data": {
            "player_count": 0,
            "active_boss_count": 0,
            "active_bosses": [],
            "loaded_mods": [
                "@CommunityFramework",
                "@BossSignal",
                {"name": "@TrophyHunter", "version": "0.2.1"},
            ],
        },
    }
    r = await client.post("/api/v1/events", json=payload, headers=HEADERS)
    assert r.status_code == 202, r.text

    r = await client.get("/api/v1/server/status", params={"server_id": "server_01"})
    assert r.status_code == 200
    body = r.json()
    mods = body["loaded_mods"]
    assert mods is not None
    assert len(mods) == 3

    by_name = {m["name"]: m for m in mods}
    assert by_name["@CommunityFramework"] == {"name": "@CommunityFramework", "version": "", "status": "ok"}
    assert by_name["@BossSignal"]["status"] == "ok"
    assert by_name["@TrophyHunter"]["version"] == "0.2.1"


@pytest.mark.asyncio
async def test_server_started_persists_loaded_mods(client):
    payload = {
        "event_type": "server.started",
        "server_id":  "server_02",
        "server_time": 0.0,
        "data": {
            "bosssignal_version": "0.1.0",
            "loaded_mods": ["@CommunityFramework", "@HiveApiMod"],
        },
    }
    r = await client.post("/api/v1/events", json=payload, headers=HEADERS)
    assert r.status_code == 202, r.text

    r = await client.get("/api/v1/server/status", params={"server_id": "server_02"})
    assert r.status_code == 200
    body = r.json()
    assert body["bosssignal_version"] == "0.1.0"
    names = [m["name"] for m in (body["loaded_mods"] or [])]
    assert names == ["@CommunityFramework", "@HiveApiMod"]


@pytest.mark.asyncio
async def test_heartbeat_without_loaded_mods_preserves_existing(client):
    # First: server.started carries a manifest.
    started = {
        "event_type": "server.started",
        "server_id":  "server_03",
        "server_time": 0.0,
        "data": {
            "loaded_mods": ["@CommunityFramework", "@BossSignal"],
        },
    }
    r = await client.post("/api/v1/events", json=started, headers=HEADERS)
    assert r.status_code == 202

    # Then: a heartbeat that doesn't carry loaded_mods should NOT clear it.
    hb = {
        "event_type": "server.heartbeat",
        "server_id":  "server_03",
        "server_time": 1.0,
        "data": {"player_count": 1, "active_boss_count": 0, "active_bosses": []},
    }
    r = await client.post("/api/v1/events", json=hb, headers=HEADERS)
    assert r.status_code == 202

    r = await client.get("/api/v1/server/status", params={"server_id": "server_03"})
    assert r.status_code == 200
    mods = r.json()["loaded_mods"]
    assert mods is not None
    assert [m["name"] for m in mods] == ["@CommunityFramework", "@BossSignal"]


@pytest.mark.asyncio
async def test_server_status_returns_null_when_no_manifest(client):
    # Heartbeat without loaded_mods, no prior server.started — manifest stays null.
    payload = {
        "event_type": "server.heartbeat",
        "server_id":  "server_04",
        "server_time": 0.0,
        "data": {"player_count": 0, "active_boss_count": 0, "active_bosses": []},
    }
    r = await client.post("/api/v1/events", json=payload, headers=HEADERS)
    assert r.status_code == 202

    r = await client.get("/api/v1/server/status", params={"server_id": "server_04"})
    assert r.status_code == 200
    assert r.json()["loaded_mods"] is None


@pytest.mark.asyncio
async def test_servers_list_includes_loaded_mods(client):
    payload = {
        "event_type": "server.started",
        "server_id":  "server_05",
        "server_time": 0.0,
        "data": {
            "loaded_mods": ["@CommunityFramework"],
        },
    }
    r = await client.post("/api/v1/events", json=payload, headers=HEADERS)
    assert r.status_code == 202

    r = await client.get("/api/v1/servers")
    assert r.status_code == 200
    rows = r.json()
    target = next(s for s in rows if s["server_id"] == "server_05")
    assert "loaded_mods" in target
    assert [m["name"] for m in (target["loaded_mods"] or [])] == ["@CommunityFramework"]
