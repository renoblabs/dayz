"""Settings — pydantic-settings, env-driven. Doppler integration deferred."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Stack-wide settings. Override via env vars or .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="DAYZSTACK_",
        extra="ignore",
    )

    # Postgres
    db_host: str = "127.0.0.1"
    db_port: int = 5436
    db_user: str = "dayzstack"
    db_password: str = "dayzstack"
    db_name: str = "dayzstack"

    # Embedding model
    ollama_url: str = "http://127.0.0.1:11434"
    embed_model: str = "nomic-embed-text"
    embed_dim: int = 768

    # Source dirs to ingest from (relative to repo root or absolute)
    dayzapi_root: str = "../dayzAPI"

    # Logging
    log_level: str = "INFO"
    log_format: str = Field(default="console", pattern="^(console|json)$")

    @property
    def db_url(self) -> str:
        """SQLAlchemy async URL."""
        return (
            f"postgresql+asyncpg://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    @property
    def db_url_sync(self) -> str:
        """Sync URL for alembic migrations."""
        return (
            f"postgresql+psycopg://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )


_settings: Settings | None = None


def get_settings() -> Settings:
    """Cached settings accessor."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
