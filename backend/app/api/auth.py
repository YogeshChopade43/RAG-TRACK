"""
Authentication API endpoints for RAG-TRACK.

Provides user registration, login, and token management endpoints.
"""

import re
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from app.core.auth_service import (
    authenticate_user,
    change_password,
    create_tokens,
    is_token_revoked,
    register_user,
)
from app.core.auth_service import (
    logout as revoke_token,
)
from app.core.security import decode_token
from app.db.models.user import User
from app.db.session import get_db

router = APIRouter()

bearer = HTTPBearer(auto_error=False)


def validate_email(v: str) -> str:
    """Validate email format."""
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    if not re.match(pattern, v):
        raise ValueError("Invalid email format")
    return v


# =============================================================================
# Request/Response Models
# =============================================================================

class RegisterRequest(BaseModel):
    """Request model for registration."""

    email: str = Field(..., max_length=255)
    password: str = Field(..., min_length=8, max_length=100)
    full_name: Optional[str] = Field(None, max_length=255)

    @field_validator("email")
    @classmethod
    def validate_email_field(cls, v: str) -> str:
        return validate_email(v)


class RegisterResponse(BaseModel):
    """Response model for registration."""

    id: str
    email: str
    full_name: Optional[str] = None
    message: str


class LoginRequest(BaseModel):
    """Request model for login."""

    email: str = Field(..., max_length=255)
    password: str

    @field_validator("email")
    @classmethod
    def validate_email_field(cls, v: str) -> str:
        return validate_email(v)


class TokenResponse(BaseModel):
    """Response model for tokens."""

    access_token: str
    refresh_token: str
    token_type: str


class RefreshRequest(BaseModel):
    """Request model for token refresh."""

    refresh_token: str


class ChangePasswordRequest(BaseModel):
    """Request model for password change."""

    current_password: str
    new_password: str = Field(..., min_length=8, max_length=100)


# =============================================================================
# Dependencies
# =============================================================================


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    """
    Get current user from JWT token.

    Returns:
        User object

    Raises:
        HTTPException: If token is invalid or user not found
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    token = credentials.credentials

    try:
        payload = decode_token(token)
        user_id = payload.get("sub")

        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
            )

        if is_token_revoked(db, token):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked",
            )

        user = db.query(User).filter(User.id == uuid.UUID(user_id)).first()

        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Inactive user",
            )

        return user

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        ) from None


def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Get current active user."""
    return current_user


# =============================================================================
# Endpoints
# =============================================================================


@router.post("/register", response_model=RegisterResponse)
async def register(
    request: RegisterRequest,
    db: Session = Depends(get_db),
):
    """Register a new user."""
    user = register_user(
        db,
        email=request.email,
        password=request.password,
        full_name=request.full_name,
    )

    return RegisterResponse(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        message="User registered successfully",
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    db: Session = Depends(get_db),
):
    """Login and get access/refresh tokens."""
    user = authenticate_user(db, request.email, request.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    tokens = create_tokens(db, user)

    return tokens


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: RefreshRequest,
    db: Session = Depends(get_db),
):
    """Refresh access token using refresh token."""
    try:
        payload = decode_token(request.refresh_token)

        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
            )

        user_id = payload.get("sub")
        user = db.query(User).filter(User.id == uuid.UUID(user_id)).first()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )

        tokens = create_tokens(db, user)

        return tokens

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        ) from None


@router.post("/logout")
async def logout_user(
    current_user: User = Depends(get_current_active_user),
    authorization: str = Header(None, alias="Authorization"),
    db: Session = Depends(get_db),
):
    """Logout and revoke current token."""
    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization.replace("Bearer ", "")

    if token:
        revoke_token(db, current_user.id, token)

    return {"message": "Successfully logged out"}


@router.get("/me")
async def read_users_me(
    current_user: User = Depends(get_current_active_user),
):
    """Get current user info."""
    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "full_name": current_user.full_name,
        "is_active": current_user.is_active,
    }


@router.post("/change-password")
async def change_user_password(
    request: ChangePasswordRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Change user password."""
    change_password(db, current_user, request.current_password, request.new_password)

    return {"message": "Password changed successfully"}
