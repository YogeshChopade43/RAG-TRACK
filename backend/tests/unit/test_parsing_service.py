"""
Unit tests for ParsingService.
"""
from unittest.mock import patch

import pytest

from app.services.parsing.parsing_service import ParsingService


class TestParsingService:
    """Tests for ParsingService."""

    @pytest.fixture
    def service(self):
        """Create parsing service."""
        return ParsingService()

    def test_parse_handles_empty_document(self, service):
        """Test parsing document with no files."""
        with patch('os.path.isdir', return_value=True):
            with patch('os.listdir', return_value=[]):
                with pytest.raises(ValueError, match="No files found for document"):
                    service.parse("test-doc-123")

    def test_parse_raises_error_on_unsupported_file_type(self, service):
        """Test that unsupported file types raise ValueError."""
        with patch('os.path.isdir', return_value=True):
            with patch('os.listdir', return_value=['test.exe']):
                with pytest.raises(ValueError, match="Unsupported source type"):
                    service.parse("test-doc-123")

    def test_parse_handles_missing_raw_directory(self, service):
        """Test parsing when raw document directory doesn't exist."""
        with patch('os.path.isdir', return_value=False):
            with pytest.raises(ValueError, match="Raw document directory not found"):
                service.parse("test-doc-123")

    def test_parse_service_initialization(self, service):
        """Test that the parsing service initializes correctly."""
        assert service is not None
        assert hasattr(service, 'parse')
        assert callable(service.parse)

    def test_parse_txt_success(self, service):
        """Test successful parsing of a text file."""
        document_id = "test-txt-doc-123"
        import shutil

        from app.core.config import settings

        raw_dir = settings.raw_dir / document_id
        raw_dir.mkdir(parents=True, exist_ok=True)
        txt_file = raw_dir / "document.txt"
        txt_file.write_text("This is a test document.\nSecond line.")

        parsed_dir = settings.parsed_dir
        parsed_dir.mkdir(parents=True, exist_ok=True)

        try:
            result = service.parse(document_id)
            assert "file_name" in result
            assert result["file_name"].endswith(".txt")
            assert "pages" in result
            assert len(result["pages"]) > 0
            # Check that a metadata file was written
            metadata_files = list(parsed_dir.glob("*.json"))
            assert len(metadata_files) > 0
        finally:
            if raw_dir.exists():
                shutil.rmtree(raw_dir)
            # Clean parsed files matching document_id
            parsed_file = parsed_dir / f"{document_id}.json"
            if parsed_file.exists():
                parsed_file.unlink()

    def test_parse_handles_empty_text_file(self, service):
        """Test parsing a text file with only whitespace."""
        document_id = "empty-doc-456"
        import shutil

        from app.core.config import settings

        raw_dir = settings.raw_dir / document_id
        raw_dir.mkdir(parents=True, exist_ok=True)
        (raw_dir / "empty.txt").write_text("   \n\n   ")

        parsed_dir = settings.parsed_dir
        parsed_dir.mkdir(parents=True, exist_ok=True)

        try:
            result = service.parse(document_id)
            assert "pages" in result
        finally:
            if raw_dir.exists():
                shutil.rmtree(raw_dir)
            parsed_file = parsed_dir / f"{document_id}.json"
            if parsed_file.exists():
                parsed_file.unlink()


DOCLING_PAGES = [{"page_number": None, "text": "# Charter\n\n| A | B |\n| --- | --- |", "source": "text"}]


def test_docx_dispatches_to_docling_and_keeps_markdown(tmp_path):
    import json

    raw = tmp_path / "raw" / "doc-1"
    raw.mkdir(parents=True)
    (raw / "plan.docx").write_bytes(b"x")
    with patch("app.services.parsing.parsing_service.RAW_BASE", tmp_path / "raw"), \
         patch("app.services.parsing.parsing_service.PARSED_BASE", tmp_path / "parsed"), \
         patch("app.services.parsing.parsing_service.parse_with_docling", return_value=DOCLING_PAGES) as dl:
        out = ParsingService().parse("doc-1")
    assert dl.call_args.args[1] == "docx"
    assert "| --- | --- |" in out["pages"][0]["text"].splitlines()
    written = json.loads((tmp_path / "parsed" / "doc-1.json").read_text(encoding="utf-8"))
    assert written["pages"][0]["source"] == "text"


def test_txt_still_uses_txt_parser(tmp_path):
    raw = tmp_path / "raw" / "doc-2"
    raw.mkdir(parents=True)
    (raw / "notes.txt").write_text("Plain notes here.", encoding="utf-8")
    with patch("app.services.parsing.parsing_service.RAW_BASE", tmp_path / "raw"), \
         patch("app.services.parsing.parsing_service.PARSED_BASE", tmp_path / "parsed"), \
         patch("app.services.parsing.parsing_service.parse_with_docling") as dl:
        out = ParsingService().parse("doc-2")
    dl.assert_not_called()
    assert out["pages"][0]["text"] == "Plain notes here"  # cleaner drops a trailing period, as before
