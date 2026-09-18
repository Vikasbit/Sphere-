"""
User and RefreshSession data models and MongoDB document representations.
"""

from datetime import datetime, timezone
from typing import Any
from bson import ObjectId
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class MongoBaseModel(BaseModel):
    """Base model supporting MongoDB ObjectId serialization."""
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str},
    )


class UserModel(MongoBaseModel):
    """Internal user model representation in MongoDB."""
    id: str | None = Field(default=None, alias="_id")
    name: str
    email: str
    passwordHash: str
    username: str
    isEmailVerified: bool = False
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Email verification fields
    emailVerificationTokenHash: str | None = None
    emailVerificationExpiresAt: datetime | None = None

    # Password reset fields
    passwordResetTokenHash: str | None = None
    passwordResetExpiresAt: datetime | None = None


class RefreshSessionModel(MongoBaseModel):
    """Refresh session model tracking rotating refresh tokens."""
    id: str | None = Field(default=None, alias="_id")
    userId: str
    tokenHash: str
    expiresAt: datetime
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    revokedAt: datetime | None = None
    replacedBy: str | None = None
