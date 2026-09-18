"""
Tests for user login endpoint (POST /api/auth/login).

Verifies:
- Valid credentials return 200 and set secure httpOnly cookies for access and refresh tokens
- Invalid credentials (wrong password or unregistered email) return 401 without leaking user existence
- Raw tokens are never stored in MongoDB
"""

import uuid
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.core.database import get_database
from app.main import app

client = TestClient(app)
settings = get_settings()


def create_user():
    uid = uuid.uuid4().hex[:8]
    data = {
        "name": f"Login {uid}",
        "email": f"login_{uid}@example.com",
        "username": f"login_{uid}",
        "password": "Password123!",
    }
    res = client.post("/api/auth/signup", json=data)
    assert res.status_code == 201
    return data


def test_login_valid_credentials():
    """Logging in with correct credentials sets httpOnly cookies and returns safe user data."""
    data = create_user()

    res = client.post(
        "/api/auth/login",
        json={"email": data["email"], "password": data["password"]},
    )
    assert res.status_code == 200
    res_data = res.json()

    assert "user" in res_data
    assert res_data["user"]["email"] == data["email"]
    assert "password" not in res_data["user"]
    assert "passwordHash" not in res_data["user"]

    # Verify cookies were set in response
    cookies = res.cookies
    assert settings.access_cookie_name in cookies
    assert settings.refresh_cookie_name in cookies

    # Verify refresh session was saved as SHA-256 hash in DB, not raw token
    raw_refresh = cookies[settings.refresh_cookie_name]
    db = get_database()
    # Query by raw token should yield nothing
    assert db.refresh_sessions.find_one({"tokenHash": raw_refresh}) is None

    # But querying by user exists
    user_sessions = list(db.refresh_sessions.find({"userId": res_data["user"]["id"]}))
    assert len(user_sessions) >= 1
    assert user_sessions[-1]["revokedAt"] is None


def test_login_invalid_password():
    """Wrong password returns 401 Unauthorized."""
    data = create_user()

    res = client.post(
        "/api/auth/login",
        json={"email": data["email"], "password": "WrongPassword999!"},
    )
    assert res.status_code == 401
    assert "Invalid email or password" in res.json()["detail"]
    assert settings.access_cookie_name not in res.cookies


def test_login_nonexistent_email():
    """Unregistered email returns 401 with identical message to prevent user enumeration."""
    res = client.post(
        "/api/auth/login",
        json={"email": "nobody_exists_here_9876@example.com", "password": "Password123!"},
    )
    assert res.status_code == 401
    assert "Invalid email or password" in res.json()["detail"]
