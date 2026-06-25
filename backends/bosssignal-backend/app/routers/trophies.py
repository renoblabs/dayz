"""
/api/v1/trophies — trophy queries backed by the Trophy table.

Read-only router. Writes happen via /api/v1/events (trophy.awarded,
trophy.transferred) and are handled in events.py.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import optional_read_secret
from app.db.database import get_db
from app.db.models import Trophy

router = APIRouter(
    prefix="/api/v1/trophies",
    tags=["trophies"],
    dependencies=[Depends(optional_read_secret)],
)


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
    try:
        tid = uuid.UUID(trophy_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="trophy_id is not a valid UUID")
    t = await db.scalar(select(Trophy).where(Trophy.id == tid))
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
