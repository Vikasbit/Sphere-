"""
Tests for link deletion endpoint (DELETE /api/links/{link_id}).

Verifies:
- Authenticated user can delete their own link
- Link is removed from MongoDB
- Attempting to delete another user's link returns 404 and does not delete it
- Attempting to delete a nonexistent link returns 404
- Unauthenticated requests return 401
"""

import uuid
from bson import ObjectId
from fastapi.testclient import TestClient

from app.core.database import get_database
from app.main import app

client = TestClient(app)


def create_user_and_session(prefix="Deleter"):
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


def test_delete_link_success():
    """User deletes their own link."""
    cookies, _ = create_user_and_session("OwnerDel")

    create_res = client.post(
        "/api/links",
        json={"destinationUrl": "https://example.com/to-delete"},
        cookies=cookies,
    )
    assert create_res.status_code == 201
    link_id = create_res.json()["id"]

    # Delete link
    del_res = client.delete(f"/api/links/{link_id}", cookies=cookies)
    assert del_res.status_code == 200
    assert "deleted" in del_res.json()["message"].lower()

    # Verify removed from database
    db = get_database()
    assert db.links.find_one({"_id": ObjectId(link_id)}) is None

    # Subsequent GET returns 404
    get_res = client.get(f"/api/links/{link_id}", cookies=cookies)
    assert get_res.status_code == 404


def test_delete_link_another_users_link_prevented():
    """Attempting to delete another user's link returns 404 and does NOT delete it."""
    cookies_owner, _ = create_user_and_session("RealOwner")
    cookies_intruder, _ = create_user_and_session("Intruder")

    create_res = client.post(
        "/api/links",
        json={"destinationUrl": "https://protected-from-deletion.com"},
        cookies=cookies_owner,
    )
    assert create_res.status_code == 201
    link_id = create_res.json()["id"]

    # Intruder tries to delete
    del_res = client.delete(f"/api/links/{link_id}", cookies=cookies_intruder)
    assert del_res.status_code == 404
    assert "not found" in del_res.json()["detail"].lower()

    # Verify link STILL exists in database!
    db = get_database()
    assert db.links.find_one({"_id": ObjectId(link_id)}) is not None


def test_delete_link_nonexistent():
    """Deleting nonexistent link returns 404."""
    cookies, _ = create_user_and_session("DeleteNonExistent")
    fake_id = "507f1f77bcf86cd799439011"

    res = client.delete(f"/api/links/{fake_id}", cookies=cookies)
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()


def test_delete_link_unauthenticated():
    """Unauthenticated requests must return 401."""
    fresh_client = TestClient(app)
    res = fresh_client.delete("/api/links/507f1f77bcf86cd799439011")
    assert res.status_code == 401
