"""
Unit tests for the production-grade reranking service.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import numpy as np
from pathlib import Path


class TestRerankingService:
    """Tests for RerankingService."""

    @pytest.fixture
    def mock_settings(self):
        """Mock settings for testing."""
        with patch('app.services.reranking.reranking_service.settings') as mock:
            mock.embedding_model = "test-model"
            mock.use_reranking = True
            mock.use_llm_reranking = False
            mock.rerank_top_k = 20
            mock.rerank_weights = {
                "semantic": 0.40,
                "keyword": 0.25,
                "original": 0.25,
                "llm": 0.10,
            }
            yield mock

    @pytest.fixture
    def reranker(self, mock_settings):
        """Create a reranking service with mocked model."""
        with patch('app.services.reranking.reranking_service.SentenceTransformer') as mock_st:
            mock_model = Mock()
            mock_model.encode.side_effect = lambda x: np.random.rand(len(x) if isinstance(x, list) else 1, 384).astype('float32')
            mock_st.return_value = mock_model
            from app.services.reranking.reranking_service import RerankingService
            return RerankingService()

    def test_initialization(self, reranker):
        """Test reranking service initialization."""
        assert reranker is not None
        assert reranker.use_llm_scoring is False
        assert reranker.use_reranking is True

    def test_rerank_returns_ranked_items(self, reranker):
        """Test that rerank returns properly ranked items."""
        chunks = [
            {
                "chunk_id": "chunk_1",
                "chunk_text": "This is about machine learning and AI systems.",
                "score": 0.85,
                "file_name": "doc1.txt",
                "page_number": 1,
                "metadata": {"file_name": "doc1.txt", "page_number": 1},
            },
            {
                "chunk_id": "chunk_2",
                "chunk_text": "Python is a programming language for software development.",
                "score": 0.72,
                "file_name": "doc1.txt",
                "page_number": 2,
                "metadata": {"file_name": "doc1.txt", "page_number": 2},
            },
            {
                "chunk_id": "chunk_3",
                "chunk_text": "Data science involves statistics and analysis of data.",
                "score": 0.91,
                "file_name": "doc2.txt",
                "page_number": 1,
                "metadata": {"file_name": "doc2.txt", "page_number": 1},
            },
        ]

        result = reranker.rerank(
            query="machine learning AI",
            chunks=chunks,
            top_k=2,
            return_all=False,
        )

        assert "ranked_items" in result
        assert "top_k_items" in result
        assert "ranking_summary" in result
        assert "signal_scores" in result
        assert "weights_used" in result

        # Should have 3 ranked items (all candidates)
        assert len(result["ranked_items"]) == 3
        # Should have 2 top-k items
        assert len(result["top_k_items"]) == 2

        # Check ranking order
        assert result["ranked_items"][0]["rank"] == 1
        assert result["ranked_items"][1]["rank"] == 2
        assert result["ranked_items"][2]["rank"] == 3

        # Scores should be in descending order
        scores = [item["final_score"] for item in result["ranked_items"]]
        assert scores == sorted(scores, reverse=True)

        # Each item should have all score components
        for item in result["ranked_items"]:
            assert "semantic_score" in item
            assert "keyword_score" in item
            assert "original_score" in item
            assert "final_score" in item
            assert "rank" in item
            # Backward compatibility: 'score' should alias 'final_score'
            assert item["score"] == item["final_score"]

    def test_rerank_all_items(self, reranker):
        """Test rerank with return_all=True."""
        chunks = [
            {
                "chunk_id": f"chunk_{i}",
                "chunk_text": f"Document chunk {i} about various topics.",
                "score": 0.5 + i * 0.1,
                "file_name": "test.txt",
                "page_number": 1,
                "metadata": {},
            }
            for i in range(5)
        ]

        result = reranker.rerank(
            query="test query",
            chunks=chunks,
            top_k=3,
            return_all=True,
        )

        # Should return all 5 items in ranked_items
        assert len(result["ranked_items"]) == 5
        # Should return only top 3 in top_k_items
        assert len(result["top_k_items"]) == 3

    def test_rerank_empty_chunks(self, reranker):
        """Test rerank with empty chunk list."""
        result = reranker.rerank(
            query="test query",
            chunks=[],
            top_k=5,
        )

        assert result["ranked_items"] == []
        assert result["top_k_items"] == []
        assert result["ranking_summary"]["total_candidates"] == 0

    def test_rerank_single_chunk(self, reranker):
        """Test rerank with single chunk."""
        chunks = [
            {
                "chunk_id": "chunk_1",
                "chunk_text": "Single chunk content.",
                "score": 0.85,
                "file_name": "test.txt",
                "page_number": 1,
                "metadata": {},
            }
        ]

        result = reranker.rerank(
            query="test query",
            chunks=chunks,
            top_k=5,
        )

        assert len(result["ranked_items"]) == 1
        assert result["ranked_items"][0]["rank"] == 1
        assert result["ranking_summary"]["total_candidates"] == 1

    def test_rerank_simple_interface(self, reranker):
        """Test the simplified rerank interface."""
        chunks = [
            {
                "chunk_id": "chunk_1",
                "chunk_text": "First chunk about AI and ML.",
                "score": 0.85,
                "file_name": "test.txt",
                "page_number": 1,
                "metadata": {},
            },
            {
                "chunk_id": "chunk_2",
                "chunk_text": "Second chunk about programming.",
                "score": 0.72,
                "file_name": "test.txt",
                "page_number": 2,
                "metadata": {},
            },
        ]

        result = reranker.rerank_simple(
            query="artificial intelligence",
            chunks=chunks,
            top_k=1,
        )

        assert isinstance(result, list)
        assert len(result) == 1
        assert "chunk_id" in result[0]
        assert "final_score" in result[0]

    def test_ranking_summary_statistics(self, reranker):
        """Test that ranking summary contains correct statistics."""
        chunks = [
            {
                "chunk_id": f"chunk_{i}",
                "chunk_text": f"Chunk {i} content.",
                "score": 0.5 + i * 0.1,
                "file_name": "test.txt",
                "page_number": 1,
                "metadata": {},
            }
            for i in range(5)
        ]

        result = reranker.rerank(
            query="test",
            chunks=chunks,
            top_k=3,
        )

        summary = result["ranking_summary"]
        assert summary["total_candidates"] == 5
        assert summary["returned_count"] == 3
        assert summary["max_score"] >= summary["min_score"]
        assert summary["mean_score"] >= 0
        assert "score_std" in summary

    def test_custom_weights(self, reranker):
        """Test rerank with custom weights."""
        chunks = [
            {
                "chunk_id": "chunk_1",
                "chunk_text": "Machine learning content.",
                "score": 0.85,
                "file_name": "test.txt",
                "page_number": 1,
                "metadata": {},
            },
            {
                "chunk_id": "chunk_2",
                "chunk_text": "Deep learning neural networks.",
                "score": 0.92,
                "file_name": "test.txt",
                "page_number": 2,
                "metadata": {},
            },
        ]

        custom_weights = {
            "semantic": 0.60,
            "keyword": 0.20,
            "original": 0.20,
            "llm": 0.0,
        }

        result = reranker.rerank(
            query="neural networks deep learning",
            chunks=chunks,
            top_k=2,
            weights=custom_weights,
        )

        assert result["weights_used"] == custom_weights
        assert len(result["top_k_items"]) == 2

    def test_semantic_score_range(self, reranker):
        """Test that semantic scores are in [0, 1] range."""
        chunks = [
            {
                "chunk_id": "chunk_1",
                "chunk_text": "Test content for semantic scoring.",
                "score": 0.85,
                "file_name": "test.txt",
                "page_number": 1,
                "metadata": {},
            }
        ]

        result = reranker.rerank(
            query="test query",
            chunks=chunks,
            top_k=1,
        )

        for item in result["ranked_items"]:
            assert 0 <= item["semantic_score"] <= 1
            assert 0 <= item["keyword_score"] <= 1
            assert 0 <= item["original_score"] <= 1
            assert 0 <= item["final_score"] <= 1

    def test_rank_assignment_sequential(self, reranker):
        """Test that ranks are assigned sequentially starting from 1."""
        chunks = [
            {
                "chunk_id": f"chunk_{i}",
                "chunk_text": f"Content chunk {i}.",
                "score": 0.5 + i * 0.1,
                "file_name": "test.txt",
                "page_number": 1,
                "metadata": {},
            }
            for i in range(10)
        ]

        result = reranker.rerank(
            query="test",
            chunks=chunks,
            top_k=10,
        )

        ranks = [item["rank"] for item in result["ranked_items"]]
        assert ranks == list(range(1, 11))

    def test_metadata_preserved(self, reranker):
        """Test that metadata is preserved through reranking."""
        chunks = [
            {
                "chunk_id": "chunk_1",
                "chunk_text": "Content with metadata.",
                "score": 0.85,
                "file_name": "document.pdf",
                "page_number": 42,
                "metadata": {"author": "John Doe", "section": "Introduction"},
            }
        ]

        result = reranker.rerank(
            query="test",
            chunks=chunks,
            top_k=1,
        )

        item = result["top_k_items"][0]
        assert item["file_name"] == "document.pdf"
        assert item["page_number"] == 42
        assert item["metadata"]["author"] == "John Doe"
        assert item["metadata"]["section"] == "Introduction"

    def test_rerank_with_llm_disabled(self, reranker):
        """Test that LLM scores are None when LLM scoring is disabled."""
        chunks = [
            {
                "chunk_id": "chunk_1",
                "chunk_text": "Test content.",
                "score": 0.85,
                "file_name": "test.txt",
                "page_number": 1,
                "metadata": {},
            }
        ]

        result = reranker.rerank(
            query="test",
            chunks=chunks,
            top_k=1,
        )

        for item in result["ranked_items"]:
            assert item["llm_relevance_score"] is None

    def test_signal_scores_computed(self, reranker):
        """Test that signal scores are computed and returned."""
        chunks = [
            {
                "chunk_id": f"chunk_{i}",
                "chunk_text": f"Content chunk {i} about various topics and subjects.",
                "score": 0.5 + i * 0.05,
                "file_name": "test.txt",
                "page_number": 1,
                "metadata": {},
            }
            for i in range(3)
        ]

        result = reranker.rerank(
            query="topics and subjects",
            chunks=chunks,
            top_k=2,
        )

        signal_scores = result["signal_scores"]
        assert "semantic" in signal_scores
        assert "keyword" in signal_scores
        assert "original" in signal_scores
        assert "llm" in signal_scores
        assert signal_scores["llm"] is None  # LLM scoring disabled


class TestRerankingServiceDisabled:
    """Tests for RerankingService when reranking is disabled."""

    @pytest.fixture
    def mock_settings_disabled(self):
        """Mock settings with reranking disabled."""
        with patch('app.services.reranking.reranking_service.settings') as mock:
            mock.embedding_model = "test-model"
            mock.use_reranking = False
            mock.use_llm_reranking = False
            yield mock

    @pytest.fixture
    def reranker_disabled(self, mock_settings_disabled):
        """Create a reranking service with reranking disabled."""
        with patch('app.services.reranking.reranking_service.SentenceTransformer') as mock_st:
            mock_model = Mock()
            mock_model.encode.return_value = np.random.rand(1, 384).astype('float32')
            mock_st.return_value = mock_model
            from app.services.reranking.reranking_service import RerankingService
            return RerankingService()

    def test_reranking_disabled_flag(self, reranker_disabled):
        """Test that reranking is disabled when use_reranking is False."""
        assert reranker_disabled.use_reranking is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
