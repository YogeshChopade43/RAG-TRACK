"""
Unit tests for PDF parser.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import json
from app.services.generic.parsers.pdf_parser import parse_pdf


class TestPDFParser:
    """Tests for PDF parser."""

    def test_parse_pdf_handles_valid_pdf(self, tmp_path):
        """Test parsing a well-formed PDF."""
        pdf_path = tmp_path / "test.pdf"
        pdf_path.write_bytes(b"%PDF-1.4\n1 0 obj<</Type/Catalog>>endobj\ntrailer<</Root 1 0 R>>\n%%EOF")

        with patch('app.services.generic.parsers.pdf_parser.pdfplumber') as mock_pdfplumber:
            mock_pdf = MagicMock()
            mock_page = MagicMock()
            mock_page.extract_text.return_value = "This is extracted page text."
            mock_pdf.pages = [mock_page]
            mock_pdfplumber.open.return_value.__enter__ = MagicMock(return_value=mock_pdf)
            mock_pdfplumber.open.return_value.__exit__ = MagicMock(return_value=False)

            result = parse_pdf(str(pdf_path))

            assert isinstance(result, list)
            assert len(result) >= 1

    def test_parse_pdf_normalizes_text(self, tmp_path):
        """Test that extracted text is normalized."""
        pdf_path = tmp_path / "test.pdf"
        pdf_path.write_bytes(b"%PDF-1.4\n1 0 obj\nendobj\ntrailer\n%%EOF")

        with patch('app.services.generic.parsers.pdf_parser.pdfplumber') as mock_pdfplumber:
            mock_pdf = MagicMock()
            mock_page = MagicMock()
            mock_page.extract_text.return_value = "  Too   many    spaces   "
            mock_pdf.pages = [mock_page]
            mock_pdfplumber.open.return_value.__enter__ = MagicMock(return_value=mock_pdf)
            mock_pdfplumber.open.return_value.__exit__ = MagicMock(return_value=False)

            result = parse_pdf(str(pdf_path))
            text = result[0]["text"]
            assert "   " not in text

    def test_parse_pdf_handles_empty_pages(self, tmp_path):
        """Test that error is raised if all pages have no text."""
        pdf_path = tmp_path / "test.pdf"
        pdf_path.write_bytes(b"%PDF-1.4\n1 0 obj\nendobj\ntrailer\n%%EOF")

        with patch('app.services.generic.parsers.pdf_parser.pdfplumber') as mock_pdfplumber:
            mock_pdf = MagicMock()
            mock_page = MagicMock()
            mock_page.extract_text.return_value = "   "  # Only whitespace
            mock_pdf.pages = [mock_page]
            mock_pdfplumber.open.return_value.__enter__ = MagicMock(return_value=mock_pdf)
            mock_pdfplumber.open.return_value.__exit__ = MagicMock(return_value=False)

            with pytest.raises(ValueError, match=r"image-based.*contains no extractable text"):
                parse_pdf(str(pdf_path))

    def test_parse_pdf_raises_on_corrupted_pdf(self, tmp_path):
        """Test error handling for corrupted PDF."""
        pdf_path = tmp_path / "corrupt.pdf"
        pdf_path.write_bytes(b"not a pdf at all")

        with patch('app.services.generic.parsers.pdf_parser.pdfplumber') as mock_pdfplumber:
            mock_pdfplumber.open.side_effect = Exception("PDF structure error")

            with pytest.raises(ValueError, match="Failed to read PDF structure"):
                parse_pdf(str(pdf_path))

    def test_parse_pdf_handles_mixed_pages(self, tmp_path):
        """Test PDF with mix of text and empty pages."""
        pdf_path = tmp_path / "test.pdf"
        pdf_path.write_bytes(b"%PDF-1.4\n1 0 obj\nendobj\ntrailer\n%%EOF")

        with patch('app.services.generic.parsers.pdf_parser.pdfplumber') as mock_pdfplumber:
            mock_pdf = MagicMock()
            mock_page1 = MagicMock()
            mock_page1.extract_text.return_value = "Page 1 with content"
            mock_page2 = MagicMock()
            mock_page2.extract_text.return_value = "   "  # Empty
            mock_page3 = MagicMock()
            mock_page3.extract_text.return_value = "Page 3 content"
            mock_pdf.pages = [mock_page1, mock_page2, mock_page3]
            mock_pdfplumber.open.return_value.__enter__ = MagicMock(return_value=mock_pdf)
            mock_pdfplumber.open.return_value.__exit__ = MagicMock(return_value=False)

            result = parse_pdf(str(pdf_path))
            # Only pages with text
            assert len(result) == 2
            assert result[0]["page_number"] == 1
            assert result[1]["page_number"] == 3

    def test_parse_pdf_page_numbers_start_at_1(self, tmp_path):
        """Test page numbering starts at 1."""
        pdf_path = tmp_path / "test.pdf"
        pdf_path.write_bytes(b"%PDF-1.4\n1 0 obj\nendobj\ntrailer\n%%EOF")

        with patch('app.services.generic.parsers.pdf_parser.pdfplumber') as mock_pdfplumber:
            mock_pdf = MagicMock()
            pages = []
            for i in range(3):
                page = MagicMock()
                page.extract_text.return_value = f"Page {i+1}"
                pages.append(page)
            mock_pdf.pages = pages
            mock_pdfplumber.open.return_value.__enter__ = MagicMock(return_value=mock_pdf)
            mock_pdfplumber.open.return_value.__exit__ = MagicMock(return_value=False)

            result = parse_pdf(str(pdf_path))
            for i, page in enumerate(result):
                assert page["page_number"] == i + 1
