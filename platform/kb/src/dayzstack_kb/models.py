"""SQLAlchemy ORM models matching the migration schema."""

from datetime import datetime
from uuid import UUID

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    ARRAY,
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR, UUID as PgUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    url: Mapped[str] = mapped_column(Text, nullable=False)
    source_type: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[str | None] = mapped_column(Text)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    cleaned_text: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    content_hash: Mapped[str] = mapped_column(Text, nullable=False)

    chunks: Mapped[list["Chunk"]] = relationship(back_populates="source", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("url", "content_hash", name="uq_sources_url_hash"),
        CheckConstraint(
            "source_type IN ('bistudio_wiki','yadz_docs','github_mod_file',"
            "'youtube_transcript','community_doc','manual','local_repo')",
            name="ck_sources_source_type",
        ),
        Index("sources_source_type_idx", "source_type"),
        Index("sources_metadata_gin", "metadata", postgresql_using="gin"),
    )


class Chunk(Base):
    __tablename__ = "chunks"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    source_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("sources.id", ondelete="CASCADE"), nullable=False
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    text_: Mapped[str] = mapped_column("text", Text, nullable=False)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    embedding: Mapped[list[float] | None] = mapped_column(Vector(768))
    # text_tsv is a generated column — declared in migration, not here

    source: Mapped[Source] = relationship(back_populates="chunks")

    __table_args__ = (
        UniqueConstraint("source_id", "chunk_index", name="uq_chunks_source_idx"),
        Index("chunks_source_id_idx", "source_id"),
        Index("chunks_metadata_gin", "metadata", postgresql_using="gin"),
        # HNSW index defined in migration (vector_cosine_ops)
    )


class Symbol(Base):
    __tablename__ = "symbols"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    name: Mapped[str] = mapped_column(Text, nullable=False)
    kind: Mapped[str] = mapped_column(String, nullable=False)
    qualified_name: Mapped[str | None] = mapped_column(Text)
    parent_class: Mapped[str | None] = mapped_column(Text)
    source_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), ForeignKey("sources.id", ondelete="SET NULL"))
    signature: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    examples: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    dayz_version: Mapped[str | None] = mapped_column(String)

    __table_args__ = (
        CheckConstraint(
            "kind IN ('class','method','function','enum','constant','property')",
            name="ck_symbols_kind",
        ),
        Index("symbols_name_idx", "name"),
        Index("symbols_qualified_name_idx", "qualified_name"),
    )


class ScrapeRun(Base):
    __tablename__ = "scrape_runs"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    scraper_type: Mapped[str] = mapped_column(String, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String, nullable=False)
    sources_added: Mapped[int] = mapped_column(Integer, default=0)
    sources_updated: Mapped[int] = mapped_column(Integer, default=0)
    chunks_added: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)

    __table_args__ = (
        CheckConstraint(
            "status IN ('running','succeeded','failed','partial')",
            name="ck_scrape_runs_status",
        ),
        Index("scrape_runs_scraper_idx", "scraper_type", "started_at"),
    )
