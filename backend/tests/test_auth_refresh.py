"""
Tests for refresh token endpoint and token rotation (POST /api/auth/refresh).

Verifies:
- Valid refresh rotates token, revokes old session, creates new session
- Expired refresh session is rejected
- Revoked refresh session is rejected
- Old rotated refresh token cannot be reused
- Reuse detection: attempting to reuse an already rotated token revokes all active sessions for the user
"""

import uuid
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.core.database import get_database
from app.main import app

client = TestClient(app)
settings = get_settings()


def get_authenticated_session():
    uid = uuid.uuid4().hex[:8]
    data = {
        "name": f"Refresh {uid}",
        "email": f"refresh_{uid}@example.com",
        "username": f"refresh_{uid}",
        "password": "Password123!",
    }
    client.post("/api/auth/signup", json=data)
    res = client.post(
        "/api/auth/login",
        json={"email": data["email"], "password": data["password"]},
    )
    assert res.status_code == 200
    return data, res.cookies, res.json()["user"]["id"]


def test_refresh_valid_token_rotation():
    """Valid refresh should rotate both access and refresh cookies and revoke previous session."""
    data, cookies, user_id = get_authenticated_session()
    old_refresh = cookies[settings.refresh_cookie_name]
    old_access = cookies[settings.access_cookie_name]

    # Perform refresh
    res = client.post("/api/auth/refresh", cookies={settings.refresh_cookie_name: old_refresh})
    assert res.status_code == 200
    assert "refreshed" in res.json()["message"]

    new_cookies = res.cookies
    new_refresh = new_cookies[settings.refresh_cookie_name]
    new_access = new_cookies[settings.access_cookie_name]

    # Cookies must be rotated (new distinct values)
    assert new_refresh != old_refresh
    assert new_access != old_access

    # In database: verify old session has revokedAt set
    db = get_database()
    sessions = list(db.refresh_sessions.find({"userId": user_id}))
    assert len(sessions) == 2

    # One is revoked with replacedBy, one is active
    revoked_count = sum(1 for s in sessions if s.get("revokedAt") is not None)
    active_count = sum(1 for s in sessions if s.get("revokedAt") is None)
    assert revoked_count == 1
    assert active_count == 1


def test_refresh_expired_token():
    """Expired refresh token must be rejected with 401."""
    data, cookies, user_id = get_authenticated_session()
    raw_refresh = cookies[settings.refresh_cookie_name]

    # Expire the session in MongoDB
    db = get_database()
    past_time = datetime.now(timezone.utc) - timedelta(days=1)
    db.refresh_sessions.update_one(
        {"userId": user_id},
        {"$set": {"expiresAt": past_time}},
    )

    res = client.post("/api/auth/refresh", cookies={settings.refresh_cookie_name: raw_refresh})
    assert res.status_code == 401
    assert "expired" in res.json()["detail"].lower()


def test_refresh_token_reuse_revokes_all_sessions():
    """
    Attempting to reuse an already rotated refresh token is treated as an attack.
    The system must detect reuse and revoke ALL active sessions for that user.
    """
    data, cookies, user_id = get_authenticated_session()
    original_refresh = cookies[settings.refresh_cookie_name]

    # First rotation: original_refresh -> second_refresh
    res1 = client.post("/api/auth/refresh", cookies={settings.refresh_cookie_name: original_refresh})
    assert res1.status_code == 200
    second_refresh = res1.cookies[settings.refresh_cookie_name]

    # Now attacker or replay tries to use original_refresh again
    res2 = client.post("/api/auth/refresh", cookies={settings.refresh_cookie_name: original_refresh})
    assert res2.status_code == 401
    assert "reused" in res2.json()["detail"].lower()

    # Verify that the second (previously active) session was ALSO revoked as punishment/protection
    db = get_database()
    active_sessions = list(db.refresh_sessions.find({"userId": user_id, "revokedAt": None}))
    assert len(active_sessions) == 0

    # Even second_refresh is now invalid
    res3 = client.post("/api/auth/refresh", cookies={settings.refresh_cookie_name: second_refresh})
    assert res3.status_code == 401
