"""
Security tests for the BossSignal shared-secret hardening.

Covers:
  - The write path (POST /api/v1/events) requires the X-BossSignal-Secret
    header (401 without it).
  - The secret is NOT accepted via the ?secret= query parameter anymore.
  - The hive read paths require the header (401 without it).
  - The dashboard read endpoints stay OPEN by default (REQUIRE_READ_AUTH unset)
    so the browser dashboard keeps working with no secret.
  - Bad UUID path params return 400, not a 500 with a leaked DB error.
"""
from __future__ import annotations

import pytest

SECRET = "test-secret"
HEADER = {"X-BossSignal-Secret": SECRET}


def _heartbeat(server_id: str = "server_sec") -> dict:
    return {
        "event_type": "server.heartbeat",
        "server_id": server_id,
        "server_time": 1.0,
        "data": {"player_count": 0, "active_boss_count": 0, "active_bosses": []},
    }


# ── Write path requires the header ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_post_events_requires_secret_header(client):
    # No header at all -> 401.
    r = await client.post("/api/v1/events", json=_heartbeat())
    assert r.status_code == 401, r.text


@pytest.mark.asyncio
async def test_post_events_rejects_wrong_secret(client):
    r = await client.post(
        "/api/v1/events",
        json=_heartbeat(),
        headers={"X-BossSignal-Secret": "not-the-secret"},
    )
    assert r.status_code == 401, r.text


@pytest.mark.asyncio
async def test_post_events_query_param_secret_is_rejected(client):
    # The old ?secret= bypass must no longer authenticate the request.
    r = await client.post(
        f"/api/v1/events?secret={SECRET}",
        json=_heartbeat(),
    )
    assert r.status_code == 401, r.text


@pytest.mark.asyncio
async def test_post_events_accepts_valid_header(client):
    r = await client.post("/api/v1/events", json=_heartbeat(), headers=HEADER)
    assert r.status_code == 202, r.text


# ── Hive read paths require the header ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_hive_player_requires_secret(client):
    r = await client.get("/api/v1/hive/player/76561198000000000")
    assert r.status_code == 401, r.text


@pytest.mark.asyncio
async def test_hive_player_query_param_secret_rejected(client):
    r = await client.get(f"/api/v1/hive/player/76561198000000000?secret={SECRET}")
    assert r.status_code == 401, r.text


@pytest.mark.asyncio
async def test_hive_player_accepts_valid_header(client):
    r = await client.get("/api/v1/hive/player/76561198000000000", headers=HEADER)
    assert r.status_code == 200, r.text
    assert r.json()["exists"] is False


# ── Dashboard reads stay open by default (REQUIRE_READ_AUTH unset) ─────────────


@pytest.mark.asyncio
async def test_dashboard_reads_open_by_default(client):
    # No secret header — these must still serve the dashboard.
    for path in (
        "/api/v1/servers",
        "/api/v1/server/status",
        "/api/v1/leaderboard/boss-kills",
        "/api/v1/encounters/recent",
        "/api/v1/trophies",
        "/api/v1/bosses",
        "/api/v1/events",
    ):
        r = await client.get(path)
        assert r.status_code == 200, f"{path} -> {r.status_code}: {r.text}"


# ── Read auth can be opted in ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_require_read_auth_locks_reads_when_enabled(client, monkeypatch):
    from app import auth as auth_module

    monkeypatch.setattr(auth_module.settings, "require_read_auth", True)
    # Without the header, a read route now 401s.
    r = await client.get("/api/v1/trophies")
    assert r.status_code == 401, r.text
    # With the header, it works again.
    r = await client.get("/api/v1/trophies", headers=HEADER)
    assert r.status_code == 200, r.text


# ── Bad UUIDs return 400, not a leaked 500 ─────────────────────────────────────


@pytest.mark.asyncio
async def test_top_damager_bad_uuid_returns_400(client):
    r = await client.get("/api/v1/encounters/not-a-uuid/top-damager")
    assert r.status_code == 400, r.text


@pytest.mark.asyncio
async def test_trophy_history_bad_uuid_returns_400(client):
    r = await client.get("/api/v1/trophies/not-a-uuid/history")
    assert r.status_code == 400, r.text
