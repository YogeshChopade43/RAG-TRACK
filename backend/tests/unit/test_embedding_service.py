"""
Unit tests for EmbeddingService.
"""
import pytest
from unittest.mock import Mock, patch
import numpy as np
import tempfile
import os
from app.services.embedding.embedding_service import EmbeddingService


class TestEmbeddingService:
    """Tests for EmbeddingService."""

    @pytest.fixture
    def service(self, tmp_path):
        """Create embedding service with mocked model."""
        with patch('app.services.embedding.embedding_service.SentenceTransformer') as mock_st:
            mock_model = Mock()
            mock_model.encode.return_value = np.random.rand(2, 384).astype('float32')
            mock_st.return_value = mock_model

            with patch('app.services.embedding.embedding_service.settings') as mock_settings:
                mock_settings.vector_store_dir = tmp_path
                mock_settings.embedding_model = "test-model"

                yield EmbeddingService()

    @pytest.fixture
    def sample_chunks(self):
        """Sample chunks for testing."""
        return [
            {
                "chunk_id": "test-doc-123_chunk_1",
                "document_id": "test-doc-123",
                "file_name": "test.txt",
                "page_number": 1,
                "chunk_text": "This is a test chunk.",
                "char_start": 0,
                "char_end": 22,
            },
            {
                "chunk_id": "test-doc-123_chunk_2",
                "document_id": "test-doc-123",
                "file_name": "test.txt",
                "page_number": 1,
                "chunk_text": "Another test chunk.",
                "char_start": 23,
                "char_end": 40,
            }
        ]

    def test_embed_returns_expected_structure(self, service, sample_chunks, tmp_path):
        """Test that embed returns expected structure."""
        result = service.embed(sample_chunks)

        assert isinstance(result, dict)
        assert "index_path" in result
        assert "metadata_path" in result
        assert "chunks" in result
        assert result["chunks"] == 2

    def test_embed_handles_empty_chunks(self, service):
        """Test embedding empty chunks list raises ValueError."""
        with pytest.raises(ValueError, match="No chunks provided"):
            service.embed([])

    def test_embed_preserves_order(self, service, sample_chunks):
        """Test that embedding order matches chunk order."""
        result = service.embed(sample_chunks)
        assert result["chunks"] == 2

    def test_embed_saves_metadata_correctly(self, service, sample_chunks, tmp_path):
        """Test that metadata JSON is saved with correct content."""
        service.embed(sample_chunks)

        metadata_file = tmp_path / f"{sample_chunks[0]['document_id']}_metadata.json"
        assert metadata_file.exists()

        import json
        with open(metadata_file, 'r') as f:
            metadata = json.load(f)

        assert len(metadata) == 2
        assert metadata[0]["chunk_id"] == "test-doc-123_chunk_1"

    def test_get_embedding_model_returns_singleton(self):
        """Test that get_embedding_model returns cached instance."""
        from app.services.embedding.embedding_service import get_embedding_model

        with patch('app.services.embedding.embedding_service.SentenceTransformer') as mock_st:
            mock_model = Mock()
            mock_st.return_value = mock_model

            with patch('app.services.embedding.embedding_service.settings') as mock_settings:
                mock_settings.embedding_model = "test-model"

                # Clear cache first
                get_embedding_model.cache_clear()
                model1 = get_embedding_model()
                model2 = get_embedding_model()
                assert model1 is model2
                mock_st.assert_called_once()

    def test_embedding_service_repr(self, service):
        """Test __repr__ string."""
        repr_str = repr(service)
        assert "EmbeddingService" in repr_str
        assert "test-model" in repr_str or "dummy" in repr_str.lower()
