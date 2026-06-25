"""workshop_snapshots in intel schema.

Revision ID: 0001
Revises:
Create Date: 2026-04-25
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS intel")

    op.create_table(
        "workshop_snapshots",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("snapshot_date", sa.Date, nullable=False),
        sa.Column("query_type", sa.Text, nullable=False),
        sa.Column("workshop_id", sa.Text, nullable=False),
        sa.Column("title", sa.Text, nullable=False),
        sa.Column("author_id", sa.Text),
        sa.Column("author_name", sa.Text),
        sa.Column("subscriptions", sa.BigInteger),
        sa.Column("favorites", sa.BigInteger),
        sa.Column("views", sa.BigInteger),
        sa.Column("file_size", sa.BigInteger),
        sa.Column("tags", postgresql.ARRAY(sa.Text)),
        sa.Column("created_at", sa.DateTime(timezone=True)),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
        sa.Column("rank_in_query", sa.Integer),
        sa.Column("raw_response", postgresql.JSONB),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        schema="intel",
    )
    op.create_index("idx_snapshots_workshop_id", "workshop_snapshots", ["workshop_id"], schema="intel")
    op.create_index("idx_snapshots_date_query", "workshop_snapshots", ["snapshot_date", "query_type"], schema="intel")
    op.create_index("idx_snapshots_captured_at", "workshop_snapshots", ["captured_at"], schema="intel")


def downgrade() -> None:
    op.drop_table("workshop_snapshots", schema="intel")
    op.execute("DROP SCHEMA IF EXISTS intel CASCADE")
