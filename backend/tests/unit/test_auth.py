"""
Unit tests for authentication.
"""
import pytest
from unittest.mock import patch, MagicMock
from fastapi import HTTPException, Request
from app.core.auth import get_api_key, is_token_blacklisted, add_token_to_blacklist
from app.core.config import settings


class TestAuth:
    """Tests for API authentication."""

    @pytest.fixture
    def mock_request(self):
        """Create a mock request object."""
        return MagicMock(spec=Request)

    @pytest.mark.asyncio
    async def test_auth_disabled_in_dev_mode(self, mock_request):
        """Test auth is skipped when no API key configured."""
        with patch.object(settings, "api_key", None):
            result = await get_api_key(mock_request, api_key=None)
            assert result == "dev-mode"

    @pytest.mark.asyncio
    async def test_auth_fails_without_header(self, mock_request):
        """Test auth fails when API key header is missing."""
        with patch.object(settings, "api_key", "test-key-123"):
            with pytest.raises(HTTPException) as exc_info:
                await get_api_key(mock_request, api_key=None)
            assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_auth_fails_with_wrong_key(self, mock_request):
        """Test auth fails with invalid API key."""
        with patch.object(settings, "api_key", "test-key-123"):
            with pytest.raises(HTTPException) as exc_info:
                await get_api_key(mock_request, api_key="wrong-key")
            assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_auth_succeeds_with_valid_key(self, mock_request):
        """Test auth succeeds with valid API key."""
        with patch.object(settings, "api_key", "test-key-123"):
            result = await get_api_key(mock_request, api_key="test-key-123")
            assert result == "test-key-123"


class TestTokenBlacklist:
    """Tests for token blacklist functionality."""

    def test_add_token_to_blacklist(self):
        """Test adding token to blacklist."""
        test_token = "test-token-123"
        add_token_to_blacklist(test_token)
        assert is_token_blacklisted(test_token) is True


class TestSecurity:
    """Tests for security utilities."""

    def test_jwt_token_creation(self):
        """Test JWT token creation."""
        from app.core.security import create_access_token, decode_token

        data = {"sub": "user-123"}
        token = create_access_token(data)

        payload = decode_token(token)
        assert payload["sub"] == "user-123"
        assert payload["type"] == "access"

    def test_jwt_refresh_token(self):
        """Test JWT refresh token creation."""
        from app.core.security import create_refresh_token, decode_token

        data = {"sub": "user-123"}
        token = create_refresh_token(data)

        payload = decode_token(token)
        assert payload["sub"] == "user-123"
        assert payload["type"] == "refresh"