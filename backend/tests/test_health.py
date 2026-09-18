"""
Tests for the health check endpoint.

Uses FastAPI's TestClient (backed by httpx) to test the /api/health route.
Note: These tests require a running MongoDB instance.
"""

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_check_returns_200():
    """Health endpoint should return 200 with status and database fields."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "database" in data


def test_health_check_reports_database_status():
    """Health endpoint should report database as connected when MongoDB is available."""
    response = client.get("/api/health")
    data = response.json()
    # If MongoDB is running, this should be "connected"
    # If not, "disconnected" — but the endpoint should still return 200
    assert data["database"] in ("connected", "disconnected")
    if data["database"] == "connected":
        assert data["status"] == "healthy"
    else:
        assert data["status"] == "degraded"
