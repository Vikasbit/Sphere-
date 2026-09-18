"""
Tests for current user profile endpoint (GET /api/auth/me).

Verifies:
- Authenticated requests return safe user profile
- Unauthenticated requests return 401
- Expired or malformed tokens return 401
- Sensitive fields (passwords, hashes, tokens) are never returned
"""

import uuid
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from jose import jwt

from app.core.config import get_settings
from app.main import app

client = TestClient(app)
settings = get_settings()


def register_and_login():
    uid = uuid.uuid4().hex[:8]
    data = {
        "name": f"Me {uid}",
        "email": f"me_{uid}@example.com",
        "username": f"me_{uid}",
        "password": "Password123!",
    }
    client.post("/api/auth/signup", json=data)
    res = client.post(
        "/api/auth/login",
        json={"email": data["email"], "password": data["password"]},
    )
    assert res.status_code == 200
    return data, res.cookies


def test_me_authenticated():
    """Valid access token cookie returns current user details."""
    data, cookies = register_and_login()

    res = client.get("/api/auth/me", cookies=cookies)
    assert res.status_code == 200
    user = res.json()

    assert user["email"] == data["email"]
    assert user["username"] == data["username"]
    assert user["name"] == data["name"]
    assert "isEmailVerified" in user

    # Strict security validation: no secrets
    assert "password" not in user
    assert "passwordHash" not in user
    assert "emailVerificationTokenHash" not in user
    assert "passwordResetTokenHash" not in user


def test_me_unauthenticated():
    """Request with no cookies or authorization header returns 401."""
    # Create new client without saved cookies
    fresh_client = TestClient(app)
    res = fresh_client.get("/api/auth/me")
    assert res.status_code == 401
    assert "Not authenticated" in res.json()["detail"]


def test_me_invalid_token():
    """Malformed or invalid signature returns 401."""
    res = client.get(
        "/api/auth/me",
        cookies={settings.access_cookie_name: "invalid.jwt.token"},
    )
    assert res.status_code == 401


def test_me_expired_token():
    """Expired JWT token returns 401."""
    past = datetime.now(timezone.utc) - timedelta(minutes=30)
    expired_payload = {
        "sub": "507f1f77bcf86cd799439011",
        "type": "access",
        "iat": int((past - timedelta(minutes=15)).timestamp()),
        "exp": int(past.timestamp()),
    }
    expired_token = jwt.encode(expired_payload, settings.jwt_secret, algorithm="HS256")

    res = client.get(
        "/api/auth/me",
        cookies={settings.access_cookie_name: expired_token},
    )
    assert res.status_code == 401
