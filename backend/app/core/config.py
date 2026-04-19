"""
Centralized configuration for RAG-TRACK application.

Uses pydantic-settings for environment-based configuration with validation.
"""

import os
from pathlib import Path
from typing import List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Application
    app_name: str = "RAG-TRACK"
    debug: bool = Field(default=False)
    environment: str = "development"

    @field_validator("debug", mode="before")
    @classmethod
    def parse_debug(cls, v):
        """Parse debug from string or bool."""
        if isinstance(v, str):
            return v.lower() not in ("false", "0", "no", "release")
        return v

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # CORS - configurable via environment
    allowed_origins: List[str] = Field(
        default=["http://localhost:5173", "http://127.0.0.1:5173"],
        validation_alias="ALLOWED_ORIGINS",
    )

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_origins(cls, v: str) -> List[str]:
        """Parse comma-separated origins into a list."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    # Rate Limiting
    rate_limit_enabled: bool = True
    rate_limit_per_minute: int = 30
    rate_limit_burst: int = 10

    # File Upload
    allowed_extensions: List[str] = Field(default=["pdf", "txt"])
    max_file_size_mb: int = 10
    max_file_size_bytes: int = Field(default=10 * 1024 * 1024)

    @field_validator("max_file_size_bytes", mode="before")
    @classmethod
    def parse_file_size(cls, v: int, info) -> int:
        """Convert MB to bytes if needed."""
        if info.data.get("max_file_size_mb"):
            return int(info.data["max_file_size_mb"] * 1024 * 1024)
        return v

    # Chunking
    chunk_size: int = 500
    chunk_overlap: int = 125

    # Embedding
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"

    # Vector Store
    vector_store_type: str = "faiss"  # faiss, qdrant, pinecone

    # LLM
    openrouter_api_key: Optional[str] = Field(
        default=None, validation_alias="OPENROUTER_API_KEY"
    )
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    llm_model: str = "google/gemma-4-26b-a4b-it:free"
    llm_temperature: float = 0.0
    llm_max_tokens: int = 2000
    llm_timeout_seconds: int = 60

    # Retrieval
    top_k_retrieval: int = 5
    retrieval_score_threshold: float = 0.0
    enable_multi_document: bool = False

    # Query Processing
    max_sub_queries: int = 5
    max_expanded_queries: int = 3

    # Observability
    trace_enabled: bool = True
    trace_storage_path: str = "backend/traces"

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"  # json, text

    # Database (future use)
    database_url: Optional[str] = Field(default=None, validation_alias="DATABASE_URL")

    # Redis (future use)
    redis_url: Optional[str] = Field(default=None, validation_alias="REDIS_URL")

    @property
    def data_dir(self) -> Path:
        """Get data directory path."""
        root = Path(__file__).parent.parent.parent.parent
        return root / "data"

    @property
    def vector_store_dir(self) -> Path:
        """Get vector store directory path."""
        return self.data_dir / "vector_store"

    @property
    def embedding_dir(self) -> Path:
        """Get embedding directory path."""
        return self.data_dir / "embeddings"

    @property
    def raw_dir(self) -> Path:
        """Get raw documents directory path."""
        return self.data_dir / "raw"

    @property
    def parsed_dir(self) -> Path:
        """Get parsed documents directory path."""
        return self.data_dir / "parsed"


# Global settings instance
settings = Settings()


# Legacy configuration (for backward compatibility)
# These are gradually being deprecated in favor of settings object
ALLOWED_EXTENSIONS = settings.allowed_extensions
MAX_FILE_SIZE_MB = settings.max_file_size_mb

CHUNK_SIZE = settings.chunk_size
CHUNK_OVERLAP = settings.chunk_overlap

EMBEDDING_DIR = str(settings.embedding_dir)
MODEL_NAME = settings.embedding_model

VECTOR_STORE_DIR = str(settings.vector_store_dir)


def get_settings() -> Settings:
    """Get settings instance."""
    return settings
