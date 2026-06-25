"""
Async SQLAlchemy engine + session factory.
Uses asyncpg driver for PostgreSQL.
"""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings

settings = get_settings()

engine_kwargs: dict = {"echo": settings.debug}
if not settings.database_url.startswith("sqlite"):
    engine_kwargs.update(pool_size=10, max_overflow=20, pool_pre_ping=True)

engine = create_async_engine(settings.database_url, **engine_kwargs)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncSession:  # type: ignore[override]
    async with AsyncSessionLocal() as session:
        yield session


async def create_tables() -> None:
    """Create all tables if they don't exist. Called at startup."""
    from sqlalchemy import text

    from app.db.models import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Idempotent column-adds for live DBs that predate model changes.
    # `create_all` only creates *missing tables*, not missing columns —
    # and we don't run alembic. List each (table, col, ddl_type) here.
    pending_columns = [
        ("server_status", "loaded_mods", "JSONB"),
    ]
    async with engine.begin() as conn:
        is_pg = engine.dialect.name == "postgresql"
        for table, col, ddl_type in pending_columns:
            if is_pg:
                await conn.execute(
                    text(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {col} {ddl_type}")
                )
            else:
                # SQLite (tests). No IF NOT EXISTS — swallow the dup-column error.
                try:
                    await conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col}"))
                except Exception:
                    pass
