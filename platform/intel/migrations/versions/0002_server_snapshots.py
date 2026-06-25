"""server_snapshots + server_mods (intel schema).

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-26
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "server_snapshots",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("snapshot_date", sa.Date, nullable=False),
        sa.Column("source", sa.Text, nullable=False),         # 'battlemetrics' | 'dzsa' | 'steam_browser'
        sa.Column("server_id", sa.Text, nullable=False),
        sa.Column("server_name", sa.Text, nullable=False),
        sa.Column("map_name", sa.Text),
        sa.Column("player_count", sa.Integer),
        sa.Column("max_players", sa.Integer),
        sa.Column("queue_count", sa.Integer),
        sa.Column("rank_in_source", sa.Integer),
        sa.Column("ip", sa.Text),
        sa.Column("port", sa.Integer),
        sa.Column("raw_response", postgresql.JSONB),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        schema="intel",
    )
    op.create_index("idx_server_snap_date_src", "server_snapshots", ["snapshot_date", "source"], schema="intel")
    op.create_index("idx_server_snap_id", "server_snapshots", ["server_id"], schema="intel")
    op.create_index("idx_server_snap_captured", "server_snapshots", ["captured_at"], schema="intel")

    op.create_table(
        "server_mods",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("snapshot_date", sa.Date, nullable=False),
        sa.Column("server_id", sa.Text, nullable=False),
        sa.Column("source", sa.Text, nullable=False),
        sa.Column("mod_name", sa.Text, nullable=False),
        sa.Column("workshop_id", sa.Text),
        sa.Column("raw_mod_string", sa.Text, nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        schema="intel",
    )
    op.create_index("idx_server_mods_workshop", "server_mods", ["workshop_id"], schema="intel")
    op.create_index("idx_server_mods_server", "server_mods", ["server_id"], schema="intel")
    op.create_index("idx_server_mods_date", "server_mods", ["snapshot_date"], schema="intel")


def downgrade() -> None:
    op.drop_table("server_mods", schema="intel")
    op.drop_table("server_snapshots", schema="intel")
