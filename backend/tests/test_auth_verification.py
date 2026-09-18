"""
Tests for email verification endpoint (POST /api/auth/verify-email).

Verifies:
- Valid token marks account as verified and invalidates token
- Invalid token returns 400
- Expired token returns 400
- Reused token returns 400
"""

from datetime import datetime, timedelta, timezone
import uuid
from fastapi.testclient import TestClient

from app.core.database import get_database
from app.main import app

client = TestClient(app)


def create_unverified_user():
    uid = uuid.uuid4().hex[:8]
    data = {
        "name": f"Verif {uid}",
        "email": f"verif_{uid}@example.com",
        "username": f"verif_{uid}",
        "password": "Password123!",
    }
    res = client.post("/api/auth/signup", json=data)
    assert res.status_code == 201
    return data, res.json()["devVerificationToken"]


def test_verify_email_success():
    """Valid verification token marks account verified."""
    data, token = create_unverified_user()

    # Verify email
    res = client.post("/api/auth/verify-email", json={"token": token})
    assert res.status_code == 200
    assert "successfully verified" in res.json()["message"]

    # Verify MongoDB state
    db = get_database()
    user = db.users.find_one({"email": data["email"]})
    assert user["isEmailVerified"] is True
    assert "emailVerificationTokenHash" not in user or user["emailVerificationTokenHash"] is None


def test_verify_email_invalid_token():
    """Invalid token returns 400 Bad Request."""
    res = client.post("/api/auth/verify-email", json={"token": "totally-bogus-token-12345"})
    assert res.status_code == 400
    assert "Invalid" in res.json()["detail"]


def test_verify_email_expired_token():
    """Expired token returns 400."""
    data, token = create_unverified_user()

    # Manually expire token in database
    db = get_database()
    past_time = datetime.now(timezone.utc) - timedelta(hours=2)
    db.users.update_one(
        {"email": data["email"]},
        {"$set": {"emailVerificationExpiresAt": past_time}},
    )

    res = client.post("/api/auth/verify-email", json={"token": token})
    assert res.status_code == 400
    assert "expired" in res.json()["detail"].lower()


def test_verify_email_reused_token():
    """Using a verification token twice must fail on the second attempt."""
    data, token = create_unverified_user()

    # First attempt succeeds
    res1 = client.post("/api/auth/verify-email", json={"token": token})
    assert res1.status_code == 200

    # Second attempt must be rejected (single-use)
    res2 = client.post("/api/auth/verify-email", json={"token": token})
    assert res2.status_code == 400
    assert "Invalid" in res2.json()["detail"]
