"""
Tests for Phase 5: Analytics Engine and Link Analytics API.

Verifies:
- Authenticated access only (401 for unauthenticated)
- Strict user ownership enforcement (404 for other users' links or nonexistent links)
- Correct total click and period click counts
- Clicks over time aggregation with zero-filling for quiet days
- Top referrers aggregation with descending sort and 'Direct' support
- Device distribution breakdown (Mobile, Desktop, Tablet)
- Date range filtering (7d, 30d, 90d, all)
- Multiple links isolation (Link B clicks do not bleed into Link A)
- Empty link handling (returns zero counts gracefully)
"""

from datetime import datetime, timedelta, timezone
import uuid
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.database import get_database

client = TestClient(app)


def create_user_and_session(prefix="AnalyticsUser"):
    """Helper to create a fresh user and return session cookies and user ID."""
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


def create_link_for_user(cookies, destination="https://example.com/target", title="Test Link"):
    """Helper to create a link for an authenticated user."""
    res = client.post(
        "/api/links",
        json={"destinationUrl": destination, "title": title},
        cookies=cookies,
    )
    assert res.status_code == 201
    return res.json()


def populate_click_events(link_id: str, events: list[dict]):
    """Insert raw click event documents for testing analytics aggregations."""
    db = get_database()
    docs = []
    for ev in events:
        docs.append({
            "linkId": str(link_id),
            "timestamp": ev["timestamp"],
            "referrer": ev.get("referrer", "Direct"),
            "deviceType": ev.get("deviceType", "Desktop"),
            "ipHash": ev.get("ipHash", "dummyhash1234567890"),
        })
    if docs:
        db.click_events.insert_many(docs)


# =====================================================================
# Ownership & Authorization Tests
# =====================================================================

def test_analytics_ownership_isolation():
    """
    User B must receive 404 when querying User A's link analytics.
    Prevents unauthorized access and resource enumeration.
    """
    cookies_owner, _ = create_user_and_session("Owner")
    cookies_stranger, _ = create_user_and_session("Stranger")

    link = create_link_for_user(cookies_owner, "https://owner.com/page")
    link_id = link["id"]

    # Stranger attempts to view analytics
    res = client.get(f"/api/links/{link_id}/analytics", cookies=cookies_stranger)
    assert res.status_code == 404
    assert res.json()["detail"] == "Link not found"


def test_analytics_nonexistent_link():
    """Querying a nonexistent link returns 404."""
    cookies, _ = create_user_and_session("Tester")
    res = client.get("/api/links/507f1f77bcf86cd799439011/analytics", cookies=cookies)
    assert res.status_code == 404
    assert res.json()["detail"] == "Link not found"


def test_analytics_unauthenticated():
    """Unauthenticated requests must return 401."""
    fresh_client = TestClient(app)
    res = fresh_client.get("/api/links/507f1f77bcf86cd799439011/analytics")
    assert res.status_code == 401


# =====================================================================
# Empty Link Analytics
# =====================================================================

def test_analytics_empty_link():
    """
    A link with zero clicks must return a clean, valid response
    with totalClicks=0, zero-filled daily records, and 0-count devices.
    """
    cookies, _ = create_user_and_session("EmptyTester")
    link = create_link_for_user(cookies, "https://empty.com")
    link_id = link["id"]

    res = client.get(f"/api/links/{link_id}/analytics?range=7d", cookies=cookies)
    assert res.status_code == 200
    data = res.json()

    assert data["linkId"] == link_id
    assert data["overview"]["totalClicks"] == 0
    assert data["overview"]["periodClicks"] == 0
    assert len(data["clicksOverTime"]) == 7
    assert all(item["clicks"] == 0 for item in data["clicksOverTime"])
    assert data["topReferrers"] == []
    assert len(data["devices"]) == 3
    assert all(d["clicks"] == 0 for d in data["devices"])


# =====================================================================
# Aggregation & Time-Series Tests
# =====================================================================

def test_analytics_clicks_over_time_grouping_and_zerofill():
    """
    Validates that clicks are correctly grouped by UTC calendar day,
    and missing days in the period are zero-filled.
    """
    cookies, _ = create_user_and_session("TimeSeriesTester")
    link = create_link_for_user(cookies, "https://example.com/timeseries")
    link_id = link["id"]

    now = datetime.now(timezone.utc)
    today = now
    two_days_ago = now - timedelta(days=2)
    four_days_ago = now - timedelta(days=4)

    events = [
        # Today: 3 clicks
        {"timestamp": today, "referrer": "google.com", "deviceType": "Mobile"},
        {"timestamp": today, "referrer": "Direct", "deviceType": "Desktop"},
        {"timestamp": today, "referrer": "twitter.com", "deviceType": "Mobile"},
        # 2 days ago: 2 clicks
        {"timestamp": two_days_ago, "referrer": "google.com", "deviceType": "Desktop"},
        {"timestamp": two_days_ago, "referrer": "google.com", "deviceType": "Tablet"},
        # 4 days ago: 1 click
        {"timestamp": four_days_ago, "referrer": "linkedin.com", "deviceType": "Mobile"},
    ]
    populate_click_events(link_id, events)

    res = client.get(f"/api/links/{link_id}/analytics?range=7d", cookies=cookies)
    assert res.status_code == 200
    data = res.json()

    assert data["overview"]["totalClicks"] == 6
    assert data["overview"]["periodClicks"] == 6

    # 7-day range must contain exactly 7 consecutive days
    cot = data["clicksOverTime"]
    assert len(cot) == 7

    cot_dict = {item["date"]: item["clicks"] for item in cot}
    today_str = today.strftime("%Y-%m-%d")
    two_days_ago_str = two_days_ago.strftime("%Y-%m-%d")
    four_days_ago_str = four_days_ago.strftime("%Y-%m-%d")
    yesterday_str = (today - timedelta(days=1)).strftime("%Y-%m-%d")

    assert cot_dict[today_str] == 3
    assert cot_dict[two_days_ago_str] == 2
    assert cot_dict[four_days_ago_str] == 1
    # Yesterday had 0 clicks -> must be zero-filled
    assert cot_dict[yesterday_str] == 0


def test_analytics_top_referrers_ordering():
    """
    Top referrers must be sorted descending by click count,
    properly calculate percentage, and preserve 'Direct'.
    """
    cookies, _ = create_user_and_session("ReferrerTester")
    link = create_link_for_user(cookies, "https://example.com/ref")
    link_id = link["id"]

    now = datetime.now(timezone.utc)
    events = (
        [{"timestamp": now, "referrer": "google.com", "deviceType": "Desktop"}] * 5
        + [{"timestamp": now, "referrer": "Direct", "deviceType": "Mobile"}] * 3
        + [{"timestamp": now, "referrer": "github.com", "deviceType": "Desktop"}] * 2
    )
    populate_click_events(link_id, events)

    res = client.get(f"/api/links/{link_id}/analytics?range=7d", cookies=cookies)
    assert res.status_code == 200
    data = res.json()

    refs = data["topReferrers"]
    assert len(refs) == 3
    assert refs[0]["referrer"] == "google.com"
    assert refs[0]["clicks"] == 5
    assert refs[0]["percentage"] == 50.0

    assert refs[1]["referrer"] == "Direct"
    assert refs[1]["clicks"] == 3
    assert refs[1]["percentage"] == 30.0

    assert refs[2]["referrer"] == "github.com"
    assert refs[2]["clicks"] == 2
    assert refs[2]["percentage"] == 20.0


def test_analytics_device_distribution():
    """Device distribution must accurately report Mobile, Desktop, and Tablet counts."""
    cookies, _ = create_user_and_session("DeviceTester")
    link = create_link_for_user(cookies, "https://example.com/device")
    link_id = link["id"]

    now = datetime.now(timezone.utc)
    events = (
        [{"timestamp": now, "referrer": "Direct", "deviceType": "Mobile"}] * 6
        + [{"timestamp": now, "referrer": "Direct", "deviceType": "Desktop"}] * 3
        + [{"timestamp": now, "referrer": "Direct", "deviceType": "Tablet"}] * 1
    )
    populate_click_events(link_id, events)

    res = client.get(f"/api/links/{link_id}/analytics?range=7d", cookies=cookies)
    assert res.status_code == 200
    data = res.json()

    dev_map = {d["deviceType"]: d for d in data["devices"]}
    assert dev_map["Mobile"]["clicks"] == 6
    assert dev_map["Mobile"]["percentage"] == 60.0

    assert dev_map["Desktop"]["clicks"] == 3
    assert dev_map["Desktop"]["percentage"] == 30.0

    assert dev_map["Tablet"]["clicks"] == 1
    assert dev_map["Tablet"]["percentage"] == 10.0


def test_analytics_date_range_filtering():
    """
    Range parameter must filter clicks appropriately:
    Clicks older than 7 days must be excluded from 7d period clicks,
    but included in 30d or all time.
    """
    cookies, _ = create_user_and_session("RangeTester")
    link = create_link_for_user(cookies, "https://example.com/range")
    link_id = link["id"]

    now = datetime.now(timezone.utc)
    recent = now - timedelta(days=2)
    fifteen_days_ago = now - timedelta(days=15)
    forty_days_ago = now - timedelta(days=40)

    events = [
        {"timestamp": recent, "referrer": "Direct", "deviceType": "Desktop"},
        {"timestamp": fifteen_days_ago, "referrer": "Direct", "deviceType": "Desktop"},
        {"timestamp": forty_days_ago, "referrer": "Direct", "deviceType": "Desktop"},
    ]
    populate_click_events(link_id, events)

    # 7-day range: only 1 click in period
    res_7d = client.get(f"/api/links/{link_id}/analytics?range=7d", cookies=cookies).json()
    assert res_7d["overview"]["periodClicks"] == 1
    assert res_7d["overview"]["totalClicks"] == 3
    assert len(res_7d["clicksOverTime"]) == 7

    # 30-day range: 2 clicks in period
    res_30d = client.get(f"/api/links/{link_id}/analytics?range=30d", cookies=cookies).json()
    assert res_30d["overview"]["periodClicks"] == 2
    assert res_30d["overview"]["totalClicks"] == 3
    assert len(res_30d["clicksOverTime"]) == 30

    # 90-day range: all 3 clicks in period
    res_90d = client.get(f"/api/links/{link_id}/analytics?range=90d", cookies=cookies).json()
    assert res_90d["overview"]["periodClicks"] == 3
    assert res_90d["overview"]["totalClicks"] == 3
    assert len(res_90d["clicksOverTime"]) == 90

    # All time: all 3 clicks
    res_all = client.get(f"/api/links/{link_id}/analytics?range=all", cookies=cookies).json()
    assert res_all["overview"]["periodClicks"] == 3
    assert res_all["overview"]["totalClicks"] == 3


def test_analytics_multi_link_isolation():
    """Clicks belonging to Link B must never appear in Link A's analytics."""
    cookies, _ = create_user_and_session("IsolationTester")
    link_a = create_link_for_user(cookies, "https://example.com/a", title="Link A")
    link_b = create_link_for_user(cookies, "https://example.com/b", title="Link B")

    now = datetime.now(timezone.utc)
    populate_click_events(link_a["id"], [
        {"timestamp": now, "referrer": "twitter.com", "deviceType": "Mobile"},
    ])
    populate_click_events(link_b["id"], [
        {"timestamp": now, "referrer": "reddit.com", "deviceType": "Desktop"},
        {"timestamp": now, "referrer": "reddit.com", "deviceType": "Desktop"},
    ])

    res_a = client.get(f"/api/links/{link_a['id']}/analytics", cookies=cookies).json()
    assert res_a["overview"]["totalClicks"] == 1
    assert res_a["topReferrers"][0]["referrer"] == "twitter.com"

    res_b = client.get(f"/api/links/{link_b['id']}/analytics", cookies=cookies).json()
    assert res_b["overview"]["totalClicks"] == 2
    assert res_b["topReferrers"][0]["referrer"] == "reddit.com"
