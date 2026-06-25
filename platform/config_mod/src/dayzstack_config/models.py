"""SQLAlchemy ORM for the `config` schema."""

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    Index,
    MetaData,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from .types import CONFIG_TYPES

config_metadata = MetaData(schema="config")


class Base(DeclarativeBase):
    metadata = config_metadata


class ParsedConfigRow(Base):
    """One row per parsed config file. file_hash gives us idempotency."""

    __tablename__ = "parsed_configs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    config_type: Mapped[str] = mapped_column(Text, nullable=False)
    source_label: Mapped[str] = mapped_column(Text, nullable=False)
    source_path: Mapped[str | None] = mapped_column(Text)
    parsed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    parsed_data: Mapped[dict] = mapped_column(JSONB, nullable=False)
    raw_content: Mapped[str | None] = mapped_column(Text)
    file_hash: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB)

    __table_args__ = (
        CheckConstraint(
            "config_type IN ({})".format(",".join(f"'{t}'" for t in CONFIG_TYPES)),
            name="ck_parsed_configs_type",
        ),
        Index("idx_parsed_configs_type", "config_type"),
        Index("idx_parsed_configs_label", "source_label"),
        Index("idx_parsed_configs_hash", "file_hash"),
        {"schema": "config"},
    )
