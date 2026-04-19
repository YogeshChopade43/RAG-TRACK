"""
Rate limiting configuration for RAG-TRACK API.

Provides configurable rate limiting per endpoint using slowapi.
"""
import logging
from typing import Optional

from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request
from fastapi.responses import JSONResponse

from app.core.config import settings

logger = logging.getLogger(__name__)


def get_client_ip(request: Request) -> str:
    """Extract client IP from request for rate limiting."""
    # Check for forwarded header (reverse proxy)
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return get_remote_address(request)


class RateLimiterConfig:
    """Rate limiter configuration."""

    _limiter: Optional[Limiter] = None

    @classmethod
    def get_limiter(cls) -> Limiter:
        """Get or create the global limiter instance."""
        if cls._limiter is None:
            cls._limiter = Limiter(
                key_func=get_client_ip,
                default_limits=[],
                enabled=settings.rate_limit_enabled,
            )
        return cls._limiter

    @classmethod
    def get_limit(cls) -> str:
        """Get the default rate limit string."""
        return f"{settings.rate_limit_per_minute}/minute"


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """Custom handler for rate limit exceeded errors."""
    logger.warning(
        f"Rate limit exceeded for {request.client.host if request.client else 'unknown'}"
    )
    return JSONResponse(
        status_code=429,
        content={
            "error": "rate_limit_exceeded",
            "message": "Too many requests. Please try again later.",
            "detail": f"Rate limit: {exc.detail}",
        },
    )


limiter = RateLimiterConfig.get_limiter()
default_limit = RateLimiterConfig.get_limit()