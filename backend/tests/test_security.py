"""
Security regression tests covering:
1. HTTP Security Headers & Content-Security-Policy
2. CORS origin validation and credentials safety
3. SlowAPI rate limiting (HTTP 429 & Retry-After)
4. JWT token security (signature verification, expiration, type rejection)
5. Refresh token replay detection and session invalidation
6. IDOR & cross-user resource isolation
7. Malicious URL scheme injection prevention (javascript:, data:, file:)
8. Public profile privacy hygiene
"""

import time
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from jose import jwt
import pytest

from app.main import app
from app.core.config import get_settings
from app.core.security import ALGORITHM, hash_password
from app.core.database import get_database

client = TestClient(app)
settings = get_settings()


def create_user_and_session(tag: str = "SecUser"):
    """Helper to create a user and return auth cookies and user info."""
    db = get_database()
    email = f"{tag.lower()}_{int(time.time() * 1000)}@example.com"
    username = f"{tag.lower()}_{int(time.time() * 1000)}"

    # Direct signup & login through API
    client.post(
        "/api/auth/signup",
        json={
            "name": f"{tag} Name",
            "email": email,
            "username": username,
            "password": "Password123!",
        },
    )

    # Force email verification directly in DB
    db.users.update_one({"email": email}, {"$set": {"isEmailVerified": True}})

    login_res = client.post(
        "/api/auth/login",
        json={"email": email, "password": "Password123!"},
    )
    assert login_res.status_code == 200
    cookies = login_res.cookies
    user_id = login_res.json()["user"]["id"]
    return cookies, user_id, username


# =====================================================================
# 1. HTTP Security Headers
# =====================================================================

def test_security_headers_present_on_responses():
    """Verify essential HTTP security headers are set on all responses."""
    res = client.get("/api/health")
    assert res.status_code == 200

    headers = res.headers
    assert headers.get("x-content-type-options") == "nosniff"
    assert headers.get("x-frame-options") == "DENY"
    assert headers.get("referrer-policy") == "strict-origin-when-cross-origin"
    assert headers.get("x-xss-protection") == "1; mode=block"

    csp = headers.get("content-security-policy", "")
    assert "default-src 'self'" in csp
    assert "frame-ancestors 'none'" in csp


# =====================================================================
# 2. CORS Hardening
# =====================================================================

def test_cors_allowed_origin_reflection():
    """Allowed origin receives Access-Control-Allow-Origin with credentials."""
    res = client.get(
        "/api/health",
        headers={"Origin": "http://localhost:5173"},
    )
    assert res.status_code == 200
    assert res.headers.get("access-control-allow-origin") == "http://localhost:5173"
    assert res.headers.get("access-control-allow-credentials") == "true"


def test_cors_disallowed_origin_rejected():
    """Unauthorized origin does not receive Access-Control-Allow-Origin header."""
    res = client.get(
        "/api/health",
        headers={"Origin": "https://malicious-site.com"},
    )
    assert res.status_code == 200
    assert res.headers.get("access-control-allow-origin") is None


# =====================================================================
# 3. SlowAPI Rate Limiting
# =====================================================================

def test_rate_limiting_forgot_password_threshold():
    """
    Exceeding endpoint rate limit (e.g. 5/min on forgot-password) returns HTTP 429.
    Verifies Retry-After header and clean error message.
    """
    fresh_client = TestClient(app)
    endpoint = "/api/auth/forgot-password"
    payload = {"email": "ratelimit_test@example.com"}

    # Consume allowed requests (limit is 5/minute)
    responses = []
    for _ in range(6):
        r = fresh_client.post(endpoint, json=payload)
        responses.append(r)

    # At least the 6th response must be 429 Too Many Requests
    status_codes = [r.status_code for r in responses]
    assert 429 in status_codes

    rate_limited_res = [r for r in responses if r.status_code == 429][0]
    assert "Rate limit exceeded" in rate_limited_res.json().get("detail", "")
    assert "retry-after" in rate_limited_res.headers


# =====================================================================
# 4. JWT Validation & Token Security
# =====================================================================

def test_jwt_wrong_token_type_rejected():
    """Passing a refresh token or token with type!='access' to protected endpoint returns 401."""
    now = datetime.now(timezone.utc)
    # Forge a token with type: 'refresh'
    payload = {
        "sub": "507f1f77bcf86cd799439011",
        "type": "refresh",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=15)).timestamp()),
    }
    forged_token = jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)

    res = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {forged_token}"},
    )
    assert res.status_code == 401
    assert "Invalid or expired token" in res.json().get("detail", "")


def test_jwt_tampered_signature_rejected():
    """Token with an invalid signature is rejected."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": "507f1f77bcf86cd799439011",
        "type": "access",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=15)).timestamp()),
    }
    tampered_token = jwt.encode(payload, "wrong-signature-key-12345678901234567890", algorithm=ALGORITHM)

    res = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {tampered_token}"},
    )
    assert res.status_code == 401


def test_jwt_expired_token_rejected():
    """Expired token is rejected with 401."""
    past = datetime.now(timezone.utc) - timedelta(hours=1)
    payload = {
        "sub": "507f1f77bcf86cd799439011",
        "type": "access",
        "iat": int((past - timedelta(minutes=15)).timestamp()),
        "exp": int(past.timestamp()),
    }
    expired_token = jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)

    res = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert res.status_code == 401


# =====================================================================
# 5. Refresh Token Replay Detection
# =====================================================================

def test_refresh_token_replay_revokes_all_sessions():
    """
    Reusing an old rotated refresh token triggers replay detection
    and revokes all sessions for the user.
    """
    cookies, user_id, _ = create_user_and_session("ReplayUser")
    db = get_database()

    # Verify 1 active session in DB
    assert db.refresh_sessions.count_documents({"userId": user_id}) == 1

    # First rotation (valid)
    res1 = client.post("/api/auth/refresh", cookies=cookies)
    assert res1.status_code == 200
    new_cookies = res1.cookies

    # Attempt replay with original cookies (stale token)
    res_replay = client.post("/api/auth/refresh", cookies=cookies)
    assert res_replay.status_code == 401

    # Replay detection must have purged/revoked ALL active refresh sessions for this user
    assert db.refresh_sessions.count_documents({"userId": user_id, "revokedAt": None}) == 0

    # Even the new cookies are now invalidated
    res_subsequent = client.post("/api/auth/refresh", cookies=new_cookies)
    assert res_subsequent.status_code == 401


# =====================================================================
# 6. IDOR & Cross-User Resource Isolation
# =====================================================================

def test_idor_cross_user_link_access_denied():
    """
    User B cannot read, delete, or fetch analytics for User A's short link.
    Returns 404 to avoid leaking link existence.
    """
    cookies_a, _, _ = create_user_and_session("UserAlpha")
    cookies_b, _, _ = create_user_and_session("UserBeta")

    # User A creates a link
    res_create = client.post(
        "/api/links",
        json={"destinationUrl": "https://alpha.example.com"},
        cookies=cookies_a,
    )
    assert res_create.status_code == 201
    link_id = res_create.json()["id"]

    # User B attempts to access User A's link -> 404
    res_get = client.get(f"/api/links/{link_id}", cookies=cookies_b)
    assert res_get.status_code == 404

    # User B attempts to fetch analytics for User A's link -> 404
    res_analytics = client.get(f"/api/links/{link_id}/analytics", cookies=cookies_b)
    assert res_analytics.status_code == 404

    # User B attempts to delete User A's link -> 404
    res_del = client.delete(f"/api/links/{link_id}", cookies=cookies_b)
    assert res_del.status_code == 404

    # User A can still access their link -> 200
    res_a_check = client.get(f"/api/links/{link_id}", cookies=cookies_a)
    assert res_a_check.status_code == 200


def test_idor_cross_user_bio_link_access_denied():
    """
    User B cannot update, delete, or reorder User A's bio links.
    """
    cookies_a, _, _ = create_user_and_session("BioAlpha")
    cookies_b, _, _ = create_user_and_session("BioBeta")

    # User A adds a bio link
    res_link_a = client.post(
        "/api/bio/links",
        json={"title": "Alpha Project", "url": "https://alpha.dev"},
        cookies=cookies_a,
    )
    assert res_link_a.status_code == 201
    bio_link_id = res_link_a.json()["id"]

    # User B tries to update User A's bio link -> 404
    res_update = client.put(
        f"/api/bio/links/{bio_link_id}",
        json={"title": "Hacked Title", "url": "https://evil.com"},
        cookies=cookies_b,
    )
    assert res_update.status_code == 404

    # User B tries to delete User A's bio link -> 404
    res_delete = client.delete(
        f"/api/bio/links/{bio_link_id}",
        cookies=cookies_b,
    )
    assert res_delete.status_code == 404

    # User B tries to include User A's bio link in reorder batch -> 400
    res_reorder = client.patch(
        "/api/bio/links/reorder",
        json={"linkIds": [bio_link_id]},
        cookies=cookies_b,
    )
    assert res_reorder.status_code == 400


# =====================================================================
# 7. Malicious URL Scheme Prevention
# =====================================================================

def test_malicious_url_schemes_rejected():
    """
    Non-HTTP(S) schemes such as javascript:, data:, file: are strictly rejected.
    """
    cookies, _, _ = create_user_and_session("UrlTester")

    malicious_urls = [
        "javascript:alert(document.cookie)",
        "data:text/html,<script>alert(1)</script>",
        "file:///etc/passwd",
        "vbscript:msgbox(1)",
    ]

    for bad_url in malicious_urls:
        # 1. Short link creation
        res1 = client.post(
            "/api/links",
            json={"destinationUrl": bad_url},
            cookies=cookies,
        )
        assert res1.status_code == 422

        # 2. Bio link creation
        res2 = client.post(
            "/api/bio/links",
            json={"title": "Malicious Link", "url": bad_url},
            cookies=cookies,
        )
        assert res2.status_code == 422

        # 3. Avatar URL update
        res3 = client.put(
            "/api/bio",
            json={"avatarUrl": bad_url},
            cookies=cookies,
        )
        assert res3.status_code == 422


# =====================================================================
# 8. Privacy Hygiene Audit
# =====================================================================

def test_privacy_public_bio_does_not_leak_private_data():
    """
    Public profile response never contains userId, email, passwordHash,
    or invisible links.
    """
    cookies, user_id, username = create_user_and_session("PrivacyHero")

    # Configure profile
    client.put(
        "/api/bio",
        json={
            "displayName": "Privacy Advocate",
            "bio": "Protecting digital rights.",
            "isPublished": True,
            "backgroundColor": "#0F172A",
            "buttonColor": "#1E293B",
            "textColor": "#FFFFFF",
        },
        cookies=cookies,
    )

    # Add 1 visible link and 1 hidden link
    client.post(
        "/api/bio/links",
        json={"title": "Public Project", "url": "https://eff.org", "isVisible": True},
        cookies=cookies,
    )
    client.post(
        "/api/bio/links",
        json={"title": "Secret Project", "url": "https://internal.site", "isVisible": False},
        cookies=cookies,
    )

    # Fetch via unauthenticated public request
    fresh_client = TestClient(app)
    res = fresh_client.get(f"/api/bio/public/{username}")
    assert res.status_code == 200

    data = res.json()
    assert "userId" not in data
    assert "email" not in data
    assert "passwordHash" not in data
    assert "sessions" not in data

    # Verify hidden link was filtered out
    link_titles = [l["title"] for l in data.get("links", [])]
    assert "Public Project" in link_titles
    assert "Secret Project" not in link_titles
