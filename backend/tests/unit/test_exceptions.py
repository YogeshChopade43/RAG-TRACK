"""
Unit tests for custom exception classes.
"""
import pytest
from app.core.exceptions import (
    RAGTrackError,
    IngestionError,
    ParsingError,
    ChunkingError,
    EmbeddingError,
    RetrievalError,
    VectorStoreError,
    LLMError,
    LLMTimeoutError,
    LLMConnectionError,
    LLMEmptyResponseError,
    LLMAuthenticationError,
    ValidationError,
    ConfigurationError,
)


class TestExceptions:
    """Tests for exception classes."""

    def test_base_ragtrack_error(self):
        """Test base RAGTrackError."""
        error = RAGTrackError("Base error")
        assert str(error) == "Base error"
        assert isinstance(error, Exception)

    def test_ingestion_error_with_metadata(self):
        """Test IngestionError with stage and document_id."""
        error = IngestionError(
            message="Failed to parse PDF",
            stage="parsing",
            document_id="doc-123"
        )
        assert error.stage == "parsing"
        assert error.document_id == "doc-123"

    def test_ingestion_error_without_metadata(self):
        """Test IngestionError without optional fields."""
        error = IngestionError("Simple error")
        assert error.stage is None
        assert error.document_id is None

    def test_parsing_error_with_metadata(self):
        """Test ParsingError with filename."""
        error = ParsingError(
            message="Unsupported format",
            document_id="doc-456",
            filename="file.xyz"
        )
        assert error.document_id == "doc-456"
        assert error.filename == "file.xyz"

    def test_chunking_error(self):
        """Test ChunkingError."""
        error = ChunkingError("Chunk failed", document_id="chunk-doc")
        assert error.document_id == "chunk-doc"

    def test_embedding_error(self):
        """Test EmbeddingError."""
        error = EmbeddingError("Model failed", document_id="embed-doc")
        assert error.document_id == "embed-doc"

    def test_retrieval_error(self):
        """Test RetrievalError with query."""
        error = RetrievalError("No results found", query="test query")
        assert error.query == "test query"

    def test_vector_store_error(self):
        """Test VectorStoreError with operation."""
        error = VectorStoreError("Index corrupted", operation="write")
        assert error.operation == "write"

    def test_llm_error_base(self):
        """Test base LLMError."""
        error = LLMError("LLM failed", provider="openai")
        assert error.provider == "openai"

    def test_llm_timeout_error(self):
        """Test LLMTimeoutError with timeout value."""
        error = LLMTimeoutError("Request timed out", timeout_seconds=30)
        assert error.timeout_seconds == 30

    def test_llm_connection_error(self):
        """Test LLMConnectionError with endpoint."""
        error = LLMConnectionError("Connection refused", endpoint="http://localhost:11434")
        assert error.endpoint == "http://localhost:11434"

    def test_llm_empty_response_error_default(self):
        """Test LLMEmptyResponseError with default message."""
        error = LLMEmptyResponseError()
        assert "empty response" in str(error).lower()

    def test_llm_authentication_error_default(self):
        """Test LLMAuthenticationError default message."""
        error = LLMAuthenticationError()
        assert "authentication" in str(error).lower()

    def test_validation_error_with_field(self):
        """Test ValidationError with field info."""
        error = ValidationError(
            "Invalid value",
            field="document_id",
            value="bad-id"
        )
        assert error.field == "document_id"
        assert error.value == "bad-id"

    def test_configuration_error(self):
        """Test ConfigurationError with config key."""
        error = ConfigurationError(
            "Missing API key",
            config_key="OPENAI_API_KEY"
        )
        assert error.config_key == "OPENAI_API_KEY"

    def test_exception_inheritance(self):
        """Test that all exceptions inherit from RAGTrackError."""
        exceptions = [
            IngestionError("e"),
            ParsingError("e"),
            ChunkingError("e"),
            EmbeddingError("e"),
            RetrievalError("e"),
            VectorStoreError("e"),
            LLMError("e"),
            LLMTimeoutError("e"),
            LLMConnectionError("e"),
            LLMEmptyResponseError("e"),
            LLMAuthenticationError("e"),
            ValidationError("e"),
            ConfigurationError("e"),
        ]
        for exc in exceptions:
            assert isinstance(exc, RAGTrackError)
            assert isinstance(exc, Exception)
