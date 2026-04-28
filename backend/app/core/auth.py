"""
API Authentication middleware.

Validates API key from request headers.
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


async def verify_api_key(
    api_key: str = Header(None, alias="X-API-Key"),
) -> Optional[str]:
    """
    Dependency for endpoints that need optional API key verification.

    Returns the API key if valid, raises 401/403 otherwise.
    """
    return await get_api_key(Header, api_key)
