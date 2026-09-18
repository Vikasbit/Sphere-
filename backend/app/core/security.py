"""
Security, hashing, JWT token, and cookie utilities.

- Password hashing: Argon2id via passlib
- Access token: 15-minute JWT signed with HS256
- Refresh token: High-entropy random token hashed via SHA-256 for database storage
- Verification/reset tokens: Secure random tokens hashed via SHA-256
- Cookie helpers: Centralized httpOnly cookie management for auth tokens
"""

from datetime import datetime, timedelta, timezone
import hashlib
import logging
import secrets
from typing import Any

from fastapi import Response
from jose import JWTError, jwt
from passlib.hash import argon2

from app.core.config import get_settings

logger = logging.getLogger(__name__)

ALGORITHM = "HS256"
# Argon2id hasher using passlib with recommended RFC parameters
_hasher = argon2.using(type="ID")


# ---------------------------------------------------------------------------
# Password Security (Argon2id)
# ---------------------------------------------------------------------------

def hash_password(password: str) -> str:
    """Hash a plaintext password using Argon2id."""
    return _hasher.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against an Argon2id hash."""
    try:
        return _hasher.verify(plain_password, hashed_password)
    except Exception as e:
        logger.warning("Password verification error: %s", e)
        return False


# ---------------------------------------------------------------------------
# Token Utilities
# ---------------------------------------------------------------------------

def generate_secure_token(nbytes: int = 32) -> str:
    """Generate a URL-safe cryptographically secure random token string."""
    return secrets.token_urlsafe(nbytes)


def hash_token(raw_token: str) -> str:
    """Compute SHA-256 hex digest of a token for secure database storage."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def create_access_token(user_id: str, custom_claims: dict[str, Any] | None = None) -> str:
    """
    Create a signed 15-minute JWT access token.

    Contains:
    - sub: user_id (string)
    - type: "access"
    - iat: issued-at timestamp
    - exp: expiration timestamp (current time + 15 min)
    """
    settings = get_settings()
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=settings.access_token_expire_minutes)

    payload: dict[str, Any] = {
        "sub": str(user_id),
        "type": "access",
        "jti": secrets.token_hex(16),
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }
    if custom_claims:
        payload.update(custom_claims)

    encoded_jwt = jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> dict[str, Any]:
    """
    Decode and validate a JWT access token.

    Raises:
        JWTError: If signature is invalid, token has expired, or payload malformed.
        ValueError: If token type is not 'access'.
    """
    settings = get_settings()
    payload = jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])

    if payload.get("type") != "access":
        raise ValueError("Invalid token type")

    return payload


def create_refresh_token() -> tuple[str, str, datetime]:
    """
    Create a new 7-day refresh token.

    Returns:
        tuple of (raw_token, token_hash, expires_at)
        - raw_token: sent to user via httpOnly cookie only, never stored in DB
        - token_hash: SHA-256 hash stored in refresh_sessions collection
        - expires_at: datetime in UTC when the token expires
    """
    settings = get_settings()
    raw_token = generate_secure_token(48)
    token_hash = hash_token(raw_token)
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
    return raw_token, token_hash, expires_at


# ---------------------------------------------------------------------------
# Cookie Security Management
# ---------------------------------------------------------------------------

def set_auth_cookies(
    response: Response,
    access_token: str,
    refresh_token: str,
) -> None:
    """
    Set centralized secure httpOnly cookies for access and refresh tokens.

    - access_token: lifetime = access_token_expire_minutes (default 15m)
    - refresh_token: lifetime = refresh_token_expire_days (default 7d)
    - httpOnly=True
    - secure controlled via settings.cookie_secure
    - samesite controlled via settings.cookie_samesite
    """
    settings = get_settings()

    access_max_age = settings.access_token_expire_minutes * 60
    refresh_max_age = settings.refresh_token_expire_days * 86400

    response.set_cookie(
        key=settings.access_cookie_name,
        value=access_token,
        max_age=access_max_age,
        expires=access_max_age,
        httponly=True,
        secure=settings.effective_cookie_secure,
        samesite=settings.cookie_samesite,
        domain=settings.cookie_domain,
        path="/",
    )

    response.set_cookie(
        key=settings.refresh_cookie_name,
        value=refresh_token,
        max_age=refresh_max_age,
        expires=refresh_max_age,
        httponly=True,
        secure=settings.effective_cookie_secure,
        samesite=settings.cookie_samesite,
        domain=settings.cookie_domain,
        path="/",
    )


def clear_auth_cookies(response: Response) -> None:
    """
    Clear authentication cookies upon logout or credential invalidation.
    Sets max_age=0 and empty values.
    """
    settings = get_settings()

    response.delete_cookie(
        key=settings.access_cookie_name,
        domain=settings.cookie_domain,
        path="/",
        httponly=True,
        secure=settings.effective_cookie_secure,
        samesite=settings.cookie_samesite,
    )
    response.delete_cookie(
        key=settings.refresh_cookie_name,
        domain=settings.cookie_domain,
        path="/",
        httponly=True,
        secure=settings.effective_cookie_secure,
        samesite=settings.cookie_samesite,
    )
