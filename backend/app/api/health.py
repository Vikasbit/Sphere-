"""
Health check API endpoint.

Provides a simple endpoint to verify the API and database are operational.
"""

from fastapi import APIRouter, status
from pydantic import BaseModel

from app.core.database import get_database

router = APIRouter(prefix="/api", tags=["health"])


class HealthResponse(BaseModel):
    status: str
    database: str


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Health check",
    description="Returns the health status of the API and database connection.",
)
def health_check() -> HealthResponse:
    """Check API and database health."""
    try:
        db = get_database()
        # PyMongo ping to verify the connection is alive
        db.client.admin.command("ping")
        db_status = "connected"
    except Exception:
        db_status = "disconnected"

    return HealthResponse(
        status="healthy" if db_status == "connected" else "degraded",
        database=db_status,
    )
