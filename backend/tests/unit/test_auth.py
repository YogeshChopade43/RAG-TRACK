"""
Unit tests for authentication.
"""
import pytest
from unittest.mock import patch, MagicMock
from fastapi import HTTPException, Request
from app.core.auth import get_api_key
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
        # When api_key is None, auth should pass
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