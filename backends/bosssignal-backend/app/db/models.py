"""
SQLAlchemy ORM models for BossSignal.

Stripped from dayzAPI: removed Tenant, Cluster, Character, Inventory,
MoveTicket — none of that lives here. BossSignal observes and reports;
it doesn't store character state.

Schema:
  events         — raw event log (append-only)
  boss_encounters — structured encounter timeline derived from events
  server_status  — last-known state per server_id (upserted on heartbeat)
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    BigInteger,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, relationship
from sqlalchemy.types import TypeDecorator, CHAR


# Dialect-portable types: JSONB on Postgres, JSON on SQLite / others.
# UUID as native on Postgres, CHAR(36) string elsewhere.
JSON_TYPE = JSONB().with_variant(JSON(), "sqlite")


class UUIDType(TypeDecorator):
    """UUID column: native UUID on Postgres, CHAR(36) text elsewhere."""
    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_UUID(as_uuid=True))
        return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if dialect.name == "postgresql":
            return value
        return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        import uuid as _uuid
        if isinstance(value, _uuid.UUID):
            return value
        return _uuid.UUID(value)


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


# ── Raw event log ─────────────────────────────────────────────────────────────
class Event(Base):
    """
    Append-only log of every payload the Enforce mod sends.
    No updates, no deletes. This is the source of truth.
    Boss encounter records are derived from this table.
    """

    __tablename__ = "events"

    id              = Column(UUIDType(), primary_key=True, default=uuid.uuid4)
    server_id       = Column(String(64), nullable=False, index=True)
    event_type      = Column(String(64), nullable=False, index=True)

    # Full JSON payload as received from the game server
    payload         = Column(JSON_TYPE, nullable=False)

    # When the backend received the event (not the server_time in the payload)
    received_at     = Column(DateTime(timezone=True), nullable=False, default=_now, index=True)

    # Idempotency: store the event_type + server_id + server_time hash
    # so duplicate retries (engine restarts, retry loops) don't double-count
    idempotency_key = Column(String(128), nullable=True, unique=True, index=True)


# ── Structured boss encounters ────────────────────────────────────────────────
class BossEncounter(Base):
    """
    One row per boss lifecycle (spawn → kill or despawn).
    Created when we receive boss.spawned.
    Updated when we receive boss.killed or boss.despawned.
    """

    __tablename__ = "boss_encounters"

    id              = Column(UUIDType(), primary_key=True, default=uuid.uuid4)
    server_id       = Column(String(64), nullable=False, index=True)

    # Session-scoped entity ID from the game engine (entity.GetID().ToString())
    boss_id         = Column(String(64), nullable=False, index=True)

    boss_type       = Column(String(128), nullable=False)
    display_name    = Column(String(128), nullable=False)

    spawned_at      = Column(DateTime(timezone=True), nullable=False, default=_now)
    killed_at       = Column(DateTime(timezone=True), nullable=True)
    despawned_at    = Column(DateTime(timezone=True), nullable=True)

    # Null while boss is alive; set on kill/despawn
    time_to_kill_seconds = Column(Float, nullable=True)

    max_health      = Column(Float, nullable=True)

    # {x, y, z} at spawn and kill
    spawn_position  = Column(JSON_TYPE, nullable=True)
    kill_position   = Column(JSON_TYPE, nullable=True)

    # Player who landed the killing blow
    killer_player_id   = Column(String(64), nullable=True)
    killer_player_name = Column(String(128), nullable=True)
    killer_weapon      = Column(String(128), nullable=True)

    # All participants and their damage dealt
    # [{player_id, player_name, damage_dealt, kill_shot}]
    participants    = Column(JSON_TYPE, nullable=True)

    # Server player count at spawn time
    player_count_at_spawn = Column(Integer, nullable=True)

    # Status: "active" | "killed" | "despawned"
    status          = Column(String(16), nullable=False, default="active", index=True)

    __table_args__ = (
        UniqueConstraint("server_id", "boss_id", "spawned_at",
                         name="uq_encounter_server_boss_spawn"),
    )


# ── Server status (heartbeat-derived) ────────────────────────────────────────
class ServerStatus(Base):
    """
    One row per server_id. Upserted on every heartbeat event.
    Gives the dashboard a fast "current state" read without
    scanning the events table.
    """

    __tablename__ = "server_status"

    server_id       = Column(String(64), primary_key=True)
    last_seen       = Column(DateTime(timezone=True), nullable=False, default=_now)
    started_at      = Column(DateTime(timezone=True), nullable=True)  # When server came online (set on first heartbeat after downtime)
    player_count    = Column(Integer, nullable=False, default=0)
    active_boss_count = Column(Integer, nullable=False, default=0)

    # [{boss_id, boss_type, display_name, elapsed_seconds, health_pct}]
    active_bosses   = Column(JSON_TYPE, nullable=False, default=list)

    bosssignal_version = Column(String(16), nullable=True)
    is_online       = Column(Boolean, nullable=False, default=True)

    # Mod manifest as reported by the server. Either a list of strings
    # (raw mod names like "@CommunityFramework") or a list of objects
    # like {name, version, status}. Stored as raw JSON; the dashboard
    # router normalizes it to the {name, version, status} shape the UI wants.
    loaded_mods     = Column(JSON_TYPE, nullable=True)


# ── Player tracking ──────────────────────────────────────────────────────────
class Player(Base):
    """
    Registry of every player seen by the system.
    Updated on join/leave and boss kills.
    """
    __tablename__ = "players"

    steam_id        = Column(String(64), primary_key=True)
    name            = Column(String(128), nullable=False)
    
    # "online" | "offline"
    status          = Column(String(16), nullable=False, default="offline")
    last_seen       = Column(DateTime(timezone=True), nullable=False, default=_now)
    joined_at       = Column(DateTime(timezone=True), nullable=False, default=_now)
    
    boss_kills      = Column(Integer, nullable=False, default=0)
    flagged         = Column(Boolean, nullable=False, default=False)
    
    # Derived total (seconds)
    play_time_seconds = Column(BigInteger, nullable=False, default=0)
    
    # Metadata: {last_weapon, preferred_server, etc}
    meta            = Column(JSON_TYPE, nullable=False, default=dict)


class PlayerSession(Base):
    """
    Tracks a single connection session.
    Created on join, updated on leave or heartbeat.
    """
    __tablename__ = "player_sessions"

    id              = Column(UUIDType(), primary_key=True, default=uuid.uuid4)
    steam_id        = Column(String(64), ForeignKey("players.steam_id"), nullable=False, index=True)
    server_id       = Column(String(64), nullable=False, index=True)
    
    joined_at       = Column(DateTime(timezone=True), nullable=False, default=_now)
    last_seen       = Column(DateTime(timezone=True), nullable=False, default=_now)
    left_at         = Column(DateTime(timezone=True), nullable=True)
    
    is_active       = Column(Boolean, nullable=False, default=True)


# ── Trophy awards ────────────────────────────────────────────────────────────
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

    # Current holder — updated on transfer
    current_holder_id      = Column(String(64), nullable=False, index=True)
    current_holder_name    = Column(String(128), nullable=False)
    current_server_id      = Column(String(64), nullable=False, index=True)
    current_held_since     = Column(DateTime(timezone=True), nullable=False, default=_now)

    # History of transfers: [{from_player_id, to_player_id, to_player_name, server_id, at}]
    transfer_history       = Column(JSON_TYPE, nullable=False, default=list)


# ── Alerts ────────────────────────────────────────────────────────────────────
class AlertRule(Base):
    """
    Configurable alert rules that fire on specific event patterns.
    """
    __tablename__ = "alert_rules"

    id              = Column(UUIDType(), primary_key=True, default=uuid.uuid4)
    name            = Column(String(128), nullable=False)
    description     = Column(Text, nullable=True)
    
    # Event type to trigger on (e.g. "boss.killed", "player.joined")
    # or "*" for all events (expensive!)
    event_type      = Column(String(64), nullable=False, default="*")
    
    # Simple JSONPath-like or key=value filter for the payload
    # e.g. "boss_type=ZmbM_MarksTester"
    condition       = Column(String(255), nullable=True)
    
    # Target channel: "dashboard", "discord", "webhook"
    channel         = Column(String(64), nullable=False, default="dashboard")
    webhook_url     = Column(String(255), nullable=True)
    
    enabled         = Column(Boolean, nullable=False, default=True)
    created_at      = Column(DateTime(timezone=True), nullable=False, default=_now)
    last_fired_at   = Column(DateTime(timezone=True), nullable=True)


class AlertHistory(Base):
    """
    Log of every time an alert rule fired.
    """
    __tablename__ = "alert_history"

    id              = Column(UUIDType(), primary_key=True, default=uuid.uuid4)
    rule_id         = Column(PG_UUID(as_uuid=True), ForeignKey("alert_rules.id"), nullable=False, index=True)
    
    server_id       = Column(String(64), nullable=False, index=True)
    event_id        = Column(PG_UUID(as_uuid=True), ForeignKey("events.id"), nullable=True)
    
    # Summarized detail for the UI
    detail          = Column(Text, nullable=False)
    
    fired_at        = Column(DateTime(timezone=True), nullable=False, default=_now, index=True)
    
    # Full context at fire time
    context         = Column(JSON_TYPE, nullable=True)

    rule = relationship("AlertRule", backref="history")
