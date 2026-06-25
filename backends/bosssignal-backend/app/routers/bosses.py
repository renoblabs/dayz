"""
/api/v1/bosses   — boss encounter analytics
/api/v1/servers  — per-server status overview
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.database import get_db
from app.db.models import BossEncounter, ServerStatus

router = APIRouter(tags=["bosses"])
settings = get_settings()


# ── GET /api/v1/bosses ────────────────────────────────────────────────────────
@router.get("/api/v1/bosses", summary="Boss encounter history")
async def list_boss_encounters(
    server_id: Optional[str] = Query(default=None),
    boss_type: Optional[str] = Query(default=None),
    status: Optional[str]    = Query(default=None, description="active | killed | despawned"),
    limit: int               = Query(default=20, le=settings.bosses_page_size),
    db: AsyncSession         = Depends(get_db),
) -> list[dict]:
    q = (
        select(BossEncounter)
        .order_by(BossEncounter.spawned_at.desc())
        .limit(limit)
    )
    if server_id:
        q = q.where(BossEncounter.server_id == server_id)
    if boss_type:
        q = q.where(BossEncounter.boss_type == boss_type)
    if status:
        q = q.where(BossEncounter.status == status)

    result = await db.scalars(q)
    encounters = result.all()

    return [_enc_to_dict(e) for e in encounters]


# ── GET /api/v1/bosses/stats ──────────────────────────────────────────────────
@router.get("/api/v1/bosses/stats", summary="Aggregate boss difficulty stats")
async def boss_stats(
    server_id: Optional[str] = Query(default=None),
    boss_type: Optional[str] = Query(default=None),
    db: AsyncSession         = Depends(get_db),
) -> list[dict]:
    """
    Returns per-boss-type aggregates:
      - kill count, despawn count
      - avg / min / max time-to-kill
      - avg player count at spawn
      - most common killer weapon

    Useful for a server operator to tune boss difficulty across the server network.
    """
    q = (
        select(
            BossEncounter.boss_type,
            BossEncounter.server_id,
            func.count().label("total_encounters"),
            # Count rows where killed_at is not null (only set on status="killed")
            func.count(BossEncounter.killed_at).label("kill_count"),
            func.avg(BossEncounter.time_to_kill_seconds).label("avg_ttk"),
            func.min(BossEncounter.time_to_kill_seconds).label("min_ttk"),
            func.max(BossEncounter.time_to_kill_seconds).label("max_ttk"),
            func.avg(BossEncounter.player_count_at_spawn).label("avg_players_at_spawn"),
        )
        .where(BossEncounter.status != "active")
        .group_by(BossEncounter.boss_type, BossEncounter.server_id)
        .order_by(BossEncounter.server_id, BossEncounter.boss_type)
    )
    if server_id:
        q = q.where(BossEncounter.server_id == server_id)
    if boss_type:
        q = q.where(BossEncounter.boss_type == boss_type)

    result = await db.execute(q)
    rows = result.all()

    return [
        {
            "boss_type":             r.boss_type,
            "server_id":             r.server_id,
            "total_encounters":      r.total_encounters,
            "kill_count":            r.kill_count or 0,
            "despawn_count":         (r.total_encounters - (r.kill_count or 0)),
            "avg_time_to_kill_min":  round(r.avg_ttk / 60, 1) if r.avg_ttk else None,
            "min_time_to_kill_min":  round(r.min_ttk / 60, 1) if r.min_ttk else None,
            "max_time_to_kill_min":  round(r.max_ttk / 60, 1) if r.max_ttk else None,
            "avg_players_at_spawn":  round(r.avg_players_at_spawn, 1) if r.avg_players_at_spawn else None,
        }
        for r in rows
    ]


# ── GET /api/v1/servers ───────────────────────────────────────────────────────
@router.get("/api/v1/servers", summary="Current status of all servers")
async def list_servers(db: AsyncSession = Depends(get_db)) -> list[dict]:
    """
    The "all servers at a glance" endpoint.
    Aggregates latest heartbeat data per server.
    """
    result = await db.scalars(
        select(ServerStatus).order_by(ServerStatus.server_id)
    )
    servers = result.all()

    # Inline normalization — keeps bosses.py self-contained (this route shadows
    # the /servers in dashboard.py for historical reasons).
    def _norm_mods(raw):
        if not raw or not isinstance(raw, list):
            return None
        out = []
        for item in raw:
            if isinstance(item, str):
                out.append({"name": item, "version": "", "status": "ok"})
            elif isinstance(item, dict) and item.get("name"):
                out.append({
                    "name":    item["name"],
                    "version": item.get("version", "") or "",
                    "status":  item.get("status", "ok") or "ok",
                })
        return out or None

    return [
        {
            "server_id":          s.server_id,
            "last_seen":          s.last_seen.isoformat() if s.last_seen else None,
            "is_online":          s.is_online,
            "player_count":       s.player_count,
            "active_boss_count":  s.active_boss_count,
            "active_bosses":      s.active_bosses or [],
            "bosssignal_version": s.bosssignal_version,
            "loaded_mods":        _norm_mods(s.loaded_mods),
        }
        for s in servers
    ]


# ── GET /api/v1/servers/{server_id} ───────────────────────────────────────────
@router.get("/api/v1/servers/{server_id}", summary="Single server status + recent kills")
async def get_server(server_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    status = await db.scalar(
        select(ServerStatus).where(ServerStatus.server_id == server_id)
    )
    recent = await db.scalars(
        select(BossEncounter)
        .where(BossEncounter.server_id == server_id)
        .where(BossEncounter.status == "killed")
        .order_by(BossEncounter.killed_at.desc())
        .limit(10)
    )
    recent_kills = recent.all()

    return {
        "status": {
            "server_id":         server_id,
            "last_seen":         status.last_seen.isoformat() if status else None,
            "is_online":         status.is_online if status else False,
            "player_count":      status.player_count if status else 0,
            "active_boss_count": status.active_boss_count if status else 0,
            "active_bosses":     status.active_bosses if status else [],
        },
        "recent_kills": [_enc_to_dict(e) for e in recent_kills],
    }


# ── Serialiser ────────────────────────────────────────────────────────────────
def _enc_to_dict(e: BossEncounter) -> dict:
    return {
        "id":                    str(e.id),
        "server_id":             e.server_id,
        "boss_id":               e.boss_id,
        "boss_type":             e.boss_type,
        "display_name":          e.display_name,
        "status":                e.status,
        "spawned_at":            e.spawned_at.isoformat() if e.spawned_at else None,
        "killed_at":             e.killed_at.isoformat() if e.killed_at else None,
        "despawned_at":          e.despawned_at.isoformat() if e.despawned_at else None,
        "time_to_kill_seconds":  e.time_to_kill_seconds,
        "time_to_kill_minutes":  round(e.time_to_kill_seconds / 60, 1) if e.time_to_kill_seconds else None,
        "max_health":            e.max_health,
        "spawn_position":        e.spawn_position,
        "kill_position":         e.kill_position,
        "killer":                {
            "player_id":   e.killer_player_id,
            "player_name": e.killer_player_name,
            "weapon":      e.killer_weapon,
        } if e.killer_player_id else None,
        "participants":          e.participants or [],
        "player_count_at_spawn": e.player_count_at_spawn,
    }


# ── Top-damager lookups ──────────────────────────────────────────────────────

def _rank_participants(participants: list[dict], skip_holders: Optional[str]) -> list[dict]:
    skip = {s for s in (skip_holders or "").split(",") if s}
    return sorted(
        (p for p in participants if p.get("player_id") and p["player_id"] not in skip),
        key=lambda p: (-p.get("damage_dealt", 0), not p.get("kill_shot", False)),
    )


def _top_damager_response(enc: BossEncounter, skip_holders: Optional[str]) -> dict:
    participants = enc.participants or []
    ranked = _rank_participants(participants, skip_holders)
    if not ranked:
        raise HTTPException(status_code=404, detail="No eligible damagers")
    top = ranked[0]
    original_index = next(
        (i for i, p in enumerate(participants) if p.get("player_id") == top["player_id"]),
        None,
    )
    # _rank_participants only returns players who are in `participants`, so this
    # should never be None. Raise loudly if it ever is rather than returning
    # rank=1 silently.
    if original_index is None:
        raise HTTPException(status_code=500, detail="Rank lookup inconsistent")
    rank = 1 + original_index
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
