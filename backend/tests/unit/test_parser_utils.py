"""
Unit tests for parser utility functions.
"""
import pytest
import logging
from app.services.generic.utils.parser_utils import (
    normalize_text,
    normalize_pages,
    get_page_text,
)


class TestParserUtils:
    """Tests for parser utility functions."""

    def test_normalize_text_collapses_whitespace(self):
        """Test that normalize_text collapses multiple spaces and newlines."""
        text = "  Hello   \n\n  World  "
        result = normalize_text(text)
        assert result == "Hello World"

    def test_normalize_text_handles_tabs(self):
        """Test that tabs are normalized to spaces."""
        text = "Hello\t\tWorld"
        result = normalize_text(text)
        assert "\t" not in result
        assert result == "Hello World"

    def test_normalize_text_strips_leading_trailing(self):
        """Test that leading/trailing whitespace is removed."""
        text = "   Centered text   "
        result = normalize_text(text)
        assert result == "Centered text"

    def test_normalize_text_handles_multiple_newlines(self):
        """Test that multiple newlines become single spaces."""
        text = "Line1\n\n\n\nLine2"
        result = normalize_text(text)
        assert "\n" not in result
        assert "Line1" in result and "Line2" in result

    def test_normalize_text_returns_empty_for_empty_input(self):
        """Test empty string input."""
        assert normalize_text("") == ""
        assert normalize_text("   ") == ""

    def test_normalize_pages_with_strings(self):
        """Test normalize_pages with plain strings returns them as-is."""
        pages = ["Page 1", "Page 2"]
        result = normalize_pages(pages)
        assert result == ["Page 1", "Page 2"]

    def test_normalize_pages_with_bytes(self):
        """Test normalize_pages decodes bytes."""
        pages = [b"Hello bytes", b"World"]
        result = normalize_pages(pages)
        assert result == ["Hello bytes", "World"]
        assert all(isinstance(s, str) for s in result)

    def test_normalize_pages_handles_mixed_types(self):
        """Test normalize_pages handles mixed input."""
        pages = ["String", b"Bytes", 123]
        result = normalize_pages(pages)
        assert len(result) == 3
        assert result[0] == "String"
        assert result[1] == "Bytes"
        assert "123" in result[2]

    def test_get_page_text_combines_pages(self):
        """Test get_page_text combines all page texts."""
        pages = [
            {"text": "First page content"},
            {"text": "Second page content"},
        ]
        result = get_page_text(pages)
        assert "First page" in result
        assert "Second page" in result

    def test_get_page_text_joins_with_spaces(self):
        """Test pages are joined with spaces."""
        pages = [{"text": "Page1"}, {"text": "Page2"}]
        result = get_page_text(pages)
        assert result == "Page1 Page2"

    def test_get_page_text_handles_empty_pages(self):
        """Test get_page_text with empty list."""
        result = get_page_text([])
        assert result == ""

    def test_get_page_text_logs_combined_text(self, caplog):
        """Test that combined text is logged."""
        with caplog.at_level(logging.DEBUG):
            pages = [{"text": "Some content here"}]
            get_page_text(pages)
        # Should log debug message
        assert any("Combined text" in record.message for record in caplog.records)
