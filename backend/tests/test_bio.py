"""
Tests for Phase 7: Bio-Link Builder and Public Bio Page API.

Verifies:
- Profile auto-initialization with defaults
- Profile updates (displayName, bio, avatar, colors, social links)
- Color and URL validation rules (rejects invalid hex and non-web URLs)
- Bio link CRUD (create, update, delete, toggle visibility)
- Sequential link reordering with foreign link rejection
- User ownership isolation (User B cannot edit or delete User A's profile/links)
- Public profile endpoint:
  - Accessible without authentication
  - 200 for published profiles
  - 404 for unpublished profiles (prevents existence leakage)
  - 404 for nonexistent profiles
  - Only visible links returned in sequential position order
  - Private metadata (userId, email, passwordHash) strictly omitted
"""

import uuid
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def create_user_and_session(prefix="BioUser"):
    """Helper to create a fresh user and return session cookies, user ID, and username."""
    uid = uuid.uuid4().hex[:8]
    username = f"{prefix.lower()}_{uid}"
    data = {
        "name": f"{prefix} {uid}",
        "email": f"{username}@example.com",
        "username": username,
        "password": "Password123!",
    }
    client.post("/api/auth/signup", json=data)
    login_res = client.post(
        "/api/auth/login",
        json={"email": data["email"], "password": data["password"]},
    )
    assert login_res.status_code == 200
    return login_res.cookies, login_res.json()["user"]["id"], username


# =====================================================================
# Profile Initialization & Update Tests
# =====================================================================

def test_get_or_create_bio_profile_default():
    """Initial GET /api/bio creates and returns default BioProfile."""
    cookies, user_id, username = create_user_and_session("InitBio")

    res = client.get("/api/bio", cookies=cookies)
    assert res.status_code == 200
    data = res.json()

    assert data["userId"] == user_id
    assert data["username"] == username
    assert data["backgroundColor"] == "#0F172A"
    assert data["buttonColor"] == "#1E293B"
    assert data["textColor"] == "#FFFFFF"
    assert data["isPublished"] is True
    assert data["socialLinks"] == []


def test_update_bio_profile_success():
    """Update profile settings, theme colors, and social links."""
    cookies, _, username = create_user_and_session("UpdateBio")

    update_payload = {
        "displayName": "Alex Rivera",
        "bio": "Open-source developer and content creator.",
        "avatarUrl": "https://example.com/avatar.jpg",
        "backgroundColor": "#1E1B4B",
        "buttonColor": "#4338CA",
        "textColor": "#EEF2FF",
        "isPublished": True,
        "socialLinks": [
            {"platform": "github", "url": "https://github.com/alexrivera"},
            {"platform": "twitter", "url": "https://x.com/alexrivera"},
        ],
    }

    res = client.put("/api/bio", json=update_payload, cookies=cookies)
    assert res.status_code == 200
    data = res.json()

    assert data["displayName"] == "Alex Rivera"
    assert data["bio"] == "Open-source developer and content creator."
    assert data["avatarUrl"] == "https://example.com/avatar.jpg"
    assert data["backgroundColor"] == "#1E1B4B"
    assert data["buttonColor"] == "#4338CA"
    assert data["textColor"] == "#EEF2FF"
    assert len(data["socialLinks"]) == 2
    assert data["socialLinks"][0]["platform"] == "github"


def test_update_bio_profile_validation_invalid_color():
    """Submitting an invalid hex color returns 422."""
    cookies, _, _ = create_user_and_session("BadColorBio")

    payload = {
        "displayName": "Test",
        "backgroundColor": "not-a-hex-color",
        "buttonColor": "#1E293B",
        "textColor": "#FFFFFF",
        "isPublished": True,
        "socialLinks": [],
    }
    res = client.put("/api/bio", json=payload, cookies=cookies)
    assert res.status_code == 422


def test_update_bio_profile_validation_invalid_avatar_url():
    """Unsafe or non-HTTP/HTTPS avatar URLs return 422."""
    cookies, _, _ = create_user_and_session("BadAvatarBio")

    payload = {
        "displayName": "Test",
        "avatarUrl": "javascript:alert('XSS')",
        "backgroundColor": "#0F172A",
        "buttonColor": "#1E293B",
        "textColor": "#FFFFFF",
        "isPublished": True,
        "socialLinks": [],
    }
    res = client.put("/api/bio", json=payload, cookies=cookies)
    assert res.status_code == 422


# =====================================================================
# Bio Links CRUD & Reorder Tests
# =====================================================================

def test_create_and_list_bio_links():
    """Add multiple links and retrieve them ordered by position."""
    cookies, _, _ = create_user_and_session("LinkCrud")
    # Initialize profile
    client.get("/api/bio", cookies=cookies)

    # 1. Create first link
    res1 = client.post(
        "/api/bio/links",
        json={"title": "My Portfolio", "url": "https://alexrivera.dev"},
        cookies=cookies,
    )
    assert res1.status_code == 201
    link1 = res1.json()
    assert link1["title"] == "My Portfolio"
    assert link1["position"] == 0

    # 2. Create second link
    res2 = client.post(
        "/api/bio/links",
        json={"title": "My Blog", "url": "https://alexrivera.dev/blog"},
        cookies=cookies,
    )
    assert res2.status_code == 201
    link2 = res2.json()
    assert link2["title"] == "My Blog"
    assert link2["position"] == 1

    # 3. List links
    list_res = client.get("/api/bio/links", cookies=cookies)
    assert list_res.status_code == 200
    items = list_res.json()
    assert len(items) == 2
    assert items[0]["id"] == link1["id"]
    assert items[1]["id"] == link2["id"]


def test_update_bio_link():
    """Update title, URL, and visibility of an existing link."""
    cookies, _, _ = create_user_and_session("LinkUpdate")
    client.get("/api/bio", cookies=cookies)

    create_res = client.post(
        "/api/bio/links",
        json={"title": "Initial Title", "url": "https://example.com/initial"},
        cookies=cookies,
    )
    link_id = create_res.json()["id"]

    update_res = client.put(
        f"/api/bio/links/{link_id}",
        json={"title": "Updated Title", "isVisible": False},
        cookies=cookies,
    )
    assert update_res.status_code == 200
    updated = update_res.json()
    assert updated["title"] == "Updated Title"
    assert updated["isVisible"] is False
    assert updated["url"] == "https://example.com/initial"


def test_delete_bio_link():
    """Delete an existing bio link."""
    cookies, _, _ = create_user_and_session("LinkDelete")
    client.get("/api/bio", cookies=cookies)

    create_res = client.post(
        "/api/bio/links",
        json={"title": "To Delete", "url": "https://example.com/delete"},
        cookies=cookies,
    )
    link_id = create_res.json()["id"]

    del_res = client.delete(f"/api/bio/links/{link_id}", cookies=cookies)
    assert del_res.status_code == 200
    assert del_res.json()["message"] == "Bio link deleted successfully"

    # Verify link is gone
    list_res = client.get("/api/bio/links", cookies=cookies)
    assert all(l["id"] != link_id for l in list_res.json())


def test_reorder_bio_links():
    """Reorder bio links and verify persisted sequential positions."""
    cookies, _, _ = create_user_and_session("LinkReorder")
    client.get("/api/bio", cookies=cookies)

    l1 = client.post("/api/bio/links", json={"title": "Link 1", "url": "https://example.com/1"}, cookies=cookies).json()
    l2 = client.post("/api/bio/links", json={"title": "Link 2", "url": "https://example.com/2"}, cookies=cookies).json()
    l3 = client.post("/api/bio/links", json={"title": "Link 3", "url": "https://example.com/3"}, cookies=cookies).json()

    # Reorder as L3 -> L1 -> L2
    new_order = [l3["id"], l1["id"], l2["id"]]
    reorder_res = client.patch(
        "/api/bio/links/reorder",
        json={"linkIds": new_order},
        cookies=cookies,
    )
    assert reorder_res.status_code == 200
    reordered = reorder_res.json()

    assert reordered[0]["id"] == l3["id"]
    assert reordered[0]["position"] == 0
    assert reordered[1]["id"] == l1["id"]
    assert reordered[1]["position"] == 1
    assert reordered[2]["id"] == l2["id"]
    assert reordered[2]["position"] == 2


def test_reorder_foreign_link_rejected():
    """Attempting to reorder with another user's link ID is rejected."""
    cookies_a, _, _ = create_user_and_session("UserA")
    cookies_b, _, _ = create_user_and_session("UserB")
    client.get("/api/bio", cookies=cookies_a)
    client.get("/api/bio", cookies=cookies_b)

    link_a = client.post("/api/bio/links", json={"title": "A", "url": "https://a.com"}, cookies=cookies_a).json()
    link_b = client.post("/api/bio/links", json={"title": "B", "url": "https://b.com"}, cookies=cookies_b).json()

    # User A tries to reorder including Link B
    res = client.patch(
        "/api/bio/links/reorder",
        json={"linkIds": [link_a["id"], link_b["id"]]},
        cookies=cookies_a,
    )
    assert res.status_code == 400
    assert "do not belong" in res.json()["detail"].lower()


def test_ownership_isolation_link_modification():
    """User B cannot update or delete User A's links."""
    cookies_a, _, _ = create_user_and_session("OwnerUser")
    cookies_b, _, _ = create_user_and_session("AttackerUser")
    client.get("/api/bio", cookies=cookies_a)

    link_a = client.post("/api/bio/links", json={"title": "Private", "url": "https://a.com"}, cookies=cookies_a).json()

    # Attacker tries to update
    put_res = client.put(f"/api/bio/links/{link_a['id']}", json={"title": "Hacked"}, cookies=cookies_b)
    assert put_res.status_code == 404

    # Attacker tries to delete
    del_res = client.delete(f"/api/bio/links/{link_a['id']}", cookies=cookies_b)
    assert del_res.status_code == 404


# =====================================================================
# Public Bio Profile Tests (Unauthenticated)
# =====================================================================

def test_public_bio_published_profile():
    """
    Public visitor can access a published profile without authentication.
    Verifies public data hygiene: no userId, email, or passwordHash.
    """
    cookies, _, username = create_user_and_session("PublicHero")

    # Set up profile
    client.put(
        "/api/bio",
        json={
            "displayName": "Hero Developer",
            "bio": "Building the future.",
            "avatarUrl": "https://example.com/hero.png",
            "backgroundColor": "#0F172A",
            "buttonColor": "#1E293B",
            "textColor": "#FFFFFF",
            "isPublished": True,
            "socialLinks": [{"platform": "github", "url": "https://github.com/hero"}],
        },
        cookies=cookies,
    )

    # Add visible link
    client.post(
        "/api/bio/links",
        json={"title": "My Project", "url": "https://hero.dev/project", "isVisible": True},
        cookies=cookies,
    )

    # Public request (no cookies)
    fresh_client = TestClient(app)
    res = fresh_client.get(f"/api/bio/public/{username}")
    assert res.status_code == 200
    data = res.json()

    assert data["username"] == username
    assert data["displayName"] == "Hero Developer"
    assert data["bio"] == "Building the future."
    assert data["avatarUrl"] == "https://example.com/hero.png"
    assert len(data["links"]) == 1
    assert data["links"][0]["title"] == "My Project"

    # Strict privacy assertions: NO private fields exposed
    assert "userId" not in data
    assert "email" not in data
    assert "password" not in data
    assert "passwordHash" not in data


def test_public_bio_hides_invisible_links():
    """Hidden links (isVisible=False) must never be returned on the public page."""
    cookies, _, username = create_user_and_session("HiddenTester")
    client.get("/api/bio", cookies=cookies)

    client.post(
        "/api/bio/links",
        json={"title": "Visible Link", "url": "https://example.com/vis", "isVisible": True},
        cookies=cookies,
    )
    client.post(
        "/api/bio/links",
        json={"title": "Secret Draft", "url": "https://example.com/draft", "isVisible": False},
        cookies=cookies,
    )

    fresh_client = TestClient(app)
    res = fresh_client.get(f"/api/bio/public/{username}")
    assert res.status_code == 200
    links = res.json()["links"]

    assert len(links) == 1
    assert links[0]["title"] == "Visible Link"


def test_public_bio_unpublished_returns_404():
    """
    When isPublished=False, public endpoint returns 404
    to protect draft/unpublished profiles from leaking existence.
    """
    cookies, _, username = create_user_and_session("UnpublishedUser")

    client.put(
        "/api/bio",
        json={
            "displayName": "Draft User",
            "backgroundColor": "#0F172A",
            "buttonColor": "#1E293B",
            "textColor": "#FFFFFF",
            "isPublished": False,  # Unpublished
            "socialLinks": [],
        },
        cookies=cookies,
    )

    fresh_client = TestClient(app)
    res = fresh_client.get(f"/api/bio/public/{username}")
    assert res.status_code == 404
    assert res.json()["detail"] == "Bio profile not found"


def test_public_bio_nonexistent_username_returns_404():
    """Querying a nonexistent username returns 404."""
    fresh_client = TestClient(app)
    res = fresh_client.get("/api/bio/public/nonexistent_user_999999")
    assert res.status_code == 404
    assert res.json()["detail"] == "Bio profile not found"
