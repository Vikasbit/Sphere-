"""
Link business logic service.

Handles short code generation, collision retries, custom vanity slug checks,
reserved slug protection, user-isolated link listing with pagination, and deletion.
"""

from datetime import datetime, timezone
import logging
import secrets
import re
from typing import Any
from bson import ObjectId
from fastapi import HTTPException, status
from pymongo.errors import DuplicateKeyError

from app.core.config import get_settings
from app.core.constants import (
    MAX_CODE_GEN_ATTEMPTS,
    RESERVED_SLUGS,
    SHORT_CODE_ALPHABET,
    SHORT_CODE_LENGTH,
)
from app.core.database import get_database
from app.schemas.link import CreateLinkRequest, LinkListResponse, LinkResponse

logger = logging.getLogger(__name__)


def sanitize_link_doc(link: dict[str, Any]) -> LinkResponse:
    """Transform a MongoDB link document into a safe LinkResponse schema."""
    settings = get_settings()
    short_code = link.get("shortCode", "")
    short_url = f"{settings.short_link_base_url}/{short_code}"

    return LinkResponse(
        id=str(link["_id"]),
        destinationUrl=link.get("destinationUrl", ""),
        shortCode=short_code,
        shortUrl=short_url,
        clickCount=int(link.get("clickCount", 0)),
        title=link.get("title"),
        createdAt=link.get("createdAt", datetime.now(timezone.utc)),
        updatedAt=link.get("updatedAt", datetime.now(timezone.utc)),
    )


class LinkService:
    """Short link operations and management."""

    @staticmethod
    def generate_short_code() -> str:
        """Generate a cryptographically secure random 6-character short code."""
        return "".join(secrets.choice(SHORT_CODE_ALPHABET) for _ in range(SHORT_CODE_LENGTH))

    @staticmethod
    def validate_custom_slug(slug: str) -> None:
        """
        Verify that a custom vanity slug does not collide with reserved system or application routes.
        Raises HTTPException(400) if reserved.
        """
        normalized = slug.strip().lower()
        if normalized in RESERVED_SLUGS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"'{slug}' is a reserved system route and cannot be used as a custom slug",
            )

    @classmethod
    def create_link(cls, user_id: str, data: CreateLinkRequest) -> LinkResponse:
        """
        Create a new short link for an authenticated user.

        If `customSlug` is provided:
        - Validates against reserved routes.
        - Enforces uniqueness via MongoDB unique index. Returns 409 on conflict.

        If `customSlug` is omitted:
        - Generates a 6-character code.
        - Attempts insertion; if a collision occurs, retries up to MAX_CODE_GEN_ATTEMPTS.
        """
        db = get_database()
        now = datetime.now(timezone.utc)
        user_id_str = str(user_id)

        # -------------------------------------------------------------------
        # Custom vanity slug flow
        # -------------------------------------------------------------------
        if data.customSlug:
            cls.validate_custom_slug(data.customSlug)

            # Application-level check
            if db.links.find_one({"shortCode": data.customSlug}):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Custom slug '{data.customSlug}' is already in use",
                )

            link_doc = {
                "userId": user_id_str,
                "destinationUrl": data.destinationUrl,
                "shortCode": data.customSlug,
                "clickCount": 0,
                "title": data.title,
                "createdAt": now,
                "updatedAt": now,
            }

            try:
                res = db.links.insert_one(link_doc)
                link_doc["_id"] = res.inserted_id
                return sanitize_link_doc(link_doc)
            except DuplicateKeyError:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Custom slug '{data.customSlug}' is already in use",
                )

        # -------------------------------------------------------------------
        # Auto-generated 6-character code flow with bounded collision retry
        # -------------------------------------------------------------------
        for attempt in range(1, MAX_CODE_GEN_ATTEMPTS + 1):
            candidate_code = cls.generate_short_code()

            # Ensure candidate doesn't match a reserved route
            if candidate_code.lower() in RESERVED_SLUGS:
                continue

            link_doc = {
                "userId": user_id_str,
                "destinationUrl": data.destinationUrl,
                "shortCode": candidate_code,
                "clickCount": 0,
                "title": data.title,
                "createdAt": now,
                "updatedAt": now,
            }

            try:
                res = db.links.insert_one(link_doc)
                link_doc["_id"] = res.inserted_id
                logger.info("Created short link '%s' on attempt %d", candidate_code, attempt)
                return sanitize_link_doc(link_doc)
            except DuplicateKeyError:
                logger.warning(
                    "Short code collision for '%s' on attempt %d/%d; retrying...",
                    candidate_code,
                    attempt,
                    MAX_CODE_GEN_ATTEMPTS,
                )
                continue

        # If all attempts exhausted
        logger.error("Exhausted all %d short code generation attempts.", MAX_CODE_GEN_ATTEMPTS)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to generate a unique short code. Please try again.",
        )

    @staticmethod
    def list_links(
        user_id: str,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
    ) -> LinkListResponse:
        """
        List user's short links with server-side pagination and search filtering.
        Strictly isolates links so users only see their own records.
        """
        db = get_database()
        user_id_str = str(user_id)

        # Normalize pagination arguments
        clean_page = max(1, page)
        clean_page_size = max(1, min(100, page_size))

        query: dict[str, Any] = {"userId": user_id_str}

        if search and search.strip():
            escaped_search = re.escape(search.strip())
            query["$or"] = [
                {"destinationUrl": {"$regex": escaped_search, "$options": "i"}},
                {"shortCode": {"$regex": escaped_search, "$options": "i"}},
                {"title": {"$regex": escaped_search, "$options": "i"}},
            ]

        total = db.links.count_documents(query)
        total_pages = (total + clean_page_size - 1) // clean_page_size if total > 0 else 1
        skip = (clean_page - 1) * clean_page_size

        cursor = (
            db.links.find(query)
            .sort("createdAt", -1)
            .skip(skip)
            .limit(clean_page_size)
        )

        items = [sanitize_link_doc(doc) for doc in cursor]

        return LinkListResponse(
            items=items,
            page=clean_page,
            pageSize=clean_page_size,
            total=total,
            totalPages=total_pages,
        )

    @staticmethod
    def get_link(user_id: str, link_id: str) -> LinkResponse:
        """
        Retrieve a single short link by its ID.
        Verifies ownership; returns 404 if not found or owned by another user.
        """
        db = get_database()
        try:
            oid = ObjectId(link_id)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Link not found",
            )

        link = db.links.find_one({"_id": oid})
        if not link or str(link.get("userId")) != str(user_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Link not found",
            )

        return sanitize_link_doc(link)

    @staticmethod
    def delete_link(user_id: str, link_id: str) -> None:
        """
        Delete a link by its ID.
        Verifies ownership; returns 404 if not found or owned by another user.
        """
        db = get_database()
        try:
            oid = ObjectId(link_id)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Link not found",
            )

        link = db.links.find_one({"_id": oid})
        if not link or str(link.get("userId")) != str(user_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Link not found",
            )

        db.links.delete_one({"_id": oid})
        logger.info("Link %s (shortCode=%s) deleted by user %s", link_id, link.get("shortCode"), user_id)
