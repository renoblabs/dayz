# TrophyHunter Implementation Plan

> Historical implementation plan. Paths, ports, and completion language reflect the pre-consolidation branch state. Current source paths are `mods/TrophyHunter`, `mods/BossSignal`, and `backends/bosssignal-backend`; current local stack port is `6700`. Treat this file as build history, not a current readiness statement. The in-game trophy loop still needs live validation.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship TrophyHunter - a new DayZ server-side mod that awards top-damage players a unique carryable trophy when a boss dies - plus the backend + dashboard pieces needed to surface trophies across a server network.

**Architecture:** Backend is FastAPI + SQLAlchemy async; Enforce mod mirrors the BossSignal mod layout (`3_game` config + `4_world` HTTP client + `5_mission` mission entry). TrophyHunter hooks `OnEntityKilled`, checks a configurable boss allowlist, reads the top damager from BossSignal's in-memory encounter, spawns the trophy item, stamps provenance, announces, and POSTs `trophy.awarded` to the backend for dashboard broadcast.

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy 2 async, SQLite (dev) / Postgres (prod), vanilla JS (dashboard), Enforce Script (DayZ mod), Community Framework.

**Spec:** `docs/superpowers/specs/2026-04-19-trophy-hunter-mod-design.md`

---

## File Structure (locked in before task breakdown)

**NEW files:**
- `backends/bosssignal-backend/requirements-dev.txt` - pytest + httpx + pytest-asyncio
- `backends/bosssignal-backend/tests/__init__.py`
- `backends/bosssignal-backend/tests/conftest.py` - SQLite in-memory DB, FastAPI TestClient, seeded encounter fixture
- `backends/bosssignal-backend/tests/test_top_damager.py` - top-damager endpoint
- `backends/bosssignal-backend/tests/test_trophies.py` - trophy ingest + queries
- `backends/bosssignal-backend/app/routers/trophies.py` - trophy query routes
- `mods/TrophyHunter/config.cpp`
- `mods/TrophyHunter/config/bosses.json`
- `mods/TrophyHunter/TrophyHunter.pboproject`
- `mods/TrophyHunter/scripts/3_game/TrophyHunterConfig.c`
- `mods/TrophyHunter/scripts/4_world/TrophyHunterClient.c`
- `mods/TrophyHunter/scripts/5_mission/TrophyHunterMission.c`
- `mods/TrophyHunter/scripts/5_mission/TrophyAwarder.c`
- `mods/TrophyHunter/scripts/5_mission/TrophyProvenance.c`
- `docs/TROPHYHUNTER-PREDEPLOY.md`

**MODIFIED files:**
- `backends/bosssignal-backend/app/db/models.py` - add `Trophy` model
- `backends/bosssignal-backend/app/routers/events.py` - add `trophy.awarded` + `trophy.transferred` handlers
- `backends/bosssignal-backend/app/routers/bosses.py` - add encounter-uuid + boss-id top-damager routes
- `backends/bosssignal-backend/app/main.py` - register trophies router
- `backends/bosssignal-backend/static/dashboard.html` - add Trophy Hall panel + SSE handler
- `mods/BossSignal/scripts/4_world/BossSignalAPI.c` - add `GetEncounterIdForBoss(entity)`
- `mods/BossSignal/scripts/5_mission/BossSignalEmitter.c` - add resolver used by that API method
- `test-harness/simulate_boss_encounter.py` - emit `trophy.awarded` after each `boss.killed`
- `README.md` - mention TrophyHunter
- `HANDOFF.md` - update current-state and next-session context

---

## Phase 1 - Backend: enable TDD

### Task 1: Add dev test harness

**Files:**
- Create: `backends/bosssignal-backend/requirements-dev.txt`
- Create: `backends/bosssignal-backend/tests/__init__.py`
- Create: `backends/bosssignal-backend/tests/conftest.py`

- [ ] **Step 1: Add dev dependencies file**

Create `backends/bosssignal-backend/requirements-dev.txt`:
```
pytest==8.3.4
pytest-asyncio==0.25.0
httpx==0.28.1
aiosqlite==0.20.0
```

- [ ] **Step 2: Install dev deps**

Run: `cd bosssignal-backend && python -m pip install -r requirements-dev.txt`
Expected: all 4 installed cleanly.

- [ ] **Step 3: Create empty tests package**

Create `backends/bosssignal-backend/tests/__init__.py` as an empty file (touch is fine).

- [ ] **Step 4: Create conftest with SQLite fixture**

Create `backends/bosssignal-backend/tests/conftest.py`:
```python
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
async def client(engine):
    """TestClient bound to the test engine."""
    from app.main import app
    from app.db import database as db_module

    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)
    db_module.engine = engine
    db_module.AsyncSessionLocal = SessionLocal

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
```

- [ ] **Step 5: Run the empty test suite to confirm wiring**

Run: `cd bosssignal-backend && python -m pytest tests/ -v`
Expected: "no tests ran" (0 collected, 0 errors).

- [ ] **Step 6: Commit**

```bash
git add backends/bosssignal-backend/requirements-dev.txt backends/bosssignal-backend/tests/__init__.py backends/bosssignal-backend/tests/conftest.py
git commit -m "test: add pytest harness with sqlite in-memory fixtures"
```

---

### Task 2: `Trophy` SQLAlchemy model

**Files:**
- Modify: `backends/bosssignal-backend/app/db/models.py` (append new class)
- Test: `backends/bosssignal-backend/tests/test_trophies.py` (new file)

- [ ] **Step 1: Write failing test for trophy row creation**

Create `backends/bosssignal-backend/tests/test_trophies.py`:
```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd bosssignal-backend && python -m pytest tests/test_trophies.py -v`
Expected: FAIL with `ImportError: cannot import name 'Trophy'`.

- [ ] **Step 3: Append Trophy model to `app/db/models.py`**

At the end of `backends/bosssignal-backend/app/db/models.py`, add:
```python
# -- Trophy awards ------------------------------------------------------------
class Trophy(Base):
    """
    One row per trophy instance. A trophy is born when a boss dies and the
    top-damage player receives it. The row is mutated as the trophy changes
    hands (current_* fields) but the original_* fields stay frozen as
    permanent provenance.
    """

    __tablename__ = "trophies"

    id                     = Column(UUIDType(), primary_key=True, default=uuid.uuid4)

    trophy_class           = Column(String(64), nullable=False, index=True)
    boss_type              = Column(String(128), nullable=False)
    encounter_id           = Column(UUIDType(), nullable=False, index=True)

    # Frozen at creation, never changes
    original_holder_id     = Column(String(64), nullable=False)
    original_holder_name   = Column(String(128), nullable=False)
    original_server_id     = Column(String(64), nullable=False)
    original_claimed_at    = Column(DateTime(timezone=True), nullable=False)

    # Current holder - updated on transfer
    current_holder_id      = Column(String(64), nullable=False, index=True)
    current_holder_name    = Column(String(128), nullable=False)
    current_server_id      = Column(String(64), nullable=False, index=True)
    current_held_since     = Column(DateTime(timezone=True), nullable=False, default=_now)

    # History of transfers: [{from_player_id, to_player_id, to_player_name, server_id, at}]
    transfer_history       = Column(JSON_TYPE, nullable=False, default=list)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd bosssignal-backend && python -m pytest tests/test_trophies.py::test_trophy_row_persists -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backends/bosssignal-backend/app/db/models.py backends/bosssignal-backend/tests/test_trophies.py
git commit -m "feat(models): add Trophy model with frozen provenance fields"
```

---

### Task 3: Top-damager lookup endpoints

**Files:**
- Modify: `backends/bosssignal-backend/app/routers/bosses.py` (append two routes)
- Test: `backends/bosssignal-backend/tests/test_top_damager.py` (new file)

- [ ] **Step 1: Write failing tests**

Create `backends/bosssignal-backend/tests/test_top_damager.py`:
```python
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
        f"skip_holders=p-top"
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd bosssignal-backend && python -m pytest tests/test_top_damager.py -v`
Expected: 4 FAILs (404 on the new routes).

- [ ] **Step 3: Append routes to `app/routers/bosses.py`**

At the top of `backends/bosssignal-backend/app/routers/bosses.py`, make sure `HTTPException` is imported. Change the existing FastAPI import line from:
```python
from fastapi import APIRouter, Depends, Query
```
to:
```python
from fastapi import APIRouter, Depends, HTTPException, Query
```

Append to the end of `backends/bosssignal-backend/app/routers/bosses.py`:
```python
# -- Top-damager lookups ------------------------------------------------------

def _rank_participants(participants: list[dict], skip_holders: str | None) -> list[dict]:
    skip = set((skip_holders or "").split(",")) if skip_holders else set()
    return sorted(
        (p for p in participants if p.get("player_id") and p["player_id"] not in skip),
        key=lambda p: (-p.get("damage_dealt", 0), not p.get("kill_shot", False)),
    )


def _top_damager_response(enc: BossEncounter, skip_holders: str | None) -> dict:
    participants = enc.participants or []
    ranked = _rank_participants(participants, skip_holders)
    if not ranked:
        raise HTTPException(status_code=404, detail="No eligible damagers")
    top = ranked[0]
    rank = 1 + next(
        (i for i, p in enumerate(participants) if p.get("player_id") == top["player_id"]),
        0,
    )
    return {
        "encounter_id": str(enc.id),
        "boss_type":    enc.boss_type,
        "server_id":    enc.server_id,
        "player_id":    top["player_id"],
        "player_name":  top.get("player_name", "Unknown"),
        "damage_dealt": top.get("damage_dealt", 0),
        "kill_shot":    top.get("kill_shot", False),
        "rank":         rank,
    }


@router.get(
    "/api/v1/encounters/{encounter_id}/top-damager",
    summary="Top-damage player for an encounter (for trophy award)",
)
async def top_damager(
    encounter_id: str,
    skip_holders: Optional[str] = Query(
        default=None,
        description="Comma-separated player_ids to exclude from ranking.",
    ),
    db: AsyncSession = Depends(get_db),
) -> dict:
    enc = await db.scalar(
        select(BossEncounter).where(BossEncounter.id == encounter_id)
    )
    if not enc:
        raise HTTPException(status_code=404, detail="Encounter not found")
    return _top_damager_response(enc, skip_holders)


@router.get(
    "/api/v1/servers/{server_id}/active-boss/{boss_id}/top-damager",
    summary="Top-damage lookup by in-game boss_id (for TrophyHunter)",
)
async def top_damager_by_boss_id(
    server_id: str,
    boss_id: str,
    skip_holders: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> dict:
    enc = await db.scalar(
        select(BossEncounter)
        .where(BossEncounter.server_id == server_id)
        .where(BossEncounter.boss_id == boss_id)
        .where(BossEncounter.status != "despawned")
        .order_by(BossEncounter.spawned_at.desc())
        .limit(1)
    )
    if not enc:
        raise HTTPException(status_code=404, detail="No active encounter for that boss_id")
    return _top_damager_response(enc, skip_holders)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd bosssignal-backend && python -m pytest tests/test_top_damager.py -v`
Expected: 4 PASS.

- [ ] **Step 5: Commit**

```bash
git add backends/bosssignal-backend/app/routers/bosses.py backends/bosssignal-backend/tests/test_top_damager.py
git commit -m "feat(api): add top-damager lookup (by encounter UUID and by boss_id)"
```

---

### Task 4: Accept `trophy.awarded` + `trophy.transferred` events

**Files:**
- Modify: `backends/bosssignal-backend/app/routers/events.py` (add handlers + dispatch cases)
- Test: `backends/bosssignal-backend/tests/test_trophies.py` (append tests)

- [ ] **Step 1: Write failing test**

Append to `backends/bosssignal-backend/tests/test_trophies.py`:
```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd bosssignal-backend && python -m pytest tests/test_trophies.py::test_trophy_awarded_ingests_and_persists -v`
Expected: FAIL on `len(trophies) == 1` (event is accepted but no handler persists a Trophy row).

- [ ] **Step 3: Add handlers to events.py**

In `backends/bosssignal-backend/app/routers/events.py`:

Change the model import line from:
```python
from app.db.models import BossEncounter, Event, ServerStatus
```
to:
```python
from app.db.models import BossEncounter, Event, ServerStatus, Trophy
```

Inside `ingest_event`, add two more `elif` branches after the `server.started` branch:
```python
    elif event_type == "trophy.awarded":
        await _handle_trophy_awarded(db, server_id, payload)

    elif event_type == "trophy.transferred":
        await _handle_trophy_transferred(db, server_id, payload)
```

Append these two functions at the end of the file:
```python
async def _handle_trophy_awarded(db: AsyncSession, server_id: str, payload: dict) -> None:
    """Persist a new Trophy row on trophy.awarded event."""
    import uuid as _uuid
    data = payload.get("data", {})
    now = datetime.now(timezone.utc)
    trophy = Trophy(
        id=_uuid.uuid4(),
        trophy_class=data["trophy_class"],
        boss_type=data.get("boss_type", "unknown"),
        encounter_id=_uuid.UUID(data["encounter_id"]),
        original_holder_id=data["holder_id"],
        original_holder_name=data.get("holder_name", "Unknown"),
        original_server_id=server_id,
        original_claimed_at=now,
        current_holder_id=data["holder_id"],
        current_holder_name=data.get("holder_name", "Unknown"),
        current_server_id=server_id,
        current_held_since=now,
        transfer_history=[],
    )
    db.add(trophy)


async def _handle_trophy_transferred(db: AsyncSession, server_id: str, payload: dict) -> None:
    """Update a Trophy row when it changes hands (kill loot after grace period)."""
    import uuid as _uuid
    data = payload.get("data", {})
    trophy_id = data.get("trophy_id")
    if not trophy_id:
        return
    row = await db.scalar(select(Trophy).where(Trophy.id == _uuid.UUID(trophy_id)))
    if not row:
        return
    now = datetime.now(timezone.utc)
    history = list(row.transfer_history or [])
    history.append({
        "from_player_id": row.current_holder_id,
        "to_player_id":   data["new_holder_id"],
        "to_player_name": data.get("new_holder_name", "Unknown"),
        "server_id":      server_id,
        "at":             now.isoformat(),
    })
    row.transfer_history    = history
    row.current_holder_id   = data["new_holder_id"]
    row.current_holder_name = data.get("new_holder_name", "Unknown")
    row.current_server_id   = server_id
    row.current_held_since  = now
```

- [ ] **Step 4: Run and confirm the test passes**

Run: `cd bosssignal-backend && python -m pytest tests/test_trophies.py::test_trophy_awarded_ingests_and_persists -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backends/bosssignal-backend/app/routers/events.py backends/bosssignal-backend/tests/test_trophies.py
git commit -m "feat(events): accept trophy.awarded and trophy.transferred"
```

---

### Task 5: Trophies query router

**Files:**
- Create: `backends/bosssignal-backend/app/routers/trophies.py`
- Modify: `backends/bosssignal-backend/app/main.py` (register router)
- Test: `backends/bosssignal-backend/tests/test_trophies.py` (append tests)

- [ ] **Step 1: Write failing tests**

Append to `backends/bosssignal-backend/tests/test_trophies.py`:
```python
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
```

- [ ] **Step 2: Run tests to confirm 404s**

Run: `cd bosssignal-backend && python -m pytest tests/test_trophies.py -v`
Expected: 3 new tests FAIL on 404 for `/api/v1/trophies*`.

- [ ] **Step 3: Create `app/routers/trophies.py`**

Create `backends/bosssignal-backend/app/routers/trophies.py`:
```python
"""
/api/v1/trophies - trophy queries backed by the Trophy table.

Read-only router. Writes happen via /api/v1/events (trophy.awarded,
trophy.transferred) and are handled in events.py.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import Trophy

router = APIRouter(prefix="/api/v1/trophies", tags=["trophies"])


def _trophy_to_dict(t: Trophy) -> dict:
    return {
        "id":                   str(t.id),
        "trophy_class":         t.trophy_class,
        "boss_type":            t.boss_type,
        "encounter_id":         str(t.encounter_id),
        "original_holder_id":   t.original_holder_id,
        "original_holder_name": t.original_holder_name,
        "original_server_id":   t.original_server_id,
        "original_claimed_at":  t.original_claimed_at.isoformat() if t.original_claimed_at else None,
        "current_holder_id":    t.current_holder_id,
        "current_holder_name":  t.current_holder_name,
        "current_server_id":    t.current_server_id,
        "current_held_since":   t.current_held_since.isoformat() if t.current_held_since else None,
        "transfer_count":       len(t.transfer_history or []),
    }


@router.get("", summary="All trophies currently in circulation")
async def list_trophies(db: AsyncSession = Depends(get_db)) -> list[dict]:
    result = await db.scalars(
        select(Trophy).order_by(Trophy.original_claimed_at.desc())
    )
    return [_trophy_to_dict(t) for t in result.all()]


@router.get("/leaderboard", summary="Aggregated trophy leaderboard")
async def leaderboard(db: AsyncSession = Depends(get_db)) -> dict:
    by_player = await db.execute(
        select(
            Trophy.current_holder_id.label("player_id"),
            Trophy.current_holder_name.label("player_name"),
            func.count().label("trophy_count"),
        )
        .group_by(Trophy.current_holder_id, Trophy.current_holder_name)
        .order_by(func.count().desc())
    )
    by_server = await db.execute(
        select(
            Trophy.current_server_id.label("server_id"),
            func.count().label("trophy_count"),
        )
        .group_by(Trophy.current_server_id)
        .order_by(func.count().desc())
    )
    return {
        "by_player": [
            {"player_id": r.player_id, "player_name": r.player_name, "trophy_count": r.trophy_count}
            for r in by_player.all()
        ],
        "by_server": [
            {"server_id": r.server_id, "trophy_count": r.trophy_count}
            for r in by_server.all()
        ],
    }


@router.get("/{trophy_id}/history", summary="Transfer history for a trophy")
async def trophy_history(trophy_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    import uuid as _uuid
    t = await db.scalar(select(Trophy).where(Trophy.id == _uuid.UUID(trophy_id)))
    if not t:
        raise HTTPException(status_code=404, detail="Trophy not found")
    return {
        "id":                   str(t.id),
        "trophy_class":         t.trophy_class,
        "original_holder_name": t.original_holder_name,
        "original_server_id":   t.original_server_id,
        "original_claimed_at":  t.original_claimed_at.isoformat() if t.original_claimed_at else None,
        "current_holder_name":  t.current_holder_name,
        "current_server_id":    t.current_server_id,
        "transfer_history":     t.transfer_history or [],
    }
```

- [ ] **Step 4: Register the router in `app/main.py`**

In `backends/bosssignal-backend/app/main.py`:

Change the import line:
```python
from app.routers import bosses, events
```
to:
```python
from app.routers import bosses, events, trophies
```

Add after `app.include_router(bosses.router)`:
```python
app.include_router(trophies.router)
```

- [ ] **Step 5: Run tests**

Run: `cd bosssignal-backend && python -m pytest tests/ -v`
Expected: all tests PASS.

- [ ] **Step 6: Commit**

```bash
git add backends/bosssignal-backend/app/routers/trophies.py backends/bosssignal-backend/app/main.py backends/bosssignal-backend/tests/test_trophies.py
git commit -m "feat(api): add trophies router (list, leaderboard, history)"
```

---

## Phase 2 - Dashboard: Trophy Hall panel

### Task 6: Trophy Hall UI + SSE handler

**Files:**
- Modify: `backends/bosssignal-backend/static/dashboard.html`

Important: do NOT use `innerHTML` with any dynamic data (XSS vector). All dynamic text goes through `textContent` or `createElement`.

- [ ] **Step 1: Add Trophy Hall CSS**

In `backends/bosssignal-backend/static/dashboard.html`, find the CSS block (around line 118 near `.main-panel`). Insert this CSS block *immediately before* the `/* -- Header ---` comment:
```css
    /* -- Trophy Hall ----------------------------------- */
    .trophy-hall {
      background: var(--bg2);
      border-bottom: 1px solid var(--border);
      padding: 10px 24px;
      display: flex;
      gap: 12px;
      align-items: center;
      overflow-x: auto;
    }
    .trophy-hall-label {
      font-family: var(--font-mono);
      font-size: 11px;
      color: var(--muted);
      letter-spacing: 0.1em;
      text-transform: uppercase;
      flex-shrink: 0;
    }
    .trophy-card {
      background: var(--bg3);
      border: 1px solid var(--border);
      border-radius: 4px;
      padding: 8px 12px;
      min-width: 180px;
      display: flex;
      flex-direction: column;
      gap: 2px;
      flex-shrink: 0;
      transition: border-color 0.2s, box-shadow 0.2s;
    }
    .trophy-card.held  { border-color: var(--yellow); }
    .trophy-card.flash {
      border-color: var(--accent2);
      box-shadow: 0 0 12px rgba(249, 115, 22, 0.4);
    }
    .trophy-name   { font-family: var(--font-mono); font-size: 12px; color: var(--text); font-weight: 600; }
    .trophy-holder { font-family: var(--font-mono); font-size: 11px; color: var(--yellow); }
    .trophy-server { font-family: var(--font-mono); font-size: 10px; color: var(--muted); }
    .trophy-empty  { color: var(--muted); font-style: italic; font-size: 11px; }
```

- [ ] **Step 2: Add Trophy Hall markup**

Find `<div class="main-panel">` (around line 482). Insert *immediately before* it:
```html
  <section class="trophy-hall" id="trophy-hall">
    <div class="trophy-hall-label">Trophy Hall</div>
    <div class="trophy-empty" id="trophy-empty-msg">No trophies claimed yet - waiting for the first boss kill...</div>
  </section>
```

- [ ] **Step 3: Add rendering JS (textContent-only, no innerHTML)**

Find the existing SSE handler (grep for `'/api/v1/events/stream'` or `new EventSource`). Add this block *before* the SSE setup:
```javascript
  const TROPHY_DEFS = [
    { cls: "WarlordsCrown",     label: "Warlord's Crown" },
    { cls: "AbominationsJaw",   label: "Abomination's Jaw" },
    { cls: "HeavyTankPlate",    label: "Heavy Tank Plate" },
    { cls: "NecromancersSkull", label: "Necromancer's Skull" },
    { cls: "HuntersFang",       label: "Hunter's Fang" },
  ];

  function buildTrophyCard(def, held) {
    const card = document.createElement('div');
    card.className = 'trophy-card' + (held  ' held' : '');
    card.id = 'trophy-' + def.cls;

    const nameEl = document.createElement('div');
    nameEl.className = 'trophy-name';
    nameEl.textContent = def.label;
    card.appendChild(nameEl);

    const holderEl = document.createElement('div');
    holderEl.className = 'trophy-holder';
    holderEl.textContent = held  held.current_holder_name : '- unclaimed';
    card.appendChild(holderEl);

    const serverEl = document.createElement('div');
    serverEl.className = 'trophy-server';
    serverEl.textContent = held  held.current_server_id : '';
    card.appendChild(serverEl);

    return card;
  }

  async function refreshTrophyHall() {
    const hall     = document.getElementById('trophy-hall');
    const emptyMsg = document.getElementById('trophy-empty-msg');
    let trophies = [];
    try {
      const res = await fetch('/api/v1/trophies');
      trophies = await res.json();
    } catch (e) { return; }

    Array.from(hall.querySelectorAll('.trophy-card')).forEach(n => n.remove());

    if (!trophies.length) {
      emptyMsg.style.display = '';
      return;
    }
    emptyMsg.style.display = 'none';

    for (const def of TROPHY_DEFS) {
      const held = trophies.find(t => t.trophy_class === def.cls);
      hall.appendChild(buildTrophyCard(def, held));
    }
  }

  function flashTrophy(trophyClass) {
    const el = document.getElementById('trophy-' + trophyClass);
    if (!el) return;
    el.classList.add('flash');
    setTimeout(() => el.classList.remove('flash'), 2500);
  }
```

Find the existing SSE `onmessage` handler. Add this branch early in the handler (before any other event-type dispatch):
```javascript
        if (evt.event_type === 'trophy.awarded' || evt.event_type === 'trophy.transferred') {
          refreshTrophyHall();
          if (evt.data && evt.data.trophy_class) flashTrophy(evt.data.trophy_class);
          return;
        }
```

After the existing initial data-fetch calls on page load (they render server grid + kill feed), add:
```javascript
  refreshTrophyHall();
```

- [ ] **Step 4: Manually verify**

Start backend:
```bash
cd bosssignal-backend && python -m uvicorn app.main:app --host 127.0.0.1 --port 8080
```
Open `http://127.0.0.1:6700`. Expected: Trophy Hall strip appears above the server grid showing "No trophies claimed yet...".

In a second terminal, POST a synthetic trophy award:
```bash
ENC_ID=$(curl -s "http://127.0.0.1:6700/api/v1/bosseslimit=1" | python -c "import sys,json;d=json.load(sys.stdin);print(d[0]['id'] if d else '')")
echo "encounter: $ENC_ID"
curl -X POST "http://127.0.0.1:6700/api/v1/events" \
  -H "X-BossSignal-Secret: $BOSSSIGNAL_SECRET" \
  -H "Content-Type: application/json" \
  -d "{\"event_type\":\"trophy.awarded\",\"server_id\":\"server_03\",\"server_time\":9999,\"data\":{\"encounter_id\":\"$ENC_ID\",\"trophy_class\":\"WarlordsCrown\",\"boss_type\":\"ExampleBoss_01\",\"holder_id\":\"test\",\"holder_name\":\"TestPlayer\"}}"
```
Expected: Warlord's Crown card flashes orange, populates with "TestPlayer" and "server_03".

- [ ] **Step 5: Commit**

```bash
git add backends/bosssignal-backend/static/dashboard.html
git commit -m "feat(dashboard): add Trophy Hall panel with live SSE updates"
```

---

## Phase 3 - TrophyHunter Enforce mod

### Task 7: Scaffold mod directory + config.cpp

**Files:**
- Create: `mods/TrophyHunter/config.cpp`
- Create: `mods/TrophyHunter/config/bosses.json`
- Create: `mods/TrophyHunter/TrophyHunter.pboproject`
- Create: `mods/TrophyHunter/scripts/{3_game,4_world,5_mission}/.gitkeep`

- [ ] **Step 1: Create directory tree**

Run:
```bash
cd ~/Dayz/dayz
mkdir -p mods/TrophyHunter/scripts/3_game
mkdir -p mods/TrophyHunter/scripts/4_world
mkdir -p mods/TrophyHunter/scripts/5_mission
mkdir -p mods/TrophyHunter/config
touch mods/TrophyHunter/scripts/3_game/.gitkeep
touch mods/TrophyHunter/scripts/4_world/.gitkeep
touch mods/TrophyHunter/scripts/5_mission/.gitkeep
```

- [ ] **Step 2: Create `mods/TrophyHunter/config.cpp`**

Content:
```cpp
// ============================================================
// TrophyHunter - DayZ boss-trophy award mod
// Version : 0.1.0-alpha
// Requires: Community Framework (CF), BossSignal
//
// Drop @TrophyHunter/ into your server mods folder AFTER @BossSignal.
// Edit mods/TrophyHunter/config/bosses.json to map boss class names
// to trophy item classes.
// ============================================================

class CfgPatches {
    class TrophyHunter {
        units[]          = {};
        weapons[]        = {};
        requiredVersion  = 0.1;
        requiredAddons[] = {"Community_Framework", "BossSignal"};
    };
};

class CfgMods {
    class TrophyHunter {
        type         = "mod";
        author       = "TrophyHunter";
        name         = "TrophyHunter - Boss Kill Trophy System";
        version      = "0.1.0";
        dependencies[] = {"Community_Framework", "BossSignal", "Mission"};

        class defs {
            class gameScriptModule {
                value   = "";
                files[] = {"TrophyHunter/scripts/3_game"};
            };
            class worldScriptModule {
                value   = "";
                files[] = {"TrophyHunter/scripts/4_world"};
            };
            class missionScriptModule {
                value   = "";
                files[] = {"TrophyHunter/scripts/5_mission"};
            };
        };
    };
};

class CfgVehicles {
    // Trophies - reskins of existing DayZ items for MVP.
    // Each maps to a boss class in config/bosses.json.

    class Inventory_Base;

    class WarlordsCrown : Inventory_Base {
        scope = 2;
        displayName = "Warlord's Crown";
        descriptionShort = "A bloodied iron crown, torn from the Warlord's head.";
        model = "\dz\gear\cooking\sharpeningstone.p3d";
        weight = 800;
        itemSize[] = {1,1};
        inventorySlot[] = {"Armband"};
        varQuantityInit = 1;
        varQuantityMin = 0;
        varQuantityMax = 1;
    };

    class AbominationsJaw : Inventory_Base {
        scope = 2;
        displayName = "Abomination's Jaw";
        descriptionShort = "The oversized jawbone of the Abomination.";
        model = "\dz\gear\cooking\sharpeningstone.p3d";
        weight = 1200;
        itemSize[] = {2,1};
        inventorySlot[] = {"Armband"};
        varQuantityInit = 1;
        varQuantityMin = 0;
        varQuantityMax = 1;
    };

    class HeavyTankPlate : Inventory_Base {
        scope = 2;
        displayName = "Heavy Tank Plate";
        descriptionShort = "A dense armor plate from the Tank boss.";
        model = "\dz\gear\cooking\sharpeningstone.p3d";
        weight = 3500;
        itemSize[] = {2,2};
        inventorySlot[] = {"Body"};
        varQuantityInit = 1;
        varQuantityMin = 0;
        varQuantityMax = 1;
    };

    class NecromancersSkull : Inventory_Base {
        scope = 2;
        displayName = "Necromancer's Skull";
        descriptionShort = "A glowing skull taken from the Necromancer.";
        model = "\dz\gear\cooking\sharpeningstone.p3d";
        weight = 600;
        itemSize[] = {1,1};
        inventorySlot[] = {"Armband"};
        varQuantityInit = 1;
        varQuantityMin = 0;
        varQuantityMax = 1;
    };

    class HuntersFang : Inventory_Base {
        scope = 2;
        displayName = "Hunter's Fang";
        descriptionShort = "A pendant carved from the Hunter Elite's claw.";
        model = "\dz\gear\cooking\sharpeningstone.p3d";
        weight = 100;
        itemSize[] = {1,1};
        inventorySlot[] = {"Armband"};
        varQuantityInit = 1;
        varQuantityMin = 0;
        varQuantityMax = 1;
    };
};
```

> `sharpeningstone.p3d` is a safe placeholder. Real-play validation flushes out the right model paths for the final polish.

- [ ] **Step 3: Create `mods/TrophyHunter/config/bosses.json`**

Content (the `class` values are illustrative placeholders - substitute the real
entity classnames from your own boss mod or a licensed third-party boss pack;
TrophyHunter ships no boss entities of its own):
```json
{
  "bosses": [
    {"class": "ExampleBoss_01",  "trophy": "WarlordsCrown"},
    {"class": "ExampleBoss_02",  "trophy": "AbominationsJaw"},
    {"class": "ExampleBoss_03",  "trophy": "HeavyTankPlate"},
    {"class": "ExampleBoss_04",  "trophy": "NecromancersSkull"},
    {"class": "ExampleBoss_05",  "trophy": "HuntersFang"}
  ]
}
```

- [ ] **Step 4: Create `mods/TrophyHunter/TrophyHunter.pboproject`**

Copy the content of `mods/BossSignal/BossSignal.pboproject` verbatim, then replace every occurrence of `BossSignal` with `TrophyHunter`, and save as `mods/TrophyHunter/TrophyHunter.pboproject`.

- [ ] **Step 5: Commit**

```bash
git add mods/TrophyHunter/
git commit -m "feat(mod): scaffold TrophyHunter mod + 5 trophy item classes + boss allowlist"
```

---

### Task 8: `TrophyHunterConfig.c`

**Files:**
- Create: `mods/TrophyHunter/scripts/3_game/TrophyHunterConfig.c`

- [ ] **Step 1: Create the file**

Reference: `mods/BossSignal/scripts/3_game/BossSignalConfig.c`. Same shape. Content:
```cpp
// ============================================================
// TrophyHunterConfig - static configuration class (load order 3_game).
// Mirror of BossSignalConfig - same shared-secret header convention.
// ============================================================
class TrophyHunterConfig {
    static string BACKEND_URL   = "http://localhost:6700";
    // CHANGE_ME: inject the shared secret at build time via env substitution
    // (e.g. ${BOSSSIGNAL_SECRET}). Never commit a real secret. Treat an unset
    // or default value as misconfiguration and refuse to send authenticated calls.
    static string SHARED_SECRET = "CHANGE_ME";
    static string SERVER_ID     = "server_01";
    static string VERSION       = "0.1.0";

    // Grace period (seconds) during which a trophy cannot be looted from
    // a corpse. See design spec section 2.
    static int  GRACE_SECONDS   = 600;

    // Off by default for production. Enable only for local debugging.
    static bool DEBUG_LOGGING   = false;

    static string BOSSES_JSON_PATH = "$mpmissions:TrophyHunter/bosses.json";

    static void Load() {
        TrophyHunterConfig.Log("Config loaded | Server=" + SERVER_ID
            + " | URL=" + BACKEND_URL
            + " | v" + VERSION);
    }

    static void Log(string msg)  { if (TrophyHunterConfig.DEBUG_LOGGING) Print("[TrophyHunter] " + msg); }
    static void Warn(string msg) { Print("[TrophyHunter][WARN] "  + msg); }
    static void Err(string msg)  { Print("[TrophyHunter][ERROR] " + msg); }
};
```

- [ ] **Step 2: Commit**

```bash
git add mods/TrophyHunter/scripts/3_game/TrophyHunterConfig.c
git commit -m "feat(mod): add TrophyHunterConfig (mirror of BossSignalConfig)"
```

---

### Task 9: `TrophyHunterClient.c` - HTTP helper

**Files:**
- Create: `mods/TrophyHunter/scripts/4_world/TrophyHunterClient.c`

- [ ] **Step 1: Open reference file**

Open `mods/BossSignal/scripts/4_world/BossSignalClient.c`. Note: `RestContext`, `RestCallback`, `SetHeader`, `POST`, `GET`. Mirror that pattern.

- [ ] **Step 2: Create the file**

Content:
```cpp
// ============================================================
// TrophyHunterClient - REST helper (load order 4_world, server only).
//
// Two operations:
//   Post(endpoint, bodyJson)          - fire-and-forget POST w/ shared secret
//   GetTopDamagerAlias(fullUrl, cb)   - async GET; TrophyAwarder is the callback
// ============================================================
class TrophyHunterClient {
    protected ref RestContext m_Rest;
    protected bool            m_Ready;

    void TrophyHunterClient() {
        m_Ready = false;
        if (GetGame().IsServer()) {
            RestApi api = GetRestApi();
            if (api) {
                m_Rest  = api.GetRestContext(TrophyHunterConfig.BACKEND_URL);
                m_Ready = (m_Rest != null);
            }
        }
        if (!m_Ready) TrophyHunterConfig.Err("REST not available - trophies will not fire.");
    }

    bool IsReady() { return m_Ready; }

    void Post(string endpoint, string bodyJson) {
        if (!m_Ready) return;
        m_Rest.SetHeader("Content-Type: application/json");
        m_Rest.SetHeader("X-BossSignal-Secret: " + TrophyHunterConfig.SHARED_SECRET);
        m_Rest.SetHeader("X-BossSignal-Server: " + TrophyHunterConfig.SERVER_ID);
        m_Rest.POST(new TrophyHunterPostCB(), endpoint, bodyJson);
    }

    void GetTopDamagerAlias(string fullEndpoint, TrophyHunterCallback cb) {
        if (!m_Ready) { cb.OnTopDamagerFailed("client_not_ready"); return; }
        m_Rest.SetHeader("X-BossSignal-Server: " + TrophyHunterConfig.SERVER_ID);
        m_Rest.GET(new TrophyHunterGetCB(cb), fullEndpoint);
    }
};

class TrophyHunterPostCB extends RestCallback {
    override void OnError(int errorCode) { TrophyHunterConfig.Warn("POST error "   + errorCode); }
    override void OnTimeout()            { TrophyHunterConfig.Warn("POST timeout"); }
    override void OnSuccess(string response, int errorCode) {}
}

class TrophyHunterGetCB extends RestCallback {
    protected ref TrophyHunterCallback m_UserCB;
    void TrophyHunterGetCB(TrophyHunterCallback cb) { m_UserCB = cb; }
    override void OnError(int errorCode) { if (m_UserCB) m_UserCB.OnTopDamagerFailed("http_error_" + errorCode); }
    override void OnTimeout()            { if (m_UserCB) m_UserCB.OnTopDamagerFailed("timeout"); }
    override void OnSuccess(string response, int errorCode) {
        if (m_UserCB) m_UserCB.OnTopDamagerSuccess(response);
    }
}

class TrophyHunterCallback {
    void OnTopDamagerSuccess(string jsonBody) {}
    void OnTopDamagerFailed(string reason)   {}
}
```

> DEVLOG-TH-001: the `RestApi`/`RestContext` calls are the same ones BossSignalClient uses. If BossSignal works, this works.

- [ ] **Step 3: Commit**

```bash
git add mods/TrophyHunter/scripts/4_world/TrophyHunterClient.c
git commit -m "feat(mod): add TrophyHunterClient (POST + async GET helpers)"
```

---

### Task 10: `TrophyProvenance.c`

**Files:**
- Create: `mods/TrophyHunter/scripts/5_mission/TrophyProvenance.c`

- [ ] **Step 1: Create the file**

Content:
```cpp
// ============================================================
// TrophyProvenance - stamp/read provenance attributes on a trophy item.
// Load order : 5_mission (server authoritative).
//
// MVP uses an in-memory scratchpad keyed by entity ID. Survives the
// server session. Backend is the long-term source of truth - every
// provenance read can fall back to GET /api/v1/trophies/{id}/history.
//
// DEVLOG-TH-002: validate that a looted trophy retains its entity ID
// across the loot transfer. If not, rehydrate from the backend on
// first GetAttr after a loot event.
// ============================================================
class TrophyProvenance {
    static const string ATTR_ORIGINAL_HOLDER  = "TH_OriginalHolder";
    static const string ATTR_ORIGINAL_SERVER  = "TH_OriginalServer";
    static const string ATTR_ORIGINAL_AT      = "TH_OriginalClaimedAt";
    static const string ATTR_GRACE_UNTIL      = "TH_GraceUntil";
    static const string ATTR_CURRENT_HOLDER   = "TH_CurrentHolder";
    static const string ATTR_CURRENT_SERVER   = "TH_CurrentServer";
    static const string ATTR_TROPHY_ID        = "TH_TrophyId";

    static void Stamp(EntityAI item,
                      string trophyId,
                      string originalHolder,
                      string originalServer,
                      string originalAtISO,
                      int    graceUntilUnix,
                      string currentHolder,
                      string currentServer)
    {
        if (!item) return;
        TrophyAttrScratchpad.Set(item, ATTR_TROPHY_ID,       trophyId);
        TrophyAttrScratchpad.Set(item, ATTR_ORIGINAL_HOLDER, originalHolder);
        TrophyAttrScratchpad.Set(item, ATTR_ORIGINAL_SERVER, originalServer);
        TrophyAttrScratchpad.Set(item, ATTR_ORIGINAL_AT,     originalAtISO);
        TrophyAttrScratchpad.Set(item, ATTR_GRACE_UNTIL,     graceUntilUnix.ToString());
        TrophyAttrScratchpad.Set(item, ATTR_CURRENT_HOLDER,  currentHolder);
        TrophyAttrScratchpad.Set(item, ATTR_CURRENT_SERVER,  currentServer);
    }

    static string Read(EntityAI item, string attr) {
        return TrophyAttrScratchpad.Get(item, attr);
    }

    static bool InGrace(EntityAI item) {
        string g = Read(item, ATTR_GRACE_UNTIL);
        if (g.Length() == 0) return false;
        int until = g.ToInt();
        int now   = System.GetUnixTime();
        return now < until;
    }
}

// Simple in-memory store keyed by entity ID.
// Persists for the server session. Rehydrate from backend if needed.
class TrophyAttrScratchpad {
    static ref map<string, ref map<string, string>> s_Data;

    protected static void Ensure() {
        if (!s_Data) s_Data = new map<string, ref map<string, string>>();
    }

    protected static string KeyFor(EntityAI item) {
        if (!item) return "";
        return item.GetID().ToString();
    }

    static void Set(EntityAI item, string attr, string value) {
        Ensure();
        string k = KeyFor(item);
        if (k.Length() == 0) return;
        if (!s_Data.Contains(k)) s_Data.Set(k, new map<string, string>());
        s_Data.Get(k).Set(attr, value);
    }

    static string Get(EntityAI item, string attr) {
        Ensure();
        string k = KeyFor(item);
        if (k.Length() == 0) return "";
        if (!s_Data.Contains(k)) return "";
        map<string, string> bucket = s_Data.Get(k);
        if (!bucket.Contains(attr)) return "";
        return bucket.Get(attr);
    }
}
```

- [ ] **Step 2: Commit**

```bash
git add mods/TrophyHunter/scripts/5_mission/TrophyProvenance.c
git commit -m "feat(mod): add TrophyProvenance with scratchpad-backed attributes"
```

---

### Task 11: `TrophyAwarder.c`

**Files:**
- Create: `mods/TrophyHunter/scripts/5_mission/TrophyAwarder.c`

- [ ] **Step 1: Create the file**

Content:
```cpp
// ============================================================
// TrophyAwarder - async orchestration: boss death -> top-damager
// lookup -> item spawn -> provenance stamp -> backend POST.
// Load order : 5_mission (server-side).
// ============================================================
class TrophyAwarder extends TrophyHunterCallback {
    protected ref map<string, ref PendingAward> m_Pending;
    protected ref TrophyHunterClient            m_Client;
    protected ref map<string, string>           m_BossToTrophy;

    void Init(TrophyHunterClient client, map<string, string> bossMap) {
        m_Pending      = new map<string, ref PendingAward>();
        m_Client       = client;
        m_BossToTrophy = bossMap;
    }

    // Called by TrophyHunterMission.OnEntityKilled after allowlist hit.
    void HandleBossKill(EntityAI bossEntity, string bossClassName, string inGameBossId) {
        if (!m_BossToTrophy.Contains(bossClassName)) {
            TrophyHunterConfig.Warn("No trophy mapping for class: " + bossClassName);
            return;
        }
        if (inGameBossId.Length() == 0) {
            TrophyHunterConfig.Warn("Missing in-game boss_id for " + bossClassName + " - skipping.");
            return;
        }
        string trophyClass = m_BossToTrophy.Get(bossClassName);
        string skip        = CollectExistingHolders(trophyClass);

        // Remember what we're awarding for when the async reply comes back.
        string pendingKey = inGameBossId;
        m_Pending.Set(pendingKey, new PendingAward(pendingKey, bossClassName, trophyClass));

        string endpoint = "/api/v1/servers/" + TrophyHunterConfig.SERVER_ID
            + "/active-boss/" + inGameBossId + "/top-damager";
        if (skip.Length() > 0) endpoint += "skip_holders=" + skip;
        m_Client.GetTopDamagerAlias(endpoint, this);
    }

    override void OnTopDamagerSuccess(string jsonBody) {
        string encUUID = TrophyJSON.Field(jsonBody, "encounter_id");
        string pid     = TrophyJSON.Field(jsonBody, "player_id");
        string pname   = TrophyJSON.Field(jsonBody, "player_name");

        // Find the matching pending award by iterating (we stored by bossId, not encUUID).
        ref PendingAward pa = TakeFirstPending();
        if (!pa) return;

        PlayerBase player = FindOnlinePlayerById(pid);
        if (!player) {
            TrophyHunterConfig.Warn("Top damager " + pname + " offline - skipping award.");
            PostSkipEvent(encUUID, pa.trophyClass, "top_damager_offline");
            return;
        }

        EntityAI trophy = SpawnTrophyForPlayer(player, pa.trophyClass);
        if (!trophy) {
            PostSkipEvent(encUUID, pa.trophyClass, "spawn_failed");
            return;
        }

        int nowUnix  = System.GetUnixTime();
        int graceEnd = nowUnix + TrophyHunterConfig.GRACE_SECONDS;
        string clientNonce = "local-" + encUUID + "-" + pa.trophyClass;

        TrophyProvenance.Stamp(
            trophy, clientNonce, pname, TrophyHunterConfig.SERVER_ID,
            TimeFormatter.NowISO(), graceEnd, pname, TrophyHunterConfig.SERVER_ID);

        Announce(pname, pa.trophyClass);
        PostAwardEvent(encUUID, pa.trophyClass, pa.bossClassName, pid, pname);
    }

    override void OnTopDamagerFailed(string reason) {
        TrophyHunterConfig.Warn("Top-damager lookup failed: " + reason);
        TakeFirstPending();  // clear it so we don't leak
    }

    // -- Helpers ----------------------------------------------

    protected ref PendingAward TakeFirstPending() {
        if (!m_Pending || m_Pending.Count() == 0) return null;
        string k = m_Pending.GetKey(0);
        ref PendingAward pa = m_Pending.Get(k);
        m_Pending.Remove(k);
        return pa;
    }

    protected string CollectExistingHolders(string trophyClass) {
        array<Man> players = new array<Man>();
        GetGame().GetPlayers(players);
        string ids = "";
        foreach (Man m : players) {
            PlayerBase pb = PlayerBase.Cast(m);
            if (!pb) continue;
            if (PlayerCarriesTrophy(pb, trophyClass)) {
                if (ids.Length() > 0) ids += ",";
                ids += pb.GetIdentity().GetPlayerId();
            }
        }
        return ids;
    }

    protected bool PlayerCarriesTrophy(PlayerBase pb, string trophyClass) {
        array<EntityAI> items = new array<EntityAI>();
        pb.GetInventory().EnumerateInventory(InventoryTraversalType.PREORDER, items);
        foreach (EntityAI item : items) {
            if (item && item.GetType() == trophyClass) return true;
        }
        return false;
    }

    protected PlayerBase FindOnlinePlayerById(string playerId) {
        array<Man> players = new array<Man>();
        GetGame().GetPlayers(players);
        foreach (Man m : players) {
            PlayerBase pb = PlayerBase.Cast(m);
            if (!pb || !pb.GetIdentity()) continue;
            if (pb.GetIdentity().GetPlayerId() == playerId) return pb;
        }
        return null;
    }

    protected EntityAI SpawnTrophyForPlayer(PlayerBase pb, string trophyClass) {
        EntityAI t = pb.GetInventory().CreateInInventory(trophyClass);
        if (t) return t;
        vector pos = pb.GetPosition();
        return EntityAI.Cast(GetGame().CreateObject(trophyClass, pos, false, false, true));
    }

    protected void Announce(string playerName, string trophyClass) {
        string msg = playerName + " has claimed the " + TrophyLabel(trophyClass)
                   + " on " + TrophyHunterConfig.SERVER_ID;
        // DEVLOG-TH-004: confirm global-chat broadcast API on first play.
        GetGame().ChatPlayer(msg);
    }

    protected string TrophyLabel(string cls) {
        if (cls == "WarlordsCrown")     return "Warlord's Crown";
        if (cls == "AbominationsJaw")   return "Abomination's Jaw";
        if (cls == "HeavyTankPlate")    return "Heavy Tank Plate";
        if (cls == "NecromancersSkull") return "Necromancer's Skull";
        if (cls == "HuntersFang")       return "Hunter's Fang";
        return cls;
    }

    protected void PostAwardEvent(string encUUID, string trophyClass, string bossClass,
                                  string holderId, string holderName) {
        string body = "{"
            + "\"event_type\":\"trophy.awarded\","
            + "\"server_id\":\"" + TrophyHunterConfig.SERVER_ID + "\","
            + "\"server_time\":" + GetGame().GetTime().ToString() + ","
            + "\"data\":{"
                + "\"encounter_id\":\"" + encUUID + "\","
                + "\"trophy_class\":\"" + trophyClass + "\","
                + "\"boss_type\":\"" + bossClass + "\","
                + "\"holder_id\":\"" + holderId + "\","
                + "\"holder_name\":\"" + holderName + "\""
            + "}"
            + "}";
        m_Client.Post("/api/v1/events", body);
    }

    protected void PostSkipEvent(string encUUID, string trophyClass, string reason) {
        string body = "{"
            + "\"event_type\":\"trophy.skipped\","
            + "\"server_id\":\"" + TrophyHunterConfig.SERVER_ID + "\","
            + "\"server_time\":" + GetGame().GetTime().ToString() + ","
            + "\"data\":{"
                + "\"encounter_id\":\"" + encUUID + "\","
                + "\"trophy_class\":\"" + trophyClass + "\","
                + "\"reason\":\"" + reason + "\""
            + "}"
            + "}";
        m_Client.Post("/api/v1/events", body);
    }
}

class PendingAward {
    string encounterKey;
    string bossClassName;
    string trophyClass;

    void PendingAward(string key, string boss, string trophy) {
        encounterKey  = key;
        bossClassName = boss;
        trophyClass   = trophy;
    }
}

// Minimal JSON field extractor. Only for our known server responses.
class TrophyJSON {
    static string Field(string json, string key) {
        string needle = "\"" + key + "\":";
        int idx = json.IndexOf(needle);
        if (idx < 0) return "";
        int start = idx + needle.Length();
        while (start < json.Length() && (json.Get(start) == " " || json.Get(start) == "\"")) start++;
        int end = start;
        while (end < json.Length() && json.Get(end) != "\"" && json.Get(end) != "," && json.Get(end) != "}") end++;
        return json.Substring(start, end - start);
    }
}

class TimeFormatter {
    static string NowISO() {
        int y, mo, d, h, mi, s;
        GetYearMonthDay(y, mo, d);
        GetHourMinuteSecond(h, mi, s);
        return string.Format("%1-%2-%3T%4:%5:%6Z",
            y,
            Pad(mo), Pad(d), Pad(h), Pad(mi), Pad(s));
    }
    static string Pad(int n) { if (n < 10) return "0" + n.ToString(); return n.ToString(); }
}
```

> DEVLOG-TH-003/-004 flag in-game API signatures that need first-play validation (broadcast chat, inventory enumeration). They mirror patterns already used in BossSignalEmitter.c.

- [ ] **Step 2: Commit**

```bash
git add mods/TrophyHunter/scripts/5_mission/TrophyAwarder.c
git commit -m "feat(mod): add TrophyAwarder (lookup -> spawn -> stamp -> POST)"
```

---

### Task 12: `TrophyHunterMission.c` - entry point

**Files:**
- Create: `mods/TrophyHunter/scripts/5_mission/TrophyHunterMission.c`

- [ ] **Step 1: Create the file**

Content:
```cpp
// ============================================================
// TrophyHunterMission - mission hook (server-only, load order 5_mission).
//
// Subclasses MissionServer. Loads the allowlist at OnInit, then on
// OnEntityKilled checks the dead entity's class against it and, on hit,
// kicks off TrophyAwarder.
// ============================================================
modded class MissionServer {
    ref TrophyHunterClient m_TH_Client;
    ref TrophyAwarder      m_TH_Awarder;
    ref map<string,string> m_TH_BossMap;

    override void OnInit() {
        super.OnInit();
        TrophyHunterConfig.Load();

        m_TH_BossMap = LoadBossMap(TrophyHunterConfig.BOSSES_JSON_PATH);
        if (m_TH_BossMap.Count() == 0) {
            TrophyHunterConfig.Err("Boss allowlist is empty. Edit config/bosses.json and restart.");
            return;
        }

        m_TH_Client  = new TrophyHunterClient();
        if (!m_TH_Client.IsReady()) {
            TrophyHunterConfig.Err("REST client not ready - trophies disabled.");
            return;
        }

        m_TH_Awarder = new TrophyAwarder();
        m_TH_Awarder.Init(m_TH_Client, m_TH_BossMap);

        TrophyHunterConfig.Log("Ready. Watching " + m_TH_BossMap.Count() + " boss classes.");
    }

    override void OnEntityKilled(EntityAI victim, EntityAI killer, Man killerPlayer) {
        super.OnEntityKilled(victim, killer, killerPlayer);
        if (!victim || !m_TH_Awarder) return;

        string cls = victim.GetType();
        if (!m_TH_BossMap.Contains(cls)) return;

        string bossId = BossSignalAPI.GetEncounterIdForBoss(victim);
        m_TH_Awarder.HandleBossKill(victim, cls, bossId);
    }

    protected map<string,string> LoadBossMap(string path) {
        map<string,string> out = new map<string,string>();
        ref BossMapFile f = new BossMapFile();
        if (!JsonFileLoader<BossMapFile>.JsonLoadFile(path, f) || !f.bosses) {
            TrophyHunterConfig.Err("Failed to load " + path);
            return out;
        }
        foreach (BossMapEntry e : f.bosses) {
            if (e.cls.Length() > 0 && e.trophy.Length() > 0) out.Set(e.cls, e.trophy);
        }
        return out;
    }
};

class BossMapFile {
    ref array<ref BossMapEntry> bosses;
}

// DEVLOG-TH-005: if "class" JSON key trips the Enforce parser, rename
// the JSON key to "classname" and the field name below to match.
class BossMapEntry {
    string cls;
    string trophy;
}
```

- [ ] **Step 2: Commit**

```bash
git add mods/TrophyHunter/scripts/5_mission/TrophyHunterMission.c
git commit -m "feat(mod): add TrophyHunterMission entry point"
```

---

### Task 13: Add `GetEncounterIdForBoss()` to BossSignal

**Files:**
- Modify: `mods/BossSignal/scripts/4_world/BossSignalAPI.c`
- Modify: `mods/BossSignal/scripts/5_mission/BossSignalEmitter.c`

- [ ] **Step 1: Add the public API method**

In `mods/BossSignal/scripts/4_world/BossSignalAPI.c`, inside the `BossSignalAPI` class block, append:
```cpp
    // -- GetEncounterIdForBoss ---------------------------------
    // Returns the backend-known in-game bossId string for the given boss
    // entity, or "" if no active encounter is being tracked.
    // Used by TrophyHunter at kill-time to look up the top damager via the
    // backend's /api/v1/servers/{server_id}/active-boss/{boss_id}/top-damager
    // alias endpoint.
    static string GetEncounterIdForBoss(EntityAI bossEntity) {
        if (!bossEntity) return "";
        if (!g_BossSignalEmitter) return "";
        return g_BossSignalEmitter.GetEncounterIdForBoss(bossEntity);
    }
```

- [ ] **Step 2: Add the resolver on `BossSignalEmitter`**

In `mods/BossSignal/scripts/5_mission/BossSignalEmitter.c`, inside the `BossSignalEmitter` class, append (near existing `OnEntityKilled`):
```cpp
    // Integration hook for TrophyHunter.
    string GetEncounterIdForBoss(EntityAI bossEntity) {
        if (!bossEntity) return "";
        string bossId = bossEntity.GetID().ToString();
        if (!m_ActiveBosses.Contains(bossId)) return "";
        BossEncounter enc = m_ActiveBosses.Get(bossId);
        if (!enc) return "";
        return enc.m_BossId;
    }
```

- [ ] **Step 3: Commit**

```bash
git add mods/BossSignal/scripts/4_world/BossSignalAPI.c mods/BossSignal/scripts/5_mission/BossSignalEmitter.c
git commit -m "feat(mod): expose GetEncounterIdForBoss for TrophyHunter integration"
```

---

## Phase 4 - Docs + simulator

### Task 14: Pre-deployment checklist

**Files:**
- Create: `docs/TROPHYHUNTER-PREDEPLOY.md`

- [ ] **Step 1: Write the doc**

Content:
```markdown
# TrophyHunter - Pre-Deployment Checklist

Everything here blocks real-network deployment but does NOT block local dev.

## 1. Identify the external boss-content mod
- [ ] Obtain the exact Workshop mod name, ID, or server mod list.
- [ ] Find the mod on Steam Workshop and record attribution metadata.
- [ ] Subscribe + let DayZ auto-download. Or unpack the `.pbo` with DayZ Tools.
- [ ] Read the unpacked `config.cpp`; record every boss class name.

## 2. Populate `bosses.json`
- [ ] Replace placeholder class names in `mods/TrophyHunter/config/bosses.json`
      with the external mod's real boss class names.
- [ ] If it has more than 5 boss types, extend `mods/TrophyHunter/config.cpp`
      and dashboard's `TROPHY_DEFS` to match.

## 3. Confirm shared-character hive
- [ ] Check whether the target server network has a shared player-character hive.
- [ ] If not, trophies are server-local for MVP (design spec ?2 allows this).

## 4. Confirm damage-tracking compatibility
- [ ] Join a target test server. Watch BossSignal RPT lines.
- [ ] Verify `boss.killed` events record non-empty `participants` arrays.
- [ ] If empty, extend BossSignal's damage tracker (DEVLOG follow-up).

## 5. Sign the PBO
- [ ] Install DayZ Tools from Steam.
- [ ] Run `build-pipeline/sign-keygen.bat` once.
- [ ] Pack: `build-pipeline/pack.bat TrophyHunter`
- [ ] Sign: `build-pipeline/sign.bat TrophyHunter.pbo`
- [ ] Never commit `*.biprivatekey`.

## 6. Test server deploy
- [ ] Host a local DayZ server w/ BossSignal + TrophyHunter + a test boss mod.
- [ ] Spawn -> damage -> kill -> verify trophy lands + dashboard flashes.
- [ ] Walk DEVLOG-TH-001 through DEVLOG-TH-006.

## 7. Operator deployment
- [ ] Coordinate with the server operator to install and key-whitelist the mod.
```

- [ ] **Step 2: Commit**

```bash
git add docs/TROPHYHUNTER-PREDEPLOY.md
git commit -m "docs: add TrophyHunter pre-deployment checklist"
```

---

### Task 15: Extend simulator with trophy award

**Files:**
- Modify: `test-harness/simulate_boss_encounter.py`

- [ ] **Step 1: Locate the kill emit**

Grep for the `boss.killed` emit in `test-harness/simulate_boss_encounter.py` (likely a `_post` or `requests.post` to `/api/v1/events`).

- [ ] **Step 2: Add the trophy award right after the kill post**

Immediately after the `boss.killed` POST succeeds, append this block (adapt variable names to the existing code - `participants`, `boss_classname`, `self.server_id`, `self.base_url`, `self._post` or equivalent):
```python
        # Boss entity classnames are illustrative placeholders; substitute the
        # real classnames from your own / a licensed boss mod.
        trophy_map = {
            "ExampleBoss_01":  "WarlordsCrown",
            "ExampleBoss_02":  "AbominationsJaw",
            "ExampleBoss_03":  "HeavyTankPlate",
            "ExampleBoss_04":  "NecromancersSkull",
            "ExampleBoss_05":  "HuntersFang",
        }
        trophy_class = trophy_map.get(boss_classname)
        if trophy_class and participants:
            top = max(participants, key=lambda p: p["damage_dealt"])
            import requests as _rq
            try:
                rows = _rq.get(
                    f"{self.base_url}/api/v1/bosses",
                    params={"server_id": self.server_id, "limit": 1},
                    timeout=3,
                ).json()
                if rows and rows[0].get("id"):
                    enc_id = rows[0]["id"]
                    self._post("/api/v1/events", {
                        "event_type": "trophy.awarded",
                        "server_id":  self.server_id,
                        "server_time": server_time,
                        "data": {
                            "encounter_id": enc_id,
                            "trophy_class": trophy_class,
                            "boss_type":    boss_classname,
                            "holder_id":    top["player_id"],
                            "holder_name":  top["player_name"],
                        },
                    })
                    print(f"  ok [{self.server_id}] trophy.awarded {trophy_class} -> {top['player_name']}")
            except Exception as _e:
                print(f"  ! trophy lookup failed: {_e}")
```

- [ ] **Step 3: Manually verify**

Backend running already from previous tasks. In a fresh terminal:
```bash
cd test-harness
PYTHONIOENCODING=utf-8 python -u simulate_boss_encounter.py \
  --url http://127.0.0.1:6700 \
  --secret "$BOSSSIGNAL_SECRET" \
  --all-servers --delay 2
```
Open `http://127.0.0.1:6700`. Expected: Trophy Hall populates with 5 different trophy cards as bosses die across all servers; cards flash orange on award.

- [ ] **Step 4: Commit**

```bash
git add test-harness/simulate_boss_encounter.py
git commit -m "test(sim): emit trophy.awarded after each boss.killed for dashboard QA"
```

---

### Task 16: Update README and HANDOFF

**Files:**
- Modify: `README.md`
- Modify: `HANDOFF.md`

- [ ] **Step 1: Update README**

In `README.md`, find the repo-layout fenced code block (starts with `mods/BossSignal/`). Add this line after the `backends/bosssignal-backend/` line:
```
mods/TrophyHunter/        TrophyHunter Enforce mod - awards top-damage player a visible trophy on boss kill
```

In the Status section, append:
```
- [done] TrophyHunter mod source + backend endpoints + dashboard panel - compile-ready
- [pending] TrophyHunter first-play validation - paired with BossSignal DEVLOG items
- [pending] Identify target boss class names - see docs/TROPHYHUNTER-PREDEPLOY.md
```

- [ ] **Step 2: Update HANDOFF**

In `HANDOFF.md`, in the "What's done" list, append:
```
- TrophyHunter mod - awards top-damage player a unique carryable trophy on boss kill.
  Backend endpoints, dashboard Trophy Hall panel, and simulator integration all shipped.
  Pre-deployment checklist in docs/TROPHYHUNTER-PREDEPLOY.md.
```

In "What's NOT done yet", append:
```
- TrophyHunter first-play validation - pairs with BossSignal DEVLOG items plus
  new DEVLOG-TH-001 through DEVLOG-TH-006 (grep TrophyHunter's .c files).
- External boss-mod class names - blocks mods/TrophyHunter/config/bosses.json population.
```

In "Key file-level pointers", append rows:
```
| Add a new trophy type | `mods/TrophyHunter/config.cpp` class block + `dashboard.html` TROPHY_DEFS + `bosses.json` |
| Change who gets a trophy | `backends/bosssignal-backend/app/routers/bosses.py` top-damager handler |
| Validate TrophyHunter assumptions | grep `DEVLOG-TH-` across `mods/TrophyHunter/` |
```

- [ ] **Step 3: Commit**

```bash
git add README.md HANDOFF.md
git commit -m "docs: reference TrophyHunter in README and HANDOFF"
```

---

## Final verification

- [ ] **Run the full test suite**

```bash
cd bosssignal-backend && python -m pytest tests/ -v
```
Expected: all tests PASS.

- [ ] **End-to-end stack run**

Terminal 1: `cd bosssignal-backend && python -m uvicorn app.main:app --host 127.0.0.1 --port 8080`
Terminal 2: `cd test-harness && PYTHONIOENCODING=utf-8 python -u simulate_boss_encounter.py --url http://127.0.0.1:6700 --secret "$BOSSSIGNAL_SECRET" --all-servers --delay 2`
Browser: `http://127.0.0.1:6700`

Expected:
- Server grid populates with the configured servers.
- Kill feed scrolls as bosses die.
- Trophy Hall strip populates with 5 unique trophies as different boss types die.
- Each trophy award flashes the card orange for ~2.5s.

- [ ] **Clean working tree**

```bash
git status
```
Expected: clean tree on `bosssignal` branch, all task commits landed.

---

## Not in this plan (deferred)

- Custom 3D models for trophies (replace `sharpeningstone.p3d` placeholders).
- Tiered trophy variants (gold/silver/bronze for multi-kills).
- Trader NPC integration.
- Dashboard provenance modal on trophy click.
- Steam Workshop publication.
- Fallback damage-tracking path for boss mods bypassing standard hooks.
- **Grace-period corpse removal mechanic** (spec ?5 row "Holder killed inside grace period").
  Requires an `OnPlayerKilled` hook, trophy removal from the corpse, and a
  queued-restore that survives login cycles. Design is solid, implementation
  needs first-play insight into how DayZ 1.2x fires player-death events and
  how persistence handles the queued restore. Deferred to v0.2 after
  first-play validates the basic award flow. For MVP the 10-min grace window
  only gates the "trophy is immune to being dropped" behavior client-side;
  corpse-looting during grace will just fall through normally.
