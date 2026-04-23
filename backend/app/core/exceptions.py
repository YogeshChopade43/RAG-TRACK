"""
Custom exception classes for RAG-TRACK application.

Provides specific exception types for different error scenarios
to enable precise error handling and appropriate HTTP status codes.
"""


class RAGTrackError(Exception):
    """Base exception for all RAG-TRACK errors."""

    pass


class IngestionError(RAGTrackError):
    """Raised when document ingestion fails."""

    def __init__(self, message: str, stage: str = None, document_id: str = None):
        super().__init__(message)
        self.stage = stage
        self.document_id = document_id


class ParsingError(RAGTrackError):
    """Raised when document parsing fails."""

    def __init__(self, message: str, document_id: str = None, filename: str = None):
        super().__init__(message)
        self.document_id = document_id
        self.filename = filename


class ChunkingError(RAGTrackError):
    """Raised when chunking fails."""

    def __init__(self, message: str, document_id: str = None):
        super().__init__(message)
        self.document_id = document_id


class EmbeddingError(RAGTrackError):
    """Raised when embedding generation fails."""

    def __init__(self, message: str, document_id: str = None):
        super().__init__(message)
        self.document_id = document_id


class RetrievalError(RAGTrackError):
    """Raised when retrieval operations fail."""

    def __init__(self, message: str, query: str = None):
        super().__init__(message)
        self.query = query


class VectorStoreError(RAGTrackError):
    """Raised when vector store operations fail."""

    def __init__(self, message: str, operation: str = None):
        super().__init__(message)
        self.operation = operation


class LLMError(RAGTrackError):
    """Base exception for LLM-related errors."""

    def __init__(self, message: str, provider: str = None):
        super().__init__(message)
        self.provider = provider


class LLMTimeoutError(LLMError):
    """Raised when LLM request times out."""

    def __init__(self, message: str, timeout_seconds: int = None):
        super().__init__(message)
        self.timeout_seconds = timeout_seconds


class LLMConnectionError(LLMError):
    """Raised when LLM connection fails."""

    def __init__(self, message: str, endpoint: str = None):
        super().__init__(message)
        self.endpoint = endpoint


class LLMEmptyResponseError(LLMError):
    """Raised when LLM returns empty response."""

    def __init__(self, message: str = "LLM returned empty response"):
        super().__init__(message)


class LLMAuthenticationError(LLMError):
    """Raised when LLM API authentication fails."""

    def __init__(self, message: str = "LLM API authentication failed"):
        super().__init__(message)


class ValidationError(RAGTrackError):
    """Raised when input validation fails."""

    def __init__(self, message: str, field: str = None, value=None):
        super().__init__(message)
        self.field = field
        self.value = value


class ConfigurationError(RAGTrackError):
    """Raised when configuration is invalid or missing."""

    def __init__(self, message: str, config_key: str = None):
        super().__init__(message)
        self.config_key = config_key
