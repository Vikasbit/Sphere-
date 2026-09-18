"""
FastAPI authentication dependencies.

Provides `get_current_user` to inspect access-token httpOnly cookie (or Bearer header),
validate the JWT signature and claims, fetch the user from MongoDB, and enforce security.
"""

import logging
from typing import Any
from bson import ObjectId
from fastapi import Cookie, Depends, Header, HTTPException, Request, status
from jose import JWTError

from app.core.config import get_settings
from app.core.database import get_database
from app.core.security import decode_access_token

logger = logging.getLogger(__name__)


def extract_token_from_request(
    request: Request,
    authorization: str | None = Header(default=None),
) -> str | None:
    """
    Extract access token from httpOnly cookie or Authorization Bearer header.
    Cookie takes precedence as per web app specification.
    """
    settings = get_settings()
    cookie_token = request.cookies.get(settings.access_cookie_name)
    if cookie_token:
        return cookie_token

    if authorization and authorization.startswith("Bearer "):
        return authorization.split(" ", 1)[1].strip()

    return None


async def get_current_user(
    request: Request,
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    """
    FastAPI dependency that returns the currently authenticated user document.

    Raises:
        HTTPException(401): If token is missing, invalid, expired, or user not found.
    """
    token = extract_token_from_request(request, authorization)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_access_token(token)
    except (JWTError, ValueError) as exc:
        logger.debug("Access token validation failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id_str = payload.get("sub")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing subject identifier",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_oid = ObjectId(user_id_str)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user identifier in token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    db = get_database()
    user = db.users.find_one({"_id": user_oid})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def get_optional_current_user(
    request: Request,
    authorization: str | None = Header(default=None),
) -> dict[str, Any] | None:
    """
    Dependency for routes where authentication is optional (e.g. public profiles).
    Returns user dict if valid token is present, else None without raising 401.
    """
    token = extract_token_from_request(request, authorization)
    if not token:
        return None

    try:
        payload = decode_access_token(token)
        user_id_str = payload.get("sub")
        if not user_id_str:
            return None
        db = get_database()
        return db.users.find_one({"_id": ObjectId(user_id_str)})
    except Exception:
        return None
