"""
Unit tests for RetrievalService.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import numpy as np
import faiss
import json
import tempfile
from pathlib import Path


class TestRetrievalService:
    """Tests for RetrievalService."""

    @pytest.fixture
    def service(self, tmp_path):
        """Create retrieval service with mocked model."""
        with patch('app.services.retrieval.retrieval_service.SentenceTransformer') as mock_st:
            mock_model = Mock()
            # Return a 384-dim embedding
            mock_model.encode.return_value = np.random.rand(384).astype('float32')
            mock_st.return_value = mock_model

            with patch('app.services.retrieval.retrieval_service.settings') as mock_settings:
                mock_settings.embedding_model = "test-model"
                mock_settings.vector_store_dir = tmp_path

                from app.services.retrieval.retrieval_service import RetrievalService
                svc = RetrievalService()
                return svc

    @pytest.fixture
    def sample_index_and_metadata(self, tmp_path):
        """Create a real FAISS index and metadata for testing."""
        dim = 384
        index = faiss.IndexFlatL2(dim)
        vectors = np.random.rand(2, dim).astype('float32')
        index.add(vectors)

        document_id = "test-doc-123"
        metadata = [
            {
                "chunk_id": "test-doc-123_chunk_1",
                "document_id": document_id,
                "file_name": "test.txt",
                "page_number": 1,
                "chunk_text": "First test chunk",
                "char_start": 0,
                "char_end": 16
            },
            {
                "chunk_id": "test-doc-123_chunk_2",
                "document_id": document_id,
                "file_name": "test.txt",
                "page_number": 1,
                "chunk_text": "Second test chunk",
                "char_start": 17,
                "char_end": 33
            }
        ]

        index_path = tmp_path / f"{document_id}.index"
        metadata_path = tmp_path / f"{document_id}_metadata.json"

        faiss.write_index(index, str(index_path))
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f)

        return document_id, index_path, metadata_path

    def test_search_returns_matches_with_scores(self, service, sample_index_and_metadata, tmp_path):
        """Test that search returns matches with proper scores."""
        document_id, index_path, metadata_path = sample_index_and_metadata

        result = service.search(document_id, "test query", top_k=2)

        assert isinstance(result, dict)
        assert "matches" in result
        assert len(result["matches"]) == 2
        match1 = result["matches"][0]
        assert "score" in match1
        assert 0 <= match1["score"] <= 1

    def test_search_handles_no_results(self, service, tmp_path):
        """Test search when no index exists returns empty."""
        document_id = "empty-doc"
        # Ensure no files
        result = service.search(document_id, "test query")
        assert result["matches"] == []
        assert "message" in result

    def test_search_handles_missing_index_file(self, service, tmp_path):
        """Test handling when index file is missing."""
        document_id = "no-index-doc"
        result = service.search(document_id, "test query")
        assert result["matches"] == []

    def test_search_respects_top_k_limit(self, service, sample_index_and_metadata):
        """Test that search respects the top_k parameter."""
        document_id, _, _ = sample_index_and_metadata
        result = service.search(document_id, "test", top_k=1)
        assert len(result["matches"]) == 1

    def test_retrieval_service_initialization(self):
        """Test service instance creation."""
        with patch('app.services.retrieval.retrieval_service.settings') as mock_settings:
            mock_settings.embedding_model = "test-model"
            mock_settings.vector_store_dir = MagicMock()
            with patch('app.services.retrieval.retrieval_service.SentenceTransformer') as mock_st:
                mock_st.return_value = Mock()
                from app.services.retrieval.retrieval_service import RetrievalService
                svc = RetrievalService()
                assert svc is not None

    def test_search_handles_invalid_dimensions(self, service, tmp_path):
        """Test search with mismatched embedding dimensions."""
        # Create index with wrong dim
        document_id = "bad-dim"
        bad_index = faiss.IndexFlatL2(100)
        index_path = tmp_path / f"{document_id}.index"
        faiss.write_index(bad_index, str(index_path))
        # Create empty metadata
        metadata_path = tmp_path / f"{document_id}_metadata.json"
        with open(metadata_path, 'w') as f:
            json.dump([], f)

        # Search should handle error gracefully
        result = service.search(document_id, "test")
        # Should return empty or some error indication
        assert "matches" in result
