"""
Authentication router for DayZ HiveAPI.

This module provides endpoints for server authentication.
"""

import logging
import uuid
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
import jwt

from ..config import settings
from ..deps import get_db
from ..db.models import Server
from ..services.events import record_security_event

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter()


def _signing_secret() -> str:
    """
    Return the JWT signing secret, or raise if it is not configured.

    Tokens are signed with HS256 using JWT_SIGNING_SECRET. The signing secret
    is loaded strictly from config — there is no insecure literal fallback.
    """
    secret = settings.JWT_SIGNING_SECRET
    if not secret:
        logger.error("JWT_SIGNING_SECRET is not configured; cannot issue tokens.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Server misconfigured: JWT signing secret is not set.",
        )
    return secret

# Define request and response models
class ServerLoginRequest(BaseModel):
    server_id: str
    proof: Optional[str] = None

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int

@router.post("/server-login", response_model=TokenResponse)
async def server_login(
    request: ServerLoginRequest,
    db: Session = Depends(get_db),
):
    """
    Authenticate a server and return an access token.
    
    If REQUEST_SIGNATURE_REQUIRED is False, minimal validation is performed.
    Otherwise, proof signature would be validated (not implemented yet).
    """
    # Check if server exists
    server = db.query(Server).filter(Server.id == request.server_id).first()
    if not server:
        logger.warning(f"Login attempt for non-existent server ID: {request.server_id}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid server credentials",
        )
    
    # Update server last seen
    server.last_seen_at = datetime.utcnow()
    db.commit()
    
    # Log security event
    record_security_event(
        db=db,
        event_type="server_login",
        server_id=server.id,
        payload={"host_fingerprint": server.host_fingerprint}
    )
    
    # Generate token expiration
    expires_delta = timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    expire = datetime.utcnow() + expires_delta
    
    # When signature validation is disabled, skip proof verification but still
    # sign the token with the configured signing secret.
    if not settings.REQUEST_SIGNATURE_REQUIRED:
        logger.info(f"Signature validation skipped for server: {server.id}")

        token_data = {
            "sub": server.id,
            "iss": settings.JWT_ISSUER,
            "exp": expire.timestamp(),
            "type": "server",
            "cluster": server.cluster_id,
        }

        token = jwt.encode(token_data, _signing_secret(), algorithm="HS256")

        return TokenResponse(
            access_token=token,
            expires_in=int(expires_delta.total_seconds())
        )
    
    # In production, validate proof signature
    if not request.proof:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication proof"
        )

    try:
        import base64
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import padding
        from cryptography.exceptions import InvalidSignature

        # Load public key
        public_key = serialization.load_pem_public_key(
            server.public_key_pem.encode('utf-8')
        )

        # Decode proof (base64 signature)
        signature = base64.b64decode(request.proof)

        # Verify signature
        # The message being signed is the server_id
        public_key.verify(
            signature,
            request.server_id.encode('utf-8'),
            padding.PKCS1v15(),
            hashes.SHA256()
        )
        
        logger.info(f"Signature verified for server: {server.id}")

    except (ValueError, InvalidSignature) as e:
        logger.warning(f"Invalid signature for server {server.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication proof"
        )
    except Exception as e:
        logger.error(f"Error verifying signature: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error verifying authentication"
        )

    # Create token payload
    token_data = {
        "sub": server.id,
        "iss": settings.JWT_ISSUER,
        "exp": expire.timestamp(),
        "type": "server",
        "cluster": server.cluster_id,
    }
    
    # Sign token.
    # NOTE: settings.JWT_ALGORITHM defaults to RS256, but tokens are signed with
    # HS256 here because RS256 private-key management is not yet wired up. The
    # signing secret is loaded strictly from config (see _signing_secret).
    token = jwt.encode(token_data, _signing_secret(), algorithm="HS256")

    return TokenResponse(
        access_token=token,
        expires_in=int(expires_delta.total_seconds())
    )
