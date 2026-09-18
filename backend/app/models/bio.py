"""
Bio-Link profile and bio links data models.
"""

from datetime import datetime, timezone
from pydantic import BaseModel, Field
from app.models.user import MongoBaseModel


class SocialLinkItem(BaseModel):
    """Represents a single social link channel."""
    platform: str
    url: str


class BioProfileModel(MongoBaseModel):
    """MongoDB document representation of a user's Bio profile."""
    id: str | None = Field(default=None, alias="_id")
    userId: str
    username: str
    displayName: str
    bio: str | None = None
    avatarUrl: str | None = None
    backgroundColor: str = "#0F172A"
    buttonColor: str = "#1E293B"
    textColor: str = "#FFFFFF"
    isPublished: bool = True
    socialLinks: list[SocialLinkItem] = Field(default_factory=list)
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class BioLinkModel(MongoBaseModel):
    """MongoDB document representation of an individual link on a Bio profile."""
    id: str | None = Field(default=None, alias="_id")
    bioProfileId: str
    userId: str
    title: str
    url: str
    position: int = 0
    isVisible: bool = True
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
