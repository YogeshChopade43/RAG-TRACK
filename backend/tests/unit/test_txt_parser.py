"""
Unit tests for TXT parser.
"""
import pytest
import tempfile
import os
from app.services.generic.parsers.txt_parser import parse_txt


class TestTxtParser:
    """Tests for TXT parser."""

    def test_parse_txt_reads_file(self):
        """Test parsing a simple TXT file."""
        content = "This is a test document.\nSecond line."
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(content)
            temp_path = f.name

        try:
            result = parse_txt(temp_path)
            assert isinstance(result, list)
            assert len(result) == 1
            assert "This is a test document" in result[0]["text"]
        finally:
            os.unlink(temp_path)

    def test_parse_txt_handles_unicode(self):
        """Test parsing Unicode characters."""
        content = "Héllo Wörld! 你好"
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write(content)
            temp_path = f.name

        try:
            result = parse_txt(temp_path)
            assert "Héllo" in result[0]["text"]
            assert "你好" in result[0]["text"]
        finally:
            os.unlink(temp_path)

    def test_parse_txt_handles_empty_file(self):
        """Test parsing empty file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("")
            temp_path = f.name

        try:
            result = parse_txt(temp_path)
            assert isinstance(result, list)
        finally:
            os.unlink(temp_path)

    def test_parse_txt_normalizes_whitespace(self):
        """Test that text is normalized."""
        content = "  Extra    spaces    and\n\n\nnewlines   "
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(content)
            temp_path = f.name

        try:
            result = parse_txt(temp_path)
            text = result[0]["text"]
            # Should have normalized spacing
            assert "  " not in text or text.count("  ") < content.count("  ")
        finally:
            os.unlink(temp_path)

    def test_parse_txt_returns_correct_structure(self):
        """Test output structure matches expected format."""
        content = "Simple content"
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(content)
            temp_path = f.name

        try:
            result = parse_txt(temp_path)
            assert len(result) == 1
            assert "page_number" in result[0]
            assert "text" in result[0]
            # Text should be normalized single line
            assert isinstance(result[0]["text"], str)
        finally:
            os.unlink(temp_path)

    def test_parse_txt_handles_encoding_errors(self):
        """Test that parser handles files with encoding issues."""
        # Create file with latin-1 encoding that UTF-8 might struggle with
        content = "Café résumé".encode('latin-1')
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.txt', delete=False) as f:
            f.write(content)
            temp_path = f.name

        try:
            # Should not raise, errors='ignore' handles bad chars
            result = parse_txt(temp_path)
            assert isinstance(result, list)
        except UnicodeDecodeError:
            pytest.fail("parse_txt should handle encoding errors gracefully")
        finally:
            os.unlink(temp_path)
