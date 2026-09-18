"""
Tests for user signup endpoint (POST /api/auth/signup).

Verifies:
- Successful signup returns 201 and safe user profile
- Duplicate email returns 409
- Duplicate username returns 409
- Input validation rejects weak passwords and invalid characters
- Passwords are securely hashed with Argon2id and never stored in plaintext
"""

import uuid
from fastapi.testclient import TestClient

from app.core.database import get_database
from app.main import app

client = TestClient(app)


def get_unique_user():
    uid = uuid.uuid4().hex[:8]
    return {
        "name": f"User {uid}",
        "email": f"user_{uid}@example.com",
        "username": f"user_{uid}",
        "password": "Password123!",
    }


def test_signup_success():
    """Valid signup should create user, return 201 and safe user info without secrets."""
    data = get_unique_user()
    response = client.post("/api/auth/signup", json=data)
    assert response.status_code == 201
    res_data = response.json()

    assert "user" in res_data
    user = res_data["user"]
    assert user["email"] == data["email"]
    assert user["username"] == data["username"]
    assert user["name"] == data["name"]
    assert user["isEmailVerified"] is False
    assert "id" in user

    # Security: Ensure sensitive fields are NEVER in response
    assert "password" not in user
    assert "passwordHash" not in user
    assert "emailVerificationTokenHash" not in user

    # Dev token simulated for local test
    assert "devVerificationToken" in res_data


def test_signup_duplicate_email():
    """Registering with an already used email must return 409 Conflict."""
    data = get_unique_user()
    res1 = client.post("/api/auth/signup", json=data)
    assert res1.status_code == 201

    # Attempt signup with same email, different username
    data2 = get_unique_user()
    data2["email"] = data["email"]
    res2 = client.post("/api/auth/signup", json=data2)
    assert res2.status_code == 409
    assert "Email" in res2.json()["detail"]


def test_signup_duplicate_username():
    """Registering with an already used username must return 409 Conflict."""
    data = get_unique_user()
    res1 = client.post("/api/auth/signup", json=data)
    assert res1.status_code == 201

    # Attempt signup with same username, different email
    data2 = get_unique_user()
    data2["username"] = data["username"]
    res2 = client.post("/api/auth/signup", json=data2)
    assert res2.status_code == 409
    assert "Username" in res2.json()["detail"]


def test_signup_invalid_inputs():
    """Validation errors must reject malformed inputs."""
    data = get_unique_user()

    # Password too short (< 8 chars)
    bad_data = {**data, "password": "short"}
    res = client.post("/api/auth/signup", json=bad_data)
    assert res.status_code == 422

    # Password without digits
    bad_data = {**data, "password": "NoDigitsHere!"}
    res = client.post("/api/auth/signup", json=bad_data)
    assert res.status_code == 422

    # Invalid email format
    bad_data = {**data, "email": "not-an-email"}
    res = client.post("/api/auth/signup", json=bad_data)
    assert res.status_code == 422

    # Invalid username format (spaces or special characters)
    bad_data = {**data, "username": "bad user!"}
    res = client.post("/api/auth/signup", json=bad_data)
    assert res.status_code == 422


def test_password_hashed_with_argon2():
    """Verify stored password in MongoDB is an Argon2id hash and not plaintext."""
    data = get_unique_user()
    res = client.post("/api/auth/signup", json=data)
    assert res.status_code == 201

    db = get_database()
    db_user = db.users.find_one({"email": data["email"]})
    assert db_user is not None
    assert "passwordHash" in db_user
    assert db_user["passwordHash"] != data["password"]
    assert db_user["passwordHash"].startswith("$argon2id$")
