"""
Bio-Link API endpoints.

Routes:
- GET /api/bio: Retrieve authenticated user's BioProfile (auto-initializes if new)
- PUT /api/bio: Update profile (displayName, bio, avatar, colors, published state, socials)
- GET /api/bio/links: List authenticated user's bio links
- POST /api/bio/links: Add a new bio link
- PUT /api/bio/links/{link_id}: Update an existing bio link
- DELETE /api/bio/links/{link_id}: Delete an existing bio link
- PATCH /api/bio/links/reorder: Reorder bio links sequentially
- GET /api/bio/public/{username}: Public profile endpoint (unauthenticated, strictly filtered)
"""

from typing import Any
from fastapi import APIRouter, Depends, Request, status

from app.core.limiter import limiter
from app.dependencies.auth import get_current_user
from app.schemas.auth import MessageResponse
from app.schemas.bio import (
    BioLinkResponse,
    BioProfileResponse,
    CreateBioLinkRequest,
    PublicBioResponse,
    ReorderBioLinksRequest,
    UpdateBioLinkRequest,
    UpdateBioProfileRequest,
)
from app.services.bio_service import BioService

router = APIRouter(prefix="/api/bio", tags=["Bio"])


# =====================================================================
# Authenticated Profile Management
# =====================================================================

@router.get(
    "",
    response_model=BioProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current user's bio profile",
)
def get_my_bio_profile(
    current_user: dict[str, Any] = Depends(get_current_user),
) -> BioProfileResponse:
    """
    Retrieve authenticated user's Bio profile.
    Automatically initializes a default profile document if not already created.
    """
    return BioService.get_or_create_profile(
        user_id=str(current_user["_id"]),
        username=current_user.get("username", ""),
        name=current_user.get("name", ""),
    )


@router.put(
    "",
    response_model=BioProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Update current user's bio profile",
)
def update_my_bio_profile(
    data: UpdateBioProfileRequest,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> BioProfileResponse:
    """
    Update the authenticated user's bio profile:
    display name, bio, avatar URL, theme colors, published state, and social links.
    """
    return BioService.update_profile(
        user_id=str(current_user["_id"]),
        data=data,
        username=current_user.get("username", ""),
        name=current_user.get("name", ""),
    )


# =====================================================================
# Authenticated Bio Links CRUD & Reorder
# =====================================================================

@router.get(
    "/links",
    response_model=list[BioLinkResponse],
    status_code=status.HTTP_200_OK,
    summary="List current user's bio links",
)
def list_my_bio_links(
    current_user: dict[str, Any] = Depends(get_current_user),
) -> list[BioLinkResponse]:
    """Retrieve all bio links belonging to the user, ordered by position."""
    return BioService.list_links(user_id=str(current_user["_id"]))


@router.post(
    "/links",
    response_model=BioLinkResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new bio link",
)
def create_my_bio_link(
    data: CreateBioLinkRequest,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> BioLinkResponse:
    """Add a new link to the user's bio profile."""
    return BioService.create_link(
        user_id=str(current_user["_id"]),
        data=data,
        username=current_user.get("username", ""),
        name=current_user.get("name", ""),
    )


@router.put(
    "/links/{link_id}",
    response_model=BioLinkResponse,
    status_code=status.HTTP_200_OK,
    summary="Update a bio link",
)
def update_my_bio_link(
    link_id: str,
    data: UpdateBioLinkRequest,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> BioLinkResponse:
    """Update title, URL, or visibility of a bio link. Enforces user ownership."""
    return BioService.update_link(user_id=str(current_user["_id"]), link_id=link_id, data=data)


@router.delete(
    "/links/{link_id}",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete a bio link",
)
def delete_my_bio_link(
    link_id: str,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> MessageResponse:
    """Delete a bio link. Enforces user ownership."""
    BioService.delete_link(user_id=str(current_user["_id"]), link_id=link_id)
    return MessageResponse(message="Bio link deleted successfully")


@router.patch(
    "/links/reorder",
    response_model=list[BioLinkResponse],
    status_code=status.HTTP_200_OK,
    summary="Reorder bio links",
)
def reorder_my_bio_links(
    data: ReorderBioLinksRequest,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> list[BioLinkResponse]:
    """
    Persist new ordering for the user's bio links.
    Validates ownership of all submitted link IDs.
    """
    return BioService.reorder_links(user_id=str(current_user["_id"]), data=data)


# =====================================================================
# Public Bio Profile Endpoint (Unauthenticated)
# =====================================================================

@router.get(
    "/public/{username}",
    response_model=PublicBioResponse,
    status_code=status.HTTP_200_OK,
    summary="Get public bio profile by username",
)
@limiter.limit("60/minute")
def get_public_bio_profile(request: Request, username: str) -> PublicBioResponse:
    """
    Retrieve public Bio profile by username.
    - Public access without authentication.
    - Returns 404 if profile does not exist OR isPublished=False.
    - Only returns visible links sorted by position ascending.
    - Strips all private metadata (userId, email, passwordHash, hidden links).
    """
    return BioService.get_public_profile(username=username)
