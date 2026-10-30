"""
Unit tests for ChunkingService.
"""
from unittest.mock import patch

import pytest

from app.services.chunking.chunking_service import ChunkingService


class TestChunkingService:
    """Tests for ChunkingService."""

    @pytest.fixture
    def service(self):
        """Create chunking service."""
        return ChunkingService()

    def test_chunk_returns_list(self, service):
        """Test that chunk returns a list."""
        parsed_load = {
            "document_id": "test-123",
            "file_name": "test.txt",
            "pages": [
                {"page_number": 1, "text": "A" * 100}
            ]
        }

        result = service.chunk(parsed_load)

        assert isinstance(result, list)
        assert len(result) > 0

    def test_chunk_preserves_page_numbers(self, service):
        """Test that page numbers are preserved."""
        parsed_load = {
            "document_id": "test-123",
            "file_name": "test.txt",
            "pages": [
                {"page_number": 1, "text": "A" * 600},
                {"page_number": 2, "text": "B" * 600}
            ]
        }

        chunks = service.chunk(parsed_load)

        page_numbers = {chunk["page_number"] for chunk in chunks}
        assert 1 in page_numbers
        assert 2 in page_numbers

    def test_chunk_includes_metadata(self, service):
        """Test that chunks include required metadata."""
        parsed_load = {
            "document_id": "test-123",
            "file_name": "test.txt",
            "pages": [
                {"page_number": 1, "text": "Test content here."}
            ]
        }

        chunks = service.chunk(parsed_load)

        assert len(chunks) > 0
        chunk = chunks[0]
        assert "chunk_id" in chunk
        assert "document_id" in chunk
        assert "file_name" in chunk
        assert "page_number" in chunk
        assert "chunk_text" in chunk
        assert "char_start" in chunk
        assert "char_end" in chunk

    def test_empty_pages_raises_error(self, service):
        """Test that empty pages raise ValueError."""
        parsed_load = {
            "document_id": "test-123",
            "file_name": "test.txt",
            "pages": []
        }

        with pytest.raises(ValueError, match="No pages found"):
            service.chunk(parsed_load)

    def test_chunk_with_invalid_chunk_size_config(self):
        """Test that invalid CHUNK_SIZE raises error."""
        with patch('app.services.chunking.chunking_service.CHUNK_SIZE', 0):
            service = ChunkingService()

            parsed_load = {
                "document_id": "test-123",
                "file_name": "test.txt",
                "pages": [{"page_number": 1, "text": "A" * 100}]
            }

            with pytest.raises(ValueError, match="CHUNK_SIZE must be positive"):
                service.chunk(parsed_load)

    def test_chunk_respects_sentence_boundaries(self, service):
        """Test that chunks end at sentence boundaries."""
        text = "This is sentence one. This is sentence two. This is sentence three!"
        parsed_load = {
            "document_id": "test-123",
            "file_name": "test.txt",
            "pages": [{"page_number": 1, "text": text}]
        }

        chunks = service.chunk(parsed_load)

        for chunk in chunks:
            chunk_text = chunk["chunk_text"]
            if len(chunk_text) >= 20:
                assert chunk_text.rstrip().endswith('.') or chunk_text.rstrip().endswith('!')

    def test_chunk_with_overlap(self, service):
        """Test that chunks maintain overlap context."""
        text = "A" * 200 + ". " + "B" * 200 + ". " + "C" * 200 + "."
        parsed_load = {
            "document_id": "test-123",
            "file_name": "test.txt",
            "pages": [{"page_number": 1, "text": text}]
        }

        chunks = service.chunk(parsed_load)

        assert len(chunks) > 1

    def test_chunk_empty_text_skipped(self, service):
        """Test that whitespace-only text is skipped."""
        parsed_load = {
            "document_id": "test-123",
            "file_name": "test.txt",
            "pages": [
                {"page_number": 1, "text": "   \n\n   "},
                {"page_number": 2, "text": "Real content."}
            ]
        }

        chunks = service.chunk(parsed_load)

        assert len(chunks) > 0
        assert all(c["page_number"] == 2 for c in chunks)

    def test_custom_chunk_size(self):
        """Test service with custom chunk size."""
        service = ChunkingService(chunk_size=100, chunk_overlap=25)

        parsed_load = {
            "document_id": "test-123",
            "file_name": "test.txt",
            "pages": [{"page_number": 1, "text": "Test content for chunking."}]
        }

        chunks = service.chunk(parsed_load)
        assert len(chunks) > 0


def _load(text, source="text"):
    return {"document_id": "d", "file_name": "f.pdf", "pages": [{"page_number": 1, "text": text, "source": source}]}


def test_markdown_headings_build_hierarchy():
    chunks = ChunkingService(chunk_size=500).chunk(_load("# Experience\n\n## Acme Corp\n\nBuilt RAG systems."))
    body = [c for c in chunks if "Built RAG" in c["chunk_text"]][0]
    assert body["heading_hierarchy"] == ["Experience", "Acme Corp"]


TABLE = "| Name | Score |\n| --- | --- |\n" + "".join(f"| row{i} | {i} |\n" for i in range(40))


def test_table_is_its_own_chunk_and_never_split_mid_row():
    chunks = ChunkingService(chunk_size=200, chunk_overlap=20).chunk(_load("Intro text.\n\n" + TABLE))
    tables = [c for c in chunks if c["structural_type"] == "table"]
    assert len(tables) > 1
    for c in tables:
        lines = c["chunk_text"].splitlines()
        assert lines[0] == "| Name | Score |" and lines[1] == "| --- | --- |"
        assert all(line.startswith("|") and line.endswith("|") for line in lines)
    assert "Intro text." not in "".join(c["chunk_text"] for c in tables)
    rows = [line for c in tables for line in c["chunk_text"].splitlines()[2:]]
    assert rows == [f"| row{i} | {i} |" for i in range(40)]


def test_single_row_longer_than_chunk_size_is_kept_whole():
    long_row = "| " + "x" * 300 + " | 1 |"
    chunks = ChunkingService(chunk_size=100, chunk_overlap=10).chunk(_load("| A | B |\n| --- | --- |\n" + long_row))
    assert any(long_row in c["chunk_text"] for c in chunks)


def test_ocr_flag_follows_page_source():
    assert all(c["ocr"] for c in ChunkingService().chunk(_load("Scanned text here.", "ocr")))
    txt = {"document_id": "d", "file_name": "f.txt", "pages": [{"page_number": None, "text": "Plain."}]}
    assert not any(c["ocr"] for c in ChunkingService().chunk(txt))


def test_markdown_list_without_punctuation_is_split_into_sized_chunks():
    items = "\n".join(f"- Skill number {i} with some detail" for i in range(60))
    service = ChunkingService(chunk_size=350, chunk_overlap=50)
    chunks = service.chunk(_load("## Skills\n\n" + items))
    assert len(chunks) > 1
    assert all(len(c["chunk_text"]) <= service.chunk_size for c in chunks)
    assert all(c["heading_hierarchy"] == ["Skills"] for c in chunks)
    assert "Skill number 59 with some detail" in chunks[-1]["chunk_text"]
