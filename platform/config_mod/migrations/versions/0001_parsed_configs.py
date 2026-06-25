"""parsed_configs in config schema.

Revision ID: 0001
Revises:
Create Date: 2026-04-26
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_TYPES = (
    "types_xml,cfgspawnabletypes_xml,cfgeventspawns_xml,"
    "expansion_json,traderplus_json,mission_init_c,server_cfg"
)


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS config")
    op.create_table(
        "parsed_configs",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("config_type", sa.Text, nullable=False),
        sa.Column("source_label", sa.Text, nullable=False),
        sa.Column("source_path", sa.Text),
        sa.Column("parsed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("parsed_data", postgresql.JSONB, nullable=False),
        sa.Column("raw_content", sa.Text),
        sa.Column("file_hash", sa.Text, nullable=False),
        sa.Column("metadata", postgresql.JSONB),
        sa.CheckConstraint(
            "config_type IN ({})".format(",".join(f"'{t}'" for t in _TYPES.split(","))),
            name="ck_parsed_configs_type",
        ),
        schema="config",
    )
    op.create_index("idx_parsed_configs_type", "parsed_configs", ["config_type"], schema="config")
    op.create_index("idx_parsed_configs_label", "parsed_configs", ["source_label"], schema="config")
    op.create_index("idx_parsed_configs_hash", "parsed_configs", ["file_hash"], schema="config")


def downgrade() -> None:
    op.drop_table("parsed_configs", schema="config")
    op.execute("DROP SCHEMA IF EXISTS config CASCADE")
