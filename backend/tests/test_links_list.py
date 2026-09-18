"""
Tests for link listing endpoint (GET /api/links).

Verifies:
- Authenticated user can list their links
- Server-side pagination correctly calculates items, page, pageSize, total, totalPages
- Search parameter filters links by destinationUrl and shortCode
- User isolation: A user can ONLY view their own links, not another user's links
- Unauthenticated requests return 401
"""

import uuid
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def create_user_and_session(prefix="User"):
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


def test_list_links_pagination():
    """Verify server-side pagination metadata and limits."""
    cookies, _ = create_user_and_session("Paginator")

    # Create 5 links
    for i in range(5):
        client.post(
            "/api/links",
            json={"destinationUrl": f"https://example.com/item-{i}", "title": f"Item {i}"},
            cookies=cookies,
        )

    # Fetch page 1 with page_size=2
    res = client.get("/api/links?page=1&page_size=2", cookies=cookies)
    assert res.status_code == 200
    data = res.json()

    assert data["page"] == 1
    assert data["pageSize"] == 2
    assert data["total"] == 5
    assert data["totalPages"] == 3
    assert len(data["items"]) == 2

    # Fetch page 3 with page_size=2 (should have 1 item)
    res_p3 = client.get("/api/links?page=3&page_size=2", cookies=cookies)
    assert res_p3.status_code == 200
    data_p3 = res_p3.json()
    assert len(data_p3["items"]) == 1


def test_list_links_search_filtering():
    """Verify search filter across destinationUrl and shortCode."""
    cookies, _ = create_user_and_session("Searcher")

    client.post("/api/links", json={"destinationUrl": "https://alpha.org/docs"}, cookies=cookies)
    client.post("/api/links", json={"destinationUrl": "https://beta.com/shop"}, cookies=cookies)
    client.post("/api/links", json={"destinationUrl": "https://gamma.net/contact", "customSlug": "find-gamma"}, cookies=cookies)

    # Search for "alpha"
    res1 = client.get("/api/links?search=alpha", cookies=cookies)
    assert res1.status_code == 200
    assert res1.json()["total"] == 1
    assert "alpha.org" in res1.json()["items"][0]["destinationUrl"]

    # Search for custom slug "find-gamma"
    res2 = client.get("/api/links?search=find-gamma", cookies=cookies)
    assert res2.status_code == 200
    assert res2.json()["total"] == 1
    assert res2.json()["items"][0]["shortCode"] == "find-gamma"

    # Search for something that doesn't match
    res3 = client.get("/api/links?search=nonexistentterm123", cookies=cookies)
    assert res3.status_code == 200
    assert res3.json()["total"] == 0
    assert len(res3.json()["items"]) == 0


def test_list_links_user_isolation():
    """User A should never see User B's links."""
    cookies_a, _ = create_user_and_session("UserA")
    cookies_b, _ = create_user_and_session("UserB")

    # User A creates 2 links
    client.post("/api/links", json={"destinationUrl": "https://usera-only.com/1"}, cookies=cookies_a)
    client.post("/api/links", json={"destinationUrl": "https://usera-only.com/2"}, cookies=cookies_a)

    # User B creates 1 link
    client.post("/api/links", json={"destinationUrl": "https://userb-only.com/1"}, cookies=cookies_b)

    # User A lists links
    res_a = client.get("/api/links", cookies=cookies_a)
    assert res_a.status_code == 200
    assert res_a.json()["total"] == 2
    for item in res_a.json()["items"]:
        assert "usera-only.com" in item["destinationUrl"]
        assert "userb-only.com" not in item["destinationUrl"]

    # User B lists links
    res_b = client.get("/api/links", cookies=cookies_b)
    assert res_b.status_code == 200
    assert res_b.json()["total"] == 1
    assert "userb-only.com" in res_b.json()["items"][0]["destinationUrl"]


def test_list_links_unauthenticated():
    """Unauthenticated requests must return 401."""
    fresh_client = TestClient(app)
    res = fresh_client.get("/api/links")
    assert res.status_code == 401
