"""
Shared shared-secret auth helpers for BossSignal.

Two dependencies:

  require_secret
      Always enforces the X-BossSignal-Secret header. Used on write paths
      (POST /api/v1/events) and the hive read paths the Enforce mod calls.

  optional_read_secret
      Enforces the secret ONLY when settings.require_read_auth is True. By
      default (require_read_auth=False) it is a no-op so the unauthenticated
      browser dashboard read endpoints keep working unchanged. Operators who
      want defence-in-depth can set REQUIRE_READ_AUTH=true to lock reads too.

The secret is accepted ONLY via the X-BossSignal-Secret header — never via a
URL query parameter (query strings leak into access logs / proxies / history).
Comparison is constant-time via secrets.compare_digest.
"""
from __future__ import annotations

import secrets
from typing import Optional

from fastapi import Header, HTTPException, status

from app.config import get_settings

settings = get_settings()


def _check_secret(provided: Optional[str]) -> None:
    # Refuse all requests while the shared secret is left at its placeholder.
    if settings.bosssignal_secret == "CHANGE_ME":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Server misconfigured: set BOSSSIGNAL_SECRET.",
        )
    if not secrets.compare_digest(provided or "", settings.bosssignal_secret):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing secret.",
        )


def require_secret(
    x_bosssignal_secret: Optional[str] = Header(default=None),
) -> None:
    """Always require a valid X-BossSignal-Secret header."""
    _check_secret(x_bosssignal_secret)


def optional_read_secret(
    x_bosssignal_secret: Optional[str] = Header(default=None),
) -> None:
    """
    Require the secret on read routes ONLY when REQUIRE_READ_AUTH is set.

    Default (require_read_auth=False): no-op, reads stay open so the dashboard
    works without a secret.
    """
    if not settings.require_read_auth:
        return
    _check_secret(x_bosssignal_secret)
