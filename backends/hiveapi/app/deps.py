"""
Dependency injection for DayZ HiveAPI.

This module provides dependency injection functions for database and Redis connections.
"""

import logging
import secrets
from typing import Generator, AsyncGenerator, Optional

import jwt
from fastapi import Header, HTTPException, status, Depends
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from redis.asyncio import Redis, from_url

from .config import settings

# Configure logging
logger = logging.getLogger(__name__)

# Create SQLAlchemy engine
engine = create_engine(
    settings.DB_URL,
    pool_pre_ping=True,  # Check connection before using from pool
    pool_size=10,        # Default connection pool size
    max_overflow=20,     # Allow up to 20 connections beyond pool_size
    pool_recycle=3600,   # Recycle connections after 1 hour
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create Base class for models
Base = declarative_base()

# Import models to ensure they're registered with Base
from .db import models  # noqa

def get_db() -> Generator[Session, None, None]:
    """
    Get a database session.
    
    Yields:
        SQLAlchemy Session
    """
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Database session error: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()

async def get_redis() -> AsyncGenerator[Redis, None]:
    """
    Get a Redis client.
    
    Yields:
        Redis client
    """
    redis = from_url(settings.REDIS_URL, encoding="utf-8", decode_responses=True)
    try:
        yield redis
    except Exception as e:
        logger.error(f"Redis connection error: {str(e)}")
        raise
    finally:
        await redis.close()


def get_authenticated_server_id(authorization: Optional[str] = Header(None)) -> str:
    """Verify the Bearer JWT and return the authenticated server id (the ``sub`` claim).

    This is the ONLY trusted source of a caller's server identity. State-changing
    endpoints must derive ``server_id`` from this dependency and must never read it
    from the request body. The token is verified against ``JWT_SIGNING_SECRET`` with
    the configured algorithm, and the ``exp``, ``iss`` and ``sub`` claims are required.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or malformed Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = authorization[len("Bearer "):].strip()
    secret = settings.JWT_SIGNING_SECRET
    if not secret:
        # Fail closed: without a secret we cannot verify anything.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Server misconfigured: JWT signing secret is not set",
        )
    try:
        claims = jwt.decode(
            token,
            secret,
            algorithms=[settings.JWT_ALGORITHM],
            issuer=settings.JWT_ISSUER,
            options={"require": ["exp", "iss", "sub"]},
        )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    sub = claims.get("sub")
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing subject claim",
        )
    return sub


_admin_basic = HTTPBasic(auto_error=True)


def require_admin(credentials: HTTPBasicCredentials = Depends(_admin_basic)) -> str:
    """Enforce HTTP Basic auth on admin endpoints using constant-time comparison.

    Fails closed: if ``ADMIN_PASSWORD`` is unset, admin access is *disabled* (403),
    never silently open.
    """
    expected_user = settings.ADMIN_USERNAME or ""
    expected_pass = settings.ADMIN_PASSWORD or ""
    if not expected_pass:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access is disabled (no ADMIN_PASSWORD configured)",
        )
    user_ok = secrets.compare_digest(credentials.username, expected_user)
    pass_ok = secrets.compare_digest(credentials.password, expected_pass)
    if not (user_ok and pass_ok):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username
