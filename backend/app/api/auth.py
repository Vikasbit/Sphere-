"""
Authentication API endpoints.

Routes:
- POST /api/auth/signup: Register new user (Rate-limited: 10/min)
- POST /api/auth/verify-email: Verify email address (Rate-limited: 10/min)
- POST /api/auth/login: Authenticate user & set httpOnly cookies (Rate-limited: 10/min)
- POST /api/auth/logout: Revoke refresh session & clear cookies (Rate-limited: 30/min)
- POST /api/auth/refresh: Rotate refresh token & issue new access token (Rate-limited: 30/min)
- POST /api/auth/forgot-password: Request password reset link (Rate-limited: 5/min)
- POST /api/auth/reset-password: Reset password with token & revoke active sessions (Rate-limited: 5/min)
- GET /api/auth/me: Retrieve current authenticated user profile
"""

from typing import Any
from fastapi import APIRouter, Depends, Request, Response, status

from app.core.limiter import limiter
from app.dependencies.auth import get_current_user
from app.schemas.auth import (
    AuthResponse,
    ForgotPasswordRequest,
    LoginRequest,
    MessageResponse,
    ResetPasswordRequest,
    SignupRequest,
    UserResponse,
    VerifyEmailRequest,
)
from app.services.auth_service import AuthService, sanitize_user_doc

router = APIRouter(prefix="/api/auth", tags=["Auth"])


@router.post(
    "/signup",
    response_model=dict[str, Any],
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
@limiter.limit("10/minute")
def signup(request: Request, data: SignupRequest) -> dict[str, Any]:
    """
    Create a new user account.
    - Validates email and username uniqueness
    - Hashes password using Argon2id
    - Generates email verification token
    - Returns safe user representation
    """
    user_resp, msg_resp = AuthService.signup(data)
    return {
        "user": user_resp.model_dump(),
        "message": msg_resp.message,
        "devVerificationToken": msg_resp.devVerificationToken,
        "devVerificationUrl": msg_resp.devVerificationUrl,
    }


@router.post(
    "/verify-email",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Verify email address",
)
@limiter.limit("10/minute")
def verify_email(request: Request, data: VerifyEmailRequest) -> MessageResponse:
    """
    Verify user email using a valid single-use token.
    """
    return AuthService.verify_email(data)


@router.post(
    "/login",
    response_model=AuthResponse,
    status_code=status.HTTP_200_OK,
    summary="Authenticate and obtain session cookies",
)
@limiter.limit("10/minute")
def login(request: Request, data: LoginRequest, response: Response) -> AuthResponse:
    """
    Authenticate user using email and password.
    Sets access_token and refresh_token httpOnly cookies.
    """
    return AuthService.login(data, response)


@router.post(
    "/logout",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Log out and revoke session",
)
@limiter.limit("30/minute")
def logout(request: Request, response: Response) -> MessageResponse:
    """
    Revokes the current refresh session and clears authentication cookies.
    Safe to call repeatedly (idempotent).
    """
    return AuthService.logout(request, response)


@router.post(
    "/refresh",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Rotate refresh token and issue new access token",
)
@limiter.limit("30/minute")
def refresh(request: Request, response: Response) -> MessageResponse:
    """
    Rotates refresh token and issues a new 15-minute access token.
    Enforces reuse detection: reusing an already revoked or rotated refresh token
    revokes all active sessions for that account.
    """
    return AuthService.refresh_tokens(request, response)


@router.post(
    "/forgot-password",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Request password reset link",
)
@limiter.limit("5/minute")
def forgot_password(request: Request, data: ForgotPasswordRequest) -> MessageResponse:
    """
    Send password reset instructions. Always returns a generic response
    regardless of whether the account exists to prevent user enumeration.
    """
    return AuthService.forgot_password(data)


@router.post(
    "/reset-password",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Reset password using token",
)
@limiter.limit("5/minute")
def reset_password(request: Request, data: ResetPasswordRequest, response: Response) -> MessageResponse:
    """
    Reset password with a valid reset token.
    Updates password using Argon2id, invalidates the token,
    and revokes all active refresh sessions.
    """
    return AuthService.reset_password(data, response)


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current authenticated user profile",
)
@limiter.limit("60/minute")
def get_me(request: Request, current_user: dict[str, Any] = Depends(get_current_user)) -> UserResponse:
    """
    Return currently authenticated user information.
    Protected by httpOnly access-token cookie.
    Never exposes passwords, tokens, or private secrets.
    """
    return sanitize_user_doc(current_user)
