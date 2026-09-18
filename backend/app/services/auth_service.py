"""
Authentication business logic service.

Handles user registration, email verification, password reset,
session creation, refresh-token rotation with reuse detection, and session revocation.
"""

from datetime import datetime, timedelta, timezone
import logging
from typing import Any
from bson import ObjectId
from fastapi import HTTPException, Request, Response, status

from app.core.config import get_settings
from app.core.database import get_database
from app.core.security import (
    clear_auth_cookies,
    create_access_token,
    create_refresh_token,
    generate_secure_token,
    hash_password,
    hash_token,
    set_auth_cookies,
    verify_password,
)
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

logger = logging.getLogger(__name__)


def sanitize_user_doc(user: dict[str, Any]) -> UserResponse:
    """Transform a MongoDB user document into a safe UserResponse schema."""
    return UserResponse(
        id=str(user["_id"]),
        name=user.get("name", ""),
        email=user.get("email", ""),
        username=user.get("username", ""),
        isEmailVerified=bool(user.get("isEmailVerified", False)),
    )


class AuthService:
    """Authentication and session lifecycle management."""

    @staticmethod
    def signup(data: SignupRequest) -> tuple[UserResponse, MessageResponse]:
        """
        Register a new user account.
        Checks email/username uniqueness, hashes password with Argon2id,
        creates verification token, and stores records in MongoDB.
        """
        db = get_database()
        settings = get_settings()
        now = datetime.now(timezone.utc)

        # Check for existing email
        if db.users.find_one({"email": data.email}):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email is already registered",
            )

        # Check for existing username
        if db.users.find_one({"username": data.username}):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Username is already taken",
            )

        # Hash password with Argon2id
        pwd_hash = hash_password(data.password)

        # Generate email verification token (24-hour expiry)
        raw_verification_token = generate_secure_token(32)
        verification_hash = hash_token(raw_verification_token)
        verification_expires = now + timedelta(hours=24)

        user_doc = {
            "name": data.name,
            "email": data.email,
            "username": data.username,
            "passwordHash": pwd_hash,
            "isEmailVerified": False,
            "emailVerificationTokenHash": verification_hash,
            "emailVerificationExpiresAt": verification_expires,
            "createdAt": now,
            "updatedAt": now,
        }

        result = db.users.insert_one(user_doc)
        user_doc["_id"] = result.inserted_id

        # Development simulation link
        verification_url = f"{settings.frontend_url}/verify-email?token={raw_verification_token}"
        if not settings.is_production:
            logger.info(
                "User signup completed for %s (%s). Dev verification link: %s",
                data.email,
                data.username,
                verification_url,
            )
        else:
            logger.info("User signup completed for %s (%s).", data.email, data.username)

        user_response = sanitize_user_doc(user_doc)
        msg_response = MessageResponse(
            message="Account created successfully. Please verify your email.",
            devVerificationToken=raw_verification_token if not settings.is_production else None,
            devVerificationUrl=verification_url if not settings.is_production else None,
        )

        return user_response, msg_response

    @staticmethod
    def verify_email(data: VerifyEmailRequest) -> MessageResponse:
        """
        Verify account email with verification token.
        Enforces single-use and expiration.
        """
        db = get_database()
        token_hash = hash_token(data.token)
        now = datetime.now(timezone.utc)

        user = db.users.find_one({"emailVerificationTokenHash": token_hash})
        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or already used verification token",
            )

        expires_at = user.get("emailVerificationExpiresAt")
        if expires_at and expires_at.replace(tzinfo=timezone.utc if expires_at.tzinfo is None else None) < now:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Verification token has expired",
            )

        # Update user: mark verified and invalidate token
        db.users.update_one(
            {"_id": user["_id"]},
            {
                "$set": {"isEmailVerified": True, "updatedAt": now},
                "$unset": {
                    "emailVerificationTokenHash": "",
                    "emailVerificationExpiresAt": "",
                },
            },
        )

        return MessageResponse(message="Email successfully verified. You can now log in.")

    @staticmethod
    def login(data: LoginRequest, response: Response) -> AuthResponse:
        """
        Authenticate user with email and password.
        Sets httpOnly cookies for access token and rotating refresh token.
        """
        db = get_database()
        now = datetime.now(timezone.utc)

        user = db.users.find_one({"email": data.email})
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )

        if not verify_password(data.password, user.get("passwordHash", "")):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )

        user_id_str = str(user["_id"])

        # Generate access token (15-min JWT)
        access_token = create_access_token(user_id_str)

        # Generate refresh token (7-day random token stored as SHA-256)
        raw_refresh, refresh_hash, refresh_expires = create_refresh_token()

        session_doc = {
            "userId": user_id_str,
            "tokenHash": refresh_hash,
            "expiresAt": refresh_expires,
            "createdAt": now,
            "revokedAt": None,
            "replacedBy": None,
        }
        db.refresh_sessions.insert_one(session_doc)

        # Set secure httpOnly cookies
        set_auth_cookies(response, access_token, raw_refresh)

        return AuthResponse(
            user=sanitize_user_doc(user),
            message="Login successful",
        )

    @staticmethod
    def refresh_tokens(request: Request, response: Response) -> MessageResponse:
        """
        Rotate refresh token and issue new 15-minute access token.
        Implements genuine token rotation and reuse detection.
        """
        settings = get_settings()
        raw_refresh = request.cookies.get(settings.refresh_cookie_name)
        if not raw_refresh:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token missing",
            )

        token_hash = hash_token(raw_refresh)
        db = get_database()
        now = datetime.now(timezone.utc)

        session = db.refresh_sessions.find_one({"tokenHash": token_hash})
        if not session:
            clear_auth_cookies(response)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh session",
            )

        user_id = session.get("userId")

        # REUSE DETECTION:
        # If this session was already revoked or already rotated, someone is attempting
        # to replay an old refresh token. Revoke all active sessions for this user immediately!
        if session.get("revokedAt") is not None or session.get("replacedBy") is not None:
            logger.warning(
                "Revoked/replaced refresh token reuse detected for userId=%s! Revoking all sessions.",
                user_id,
            )
            db.refresh_sessions.update_many(
                {"userId": user_id, "revokedAt": None},
                {"$set": {"revokedAt": now}},
            )
            clear_auth_cookies(response)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token was revoked or reused",
            )

        # Expiration check
        expires_at = session.get("expiresAt")
        if expires_at and expires_at.replace(tzinfo=timezone.utc if expires_at.tzinfo is None else None) < now:
            clear_auth_cookies(response)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token has expired",
            )

        # Rotate: Create new refresh session
        new_raw_refresh, new_token_hash, new_refresh_expires = create_refresh_token()
        new_session_doc = {
            "userId": user_id,
            "tokenHash": new_token_hash,
            "expiresAt": new_refresh_expires,
            "createdAt": now,
            "revokedAt": None,
            "replacedBy": None,
        }
        insert_res = db.refresh_sessions.insert_one(new_session_doc)

        # Mark previous session as revoked & record replacement
        db.refresh_sessions.update_one(
            {"_id": session["_id"]},
            {
                "$set": {
                    "revokedAt": now,
                    "replacedBy": str(insert_res.inserted_id),
                }
            },
        )

        # Create new 15-minute access token
        new_access_token = create_access_token(user_id)

        # Set updated cookies
        set_auth_cookies(response, new_access_token, new_raw_refresh)

        return MessageResponse(message="Tokens successfully refreshed")

    @staticmethod
    def logout(request: Request, response: Response) -> MessageResponse:
        """
        Log out current user: revoke the active refresh session and clear cookies.
        Safe to call repeatedly (idempotent).
        """
        settings = get_settings()
        raw_refresh = request.cookies.get(settings.refresh_cookie_name)

        if raw_refresh:
            token_hash = hash_token(raw_refresh)
            db = get_database()
            now = datetime.now(timezone.utc)
            db.refresh_sessions.update_one(
                {"tokenHash": token_hash, "revokedAt": None},
                {"$set": {"revokedAt": now}},
            )

        clear_auth_cookies(response)
        return MessageResponse(message="Logged out successfully")

    @staticmethod
    def forgot_password(data: ForgotPasswordRequest) -> MessageResponse:
        """
        Request password reset link.
        Always returns a generic message to prevent user enumeration.
        Generates and stores a hashed reset token if account exists.
        """
        db = get_database()
        settings = get_settings()
        now = datetime.now(timezone.utc)

        user = db.users.find_one({"email": data.email})
        dev_token = None
        dev_url = None

        if user:
            raw_reset_token = generate_secure_token(32)
            reset_hash = hash_token(raw_reset_token)
            reset_expires = now + timedelta(hours=1)

            db.users.update_one(
                {"_id": user["_id"]},
                {
                    "$set": {
                        "passwordResetTokenHash": reset_hash,
                        "passwordResetExpiresAt": reset_expires,
                        "updatedAt": now,
                    }
                },
            )

            reset_url = f"{settings.frontend_url}/reset-password?token={raw_reset_token}"
            if not settings.is_production:
                logger.info("Password reset requested for %s. Dev reset link: %s", data.email, reset_url)
                dev_token = raw_reset_token
                dev_url = reset_url
            else:
                logger.info("Password reset requested for %s.", data.email)

        return MessageResponse(
            message="If that email is registered, a password reset link has been sent.",
            devResetToken=dev_token,
            devResetUrl=dev_url,
        )

    @staticmethod
    def reset_password(data: ResetPasswordRequest, response: Response) -> MessageResponse:
        """
        Reset password using secure reset token.
        Updates password with Argon2id, clears reset token,
        and revokes all active refresh sessions for security.
        """
        db = get_database()
        token_hash = hash_token(data.token)
        now = datetime.now(timezone.utc)

        user = db.users.find_one({"passwordResetTokenHash": token_hash})
        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or already used password reset token",
            )

        expires_at = user.get("passwordResetExpiresAt")
        if expires_at and expires_at.replace(tzinfo=timezone.utc if expires_at.tzinfo is None else None) < now:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password reset token has expired",
            )

        new_hash = hash_password(data.newPassword)
        user_id_str = str(user["_id"])

        # Update password and clear reset token
        db.users.update_one(
            {"_id": user["_id"]},
            {
                "$set": {
                    "passwordHash": new_hash,
                    "updatedAt": now,
                },
                "$unset": {
                    "passwordResetTokenHash": "",
                    "passwordResetExpiresAt": "",
                },
            },
        )

        # Invalidate all active refresh sessions for this user
        db.refresh_sessions.update_many(
            {"userId": user_id_str, "revokedAt": None},
            {"$set": {"revokedAt": now}},
        )

        clear_auth_cookies(response)
        return MessageResponse(
            message="Password has been reset successfully. Please log in with your new password."
        )
