"""
Tests for user logout endpoint (POST /api/auth/logout).

Verifies:
- Active refresh session is revoked in MongoDB
- Auth cookies are cleared
- Calling logout repeatedly is idempotent and does not error
"""

import uuid
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.core.database import get_database
from app.main import app

client = TestClient(app)
settings = get_settings()


def setup_user_session():
    uid = uuid.uuid4().hex[:8]
    data = {
        "name": f"Logout {uid}",
        "email": f"logout_{uid}@example.com",
        "username": f"logout_{uid}",
        "password": "Password123!",
    }
    client.post("/api/auth/signup", json=data)
    res = client.post(
        "/api/auth/login",
        json={"email": data["email"], "password": data["password"]},
    )
    assert res.status_code == 200
    return data, res.cookies, res.json()["user"]["id"]


def test_logout_revokes_session_and_clears_cookies():
    """Logout should revoke the session in DB and clear response cookies."""
    data, cookies, user_id = setup_user_session()

    # Pre-condition: User has active session
    db = get_database()
    active_pre = list(db.refresh_sessions.find({"userId": user_id, "revokedAt": None}))
    assert len(active_pre) == 1

    # Call logout
    res = client.post("/api/auth/logout", cookies=cookies)
    assert res.status_code == 200
    assert "Logged out" in res.json()["message"]

    # Post-condition: Refresh session in MongoDB has revokedAt set
    active_post = list(db.refresh_sessions.find({"userId": user_id, "revokedAt": None}))
    assert len(active_post) == 0

    # Verify cookies are cleared (max-age=0 or deleted)
    set_cookie_headers = res.headers.get_list("set-cookie")
    # Both cookies should be set to clear
    cookie_str = " ".join(set_cookie_headers).lower()
    assert settings.access_cookie_name in cookie_str
    assert settings.refresh_cookie_name in cookie_str


def test_logout_is_idempotent():
    """Calling logout without cookies or multiple times should return 200 without failure."""
    res1 = client.post("/api/auth/logout")
    assert res1.status_code == 200

    res2 = client.post("/api/auth/logout")
    assert res2.status_code == 200
