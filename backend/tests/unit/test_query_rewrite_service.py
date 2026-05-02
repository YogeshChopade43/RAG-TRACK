"""
Unit tests for QueryRewriteService.
"""

import pytest
from unittest.mock import patch, MagicMock

from app.services.query.query_rewrite.query_rewrite_service import QueryRewriteService


class TestQueryRewriteService:
    """Tests for QueryRewriteService."""

    @pytest.fixture
    def service(self):
        """Create service with mocked LLM."""
        with patch(
            "app.services.query.query_rewrite.query_rewrite_service.get_llm_service"
        ) as mock_get_llm:
            mock_instance = MagicMock()
            mock_instance.chat.return_value = "transformed query"
            mock_get_llm.return_value = mock_instance
            service = QueryRewriteService()
            service.llm = mock_instance
            return service

    def test_short_query_should_rewrite(self, service):
        """Test short queries should be rewritten."""
        # Queries with <= 3 words should be rewritten
        assert service.should_rewrite("What is AI?") is True
        assert service.should_rewrite("Tell me") is True

    def test_pronoun_query_should_rewrite(self, service):
        """Test queries with pronouns should be rewritten."""
        assert service.should_rewrite("What does it do?") is True
        assert service.should_rewrite("His method was") is True

    def test_conversational_query_should_rewrite(self, service):
        """Test conversational queries should be rewritten."""
        assert service.should_rewrite("Tell me about the project") is True
        assert service.should_rewrite("Can you explain it?") is True

    def test_clear_query_should_not_rewrite(self, service):
        """Test clear keyword queries should not be rewritten."""
        assert service.should_rewrite("machine learning neural networks") is False

    def test_clean_output_removes_quotes(self, service):
        """Test output cleaning removes quotes."""
        result = service._clean_output('"search query"')
        assert result == "search query"

    def test_clean_output_removes_prefix(self, service):
        """Test output cleaning removes query prefix."""
        result = service._clean_output("Query: original question")
        assert result == "original question"

    def test_rewrite_calls_llm(self, service):
        """Test rewrite calls LLM for complex queries."""
        result = service.rewrite("What does the document say about machine learning?")
        service.llm.chat.assert_called()
        assert result is not None

    def test_rewrite_falls_back_on_error(self, service):
        """Test rewrite falls back to original on error."""
        service.llm.chat.side_effect = Exception("API error")
        result = service.rewrite("What does it say?")
        assert result is not None
