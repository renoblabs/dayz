"""Alembic env for the intel schema (separate from kb)."""

from logging.config import fileConfig
from pathlib import Path
import sys

from alembic import context
from sqlalchemy import engine_from_config, pool, text

_here = Path(__file__).resolve().parent
sys.path.insert(0, str(_here.parent.parent.parent / "shared" / "src"))

from dayzstack_intel.models import Base  # noqa: E402
from dayzstack_shared.config import get_settings  # noqa: E402

config = context.config
config.set_main_option("sqlalchemy.url", get_settings().db_url_sync)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        version_table_schema="intel",
        include_schemas=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        # Ensure schema exists before alembic checks for the version table
        connection.execute(text("CREATE SCHEMA IF NOT EXISTS intel"))
        connection.commit()

        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            version_table_schema="intel",  # version table lives in intel.alembic_version
            include_schemas=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
