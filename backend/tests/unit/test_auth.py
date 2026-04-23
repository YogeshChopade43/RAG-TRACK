"""
Unit tests for authentication.
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi import HTTPException

from app.core.auth import get_api_key
from app.core.config import settings


class TestAuth:
    """Tests for API authentication."""

    def test_auth_disabled_in_dev_mode(self):
        """Test auth is skipped when no API key configured."""
        # When api_key is None, auth should pass
        with patch.object(settings, "api_key", None):
            result = get_api_key(api_key=None)
            assert result == "dev-mode"

    def test_auth_fails_without_header(self):
        """Test auth fails when API key header is missing."""
        with patch.object(settings, "api_key", "test-key-123"):
            with pytest.raises(HTTPException) as exc_info:
                get_api_key(api_key=None)
            assert exc_info.value.status_code == 401

    def test_auth_fails_with_wrong_key(self):
        """Test auth fails with invalid API key."""
        with patch.object(settings, "api_key", "test-key-123"):
            with pytest.raises(HTTPException) as exc_info:
                get_api_key(api_key="wrong-key")
            assert exc_info.value.status_code == 403

    def test_auth_succeeds_with_valid_key(self):
        """Test auth succeeds with valid API key."""
        with patch.object(settings, "api_key", "test-key-123"):
            result = get_api_key(api_key="test-key-123")
            assert result == "test-key-123"
