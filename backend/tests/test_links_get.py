"""
Tests for single link retrieval endpoint (GET /api/links/{link_id}).

Verifies:
- Authenticated user can retrieve their own link
- Nonexistent or invalid IDs return 404
- Another user's link returns 404 without leaking resource existence
- Unauthenticated requests return 401
"""

import uuid
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def create_user_and_session(prefix="Getter"):
    uid = uuid.uuid4().hex[:8]
    data = {
        "name": f"{prefix} {uid}",
        "email": f"{prefix.lower()}_{uid}@example.com",
        "username": f"{prefix.lower()}_{uid}",
        "password": "Password123!",
    }
    client.post("/api/auth/signup", json=data)
    login_res = client.post(
        "/api/auth/login",
        json={"email": data["email"], "password": data["password"]},
    )
    assert login_res.status_code == 200
    return login_res.cookies, login_res.json()["user"]["id"]


def test_get_link_success():
    """Retrieve existing link owned by the user."""
    cookies, _ = create_user_and_session("Owner")

    create_res = client.post(
        "/api/links",
        json={"destinationUrl": "https://example.com/single-target", "title": "Single Target"},
        cookies=cookies,
    )
    assert create_res.status_code == 201
    link_id = create_res.json()["id"]

    res = client.get(f"/api/links/{link_id}", cookies=cookies)
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == link_id
    assert data["destinationUrl"] == "https://example.com/single-target"
    assert data["title"] == "Single Target"


def test_get_link_nonexistent():
    """Nonexistent valid-format ObjectId returns 404."""
    cookies, _ = create_user_and_session("NonExistent")
    fake_id = "507f1f77bcf86cd799439011"

    res = client.get(f"/api/links/{fake_id}", cookies=cookies)
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()


def test_get_link_invalid_id_format():
    """Malformed ID returns 404."""
    cookies, _ = create_user_and_session("BadId")

    res = client.get("/api/links/not-a-valid-id", cookies=cookies)
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()


def test_get_link_another_users_link_returns_404():
    """
    Attempting to view another user's link must return 404 (not 403)
    to prevent leaking resource existence.
    """
    cookies_owner, _ = create_user_and_session("LegitOwner")
    cookies_stranger, _ = create_user_and_session("Stranger")

    # Owner creates link
    create_res = client.post(
        "/api/links",
        json={"destinationUrl": "https://private-target.com"},
        cookies=cookies_owner,
    )
    assert create_res.status_code == 201
    target_id = create_res.json()["id"]

    # Stranger attempts to retrieve it
    res = client.get(f"/api/links/{target_id}", cookies=cookies_stranger)
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()


def test_get_link_unauthenticated():
    """Unauthenticated requests must return 401."""
    fresh_client = TestClient(app)
    res = fresh_client.get("/api/links/507f1f77bcf86cd799439011")
    assert res.status_code == 401
