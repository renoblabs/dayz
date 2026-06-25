"""
Configuration settings for DayZ HiveAPI.

This module provides a Pydantic settings class that reads configuration from
environment variables with sensible defaults.
"""

from typing import Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

def normalize_db_url(url: str) -> str:
    """
    Normalize a Postgres URL so SQLAlchemy 2.x (with psycopg3) can parse it.

    Render/Railway often supply URLs starting with ``postgres://`` or
    ``postgresql://``.  The async/psycopg3 driver used by SQLAlchemy expects
    ``postgresql+psycopg://``.
    """
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg://", 1)
    if url.startswith("postgresql://") and "+psycopg" not in url:
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url

class Settings(BaseSettings):
    """Application settings loaded from environment variables with defaults."""

    # Environment
    ENV: str = Field(
        default="dev",
        description="Deployment environment: 'dev', 'test', or 'production'. "
                    "Insecure dev shortcuts are only honored when ENV is 'dev' or 'test'."
    )

    # Database settings
    DB_URL: str = Field(
        default="postgresql+psycopg://postgres:postgres@localhost:5432/hive",
        description="PostgreSQL connection string"
    )
    
    @field_validator("DB_URL")
    @classmethod
    def validate_db_url(cls, v: str) -> str:
        return normalize_db_url(v)
    
    # Redis settings
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection string"
    )
    
    # JWT settings
    JWT_ISSUER: str = Field(
        default="hiveapi",
        description="JWT issuer claim"
    )
    JWT_ALGORITHM: str = Field(
        default="HS256",
        description="JWT signing algorithm. HS256 (symmetric) using JWT_SIGNING_SECRET; "
                    "tokens are both signed and verified with this algorithm."
    )
    JWT_SIGNING_SECRET: Optional[str] = Field(
        default=None,
        description="Secret used to sign issued JWTs (HS256). Required to issue tokens."
    )
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=60,
        description="JWT access token expiration in minutes"
    )
    
    # Security settings
    REQUEST_SIGNATURE_REQUIRED: bool = Field(
        default=True,
        description="Require HTTP signatures for server endpoints"
    )
    ORIGIN_SECRET: Optional[str] = Field(
        default="",
        description="Secret for origin verification with Cloudflare Tunnel"
    )
    
    # TTL settings
    IDEMPOTENCY_TTL_SECONDS: int = Field(
        default=600,
        description="Time-to-live for idempotency keys in seconds"
    )
    MOVE_TICKET_TTL_SECONDS: int = Field(
        default=90,
        description="Time-to-live for move tickets in seconds"
    )
    LOGOUT_GRACE_SECONDS: int = Field(
        default=30,
        description="Grace period for logout intent in seconds"
    )
    SERVER_SWITCH_COOLDOWN_SECONDS: int = Field(
        default=180,
        description="Cooldown period between server switches in seconds"
    )
    
    # Observability settings
    PROMETHEUS_METRICS: bool = Field(
        default=True,
        description="Enable Prometheus metrics collection"
    )
    LOG_LEVEL: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)"
    )
    
    # Admin settings
    ADMIN_ENABLED: bool = Field(
        default=True,
        description="Enable admin endpoints"
    )
    ADMIN_USERNAME: str = Field(
        default="admin",
        description="Admin username for Basic Auth"
    )
    ADMIN_PASSWORD: str = Field(
        default="",
        description="Admin password for Basic Auth (empty disables auth)"
    )
    
    # CORS
    CORS_ORIGINS: str = Field(
        default="*",
        description="Comma-separated allowed CORS origins. '*' allows any origin but "
                    "credentialed requests are automatically disabled in that case "
                    "(per the CORS spec). Set explicit origins in production."
    )

    # Keys directory for server public keys
    KEYS_DIR: str = Field(
        default="./keys",
        description="Directory containing server keys"
    )
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True
    )

# Create a global settings instance
settings = Settings()
