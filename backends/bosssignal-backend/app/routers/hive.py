"""
/api/v1/hive — The "HiveAPI" for game-server-to-backend queries.
Consolidates all read-paths used by the Enforce mod for cross-server logic.
"""
from __future__ import annotations

import logging
import secrets
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.database import get_db
from app.db.models import Player, Trophy

log = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/api/v1/hive", tags=["hive"])

# ── Auth dependency (Same as events) ──────────────────────────────────────────
def _verify_secret(x_bosssignal_secret: Optional[str] = Header(default=None)):
    # The secret is accepted ONLY via the X-BossSignal-Secret header, never via
    # a query string.
    # Refuse all requests while the shared secret is left at its placeholder.
    if settings.bosssignal_secret == "CHANGE_ME":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Server misconfigured: set BOSSSIGNAL_SECRET.",
        )
    # Constant-time compare to avoid leaking the secret via timing.
    provided = x_bosssignal_secret or ""
    if not secrets.compare_digest(provided, settings.bosssignal_secret):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid secret.",
        )

@router.get("/player/{steam_id}", dependencies=[Depends(_verify_secret)])
async def get_player_hive_data(steam_id: str, db: AsyncSession = Depends(get_db)):
    """
    Called by the mod when a player joins.
    Returns global stats and status for cross-server persistence.
    """
    player = await db.get(Player, steam_id)
    if not player:
        return {
            "exists": False,
            "boss_kills": 0,
            "flagged": False,
            "meta": {}
        }
    
    # Also find trophies held by this player
    trophies_res = await db.scalars(select(Trophy).where(Trophy.current_holder_id == steam_id))
    trophies = trophies_res.all()
    
    return {
        "exists": True,
        "name": player.name,
        "boss_kills": player.boss_kills,
        "flagged": player.flagged,
        "meta": player.meta,
        "held_trophies": [
            {
                "id": str(t.id),
                "trophy_class": t.trophy_class,
                "boss_type": t.boss_type,
                "awarded_at": t.original_claimed_at.isoformat()
            }
            for t in trophies
        ]
    }

@router.get("/trophies", dependencies=[Depends(_verify_secret)])
async def get_server_trophies(server_id: str, db: AsyncSession = Depends(get_db)):
    """
    Called by the mod periodically or on startup.
    Returns all trophies currently recorded as being on THIS server.
    Useful for 'ghost' trophy detection or sync.
    """
    result = await db.scalars(select(Trophy).where(Trophy.current_server_id == server_id))
    trophies = result.all()
    
    return [
        {
            "id": str(t.id),
            "trophy_class": t.trophy_class,
            "holder_id": t.current_holder_id,
            "holder_name": t.current_holder_name
        }
        for t in trophies
    ]
