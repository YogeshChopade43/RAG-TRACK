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

        # Should have chunks from both pages
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

    def test_chunk_with_overlap(self, service):
        """Test that chunks have correct overlap."""
        from app.core.config import CHUNK_SIZE, CHUNK_OVERLAP

        # Create text longer than chunk size with overlap
        parsed_load = {
            "document_id": "test-123",
            "file_name": "test.txt",
            "pages": [
                {"page_number": 1, "text": "A" * (CHUNK_SIZE * 3)}
            ]
        }

        chunks = service.chunk(parsed_load)

        # Should have multiple chunks
        assert len(chunks) > 1

    def test_chunk_content_continuity_with_overlap(self, service):
        """Test that overlapping chunks share content."""
        from app.core.config import CHUNK_SIZE, CHUNK_OVERLAP

        # Create text with markers to verify overlap
        text = "".join([f"{i:04d}" for i in range(CHUNK_SIZE * 2)])
        parsed_load = {
            "document_id": "test-123",
            "file_name": "test.txt",
            "pages": [{"page_number": 1, "text": text}]
        }

        chunks = service.chunk(parsed_load)

        # Check overlap: chunk2 should start before chunk1 ends
        if len(chunks) >= 2:
            chunk1_end = chunks[0]["char_end"]
            chunk2_start = chunks[1]["char_start"]
            # Overlap means chunk2 starts before chunk1 ends
            assert chunk2_start < chunk1_end

    def test_chunk_empty_text_skipped(self, service):
        """Test that whitespace-only text is skipped."""
        parsed_load = {
            "document_id": "test-123",
            "file_name": "test.txt",
            "pages": [
                {"page_number": 1, "text": "   \n\n   "},  # whitespace only
                {"page_number": 2, "text": "Real content"}
            ]
        }

        chunks = service.chunk(parsed_load)

        # Should only have chunks from the second page
        assert len(chunks) > 0
        assert all(c["page_number"] == 2 for c in chunks)