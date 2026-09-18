"""
Tests for Phase 4: Public 302 Redirect Engine and Click Telemetry.

Validates:
- Fast indexed short-code resolution
- Strict HTTP 302 Found response with Location header
- Atomic click count increment ($inc)
- Privacy-safe telemetry recording (no raw IP storage, hashed IP with pepper)
- User-Agent device classification (Mobile, Tablet, Desktop)
- Referrer normalization (Direct fallback, length cap)
- Telemetry error resilience (telemetry failures never fail 302 redirect)
- Unit tests for ip_hashing, device_detection, and normalize_referrer
"""

from datetime import datetime, timezone
import hashlib
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.database import get_database
from app.core.config import get_settings
from app.utils.device_detection import detect_device_type
from app.utils.ip_hashing import extract_client_ip, hash_client_ip
from app.services.telemetry_service import normalize_referrer, TelemetryService


@pytest.fixture
def client():
    """Create a TestClient with base URL."""
    return TestClient(app)


@pytest.fixture
def test_link():
    """Insert a test short link into MongoDB and clean up afterwards."""
    db = get_database()
    link_doc = {
        "userId": "usr_test_12345",
        "destinationUrl": "https://example.com/target-page",
        "shortCode": "rdtest",
        "clickCount": 0,
        "title": "Test Redirect Destination",
        "createdAt": datetime.now(timezone.utc),
        "updatedAt": datetime.now(timezone.utc),
    }
    result = db.links.insert_one(link_doc)
    link_id = result.inserted_id
    link_doc["_id"] = link_id

    yield link_doc

    # Cleanup
    db.links.delete_one({"_id": link_id})
    db.click_events.delete_many({"linkId": str(link_id)})


# =====================================================================
# Public 302 Redirect Endpoint Tests
# =====================================================================

def test_redirect_success_302(client, test_link):
    """
    GET /r/{short_code} must return strict HTTP 302 Found
    with the exact destination URL in the Location header.
    """
    response = client.get("/r/rdtest", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["location"] == "https://example.com/target-page"

    # Verify link clickCount incremented in database
    db = get_database()
    updated_link = db.links.find_one({"_id": test_link["_id"]})
    assert updated_link is not None
    assert updated_link["clickCount"] == 1

    # Verify click event was recorded
    event = db.click_events.find_one({"linkId": str(test_link["_id"])})
    assert event is not None
    assert event["linkId"] == str(test_link["_id"])
    assert "timestamp" in event
    assert "ipHash" in event
    assert event["deviceType"] in ("Mobile", "Tablet", "Desktop")


def test_redirect_not_found(client):
    """GET /r/{short_code} returns 404 when short code does not exist."""
    response = client.get("/r/nonexistent999", follow_redirects=False)
    assert response.status_code == 404
    assert response.json()["detail"] == "Short link not found"


def test_redirect_blank_code(client):
    """GET /r/{short_code} with whitespace code returns 404."""
    response = client.get("/r/%20", follow_redirects=False)
    assert response.status_code == 404


def test_redirect_atomic_click_accumulation(client, test_link):
    """Consecutive redirects must increment click count correctly and record each event."""
    db = get_database()

    for i in range(1, 4):
        resp = client.get("/r/rdtest", follow_redirects=False)
        assert resp.status_code == 302

    updated = db.links.find_one({"_id": test_link["_id"]})
    assert updated["clickCount"] == 3

    events_count = db.click_events.count_documents({"linkId": str(test_link["_id"])})
    assert events_count == 3


def test_redirect_privacy_no_raw_ip_stored(client, test_link):
    """
    Raw IP addresses must NEVER be stored in the database.
    Only the salted SHA-256 hash must be recorded.
    """
    raw_ip = "198.51.100.42"
    response = client.get(
        "/r/rdtest",
        headers={"X-Forwarded-For": raw_ip},
        follow_redirects=False,
    )
    assert response.status_code == 302

    db = get_database()
    event = db.click_events.find_one({"linkId": str(test_link["_id"])})
    assert event is not None

    # Strict privacy verification: raw IP must not be present in any form
    assert "ip" not in event
    assert "client_ip" not in event
    assert raw_ip not in str(event)

    # ipHash must be a valid 64-character SHA-256 hex string
    expected_hash = hash_client_ip(raw_ip)
    assert event["ipHash"] == expected_hash
    assert len(event["ipHash"]) == 64


def test_redirect_device_detection_mobile(client, test_link):
    """User-Agent with iPhone identifier must be detected as Mobile."""
    iphone_ua = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148"
    response = client.get(
        "/r/rdtest",
        headers={"User-Agent": iphone_ua},
        follow_redirects=False,
    )
    assert response.status_code == 302

    db = get_database()
    event = db.click_events.find_one({"linkId": str(test_link["_id"])})
    assert event is not None
    assert event["deviceType"] == "Mobile"


def test_redirect_device_detection_tablet(client, test_link):
    """User-Agent with iPad identifier must be detected as Tablet."""
    ipad_ua = "Mozilla/5.0 (iPad; CPU OS 16_5 like Mac OS X) AppleWebKit/605.1.15 Version/16.5 Mobile/15E148 Safari/604.1"
    response = client.get(
        "/r/rdtest",
        headers={"User-Agent": ipad_ua},
        follow_redirects=False,
    )
    assert response.status_code == 302

    db = get_database()
    event = db.click_events.find_one({"linkId": str(test_link["_id"])})
    assert event is not None
    assert event["deviceType"] == "Tablet"


def test_redirect_device_detection_desktop(client, test_link):
    """User-Agent for desktop browser must be detected as Desktop."""
    desktop_ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    response = client.get(
        "/r/rdtest",
        headers={"User-Agent": desktop_ua},
        follow_redirects=False,
    )
    assert response.status_code == 302

    db = get_database()
    event = db.click_events.find_one({"linkId": str(test_link["_id"])})
    assert event is not None
    assert event["deviceType"] == "Desktop"


def test_redirect_referrer_captured(client, test_link):
    """Referer header must be captured and normalized."""
    referrer = "https://news.ycombinator.com/item?id=12345"
    response = client.get(
        "/r/rdtest",
        headers={"Referer": referrer},
        follow_redirects=False,
    )
    assert response.status_code == 302

    db = get_database()
    event = db.click_events.find_one({"linkId": str(test_link["_id"])})
    assert event is not None
    assert event["referrer"] == referrer


def test_redirect_referrer_default_direct(client, test_link):
    """When Referer header is missing, referrer must default to 'Direct'."""
    response = client.get("/r/rdtest", follow_redirects=False)
    assert response.status_code == 302

    db = get_database()
    event = db.click_events.find_one({"linkId": str(test_link["_id"])})
    assert event is not None
    assert event["referrer"] == "Direct"


def test_redirect_telemetry_failure_resilience(client, test_link):
    """
    Database or telemetry failure in the background task must NOT crash or prevent
    the 302 redirect from succeeding.
    """
    db = get_database()
    with patch.object(db.click_events, "insert_one", side_effect=Exception("Database down")):
        response = client.get("/r/rdtest", follow_redirects=False)
        # Redirect still succeeds with 302
        assert response.status_code == 302
        assert response.headers["location"] == "https://example.com/target-page"


def test_redirect_is_public_no_auth(client, test_link):
    """
    Redirect endpoint must be public: no Authorization header, no session cookies required.
    """
    # Clear any cookies
    client.cookies.clear()
    response = client.get("/r/rdtest", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["location"] == "https://example.com/target-page"


# =====================================================================
# Unit Tests for Device Detection Utility
# =====================================================================

def test_unit_detect_device_type():
    # Mobile devices
    assert detect_device_type("Mozilla/5.0 (iPhone; CPU iPhone OS 16_0)") == "Mobile"
    assert detect_device_type("Mozilla/5.0 (Linux; Android 13; SM-S908B) Mobile") == "Mobile"
    assert detect_device_type("Mozilla/5.0 (BlackBerry; U; BlackBerry 9800)") == "Mobile"

    # Tablets
    assert detect_device_type("Mozilla/5.0 (iPad; CPU OS 15_0)") == "Tablet"
    assert detect_device_type("Mozilla/5.0 (Linux; Android 12; SM-X800) AppleWebKit/537.36") == "Tablet"
    assert detect_device_type("Mozilla/5.0 (Silk/3.48 like Chrome) Kindle") == "Tablet"

    # Desktops
    assert detect_device_type("Mozilla/5.0 (Windows NT 10.0; Win64; x64)") == "Desktop"
    assert detect_device_type("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)") == "Desktop"
    assert detect_device_type("Mozilla/5.0 (X11; Linux x86_64)") == "Desktop"

    # Missing / None
    assert detect_device_type(None) == "Desktop"
    assert detect_device_type("") == "Desktop"
    assert detect_device_type("CustomBot/1.0") == "Desktop"


# =====================================================================
# Unit Tests for IP Hashing Utility
# =====================================================================

def test_unit_hash_client_ip():
    settings = get_settings()

    # Same IP produces same hash
    h1 = hash_client_ip("192.168.1.100")
    h2 = hash_client_ip("192.168.1.100")
    assert h1 == h2
    assert len(h1) == 64

    # Different IP produces different hash
    h3 = hash_client_ip("192.168.1.101")
    assert h1 != h3

    # Salt is incorporated
    expected = hashlib.sha256(f"192.168.1.100:{settings.ip_hash_salt}".encode("utf-8")).hexdigest()
    assert h1 == expected

    # Unknown / empty handling
    h_unknown = hash_client_ip(None)
    assert len(h_unknown) == 64


# =====================================================================
# Unit Tests for Referrer Normalization
# =====================================================================

def test_unit_normalize_referrer():
    assert normalize_referrer(None) == "Direct"
    assert normalize_referrer("") == "Direct"
    assert normalize_referrer("   ") == "Direct"

    url = "https://example.com/path?param=1"
    assert normalize_referrer(url) == url

    # Length capping at 500
    long_ref = "https://example.com/" + "a" * 600
    normalized = normalize_referrer(long_ref)
    assert len(normalized) == 500
    assert normalized.startswith("https://example.com/a")
