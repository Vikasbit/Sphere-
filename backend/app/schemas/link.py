"""
Pydantic v2 schemas for Short Links.
"""

from datetime import datetime
import re
from urllib.parse import urlparse
from typing import Annotated
from pydantic import BaseModel, ConfigDict, Field, field_validator


class CreateLinkRequest(BaseModel):
    """Schema for creating a new short link."""
    destinationUrl: Annotated[str, Field(description="Target destination URL (HTTP or HTTPS)")]
    customSlug: Annotated[str | None, Field(default=None, description="Optional vanity short slug")] = None
    title: Annotated[str | None, Field(default=None, max_length=200, description="Optional title or label")] = None

    @field_validator("destinationUrl")
    @classmethod
    def validate_destination_url(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Destination URL cannot be empty")
        parsed = urlparse(cleaned)
        if parsed.scheme.lower() not in ("http", "https"):
            raise ValueError("Destination URL must use http:// or https:// protocol")
        if not parsed.netloc:
            raise ValueError("Destination URL must include a valid domain or host")
        return cleaned

    @field_validator("customSlug")
    @classmethod
    def validate_custom_slug(cls, v: str | None) -> str | None:
        if v is None:
            return None
        cleaned = v.strip().lower()
        if not cleaned:
            return None
        if not re.match(r"^[a-z0-9_-]{3,50}$", cleaned):
            raise ValueError(
                "Custom slug must be 3-50 characters and contain only letters, numbers, hyphens, or underscores"
            )
        return cleaned


class LinkResponse(BaseModel):
    """Safe public representation of a short link."""
    model_config = ConfigDict(populate_by_name=True)

    id: str
    destinationUrl: str
    shortCode: str
    shortUrl: str
    clickCount: int = 0
    title: str | None = None
    createdAt: datetime
    updatedAt: datetime


class LinkListResponse(BaseModel):
    """Paginated list of user links."""
    items: list[LinkResponse]
    page: int
    pageSize: int
    total: int
    totalPages: int
