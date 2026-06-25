from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ── Auth ───────────────────────────────────────────────────
    # Must match BossSignalConfig.SHARED_SECRET in your Enforce mod.
    # Default is a placeholder — set BOSSSIGNAL_SECRET in the environment.
    # The shared-secret check refuses requests while this is left at CHANGE_ME.
    bosssignal_secret: str = "CHANGE_ME"

    # ── Database ───────────────────────────────────────────────
    database_url: str = "postgresql+asyncpg://bosssignal:bosssignal@localhost:5432/bosssignal"

    # KB database (platform/dayz-stack postgres). Optional — KB routes return
    # empty results rather than 500'ing if unset or unreachable.
    # In docker, point at host.docker.internal:5436 to reach the KB container
    # from outside the bosssignal-backend compose network.
    kb_database_url: str | None = "postgresql+asyncpg://dayzstack:dayzstack@host.docker.internal:5436/dayzstack"

    # ── Server ────────────────────────────────────────────────
    host: str = "0.0.0.0"
    port: int = 8080

    # CORS allowed origins. Comma-separated list, or "*" for any (local dev only).
    # In production, set CORS_ORIGINS to your dashboard origin(s).
    cors_origins: str = "*"

    # ── Behaviour ─────────────────────────────────────────────
    # How many SSE events to keep in the in-memory broadcast queue
    # per subscriber. Higher = more memory, but handles slow clients better.
    sse_queue_size: int = 256

    # Discard SSE events older than this (seconds) from replay buffer
    sse_replay_window: int = 300

    # Maximum events to return on /api/v1/events GET
    events_page_size: int = 100

    # Maximum boss encounters to return on /api/v1/bosses GET
    bosses_page_size: int = 50

    # Debug
    debug: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
