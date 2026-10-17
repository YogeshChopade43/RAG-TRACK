"""
API Authentication middleware.

Validates API key from request headers and JWT tokens for user authentication.
"""

import logging
import secrets
from typing import Optional

from fastapi import Header, HTTPException, Request

from app.core.config import settings

logger = logging.getLogger(__name__)

# In-memory token blacklist for logout (use Redis in production)
_token_blacklist: set = set()


async def get_api_key(
    request: Request, api_key: Optional[str] = Header(None, alias="X-API-Key")
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


def get_optional_user_id(request: Request) -> Optional[str]:
    """User id from a valid `Authorization: Bearer <access token>`, else None (anonymous)."""
    from app.core.security import decode_token

    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None
    try:
        payload = decode_token(auth[len("Bearer "):])
    except Exception:
        return None
    # ponytail: signature + expiry only; logged-out (revoked) tokens are checked
    # against the DB in /auth, not here, so they work until they expire (30 min)
    return payload.get("sub") if payload.get("type") == "access" else None


def check_document_access(document_id: str, request: Request) -> None:
    """404 unless the document is anonymous or owned by the requesting user."""
    from app.services.generic.file_storage import get_owner

    owner = get_owner(document_id)
    if owner and owner != get_optional_user_id(request):
        # 404, not 403: don't reveal that someone else's document exists
        raise HTTPException(status_code=404, detail="Document not found")


def add_token_to_blacklist(token: str) -> None:
    """Add a token to the blacklist."""
    _token_blacklist.add(token)


def is_token_blacklisted(token: str) -> bool:
    """Check if a token is blacklisted."""
    return token in _token_blacklist
