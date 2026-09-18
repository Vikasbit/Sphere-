"""
Link data model and MongoDB document representation.
"""

from datetime import datetime, timezone
from pydantic import Field
from app.models.user import MongoBaseModel


class LinkModel(MongoBaseModel):
    """Internal MongoDB document representation of a short link."""
    id: str | None = Field(default=None, alias="_id")
    userId: str
    destinationUrl: str
    shortCode: str
    clickCount: int = 0
    title: str | None = None
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
