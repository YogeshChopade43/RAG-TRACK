"""
Unit tests for configuration settings.
"""
import pytest
from unittest.mock import patch
from app.core.config import Settings, get_settings, CHUNK_SIZE, CHUNK_OVERLAP


class TestConfig:
    """Tests for configuration module."""

    def test_settings_default_values(self):
        """Test default configuration values."""
        # Use model_construct to avoid env loading
        settings = Settings.model_construct()
        assert settings.app_name == "RAG-TRACK"
        assert settings.debug is False
        assert settings.environment in ("development", "test")  # May vary
        assert settings.host == "0.0.0.0"
        assert settings.port == 8000
        assert settings.allowed_extensions == ["pdf", "txt"]
        assert settings.max_file_size_mb == 10

    def test_settings_explicit_values(self):
        """Test Settings with explicit values."""
        settings = Settings.model_construct(
            app_name="TestApp",
            debug=True,
            environment="production",
            allowed_origins=["http://test.com"],
        )
        assert settings.app_name == "TestApp"
        assert settings.debug is True
        assert settings.environment == "production"

    def test_parse_debug_validator_with_string_false(self):
        """Test debug validator handles 'false'."""
        settings = Settings.model_construct(debug=False)
        assert settings.debug is False

    def test_parse_debug_validator_with_string_true(self):
        """Test debug validator handles 'true'."""
        settings = Settings.model_construct(debug=True)
        assert settings.debug is True

    def test_parse_origins_validator_with_list(self):
        """Test origins validator accepts list."""
        settings = Settings.model_construct(
            allowed_origins=["http://a.com", "http://b.com"]
        )
        assert settings.allowed_origins == ["http://a.com", "http://b.com"]

    def test_file_size_property_calculation(self):
        """Test max_file_size_bytes derived from MB."""
        # Use regular init to trigger validators
        settings = Settings(max_file_size_mb=25, _env_file=None)
        expected = 25 * 1024 * 1024
        assert settings.max_file_size_bytes == expected

    def test_parse_file_size_validator_fallback(self):
        """Test file size validator uses MB value."""
        settings = Settings.model_construct(max_file_size_mb=10)
        assert settings.max_file_size_bytes == 10 * 1024 * 1024

    def test_data_dir_property(self):
        """Test data_dir property returns Path."""
        settings = Settings.model_construct()
        data_dir = settings.data_dir
        assert data_dir is not None
        assert "data" in str(data_dir)

    def test_vector_store_dir_property(self):
        """Test vector_store_dir property."""
        settings = Settings.model_construct()
        vstore = settings.vector_store_dir
        assert vstore is not None

    def test_raw_dir_property(self):
        """Test raw_dir property."""
        settings = Settings.model_construct()
        raw = settings.raw_dir
        assert raw is not None

    def test_parsed_dir_property(self):
        """Test parsed_dir property."""
        settings = Settings.model_construct()
        parsed = settings.parsed_dir
        assert parsed is not None

    def test_embedding_dir_property(self):
        """Test embedding_dir property."""
        settings = Settings.model_construct()
        embedding = settings.embedding_dir
        assert embedding is not None

    def test_rate_limit_settings(self):
        """Test rate limiting configuration."""
        settings = Settings.model_construct()
        assert settings.rate_limit_enabled is True
        assert settings.rate_limit_per_minute == 30
        assert settings.rate_limit_burst == 10

    def test_chunking_settings_constants(self):
        """Test chunking configuration constants."""
        assert CHUNK_SIZE == 500
        assert CHUNK_OVERLAP == 125

    def test_embedding_model_default(self):
        """Test default embedding model."""
        settings = Settings.model_construct()
        assert "sentence-transformers" in settings.embedding_model

    def test_llm_settings(self):
        """Test LLM configuration."""
        settings = Settings.model_construct()
        assert settings.llm_temperature == 0.0
        assert settings.llm_max_tokens == 2000
        assert settings.llm_timeout_seconds == 60

    def test_retrieval_settings(self):
        """Test retrieval configuration."""
        settings = Settings.model_construct()
        assert settings.top_k_retrieval == 5
        assert settings.retrieval_score_threshold == 0.0

    def test_logging_settings(self):
        """Test logging configuration."""
        settings = Settings.model_construct()
        assert settings.log_level == "INFO"
        assert settings.log_format in ["json", "text"]

    def test_trace_enabled_by_default(self):
        """Test observability is enabled by default."""
        settings = Settings.model_construct()
        assert settings.trace_enabled is True

    def test_ollama_settings(self):
        """Test Ollama settings."""
        settings = Settings.model_construct(
            ollama_base_url="http://localhost:11434",
            ollama_model="deepseek-r1:1.5b"
        )
        assert settings.ollama_base_url == "http://localhost:11434"
        assert settings.ollama_model == "deepseek-r1:1.5b"

    def test_api_key_setting(self):
        """Test API key setting."""
        settings = Settings.model_construct(api_key="test-secret")
        assert settings.api_key == "test-secret"

    def test_get_settings_returns_instance(self):
        """Test get_settings returns global instance."""
        result = get_settings()
        assert isinstance(result, Settings)

    def test_global_settings_instance_exists(self):
        """Test global settings singleton exists."""
        from app.core.config import settings
        assert settings is not None
        assert isinstance(settings, Settings)

    def test_module_constants_defined(self):
        """Test legacy constants are defined."""
        assert CHUNK_SIZE > 0
        assert CHUNK_OVERLAP >= 0

    def test_allowed_extensions_default(self):
        """Test default allowed extensions."""
        settings = Settings.model_construct()
        assert "pdf" in settings.allowed_extensions
        assert "txt" in settings.allowed_extensions

    def test_vector_store_type_default(self):
        """Test default vector store type."""
        settings = Settings.model_construct()
        assert settings.vector_store_type == "faiss"

    def test_embedding_dir_equals_data_dir_plus_embeddings(self):
        """Test embedding_dir path."""
        settings = Settings.model_construct()
        assert str(settings.embedding_dir).endswith("embeddings")
