"""Initial schema — sources, chunks, symbols, scrape_runs.

Revision ID: 0001
Revises:
Create Date: 2026-04-25
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # sources — raw fetched artifacts, immutable per content_hash
    op.create_table(
        "sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("url", sa.Text, nullable=False),
        sa.Column("source_type", sa.String, nullable=False),
        sa.Column("title", sa.Text),
        sa.Column("raw_text", sa.Text, nullable=False),
        sa.Column("cleaned_text", sa.Text, nullable=False),
        sa.Column("metadata", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("content_hash", sa.Text, nullable=False),
        sa.UniqueConstraint("url", "content_hash", name="uq_sources_url_hash"),
        sa.CheckConstraint(
            "source_type IN ('bistudio_wiki','yadz_docs','github_mod_file',"
            "'youtube_transcript','community_doc','manual','local_repo')",
            name="ck_sources_source_type",
        ),
    )
    op.create_index("sources_source_type_idx", "sources", ["source_type"])
    op.create_index("sources_metadata_gin", "sources", ["metadata"], postgresql_using="gin")

    # chunks — searchable units; embeddings + tsv for hybrid retrieval
    op.create_table(
        "chunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sources.id", ondelete="CASCADE"), nullable=False),
        sa.Column("chunk_index", sa.Integer, nullable=False),
        sa.Column("text", sa.Text, nullable=False),
        sa.Column("metadata", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("embedding", Vector(768)),
        sa.UniqueConstraint("source_id", "chunk_index", name="uq_chunks_source_idx"),
    )
    # Generated tsvector column (for FTS)
    op.execute(
        "ALTER TABLE chunks ADD COLUMN text_tsv tsvector "
        "GENERATED ALWAYS AS (to_tsvector('english', text)) STORED"
    )
    op.create_index("chunks_source_id_idx", "chunks", ["source_id"])
    op.create_index("chunks_metadata_gin", "chunks", ["metadata"], postgresql_using="gin")
    op.create_index("chunks_tsv_idx", "chunks", ["text_tsv"], postgresql_using="gin")
    # HNSW index for vector cosine sim
    op.execute(
        "CREATE INDEX chunks_embedding_hnsw ON chunks "
        "USING hnsw (embedding vector_cosine_ops)"
    )

    # symbols — exact-match index for class/method lookup
    op.create_table(
        "symbols",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("kind", sa.String, nullable=False),
        sa.Column("qualified_name", sa.Text),
        sa.Column("parent_class", sa.Text),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sources.id", ondelete="SET NULL")),
        sa.Column("signature", sa.Text),
        sa.Column("description", sa.Text),
        sa.Column("examples", postgresql.ARRAY(sa.Text)),
        sa.Column("dayz_version", sa.String),
        sa.CheckConstraint(
            "kind IN ('class','method','function','enum','constant','property')",
            name="ck_symbols_kind",
        ),
    )
    op.create_index("symbols_name_idx", "symbols", ["name"])
    op.create_index("symbols_qualified_name_idx", "symbols", ["qualified_name"])

    # scrape_runs — observability for ingestion jobs
    op.create_table(
        "scrape_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("scraper_type", sa.String, nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("status", sa.String, nullable=False),
        sa.Column("sources_added", sa.Integer, server_default="0"),
        sa.Column("sources_updated", sa.Integer, server_default="0"),
        sa.Column("chunks_added", sa.Integer, server_default="0"),
        sa.Column("error_message", sa.Text),
        sa.Column("metadata", postgresql.JSONB, server_default=sa.text("'{}'::jsonb")),
        sa.CheckConstraint(
            "status IN ('running','succeeded','failed','partial')",
            name="ck_scrape_runs_status",
        ),
    )
    op.create_index("scrape_runs_scraper_idx", "scrape_runs", ["scraper_type", "started_at"])


def downgrade() -> None:
    op.drop_table("scrape_runs")
    op.drop_table("symbols")
    op.drop_table("chunks")
    op.drop_table("sources")
