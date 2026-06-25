"""
Dashboard-shaped read routes for the parallel UI build.

Four endpoints:
  GET /api/v1/server/status          — current state of the primary server
  GET /api/v1/leaderboard/boss-kills — boss-kill leaderboard (top players)
  GET /api/v1/encounters/recent      — recent boss encounters timeline
  GET /api/v1/system/health          — Postgres + KB + snapshotter + embed-queue rollup

DATA NOTES (real vs synthetic):
  All fallbacks below produce synthetic/illustrative data, labelled in the
  response with `is_mock: true`, used only to give the UI shape when the
  corresponding tables are empty.
  * /server/status reads server_status table (real). If the table is empty,
    falls back to a synthetic entry for `server_01` so the UI has shape to render.
  * /encounters/recent reads boss_encounters (real). If empty, returns
    synthetic encounters dated across the last several days.
  * /leaderboard/boss-kills aggregates from boss_encounters where killed_at
    is not null AND killer_player_id is set. Empty real data -> synthetic
    players with illustrative Steam-style handles + 3-char clan tags.
  * /system/health is partially real (Postgres + KB ping) and partially
    derived from filesystem state (last snapshot timestamps, embed coverage).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.kb_database import get_kb_db
from app.db.models import BossEncounter, Player, PlayerSession, ServerStatus, Trophy, AlertRule, AlertHistory

router = APIRouter(prefix="/api/v1", tags=["dashboard"])


# ── Synthetic (demo) data factories ───────────────────────────────────────────
# Everything below is illustrative sample data, surfaced only when the real
# tables are empty and always flagged with is_mock=true in the response.

# Example DayZ infected classnames. Used only when real boss_encounters data
# is empty. Substitute your own server's classnames as needed.
_MOCK_BOSS_CLASSES = [
    ("ZmbM_MarksTester",            "Beta Zombie"),
    ("ZmbM_ElectricianFat",         "Electrician (Heavy)"),
    ("ZmbF_PolicewomanNormal_Brown", "Policewoman"),
    ("ZmbM_MilitaryPilot",          "Pilot Infected"),
    ("ZmbF_RussianCleaner",         "Russian Cleaner"),
    ("ZmbM_HermitOld_Beige",        "Hermit"),
    ("ZmbF_VillagerOld_Blue",       "Old Villager"),
    ("ZmbM_FirefighterNormal",      "Firefighter Infected"),
]

# Steam-style handles: lowercase alphanumeric, occasional 3-char clan tag,
# occasional underscore. No emojis or unicode flair.
_MOCK_PLAYERS = [
    ("76561198042817391", "[TPG] cleric_ozz"),
    ("76561198114502244", "gnarlybeard"),
    ("76561197999283041", "[SVR] m1k3wash"),
    ("76561198255410189", "crustyheist"),
    ("76561198063471002", "[WLF] vyperknight"),
    ("76561198178329015", "swedish_meatbro"),
    ("76561198091723344", "[419] sauceboss"),
    ("76561198202156879", "panko_breaded"),
    ("76561198029448712", "[INF] dramamine42"),
    ("76561198166390028", "tarp_papi"),
]

_MOCK_WEAPONS = [
    "M4A1", "AKM", "SVD", "Mosin9130", "Winchester70",
    "VSS", "FN_FAL", "SK59_66", "Saiga_MK", "Mlock-91",
]

_MOCK_SERVERS = ["server_03", "server_04", "server_05"]


# ── Loaded-mods normalization ─────────────────────────────────────────────────
def _normalize_loaded_mods(raw):
    """
    The Enforce mod can send loaded_mods as either:
      - a list of names: ["@CommunityFramework", "@BossSignal", ...]
      - a list of dicts: [{"name": "@BossSignal", "version": "0.1.0"}, ...]
    The dashboard UI expects [{name, version, status}] — normalize to that.
    Returns None if raw is None/empty so the UI can show its empty-state.
    """
    if not raw:
        return None
    if not isinstance(raw, list):
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


def _mock_encounter(idx: int, when: datetime) -> dict:
    """Build a single realistic-shaped encounter row for the timeline UI."""
    cls, display = _MOCK_BOSS_CLASSES[idx % len(_MOCK_BOSS_CLASSES)]
    plr_id, plr_name = _MOCK_PLAYERS[idx % len(_MOCK_PLAYERS)]
    weapon = _MOCK_WEAPONS[idx % len(_MOCK_WEAPONS)]
    spawned = when - timedelta(seconds=120 + (idx * 13) % 600)
    killed = when
    ttk = (killed - spawned).total_seconds()
    return {
        "id":                    f"mock-encounter-{idx:04d}",
        "server_id":             _MOCK_SERVERS[idx % len(_MOCK_SERVERS)],
        "boss_id":               f"boss-{idx:03d}",
        "boss_type":             cls,
        "display_name":          display,
        "spawned_at":            spawned.isoformat(),
        "killed_at":             killed.isoformat(),
        "time_to_kill_seconds":  round(ttk, 1),
        "killer_player_id":      plr_id,
        "killer_player_name":    plr_name,
        "killer_weapon":         weapon,
        "player_count_at_spawn": 1 + (idx * 7) % 12,
        "status":                "killed",
        "is_mock":               True,
    }


def _mock_recent_encounters(limit: int) -> list[dict]:
    """Spread N synthetic encounters across the last 7 days (demo data)."""
    now = datetime.now(timezone.utc)
    out: list[dict] = []
    for i in range(limit):
        # Weight more recent: half in last 24h, half in last 7d
        if i < limit // 2:
            offset = timedelta(hours=(i * 1.7) + 0.3)
        else:
            offset = timedelta(hours=24 + (i - limit // 2) * 11.3)
        out.append(_mock_encounter(i, now - offset))
    return out


def _mock_leaderboard(days: int) -> list[dict]:
    """Synthetic leaderboard rows (demo data). Player rank by kill counts, scoped to N days."""
    # deterministic kill-count distribution
    counts = [37, 28, 22, 19, 15, 12, 9, 7, 5, 4]
    # bias counts down for shorter windows so 1-day vs 30-day looks different
    scale = max(0.15, min(1.0, days / 7.0))
    rows = []
    for i, (pid, pname) in enumerate(_MOCK_PLAYERS):
        kc = max(1, int(counts[i] * scale))
        rows.append({
            "rank":              i + 1,
            "player_id":         pid,
            "player_name":       pname,
            "boss_kills":        kc,
            "favorite_boss":     _MOCK_BOSS_CLASSES[i % len(_MOCK_BOSS_CLASSES)][0],
            "favorite_weapon":   _MOCK_WEAPONS[i % len(_MOCK_WEAPONS)],
            "fastest_kill_sec":  round(45 + (i * 3.7) % 90, 1),
            "is_mock":           True,
        })
    return rows


# ── /servers ──────────────────────────────────────────────────────────────────


@router.get("/servers", summary="List all known game servers and their status")
async def list_servers(
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """Returns status for every server that has ever sent a heartbeat."""
    result = await db.scalars(select(ServerStatus).order_by(ServerStatus.server_id))
    rows = result.all()
    
    now = datetime.now(timezone.utc)
    out = []
    for row in rows:
        last = row.last_seen
        if last is not None and last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)
        started_at = row.started_at
        if started_at is not None and started_at.tzinfo is None:
            started_at = started_at.replace(tzinfo=timezone.utc)

        is_online = (now - last).total_seconds() < 120 if last else False

        uptime_seconds = None
        if is_online and started_at:
            uptime_seconds = int((now - started_at).total_seconds())

        out.append({
            "server_id":          row.server_id,
            "name":               row.server_id.replace("_", " ").title(),
            "map":                "chernarusplus", # default for now
            "is_online":          is_online,
            "player_count":       row.player_count,
            "active_boss_count":  row.active_boss_count,
            "last_heartbeat":     last.isoformat() if last else None,
            "bosssignal_version": row.bosssignal_version,
            "loaded_mods":        _normalize_loaded_mods(row.loaded_mods),
            "uptime_seconds":     uptime_seconds,
            "is_mock":            False,
        })
    return out


# ── /server/status ────────────────────────────────────────────────────────────


@router.get("/server/status", summary="Current server status (primary or by id)")
async def server_status(
    server_id: Optional[str] = Query(None, description="Defaults to server_01 if omitted"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Real if `server_status` row exists; otherwise a synthetic 'offline' shape (is_mock=true)."""
    target = server_id or "server_01"
    row = await db.scalar(select(ServerStatus).where(ServerStatus.server_id == target))

    # If explicit target missing, try to find ANY real server to avoid showing synthetic data
    if row is None and server_id is None:
        row = await db.scalar(select(ServerStatus).order_by(ServerStatus.server_id).limit(1))

    if row is None:
        return {
            "server_id":          target,
            "is_online":          False,
            "player_count":       0,
            "active_boss_count":  0,
            "active_bosses":      [],
            "last_seen":          None,
            "bosssignal_version": None,
            "loaded_mods":        None,
            "uptime_seconds":     None,
            "is_mock":            True,
        }
    now = datetime.now(timezone.utc)
    last = row.last_seen
    # SQLite drops tzinfo on read; coerce to UTC-aware before subtracting.
    if last is not None and last.tzinfo is None:
        last = last.replace(tzinfo=timezone.utc)
    started_at = row.started_at
    if started_at is not None and started_at.tzinfo is None:
        started_at = started_at.replace(tzinfo=timezone.utc)
    # Treat "online" loosely: last heartbeat within 2 minutes
    is_online = (now - last).total_seconds() < 120

    uptime_seconds = None
    if is_online and started_at:
        uptime_seconds = int((now - started_at).total_seconds())

    return {
        "server_id":          row.server_id,
        "is_online":          is_online,
        "player_count":       row.player_count,
        "active_boss_count":  row.active_boss_count,
        "active_bosses":      row.active_bosses,
        "last_seen":          last.isoformat(),
        "bosssignal_version": row.bosssignal_version,
        "loaded_mods":        _normalize_loaded_mods(row.loaded_mods),
        "uptime_seconds":     uptime_seconds,
        "is_mock":            False,
    }


# ── /leaderboard/boss-kills ───────────────────────────────────────────────────


@router.get("/leaderboard/boss-kills", summary="Top players by boss kills, last N days")
async def leaderboard_boss_kills(
    days: int = Query(7, ge=1, le=90),
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Aggregates from boss_encounters using only real kill data."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    result = await db.execute(
        select(
            BossEncounter.killer_player_id.label("pid"),
            BossEncounter.killer_player_name.label("pname"),
            func.count().label("kc"),
            func.min(BossEncounter.time_to_kill_seconds).label("fastest"),
        )
        .where(
            BossEncounter.killed_at.isnot(None),
            BossEncounter.killer_player_id.isnot(None),
            BossEncounter.killed_at >= cutoff,
        )
        .group_by(BossEncounter.killer_player_id, BossEncounter.killer_player_name)
        .order_by(desc("kc"))
        .limit(limit)
    )
    rows = result.all()
    if not rows:
        return {
            "window_days": days,
            "rows":        [],
            "is_mock":     False,
        }
    return {
        "window_days": days,
        "rows": [
            {
                "rank":             i + 1,
                "player_id":        r.pid,
                "player_name":      r.pname,
                "boss_kills":       r.kc,
                "fastest_kill_sec": round(r.fastest, 1) if r.fastest else None,
                "is_mock":          False,
            }
            for i, r in enumerate(rows)
        ],
        "is_mock": False,
    }


# ── /encounters/recent ────────────────────────────────────────────────────────


@router.get("/encounters/recent", summary="Recent boss encounters timeline")
async def encounters_recent(
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Real encounters from boss_encounters only."""
    result = await db.scalars(
        select(BossEncounter).order_by(desc(BossEncounter.spawned_at)).limit(limit)
    )
    rows = result.all()
    if not rows:
        return {"items": [], "is_mock": False}
    items = [
        {
            "id":                    str(r.id),
            "server_id":             r.server_id,
            "boss_id":               r.boss_id,
            "boss_type":             r.boss_type,
            "display_name":          r.display_name,
            "spawned_at":            r.spawned_at.isoformat() if r.spawned_at else None,
            "killed_at":             r.killed_at.isoformat() if r.killed_at else None,
            "time_to_kill_seconds":  r.time_to_kill_seconds,
            "killer_player_id":      r.killer_player_id,
            "killer_player_name":    r.killer_player_name,
            "killer_weapon":         r.killer_weapon,
            "player_count_at_spawn": r.player_count_at_spawn,
            "status":                r.status,
            "is_mock":               False,
        }
        for r in rows
    ]
    return {"items": items, "is_mock": False}


# ── Players list ──────────────────────────────────────────────────────────────
@router.get("/players", summary="List all registered players")
async def list_players(
    db: AsyncSession = Depends(get_db),
    limit: int = 200
) -> list[dict]:
    result = await db.scalars(
        select(Player).order_by(Player.boss_kills.desc(), Player.last_seen.desc()).limit(limit)
    )
    players = result.all()
    
    out = []
    for p in players:
        current_server = None
        if p.status == "online":
            sess = await db.scalar(
                select(PlayerSession)
                .where(PlayerSession.steam_id == p.steam_id)
                .where(PlayerSession.is_active == True)
                .limit(1)
            )
            if sess:
                current_server = sess.server_id
        
        out.append({
            "steam_id": p.steam_id,
            "name": p.name,
            "status": p.status,
            "boss_kills": p.boss_kills,
            "hours": round(p.play_time_seconds / 3600, 1),
            "last_seen": p.last_seen.isoformat(),
            "joined_at": p.joined_at.isoformat(),
            "flagged": p.flagged,
            "current_server_id": current_server
        })
    return out


# ── Trophies list ─────────────────────────────────────────────────────────────
@router.get("/trophies", summary="List all trophies in circulation")
async def list_trophies(
    db: AsyncSession = Depends(get_db)
) -> list[dict]:
    result = await db.scalars(select(Trophy).order_by(Trophy.current_held_since.desc()))
    trophies = result.all()
    
    return [
        {
            "id": str(t.id),
            "trophy_class": t.trophy_class,
            "boss_type": t.boss_type,
            "holder_id": t.current_holder_id,
            "holder_name": t.current_holder_name,
            "server_id": t.current_server_id,
            "awarded_iso": t.original_claimed_at.isoformat(),
            "transfer_count": len(t.transfer_history or [])
        }
        for t in trophies
    ]


# ── Global Stats ─────────────────────────────────────────────────────────────
@router.get("/stats", summary="Global dashboard statistics")
async def get_global_stats(
    db: AsyncSession = Depends(get_db)
) -> dict:
    total_kills = await db.scalar(select(func.count(BossEncounter.id)).where(BossEncounter.status == "killed"))
    active_players = await db.scalar(select(func.count(Player.steam_id)).where(Player.status == "online"))
    trophies_circ = await db.scalar(select(func.count(Trophy.id)))
    active_servers = await db.scalar(select(func.count(ServerStatus.server_id)).where(ServerStatus.is_online == True))
    
    return {
        "total_kills": total_kills or 0,
        "active_players": active_players or 0,
        "trophies_in_circulation": trophies_circ or 0,
        "active_servers": active_servers or 0
    }


# ── Alerts ────────────────────────────────────────────────────────────────────

async def _ensure_default_rules(db: AsyncSession):
    """Seed default alert rules if table is empty."""
    count = await db.scalar(select(func.count(AlertRule.id)))
    if count == 0:
        defaults = [
            AlertRule(
                name="Elite Boss Spawn",
                description="Fire when a rare boss spawns",
                event_type="boss.spawned",
                condition="boss_type=ZmbM_MarksTester",
                channel="dashboard"
            ),
            AlertRule(
                name="Trophy Awarded",
                description="Fire when a trophy is first claimed",
                event_type="trophy.claimed",
                channel="dashboard"
            ),
            AlertRule(
                name="Large Join",
                description="Fire when a player joins with >100 kills",
                event_type="player.joined",
                condition="boss_kills>100",
                channel="dashboard"
            )
        ]
        db.add_all(defaults)
        await db.commit()

@router.get("/alerts/rules", summary="List all alert rules")
async def list_alert_rules(
    db: AsyncSession = Depends(get_db)
) -> list[dict]:
    await _ensure_default_rules(db)
    result = await db.scalars(select(AlertRule).order_by(AlertRule.name))
    rules = result.all()
    return [
        {
            "id": str(r.id),
            "name": r.name,
            "condition": r.condition,
            "channel": r.channel,
            "enabled": r.enabled,
            "last_fired_iso": r.last_fired_at.isoformat() if r.last_fired_at else None
        }
        for r in rules
    ]

@router.get("/alerts/history", summary="Recent alert firing history")
async def list_alert_history(
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
) -> list[dict]:
    result = await db.scalars(
        select(AlertHistory).order_by(AlertHistory.fired_at.desc()).limit(limit)
    )
    history = result.all()
    return [
        {
            "id": str(h.id),
            "rule_name": (await db.get(AlertRule, h.rule_id)).name if h.rule_id else "Unknown",
            "fired_iso": h.fired_at.isoformat(),
            "detail": h.detail,
            "server_id": h.server_id
        }
        for h in history
    ]


# ── /system/health ────────────────────────────────────────────────────────────


@router.get("/system/health", summary="Subsystem rollup for the dashboard")
async def system_health(
    db: AsyncSession = Depends(get_db),
    kb: Optional[AsyncSession] = Depends(get_kb_db),
) -> dict:
    """
    Real where reachable:
      - bosssignal_db: SELECT 1
      - kb_db:         SELECT 1 (returns 'unconfigured' if KB engine None)
      - kb_corpus:     real source/chunk counts + embed coverage
      - snapshotter:   freshness of last snapshots in intel.server_snapshots
                       (is_mock=true if KB unreachable)
    """
    # BossSignal DB ping
    bs_ok = False
    bs_error = None
    try:
        await db.execute(text("SELECT 1"))
        bs_ok = True
    except Exception as e:
        bs_error = str(e)[:200]

    # KB ping + corpus stats
    kb_status = "unconfigured"
    kb_error = None
    kb_corpus: dict = {}
    if kb is not None:
        try:
            await kb.execute(text("SELECT 1"))
            kb_status = "ok"
            stats = await kb.execute(
                text(
                    """
                    SELECT
                      (SELECT COUNT(*) FROM public.sources) AS sources,
                      (SELECT COUNT(*) FROM public.chunks)  AS chunks,
                      (SELECT COUNT(*) FROM public.chunks WHERE embedding IS NOT NULL) AS embedded
                    """
                )
            )
            r = stats.first()
            if r:
                total = r.chunks or 0
                embedded = r.embedded or 0
                kb_corpus = {
                    "sources":       r.sources,
                    "chunks":        total,
                    "embedded":      embedded,
                    "embed_percent": round(100 * embedded / total, 1) if total else 0,
                }
        except Exception as e:
            kb_status = "unreachable"
            kb_error = str(e)[:200]

    # Snapshotter freshness — read from intel.server_snapshots
    snap: dict = {"status": "unknown"}
    if kb is not None:
        try:
            r = await kb.execute(
                text(
                    """
                    SELECT
                      MAX(captured_at) AS last_capture,
                      COUNT(DISTINCT snapshot_date) AS days_banked,
                      COUNT(*) AS total_rows
                    FROM intel.server_snapshots
                    """
                )
            )
            row = r.first()
            if row and row.last_capture:
                age_h = (datetime.now(timezone.utc) - row.last_capture).total_seconds() / 3600
                fresh = age_h < 30  # nightly task; >30h means it missed a run
                snap = {
                    "status":         "fresh" if fresh else "stale",
                    "last_capture":   row.last_capture.isoformat(),
                    "age_hours":      round(age_h, 1),
                    "days_banked":    row.days_banked,
                    "total_rows":     row.total_rows,
                }
            else:
                snap = {"status": "no_data"}
        except Exception as e:
            snap = {"status": "error", "detail": str(e)[:200]}

    return {
        "bosssignal_db": {"status": "ok" if bs_ok else "error", "detail": bs_error},
        "kb_db":         {"status": kb_status, "detail": kb_error},
        "kb_corpus":     kb_corpus,
        "snapshotter":   snap,
        "checked_at":    datetime.now(timezone.utc).isoformat(),
    }
