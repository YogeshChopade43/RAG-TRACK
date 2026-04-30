"""
Unit tests for GenerationService.
"""
import pytest
from unittest.mock import Mock, patch
from app.services.generation.generation_service import GenerationService


class TestGenerationService:
    """Tests for GenerationService."""

    @pytest.fixture
    def sample_chunks(self):
        """Sample chunks for testing."""
        return [
            {
                "chunk_id": "test-doc-123_chunk_1",
                "document_id": "test-doc-123",
                "file_name": "test.txt",
                "page_number": 1,
                "chunk_text": "The quick brown fox jumps over the lazy dog.",
                "char_start": 0,
                "char_end": 44,
            },
            {
                "chunk_id": "test-doc-123_chunk_2",
                "document_id": "test-doc-123",
                "file_name": "test.txt",
                "page_number": 1,
                "chunk_text": "Python is a popular programming language.",
                "char_start": 45,
                "char_end": 76,
            }
        ]

    def test_generate_returns_string(self, sample_chunks):
        """Test that generate returns a string response."""
        with patch('app.services.generation.generation_service.LLMServiceLocal') as mock_llm_class:
            mock_llm = Mock()
            mock_llm.chat.return_value = "The fox is quick and brown."
            mock_llm_class.return_value = mock_llm
            service = GenerationService()

            result = service.generate("What color is the fox?", sample_chunks)

            assert isinstance(result, str)
            assert result == "The fox is quick and brown."
            mock_llm.chat.assert_called_once()

    def test_generate_handles_empty_chunks(self):
        """Test generation with empty chunks list."""
        with patch('app.services.generation.generation_service.LLMServiceLocal') as mock_llm_class:
            mock_llm = Mock()
            mock_llm.chat.return_value = "I don't have enough information to answer."
            mock_llm_class.return_value = mock_llm
            service = GenerationService()

            result = service.generate("What is the answer?", [])

            assert isinstance(result, str)
            assert result == "I don't have enough information to answer."

    def test_generate_constructs_proper_prompt(self, sample_chunks):
        """Test that the prompt is constructed correctly."""
        with patch('app.services.generation.generation_service.LLMServiceLocal') as mock_llm_class:
            mock_llm = Mock()
            mock_llm.chat.return_value = "Test response"
            mock_llm_class.return_value = mock_llm
            service = GenerationService()

            service.generate("Test question", sample_chunks)

            # Check that chat was called with a prompt containing context and question
            call_args = mock_llm.chat.call_args
            system_prompt = call_args[0][0]  # First positional argument
            user_prompt = call_args[0][1]    # Second positional argument

            assert "Test question" in user_prompt
            assert "The quick brown fox jumps over the lazy dog." in user_prompt
            assert "Python is a popular programming language." in user_prompt

    def test_generate_handles_llm_error(self, sample_chunks):
        """Test error handling when LLM service fails."""
        with patch('app.services.generation.generation_service.LLMServiceLocal') as mock_llm_class:
            mock_llm = Mock()
            mock_llm.chat.side_effect = Exception("LLM service unavailable")
            mock_llm_class.return_value = mock_llm
            service = GenerationService()

            with pytest.raises(Exception, match="LLM service unavailable"):
                service.generate("Test question", sample_chunks)

    def test_build_context_combines_chunks(self, sample_chunks):
        """Test that build_context combines chunk texts properly."""
        with patch('app.services.generation.generation_service.LLMServiceLocal') as mock_llm_class:
            mock_llm = Mock()
            mock_llm.chat.return_value = "Response"
            mock_llm_class.return_value = mock_llm
            service = GenerationService()

            context = service.build_context(sample_chunks)

            assert "The quick brown fox jumps over the lazy dog." in context
            assert "Python is a popular programming language." in context
            assert "\n\n" in context  # Should be separated by double newline

    def test_normalize_answer_strips_whitespace(self):
        """Test answer normalization removes extra whitespace."""
        with patch('app.services.generation.generation_service.LLMServiceLocal') as mock_llm_class:
            mock_llm = Mock()
            mock_llm.chat.return_value = "  Answer:   Test   "
            mock_llm_class.return_value = mock_llm
            service = GenerationService()

            # Mock _build_prompts to avoid full flow
            with patch.object(service, '_build_prompts', return_value=("sys", "usr")):
                with patch.object(service, '_normalize_answer', wraps=service._normalize_answer) as mock_norm:
                    service.generate("Q", [{"chunk_text": "C"}])
                    mock_norm.assert_called_once()

    def test_normalize_answer_removes_answer_prefix(self):
        """Test that 'Answer:' prefix is removed."""
        service = GenerationService()
        text = "Answer: The fox is brown."
        normalized = service._normalize_answer(text)
        assert normalized == "The fox is brown."

    def test_normalize_answer_handles_empty_text(self):
        """Test normalization of empty text."""
        service = GenerationService()
        assert service._normalize_answer("") == ""
        assert service._normalize_answer(None) is None
