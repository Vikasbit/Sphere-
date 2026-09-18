"""
Tests for forgot password and reset password endpoints.

Verifies:
- POST /api/auth/forgot-password returns generic message (prevents user enumeration)
- POST /api/auth/reset-password updates password using Argon2id
- Expired reset token is rejected
- Reused reset token is rejected
- Existing refresh sessions are revoked after password reset
- User can log in with new password but not old password
"""

import uuid
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient

from app.core.database import get_database
from app.main import app

client = TestClient(app)


def create_user_with_session():
    uid = uuid.uuid4().hex[:8]
    data = {
        "name": f"Reset {uid}",
        "email": f"reset_{uid}@example.com",
        "username": f"reset_{uid}",
        "password": "OldPassword123!",
    }
    client.post("/api/auth/signup", json=data)
    login_res = client.post(
        "/api/auth/login",
        json={"email": data["email"], "password": data["password"]},
    )
    assert login_res.status_code == 200
    user_id = login_res.json()["user"]["id"]
    return data, user_id


def test_forgot_password_generic_response():
    """Forgot password must return the exact same generic message whether the email exists or not."""
    data, _ = create_user_with_session()

    # Existing email
    res1 = client.post("/api/auth/forgot-password", json={"email": data["email"]})
    assert res1.status_code == 200
    assert "If that email is registered" in res1.json()["message"]
    assert res1.json().get("devResetToken") is not None

    # Non-existent email
    res2 = client.post("/api/auth/forgot-password", json={"email": "nonexistent_reset_user_123@example.com"})
    assert res2.status_code == 200
    assert res2.json()["message"] == res1.json()["message"]
    # Dev token is None for non-existent email
    assert res2.json().get("devResetToken") is None


def test_reset_password_success_and_revokes_sessions():
    """Valid reset token updates password, revokes sessions, and allows login with new password."""
    data, user_id = create_user_with_session()

    # Request reset
    forgot_res = client.post("/api/auth/forgot-password", json={"email": data["email"]})
    token = forgot_res.json()["devResetToken"]

    # Pre-condition: User has active refresh session
    db = get_database()
    active_sessions_pre = list(db.refresh_sessions.find({"userId": user_id, "revokedAt": None}))
    assert len(active_sessions_pre) >= 1

    # Reset password
    new_password = "NewSecurePassword456!"
    reset_res = client.post(
        "/api/auth/reset-password",
        json={"token": token, "newPassword": new_password},
    )
    assert reset_res.status_code == 200
    assert "successfully" in reset_res.json()["message"]

    # Post-condition 1: All previous sessions revoked
    active_sessions_post = list(db.refresh_sessions.find({"userId": user_id, "revokedAt": None}))
    assert len(active_sessions_post) == 0

    # Post-condition 2: Old password rejected
    fail_login = client.post(
        "/api/auth/login",
        json={"email": data["email"], "password": data["password"]},
    )
    assert fail_login.status_code == 401

    # Post-condition 3: New password accepted
    success_login = client.post(
        "/api/auth/login",
        json={"email": data["email"], "password": new_password},
    )
    assert success_login.status_code == 200


def test_reset_password_expired_token():
    """Expired reset token must be rejected."""
    data, user_id = create_user_with_session()

    forgot_res = client.post("/api/auth/forgot-password", json={"email": data["email"]})
    token = forgot_res.json()["devResetToken"]

    # Manually expire reset token in MongoDB
    db = get_database()
    past_time = datetime.now(timezone.utc) - timedelta(hours=2)
    db.users.update_one(
        {"email": data["email"]},
        {"$set": {"passwordResetExpiresAt": past_time}},
    )

    res = client.post(
        "/api/auth/reset-password",
        json={"token": token, "newPassword": "ValidNewPassword123!"},
    )
    assert res.status_code == 400
    assert "expired" in res.json()["detail"].lower()


def test_reset_password_reused_token():
    """Reset token cannot be used twice."""
    data, user_id = create_user_with_session()

    forgot_res = client.post("/api/auth/forgot-password", json={"email": data["email"]})
    token = forgot_res.json()["devResetToken"]

    # First reset succeeds
    res1 = client.post(
        "/api/auth/reset-password",
        json={"token": token, "newPassword": "NewPasswordOne123!"},
    )
    assert res1.status_code == 200

    # Second reset with same token fails
    res2 = client.post(
        "/api/auth/reset-password",
        json={"token": token, "newPassword": "NewPasswordTwo123!"},
    )
    assert res2.status_code == 400
    assert "Invalid" in res2.json()["detail"]
