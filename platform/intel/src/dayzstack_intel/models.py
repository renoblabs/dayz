"""SQLAlchemy ORM for the intel schema."""

from datetime import date, datetime
from sqlalchemy import (
    ARRAY,
    BigInteger,
    Date,
    DateTime,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Intel-schema declarative base. Lives in the `intel` Postgres schema."""
    metadata = None  # set below via __table_args__ on each table


# Use a metadata object pinned to schema=intel so all tables live there.
from sqlalchemy import MetaData
intel_metadata = MetaData(schema="intel")


class Base(DeclarativeBase):  # noqa: F811 - intentional override
    metadata = intel_metadata


class WorkshopSnapshot(Base):
    __tablename__ = "workshop_snapshots"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False)
    query_type: Mapped[str] = mapped_column(Text, nullable=False)  # trend | recent | votes | updated
    workshop_id: Mapped[str] = mapped_column(Text, nullable=False)  # Steam published file id (string for safety)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    author_id: Mapped[str | None] = mapped_column(Text)
    author_name: Mapped[str | None] = mapped_column(Text)
    subscriptions: Mapped[int | None] = mapped_column(BigInteger)
    favorites: Mapped[int | None] = mapped_column(BigInteger)
    views: Mapped[int | None] = mapped_column(BigInteger)
    file_size: Mapped[int | None] = mapped_column(BigInteger)
    tags: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    created_at_ts: Mapped[datetime | None] = mapped_column("created_at", DateTime(timezone=True))
    updated_at_ts: Mapped[datetime | None] = mapped_column("updated_at", DateTime(timezone=True))
    rank_in_query: Mapped[int | None] = mapped_column(Integer)
    raw_response: Mapped[dict | None] = mapped_column(JSONB)
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("idx_snapshots_workshop_id", "workshop_id"),
        Index("idx_snapshots_date_query", "snapshot_date", "query_type"),
        Index("idx_snapshots_captured_at", "captured_at"),
        {"schema": "intel"},
    )


class ServerSnapshot(Base):
    """One row per (snapshot_date, source, server_id). Captures populated DayZ
    servers and their high-level metadata from sources like Battlemetrics."""

    __tablename__ = "server_snapshots"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False)
    source: Mapped[str] = mapped_column(Text, nullable=False)
    server_id: Mapped[str] = mapped_column(Text, nullable=False)
    server_name: Mapped[str] = mapped_column(Text, nullable=False)
    map_name: Mapped[str | None] = mapped_column(Text)
    player_count: Mapped[int | None] = mapped_column(Integer)
    max_players: Mapped[int | None] = mapped_column(Integer)
    queue_count: Mapped[int | None] = mapped_column(Integer)
    rank_in_source: Mapped[int | None] = mapped_column(Integer)
    ip: Mapped[str | None] = mapped_column(Text)
    port: Mapped[int | None] = mapped_column(Integer)
    raw_response: Mapped[dict | None] = mapped_column(JSONB)
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("idx_server_snap_date_src", "snapshot_date", "source"),
        Index("idx_server_snap_id", "server_id"),
        {"schema": "intel"},
    )


class ServerMod(Base):
    """One row per (server_id, mod) at snapshot time. Joins to ServerSnapshot
    by (snapshot_date, server_id) and to WorkshopSnapshot by workshop_id."""

    __tablename__ = "server_mods"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False)
    server_id: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(Text, nullable=False)
    mod_name: Mapped[str] = mapped_column(Text, nullable=False)
    workshop_id: Mapped[str | None] = mapped_column(Text)
    raw_mod_string: Mapped[str] = mapped_column(Text, nullable=False)
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("idx_server_mods_workshop", "workshop_id"),
        Index("idx_server_mods_server", "server_id"),
        Index("idx_server_mods_date", "snapshot_date"),
        {"schema": "intel"},
    )
