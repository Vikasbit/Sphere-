"""
ClickEvent data model and MongoDB document representation.
"""

from datetime import datetime, timezone
from pydantic import Field
from app.models.user import MongoBaseModel


class ClickEventModel(MongoBaseModel):
    """
    MongoDB document model for short link click telemetry.
    Stores privacy-safe analytics: device type, normalized referrer, hashed IP, and timestamp.
    Raw IP addresses, cookies, and user credentials are NEVER stored.
    """
    id: str | None = Field(default=None, alias="_id")
    linkId: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    referrer: str = "Direct"
    deviceType: str = "Desktop"
    ipHash: str
