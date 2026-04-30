"""
Unit tests for rate limiting configuration.
"""
import pytest
import logging
from unittest.mock import Mock, patch, MagicMock
from fastapi import Request
from fastapi.responses import JSONResponse


class TestRateLimit:
    """Tests for rate limiting module."""

    def test_get_client_ip_from_forwarded_header(self):
        """Test extracting client IP from X-Forwarded-For header."""
        from app.core.ratelimit import get_client_ip

        # Create mock request with forwarded header
        request = Mock(spec=Request)
        request.headers = {"X-Forwarded-For": "192.168.1.100, 10.0.0.1"}

        ip = get_client_ip(request)
        assert ip == "192.168.1.100"

    def test_get_client_ip_single_forwarded(self):
        """Test single IP in X-Forwarded-For."""
        from app.core.ratelimit import get_client_ip

        request = Mock(spec=Request)
        request.headers = {"X-Forwarded-For": "192.168.1.100"}

        ip = get_client_ip(request)
        assert ip == "192.168.1.100"

    def test_get_client_ip_fallback_to_remote(self):
        """Test fallback to get_remote_address when no X-Forwarded-For."""
        from app.core.ratelimit import get_client_ip

        request = Mock(spec=Request)
        request.headers = {}
        request.client = Mock()
        request.client.host = "10.0.0.5"

        with patch('app.core.ratelimit.get_remote_address', return_value="10.0.0.5"):
            ip = get_client_ip(request)
            assert ip == "10.0.0.5"

    def test_rate_limiter_config_get_limiter_creates_instance(self):
        """Test RateLimiterConfig creates limiter on first call."""
        from app.core.ratelimit import RateLimiterConfig

        # Reset the singleton
        RateLimiterConfig._limiter = None

        with patch('app.core.ratelimit.settings') as mock_settings:
            mock_settings.rate_limit_enabled = True

            limiter = RateLimiterConfig.get_limiter()

            assert limiter is not None
            assert RateLimiterConfig._limiter is limiter

    def test_rate_limiter_config_returns_same_instance(self):
        """Test get_limiter returns cached instance."""
        from app.core.ratelimit import RateLimiterConfig

        RateLimiterConfig._limiter = None

        with patch('app.core.ratelimit.settings') as mock_settings:
            mock_settings.rate_limit_enabled = True

            limiter1 = RateLimiterConfig.get_limiter()
            limiter2 = RateLimiterConfig.get_limiter()

            assert limiter1 is limiter2

    def test_rate_limiter_config_get_limit_returns_string(self):
        """Test get_limit returns proper rate limit string."""
        from app.core.ratelimit import RateLimiterConfig

        with patch('app.core.ratelimit.settings') as mock_settings:
            mock_settings.rate_limit_per_minute = 60

            limit = RateLimiterConfig.get_limit()
            assert limit == "60/minute"

    def test_rate_limit_exceeded_handler_returns_429(self):
        """Test rate limit exceeded handler returns 429 response."""
        from app.core.ratelimit import rate_limit_exceeded_handler

        request = Mock(spec=Request)
        request.client = Mock()
        request.client.host = "192.168.1.1"
        exc = Mock()
        exc.detail = "60/minute"

        response = rate_limit_exceeded_handler(request, exc)

        assert isinstance(response, JSONResponse)
        assert response.status_code == 429
        content = response.body.decode()
        assert "rate_limit_exceeded" in content or "Too many requests" in content

    def test_rate_limit_exceeded_handler_logs_warning(self, caplog):
        """Test that rate limit handler logs warning."""
        from app.core.ratelimit import rate_limit_exceeded_handler

        request = Mock(spec=Request)
        request.client = None  # No client info
        exc = Mock()
        exc.detail = "10/minute"

        with caplog.at_level(logging.WARNING):
            rate_limit_exceeded_handler(request, exc)

        assert len(caplog.records) > 0
        assert "Rate limit exceeded" in caplog.records[-1].message

    def test_limiter_singleton_initialization(self):
        """Test limiter is initialized as singleton."""
        from app.core.ratelimit import limiter

        # limiter should be an instance of Limiter
        assert limiter is not None

    def test_default_limit_string(self):
        """Test default_limit is properly formatted."""
        from app.core.ratelimit import default_limit

        # Should be a string like "X/minute"
        assert isinstance(default_limit, str)
        assert "/minute" in default_limit
