"""
API Authentication middleware.

Validates API key from request headers and JWT tokens for user authentication.
"""

import logging
import secrets
from typing import Optional

from fastapi import Header, HTTPException, Request
from fastapi.security import APIKeyHeader

from app.core.config import settings

logger = logging.getLogger(__name__)

API_KEY_HEADER = APIKeyHeader(
    name="X-API-Key",
    auto_error=False,
)

# In-memory token blacklist for logout (use Redis in production)
_token_blacklist: set = set()


async def get_api_key(
    request: Request,     api_key: Optional[str] = Header(None, alias="X-API-Key")
) -> str:
    """
    Validate API key from request header.

    Args:
        request: FastAPI request object
        api_key: API key from header

    Returns:
        The validated API key

    Raises:
        HTTPException: If API key is invalid or missing
    """
    # Skip auth if not configured (development mode)
    if not settings.api_key:
        return "dev-mode"

    # Check header
    if not api_key:
        logger.warning("Missing API key in request")
        raise HTTPException(
            status_code=401,
            detail="API key required. Add 'X-API-Key' header.",
        )

    # Validate key using constant-time comparison to prevent timing attacks
    if not secrets.compare_digest(api_key or "", settings.api_key or ""):
        logger.warning("Invalid API key provided")
        raise HTTPException(
            status_code=403,
            detail="Invalid API key",
        )

    return api_key


async def verify_api_key(
    api_key: str = Header(None, alias="X-API-Key"),
) -> Optional[str]:
    """
    Dependency for endpoints that need optional API key verification.

    Returns the API key if valid, raises 401/403 otherwise.
    """
    return await get_api_key(Header, api_key)


def add_token_to_blacklist(token: str) -> None:
    """Add a token to the blacklist."""
    _token_blacklist.add(token)


def is_token_blacklisted(token: str) -> bool:
    """Check if a token is blacklisted."""
    return token in _token_blacklist


async def get_optional_current_user(request: Request) -> Optional[object]:
    """
    Get current user from JWT token if present.

    Supports both API key and JWT authentication.
    Returns None for unauthenticated requests (for optional auth).
    """
    from app.core.security import decode_token

    authorization = request.headers.get("Authorization")
    if not authorization or not authorization.startswith("Bearer "):
        return None

    token = authorization.replace("Bearer ", "")

    try:
        payload = decode_token(token)
        if is_token_blacklisted(token):
            return None
        return {"id": payload.get("sub"), "type": payload.get("type")}
    except Exception:
        return None
