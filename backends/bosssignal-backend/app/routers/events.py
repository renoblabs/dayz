"""
/api/v1/events

POST  /api/v1/events        — receive events from game servers (Enforce mod)
GET   /api/v1/events        — query event history (dashboard, admin)
GET   /api/v1/events/stream — SSE live event feed
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import time
import uuid
from datetime import datetime, timezone
from typing import AsyncGenerator, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.database import get_db
from app.db.models import BossEncounter, Event, Player, PlayerSession, ServerStatus, Trophy

router = APIRouter(prefix="/api/v1/events", tags=["events"])
settings = get_settings()

# ── In-memory SSE broadcast ──────────────────────────────────────────────────
_sse_subscribers: list[asyncio.Queue] = []

def _broadcast(event_json: str) -> None:
    dead = []
    for q in _sse_subscribers:
        try:
            q.put_nowait(event_json)
        except asyncio.QueueFull:
            dead.append(q)
    for q in dead:
        _sse_subscribers.remove(q)

# ── Auth dependency ───────────────────────────────────────────────────────────
def _verify_secret(
    x_bosssignal_secret: Optional[str] = Header(default=None),
    secret: Optional[str] = Query(default=None),
) -> None:
    # Refuse all requests while the shared secret is left at its placeholder.
    if settings.bosssignal_secret == "CHANGE_ME":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Server misconfigured: set BOSSSIGNAL_SECRET.",
        )
    provided = x_bosssignal_secret or secret
    if provided != settings.bosssignal_secret:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing secret.",
        )

# ── POST /api/v1/events ───────────────────────────────────────────────────────
@router.post(
    "",
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(_verify_secret)],
    summary="Receive event from game server",
)
async def ingest_event(
    request: Request,
    x_bosssignal_server: Optional[str] = Header(default=None),
    x_bosssignal_version: Optional[str] = Header(default=None),
    server_id_query: Optional[str] = Query(default=None, alias="server_id"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body.")

    event_type = payload.get("event_type", "unknown")
    server_id  = payload.get("server_id") or x_bosssignal_server or server_id_query or "unknown"
    server_time = payload.get("server_time", 0)

    # Idempotency key
    idem_raw = f"{server_id}:{event_type}:{server_time}"
    idem_key = hashlib.sha256(idem_raw.encode()).hexdigest()

    existing = await db.scalar(select(Event).where(Event.idempotency_key == idem_key))
    if existing:
        return {"status": "duplicate", "event_id": str(existing.id)}

    event = Event(
        server_id=server_id,
        event_type=event_type,
        payload=payload,
        idempotency_key=idem_key,
    )
    db.add(event)

    # ── Side effects ─────────────────────
    if event_type == "boss.spawned":
        await _handle_boss_spawned(db, server_id, payload)
    elif event_type == "boss.killed":
        await _handle_boss_killed(db, server_id, payload)
    elif event_type == "boss.despawned":
        await _handle_boss_despawned(db, server_id, payload)
    elif event_type == "server.heartbeat":
        await _handle_heartbeat(db, server_id, payload)
    elif event_type == "server.started":
        await _handle_server_started(db, server_id, payload, x_bosssignal_version)
    elif event_type == "trophy.awarded":
        await _handle_trophy_awarded(db, server_id, payload)
    elif event_type == "trophy.transferred":
        await _handle_trophy_transferred(db, server_id, payload)
    elif event_type == "player.joined":
        await _handle_player_joined(db, server_id, payload)
    elif event_type == "player.left":
        await _handle_player_left(db, server_id, payload)

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        existing = await db.scalar(select(Event).where(Event.idempotency_key == idem_key))
        if existing:
            return {"status": "duplicate", "event_id": str(existing.id)}
        raise
    await db.refresh(event)

    broadcast_payload = {
        "event_id": str(event.id),
        "event_type": event_type,
        "server_id": server_id,
        "received_at": event.received_at.isoformat(),
        "data": payload.get("data", {}),
    }
    _broadcast(json.dumps(broadcast_payload))
    return {"status": "accepted", "event_id": str(event.id)}

# ── GET /api/v1/events ────────────────────────────────────────────────────────
@router.get("", summary="Query event history")
async def list_events(
    server_id: Optional[str] = Query(default=None),
    event_type: Optional[str] = Query(default=None),
    limit: int = Query(default=50, le=settings.events_page_size),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    q = select(Event).order_by(Event.received_at.desc()).limit(limit)
    if server_id:
        q = q.where(Event.server_id == server_id)
    if event_type:
        q = q.where(Event.event_type == event_type)
    result = await db.scalars(q)
    events = result.all()
    return [
        {
            "id": str(e.id),
            "server_id": e.server_id,
            "event_type": e.event_type,
            "received_at": e.received_at.isoformat(),
            "data": e.payload.get("data", {}),
        }
        for e in events
    ]

# ── SSE Stream ──────────────────────────────────────────────────────────────
@router.get("/stream", summary="Live SSE event stream")
async def event_stream(
    server_id: Optional[str] = Query(default=None),
) -> StreamingResponse:
    async def _generator() -> AsyncGenerator[str, None]:
        q: asyncio.Queue = asyncio.Queue(maxsize=settings.sse_queue_size)
        _sse_subscribers.append(q)
        try:
            yield ": connected\n\n"
            while True:
                try:
                    raw = await asyncio.wait_for(q.get(), timeout=25.0)
                    evt = json.loads(raw)
                    if server_id and evt.get("server_id") != server_id:
                        continue
                    yield f"data: {raw}\n\n"
                except asyncio.TimeoutError:
                    yield ": ping\n\n"
        finally:
            if q in _sse_subscribers:
                _sse_subscribers.remove(q)
    return StreamingResponse(_generator(), media_type="text/event-stream")

# ── Helpers ───────────────────────────────────────────────────────────────────

async def _handle_boss_spawned(db: AsyncSession, server_id: str, payload: dict) -> None:
    data = payload.get("data", {})
    enc = BossEncounter(
        server_id=server_id,
        boss_id=data.get("boss_id", "unknown"),
        boss_type=data.get("boss_type", "unknown"),
        display_name=data.get("boss_display_name", data.get("boss_type", "unknown")),
        max_health=data.get("max_health"),
        spawn_position=data.get("spawn_position"),
        player_count_at_spawn=data.get("server_player_count"),
        status="active",
    )
    db.add(enc)

async def _handle_boss_killed(db: AsyncSession, server_id: str, payload: dict) -> None:
    data = payload.get("data", {})
    boss_id = data.get("boss_id", "unknown")
    result = await db.scalars(
        select(BossEncounter)
        .where(BossEncounter.server_id == server_id)
        .where(BossEncounter.boss_id == boss_id)
        .where(BossEncounter.status == "active")
        .order_by(BossEncounter.spawned_at.desc())
        .limit(1)
    )
    enc = result.first()
    if enc:
        enc.killed_at = datetime.now(timezone.utc)
        enc.status = "killed"
        enc.time_to_kill_seconds = data.get("time_to_kill_seconds")
        enc.kill_position = data.get("kill_position")
        
        killer = data.get("killer", {})
        enc.killer_player_id   = killer.get("player_id")
        enc.killer_player_name = killer.get("player_name")
        enc.killer_weapon      = killer.get("weapon")
        enc.participants       = data.get("participants", [])

        if enc.killer_player_id:
            await _sync_player(db, enc.killer_player_id, enc.killer_player_name, is_kill=True)
        for p in enc.participants:
            pid = p.get("player_id")
            pname = p.get("player_name")
            if pid:
                await _sync_player(db, pid, pname, is_kill=False)

async def _handle_boss_despawned(db: AsyncSession, server_id: str, payload: dict) -> None:
    data = payload.get("data", {})
    boss_id = data.get("boss_id", "unknown")
    result = await db.scalars(select(BossEncounter).where(BossEncounter.server_id == server_id).where(BossEncounter.boss_id == boss_id).where(BossEncounter.status == "active").limit(1))
    enc = result.first()
    if enc:
        enc.despawned_at = datetime.now(timezone.utc)
        enc.status = "despawned"

async def _handle_heartbeat(db: AsyncSession, server_id: str, payload: dict) -> None:
    data = payload.get("data", {})
    now = datetime.now(timezone.utc)
    result = await db.scalar(select(ServerStatus).where(ServerStatus.server_id == server_id))
    if result:
        # If server was offline for >5 minutes, consider this a restart.
        # SQLite (tests) drops tzinfo on read; coerce before subtracting.
        last_seen = result.last_seen
        if last_seen is not None and last_seen.tzinfo is None:
            last_seen = last_seen.replace(tzinfo=timezone.utc)
        if last_seen and (now - last_seen).total_seconds() > 300:
            result.started_at = now
        elif not result.started_at:
            result.started_at = now

        result.last_seen = now
        result.player_count = data.get("player_count", 0)
        result.active_boss_count = data.get("active_boss_count", 0)
        result.active_bosses = data.get("active_bosses", [])
        result.is_online = True
        # Only overwrite if the heartbeat actually carried a manifest —
        # don't blank out a manifest captured on server.started.
        if "loaded_mods" in data:
            result.loaded_mods = data.get("loaded_mods")
    else:
        db.add(ServerStatus(
            server_id=server_id,
            player_count=data.get("player_count", 0),
            active_boss_count=data.get("active_boss_count", 0),
            active_bosses=data.get("active_bosses", []),
            loaded_mods=data.get("loaded_mods"),
            started_at=now,
            last_seen=now,
            is_online=True
        ))

async def _handle_server_started(db: AsyncSession, server_id: str, payload: dict, version: Optional[str]) -> None:
    data = payload.get("data", {})
    now = datetime.now(timezone.utc)
    result = await db.scalar(select(ServerStatus).where(ServerStatus.server_id == server_id))
    if result:
        result.last_seen = now
        result.started_at = now
        result.is_online = True
        result.bosssignal_version = data.get("bosssignal_version") or version
        result.active_bosses = []
        result.active_boss_count = 0
        if "loaded_mods" in data:
            result.loaded_mods = data.get("loaded_mods")
    else:
        db.add(ServerStatus(
            server_id=server_id,
            bosssignal_version=data.get("bosssignal_version") or version,
            loaded_mods=data.get("loaded_mods"),
            started_at=now,
            last_seen=now,
            is_online=True
        ))

async def _handle_trophy_awarded(db: AsyncSession, server_id: str, payload: dict) -> None:
    data = payload.get("data", {})
    trophy_class, holder_id, enc_raw = data.get("trophy_class"), data.get("holder_id"), data.get("encounter_id")
    if not (trophy_class and holder_id and enc_raw): return
    try: enc_id = uuid.UUID(enc_raw)
    except: return
    now, name = datetime.now(timezone.utc), data.get("holder_name", "Unknown")
    db.add(Trophy(id=uuid.uuid4(), trophy_class=trophy_class, boss_type=data.get("boss_type", "unknown"), encounter_id=enc_id, original_holder_id=holder_id, original_holder_name=name, original_server_id=server_id, original_claimed_at=now, current_holder_id=holder_id, current_holder_name=name, current_server_id=server_id, current_held_since=now))

async def _handle_trophy_transferred(db: AsyncSession, server_id: str, payload: dict) -> None:
    data = payload.get("data", {})
    tid_raw, new_id = data.get("trophy_id"), data.get("new_holder_id")
    if not (tid_raw and new_id): return
    try: tid = uuid.UUID(tid_raw)
    except: return
    row = await db.scalar(select(Trophy).where(Trophy.id == tid))
    if not row: return
    now, new_name = datetime.now(timezone.utc), data.get("new_holder_name", "Unknown")
    history = list(row.transfer_history or [])
    history.append({"from_player_id": row.current_holder_id, "to_player_id": new_id, "to_player_name": new_name, "server_id": server_id, "at": now.isoformat()})
    row.transfer_history, row.current_holder_id, row.current_holder_name, row.current_server_id, row.current_held_since = history, new_id, new_name, server_id, now

async def _sync_player(db: AsyncSession, steam_id: str, name: str, is_kill: bool = False) -> None:
    player = await db.get(Player, steam_id)
    now = datetime.now(timezone.utc)
    if not player:
        db.add(Player(steam_id=steam_id, name=name, last_seen=now, boss_kills=1 if is_kill else 0))
    else:
        player.name, player.last_seen = name, now
        if is_kill: player.boss_kills += 1

async def _handle_player_joined(db: AsyncSession, server_id: str, payload: dict) -> None:
    data = payload.get("data", {})
    sid, name = data.get("player_id"), data.get("player_name", "Unknown")
    if not sid: return
    await _sync_player(db, sid, name)
    player = await db.get(Player, sid)
    if player: player.status = "online"
    await db.execute(update(PlayerSession).where(PlayerSession.steam_id == sid).where(PlayerSession.is_active == True).values(is_active=False, left_at=datetime.now(timezone.utc)))
    db.add(PlayerSession(steam_id=sid, server_id=server_id, is_active=True))

async def _handle_player_left(db: AsyncSession, server_id: str, payload: dict) -> None:
    sid = payload.get("data", {}).get("player_id")
    if not sid: return
    player = await db.get(Player, sid)
    if player: player.status, player.last_seen = "offline", datetime.now(timezone.utc)
    res = await db.scalars(select(PlayerSession).where(PlayerSession.steam_id == sid).where(PlayerSession.server_id == server_id).where(PlayerSession.is_active == True).limit(1))
    sess = res.first()
    if sess:
        sess.is_active, sess.left_at = False, datetime.now(timezone.utc)
        if player: player.play_time_seconds += int((sess.left_at - sess.joined_at).total_seconds())
