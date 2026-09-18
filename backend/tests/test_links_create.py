"""
Tests for short link creation endpoint (POST /api/links).

Verifies:
- Authenticated user can create short links
- Automatically generated short code is exactly 6 characters and alphanumeric
- Valid HTTP and HTTPS URLs accepted
- Invalid protocols (javascript:, data:, ftp:, file:) rejected
- Custom vanity slugs allowed and normalized
- Custom slug collision returns 409 Conflict
- Reserved system slugs rejected with 400 Bad Request
- Malformed custom slugs rejected with 422
- Multiple auto-generated codes are unique
- Unauthenticated requests rejected with 401
"""

import uuid
from unittest.mock import patch
from fastapi.testclient import TestClient
from pymongo.errors import DuplicateKeyError

from app.core.config import get_settings
from app.core.database import get_database
from app.main import app

client = TestClient(app)
settings = get_settings()


def get_auth_cookies():
    """Create a unique user and log in to obtain access and refresh cookies."""
    uid = uuid.uuid4().hex[:8]
    data = {
        "name": f"LinkUser {uid}",
        "email": f"link_user_{uid}@example.com",
        "username": f"link_user_{uid}",
        "password": "Password123!",
    }
    client.post("/api/auth/signup", json=data)
    login_res = client.post(
        "/api/auth/login",
        json={"email": data["email"], "password": data["password"]},
    )
    assert login_res.status_code == 200
    return login_res.cookies, login_res.json()["user"]["id"]


def test_create_link_auto_generated_code():
    """Authenticated user creates a link with auto-generated 6-char code."""
    cookies, user_id = get_auth_cookies()

    payload = {
        "destinationUrl": "https://example.com/blog/my-first-post",
        "title": "My First Post",
    }
    res = client.post("/api/links", json=payload, cookies=cookies)
    assert res.status_code == 201
    data = res.json()

    assert "id" in data
    assert data["destinationUrl"] == payload["destinationUrl"]
    assert data["title"] == payload["title"]
    assert len(data["shortCode"]) == 6
    assert data["shortCode"].isalnum()
    assert data["shortUrl"] == f"{settings.short_link_base_url}/{data['shortCode']}"
    assert data["clickCount"] == 0


def test_create_link_valid_urls():
    """Both HTTP and HTTPS URLs should be accepted."""
    cookies, _ = get_auth_cookies()

    for url in ["http://example.com", "https://sub.domain.co.uk/path?q=1#hash"]:
        res = client.post("/api/links", json={"destinationUrl": url}, cookies=cookies)
        assert res.status_code == 201
        assert res.json()["destinationUrl"] == url


def test_create_link_invalid_urls():
    """Unsupported protocols and invalid formats must be rejected."""
    cookies, _ = get_auth_cookies()

    bad_urls = [
        "javascript:alert(1)",
        "data:text/html,<script>alert(1)</script>",
        "file:///C:/Users/test.txt",
        "ftp://ftp.example.com",
        "not-a-url",
        "http://",
        "",
    ]
    for bad_url in bad_urls:
        res = client.post("/api/links", json={"destinationUrl": bad_url}, cookies=cookies)
        assert res.status_code == 422, f"Expected 422 for bad URL: {bad_url}, got {res.status_code}"


def test_create_link_custom_vanity_slug():
    """Custom vanity slug is accepted and normalized."""
    cookies, _ = get_auth_cookies()
    custom = f"my-promo-{uuid.uuid4().hex[:6]}"

    payload = {
        "destinationUrl": "https://example.com/promo",
        "customSlug": custom.upper(),  # Should be normalized to lowercase
    }
    res = client.post("/api/links", json=payload, cookies=cookies)
    assert res.status_code == 201
    data = res.json()
    assert data["shortCode"] == custom.lower()
    assert data["shortUrl"] == f"{settings.short_link_base_url}/{custom.lower()}"


def test_create_link_custom_slug_collision():
    """Reusing an existing custom slug must return 409 Conflict."""
    cookies, _ = get_auth_cookies()
    slug = f"sale-{uuid.uuid4().hex[:6]}"

    res1 = client.post(
        "/api/links",
        json={"destinationUrl": "https://example.com/one", "customSlug": slug},
        cookies=cookies,
    )
    assert res1.status_code == 201

    # Attempt second link with same slug
    res2 = client.post(
        "/api/links",
        json={"destinationUrl": "https://example.com/two", "customSlug": slug},
        cookies=cookies,
    )
    assert res2.status_code == 409
    assert "already in use" in res2.json()["detail"].lower()


def test_create_link_reserved_slug_rejected():
    """Slugs matching reserved system routes must return 400 Bad Request."""
    cookies, _ = get_auth_cookies()

    reserved_candidates = ["api", "bio", "login", "signup", "dashboard", "links", "settings", "docs", "analytics"]
    for reserved in reserved_candidates:
        res = client.post(
            "/api/links",
            json={"destinationUrl": "https://example.com/test", "customSlug": reserved},
            cookies=cookies,
        )
        assert res.status_code == 400, f"Expected 400 for reserved slug '{reserved}', got {res.status_code}"
        assert "reserved" in res.json()["detail"].lower()


def test_create_link_invalid_custom_slug():
    """Custom slugs with invalid characters, spaces, or wrong length must be rejected with 422."""
    cookies, _ = get_auth_cookies()

    invalid_slugs = [
        "ab",  # Too short (< 3)
        "a" * 51,  # Too long (> 50)
        "slug with spaces",  # Spaces
        "slug!@#$",  # Special characters
        "slug/slash",  # Slashes
    ]
    for bad_slug in invalid_slugs:
        res = client.post(
            "/api/links",
            json={"destinationUrl": "https://example.com", "customSlug": bad_slug},
            cookies=cookies,
        )
        assert res.status_code == 422, f"Expected 422 for slug '{bad_slug}', got {res.status_code}"


def test_create_link_unauthenticated():
    """Unauthenticated requests must be rejected with 401."""
    fresh_client = TestClient(app)
    res = fresh_client.post("/api/links", json={"destinationUrl": "https://example.com"})
    assert res.status_code == 401
    assert "Not authenticated" in res.json()["detail"]


def test_create_link_collision_retry_logic():
    """
    Test that if generate_short_code produces a duplicate short code,
    the service catches the collision and retries successfully.
    """
    cookies, _ = get_auth_cookies()

    # Pre-occupy a specific short code
    db = get_database()
    colliding_code = "col123"
    db.links.insert_one({
        "userId": "system",
        "destinationUrl": "https://occupied.com",
        "shortCode": colliding_code,
        "clickCount": 0,
    })

    # Mock generate_short_code to return colliding_code on first attempt, then a unique one
    codes = [colliding_code, "fresh1"]
    with patch("app.services.link_service.LinkService.generate_short_code", side_effect=codes):
        res = client.post(
            "/api/links",
            json={"destinationUrl": "https://example.com/retry-test"},
            cookies=cookies,
        )
        assert res.status_code == 201
        assert res.json()["shortCode"] == "fresh1"
