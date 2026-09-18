"""
Short Links API endpoints.

Routes:
- POST /api/links: Create short link (authenticated)
- GET /api/links: List user short links with server-side pagination & search (authenticated)
- GET /api/links/{link_id}: Retrieve single short link (authenticated & ownership protected)
- DELETE /api/links/{link_id}: Delete short link (authenticated & ownership protected)
"""

from typing import Any
from fastapi import APIRouter, Depends, Query, status

from app.dependencies.auth import get_current_user
from app.schemas.auth import MessageResponse
from app.schemas.link import CreateLinkRequest, LinkListResponse, LinkResponse
from app.schemas.analytics import LinkAnalyticsResponse
from app.services.link_service import LinkService
from app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/api/links", tags=["Links"])


@router.post(
    "",
    response_model=LinkResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new short link",
)
def create_link(
    data: CreateLinkRequest,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> LinkResponse:
    """
    Create a shortened link.
    - Generates a unique 6-character short code with insertion collision retry
    - Alternatively accepts an optional custom vanity slug (validated and conflict checked)
    - Validates destination URL (must be absolute HTTP or HTTPS)
    """
    return LinkService.create_link(str(current_user["_id"]), data)


@router.get(
    "",
    response_model=LinkListResponse,
    status_code=status.HTTP_200_OK,
    summary="List user links with pagination",
)
def list_links(
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    search: str | None = Query(default=None, description="Search term across destination URL and short code"),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> LinkListResponse:
    """
    Retrieve paginated list of short links owned by the current authenticated user.
    Supports optional search filtering.
    """
    return LinkService.list_links(
        user_id=str(current_user["_id"]),
        page=page,
        page_size=page_size,
        search=search,
    )


@router.get(
    "/{link_id}",
    response_model=LinkResponse,
    status_code=status.HTTP_200_OK,
    summary="Get single link by ID",
)
def get_link(
    link_id: str,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> LinkResponse:
    """
    Get a single short link by its ID.
    Enforces user ownership; returns 404 if the link is not found or owned by another user.
    """
    return LinkService.get_link(user_id=str(current_user["_id"]), link_id=link_id)


@router.delete(
    "/{link_id}",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete link by ID",
)
def delete_link(
    link_id: str,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> MessageResponse:
    """
    Delete a short link owned by the current authenticated user.
    Enforces user ownership; returns 404 if the link is not found or owned by another user.
    """
    LinkService.delete_link(user_id=str(current_user["_id"]), link_id=link_id)
    return MessageResponse(message="Link deleted successfully")


@router.get(
    "/{link_id}/analytics",
    response_model=LinkAnalyticsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get analytics for a short link",
)
def get_link_analytics(
    link_id: str,
    range: str = Query(default="7d", description="Time period: 7d, 30d, 90d, or all"),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> LinkAnalyticsResponse:
    """
    Retrieve comprehensive analytics for a short link owned by the authenticated user.
    - Clicks over time (grouped by UTC calendar day, zero-filled)
    - Top referrers (sorted descending)
    - Device distribution (Mobile, Desktop, Tablet)
    - Overview KPIs (total clicks all time, period clicks)
    Enforces ownership; returns 404 if not found or unauthorized.
    """
    return AnalyticsService.get_link_analytics(
        user_id=str(current_user["_id"]),
        link_id=link_id,
        range_str=range,
    )

