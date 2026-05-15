"""
Unit tests for ChunkingService.
"""
import pytest
from unittest.mock import patch
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