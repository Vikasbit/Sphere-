"""
Schemas package.
"""

from app.schemas.auth import (
    SignupRequest,
    LoginRequest,
    VerifyEmailRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    UserResponse,
    MessageResponse,
    AuthResponse,
)
from app.schemas.link import (
    CreateLinkRequest,
    LinkResponse,
    LinkListResponse,
)

__all__ = [
    "SignupRequest",
    "LoginRequest",
    "VerifyEmailRequest",
    "ForgotPasswordRequest",
    "ResetPasswordRequest",
    "UserResponse",
    "MessageResponse",
    "AuthResponse",
    "CreateLinkRequest",
    "LinkResponse",
    "LinkListResponse",
]
