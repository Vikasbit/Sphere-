"""
Authentication request and response Pydantic v2 schemas.
"""

import re
from typing import Annotated
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class SignupRequest(BaseModel):
    """Schema for user signup."""
    name: Annotated[str, Field(min_length=2, max_length=100, description="User's full name")]
    email: EmailStr
    username: Annotated[str, Field(min_length=3, max_length=30, description="Unique username")]
    password: Annotated[str, Field(min_length=8, max_length=128, description="Account password")]

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        cleaned = v.strip()
        if len(cleaned) < 2:
            raise ValueError("Name must be at least 2 characters")
        return cleaned

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        if isinstance(v, str):
            return v.strip().lower()
        return v

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        cleaned = v.strip().lower()
        if not re.match(r"^[a-z0-9_-]{3,30}$", cleaned):
            raise ValueError(
                "Username must be 3-30 characters and contain only lowercase letters, numbers, hyphens, or underscores"
            )
        return cleaned

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not any(c.isalpha() for c in v):
            raise ValueError("Password must contain at least one letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one number")
        return v


class LoginRequest(BaseModel):
    """Schema for user login."""
    email: EmailStr
    password: str

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        if isinstance(v, str):
            return v.strip().lower()
        return v


class VerifyEmailRequest(BaseModel):
    """Schema for email verification."""
    token: Annotated[str, Field(min_length=1, description="Email verification token")]


class ForgotPasswordRequest(BaseModel):
    """Schema for forgot password request."""
    email: EmailStr

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        if isinstance(v, str):
            return v.strip().lower()
        return v


class ResetPasswordRequest(BaseModel):
    """Schema for resetting password with a token."""
    token: Annotated[str, Field(min_length=1, description="Password reset token")]
    newPassword: Annotated[str, Field(min_length=8, max_length=128, description="New account password")]

    @field_validator("newPassword")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not any(c.isalpha() for c in v):
            raise ValueError("Password must contain at least one letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one number")
        return v


class UserResponse(BaseModel):
    """Safe user profile response without sensitive tokens or password hash."""
    model_config = ConfigDict(populate_by_name=True)

    id: str
    name: str
    email: str
    username: str
    isEmailVerified: bool


class MessageResponse(BaseModel):
    """Standard message response with optional development helpers."""
    message: str
    devVerificationToken: str | None = None
    devVerificationUrl: str | None = None
    devResetToken: str | None = None
    devResetUrl: str | None = None


class AuthResponse(BaseModel):
    """Authentication response returning user data and status message."""
    user: UserResponse
    message: str
