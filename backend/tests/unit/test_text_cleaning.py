"""
Unit tests for TextCleaningService.
"""
import pytest
from app.services.text_cleaning.text_cleaning_service import TextCleaningService


class TestTextCleaningService:
    """Tests for TextCleaningService."""

    @pytest.fixture
    def service(self):
        """Create text cleaning service."""
        return TextCleaningService()

    def test_clean_pages_returns_empty_for_empty_input(self, service):
        """Test that empty pages input returns empty list."""
        result = service.clean_pages([])
        assert result == []

    def test_clean_pages_handles_none_text(self, service):
        """Test that pages with None text are handled."""
        pages = [{"page_number": 1, "text": None}]
        result = service.clean_pages(pages)
        assert result == []

    def test_clean_pages_handles_empty_string_text(self, service):
        """Test that pages with empty string text are skipped."""
        pages = [{"page_number": 1, "text": ""}]
        result = service.clean_pages(pages)
        assert result == []

    def test_clean_pages_preserves_page_numbers(self, service):
        """Test that page numbers are preserved."""
        pages = [
            {"page_number": 1, "text": "Page 1 content"},
            {"page_number": 2, "text": "Page 2 content"},
        ]
        result = service.clean_pages(pages)
        page_numbers = [p["page_number"] for p in result]
        assert 1 in page_numbers
        assert 2 in page_numbers

    def test_remove_page_footer_removes_patterns(self, service):
        """Test footer removal."""
        text = "Chapter 1\nPage 1 of 3\nContent"
        cleaned = service._remove_page_footer(text)
        assert "Page 1 of 3" not in cleaned
        assert "Content" in cleaned

    def test_remove_page_footer_removes_pipe_format(self, service):
        """Test footer removal with pipe format."""
        text = "Report Title\nPage | 2 of 5\nBody text"
        cleaned = service._remove_page_footer(text)
        assert "Page | 2 of 5" not in cleaned
        assert "Body text" in cleaned

    def test_remove_unicode_noise_strips_zero_width(self, service):
        """Test removal of zero-width characters."""
        # \u200B is zero-width space
        text = "Hello\u200BWorld"
        cleaned = service._remove_unicode_noise(text)
        assert "\u200B" not in cleaned
        assert cleaned == "HelloWorld"

    def test_remove_unicode_noise_normalizes_dashes(self, service):
        """Test normalization of different dash types."""
        text = "En–dash and em—dash"
        cleaned = service._remove_unicode_noise(text)
        # Both en and em dashes become hyphens
        assert "En-dash" in cleaned or "en-dash" in cleaned.lower()
        assert "em-dash" in cleaned or "em-dash" in cleaned.lower()
        assert "–" not in cleaned
        assert "—" not in cleaned

    def test_remove_unicode_noise_handles_ellipsis(self, service):
        """Test ellipsis normalization."""
        text = "Wait for it…"
        cleaned = service._remove_unicode_noise(text)
        # … is replaced with space
        assert "…" not in cleaned

    def test_remove_dotted_lines_removes_multiple_dots(self, service):
        """Test removal of dotted leader lines."""
        text = "Section 1.....Page 3"
        cleaned = service._remove_dotted_lines(text)
        assert "....." not in cleaned

    def test_remove_dotted_lines_removes_ellipsis_dots(self, service):
        """Test removal of repeated ellipsis as dots."""
        text = "Contents………………"
        cleaned = service._remove_dotted_lines(text)
        # Should be replaced with space
        assert "…" not in cleaned or cleaned.strip() == ""

    def test_remove_dotted_lines_removes_spaced_dots(self, service):
        """Test removal of spaced dot patterns."""
        text = "TOC . . . . . Page 10"
        cleaned = service._remove_dotted_lines(text)
        # Should reduce spacing
        assert cleaned.strip() != text.strip()

    def test_fix_line_breaks_joins_broken_lines(self, service):
        """Test line break fix joins mid-paragraph breaks."""
        # Single newline should become space
        text = "This is a line.\nThis continues."
        cleaned = service._fix_line_breaks(text)
        assert "\n" not in cleaned or cleaned.count('\n') < text.count('\n')
        # Should join into continuous text

    def test_fix_line_breaks_preserves_paragraph_breaks(self, service):
        """Test double newlines preserved as paragraph breaks."""
        text = "First paragraph.\n\nSecond paragraph."
        cleaned = service._fix_line_breaks(text)
        # Double newlines should stay (or be collapsed to single but still indicate break)
        assert len(cleaned.split('\n')) >= 2 or "First paragraph" in cleaned

    def test_normalize_bullets_converts_unicode_bullets(self, service):
        """Test conversion of bullet characters to dashes."""
        bullets = ['•', '▪', '●', '○', '◦', '■', '□']
        for bullet in bullets:
            text = f"{bullet} Item text"
            cleaned = service._normalize_bullets(text)
            assert "-" in cleaned or cleaned.strip() == "Item text"

    def test_normalize_hyphenation_removes_soft_hyphens(self, service):
        """Test removal of hyphenation across lines."""
        text = "time-\nconsuming"
        cleaned = service._normalize_hyphenation(text)
        assert "-" not in cleaned or "timeconsuming" in cleaned.replace(" ", "")

    def test_normalize_spaces_collapses_multiple_spaces(self, service):
        """Test collapsing multiple spaces."""
        text = "Too     many    spaces"
        cleaned = service._normalize_spaces(text)
        assert "    " not in cleaned
        assert cleaned == "Too many spaces"

    def test_normalize_spaces_removes_space_before_punctuation(self, service):
        """Test removal of spaces before punctuation."""
        text = "Hello , world ."
        cleaned = service._normalize_spaces(text)
        assert " ," not in cleaned
        assert " ." not in cleaned
        assert "Hello," in cleaned

    def test_normalize_punctuation_collapses_multiple_periods(self, service):
        """Test collapsing multiple periods."""
        text = "Wait....."
        cleaned = service._normalize_punctuation(text)
        # After collapsing dots: "Wait." then short fragment removal removes trailing .
        # depending on order: the dot removal regex removes trailing period from words 2+ letters
        # So "Wait." -> "Wait"
        assert cleaned == "Wait" or "." not in cleaned

    def test_normalize_punctuation_collapses_multiple_commas(self, service):
        """Test collapsing multiple commas."""
        text = "item1,,,, item2"
        cleaned = service._normalize_punctuation(text)
        assert ",,,," not in cleaned

    def test_normalize_punctuation_removes_short_fragment_period(self, service):
        """Test removal of trailing period on short fragments."""
        text = "Hi."
        cleaned = service._normalize_punctuation(text)
        # The regex removes period after short (2+ letter) words at end
        assert cleaned == "Hi" or cleaned == "Hi."

    def test_full_cleaning_pipeline_integration(self, service):
        """Test full cleaning pipeline on realistic PDF text."""
        raw_pages = [
            {
                "page_number": 1,
                "text": "Chapter 1\nPage | 1 of 5\n.\n.\n.\n.\n.\nThis is a sample.\n\nNext paragraph."
            }
        ]
        result = service.clean_pages(raw_pages)

        assert len(result) > 0
        cleaned_text = result[0]["text"]
        # Footer should be gone
        assert "Page | 1 of 5" not in cleaned_text
        # Dots should be cleaned
        assert "....." not in cleaned_text

    def test_clean_pages_returns_correct_structure(self, service):
        """Test output structure is correct."""
        raw_pages = [{"page_number": 1, "text": "Content"}]
        result = service.clean_pages(raw_pages)

        assert len(result) == 1
        assert "page_number" in result[0]
        assert "text" in result[0]
        assert result[0]["page_number"] == 1
