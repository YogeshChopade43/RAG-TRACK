"""
Centralized configuration for RAG-TRACK application.

Uses pydantic-settings for environment-based configuration with validation.
"""

import json
from pathlib import Path
from typing import Annotated, Optional, Union

from pydantic import (
    BeforeValidator,
    Field,
    field_validator,
    model_validator,
)
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic_settings.sources.types import NoDecode

# Determine project root (parent of backend directory)
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent


def parse_str_or_list(v: Union[str, list]) -> list[str]:
    """Parse a string value into a list of strings.

    Handles both JSON array strings (e.g. ``["a","b"]``) and
    comma-separated values (e.g. ``a,b,c``).
    """
    if isinstance(v, str):
        v = v.strip()
        if v.startswith("["):
            try:
                result = json.loads(v)
                if isinstance(result, list):
                    return [str(item).strip() for item in result if str(item).strip()]
            except (json.JSONDecodeError, ValueError):
                pass
        return [item.strip() for item in v.split(",") if item.strip()]
    if isinstance(v, list):
        return [str(item).strip() for item in v if str(item).strip()]
    return []


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
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

    @model_validator(mode="after")
    def validate_production_secrets(self) -> "Settings":
        """Validate that production secrets are not using default values."""
        if self.environment == "production":
            if self.secret_key == "your-secret-key-change-in-production":
                raise ValueError(
                    "SECRET_KEY must be changed in production. "
                    "Set a strong SECRET_KEY in your environment."
                )

            if not self.openrouter_api_key:
                raise ValueError(
                    "OPENROUTER_API_KEY must be set."
                )

            if not self.database_url:
                raise ValueError(
                    "DATABASE_URL must be set in production."
                )
        return self

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # CORS - configurable via environment
    allowed_origins: Annotated[list[str], NoDecode, BeforeValidator(parse_str_or_list)] = Field(
        default=["http://localhost:5173", "http://127.0.0.1:5173"],
        validation_alias="ALLOWED_ORIGINS",
    )

    # Rate Limiting
    rate_limit_enabled: bool = True
    rate_limit_per_minute: int = 30
    rate_limit_burst: int = 10

    # File Upload
    allowed_extensions: Annotated[list[str], NoDecode, BeforeValidator(parse_str_or_list)] = Field(default=["pdf", "txt"])
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
    chunk_overlap: int = 200

    # Embedding
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"

    # Vector Store
    vector_store_type: str = "faiss"  # faiss, qdrant, pinecone
    faiss_index_type: str = "hnsw"  # flat, hnsw
    faiss_hnsw_m: int = 32
    faiss_hnsw_ef_construction: int = 64
    faiss_hnsw_ef_search: int = 64

    # Reranking
    use_reranking: bool = True
    use_llm_reranking: bool = False
    rerank_top_k: int = 20
    rerank_weights: dict = Field(
        default_factory=lambda: {
            "semantic": 0.35,
            "keyword": 0.20,
            "original": 0.20,
            "llm": 0.05,
            "structural": 0.20,
        }
    )

    # Hybrid Search
    enable_hybrid_search: bool = True
    hybrid_weights: dict = Field(
        default_factory=lambda: {
            "bm25": 0.3,
            "vector": 0.7,
        }
    )

    # LLM
    openrouter_api_key: Optional[str] = Field(
        default=None, validation_alias="OPENROUTER_API_KEY"
    )
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    llm_model: str = "google/gemma-4-26b-a4b-it:free"
    llm_temperature: float = 0.0
    llm_max_tokens: int = 2000
    llm_timeout_seconds: int = 60

    # Authentication
    api_key: Optional[str] = Field(default=None, validation_alias="API_KEY")

    # JWT Settings
    secret_key: str = Field(
        default="your-secret-key-change-in-production",
        validation_alias="SECRET_KEY",
    )
    algorithm: str = Field(default="HS256", validation_alias="ALGORITHM")
    access_token_expire_minutes: int = Field(
        default=30, validation_alias="ACCESS_TOKEN_EXPIRE_MINUTES"
    )
    refresh_token_expire_days: int = Field(
        default=7, validation_alias="REFRESH_TOKEN_EXPIRE_DAYS"
    )

    # Password validation
    min_password_length: int = 8

    # Retrieval
    top_k_retrieval: int = 8
    retrieval_score_threshold: float = 0.0
    enable_multi_document: bool = True

    # Upload limits
    max_upload_size: int = 50 * 1024 * 1024  # 50 MB

    # Query Processing
    max_sub_queries: int = 5
    max_expanded_queries: int = 3

    # Observability
    trace_enabled: bool = True
    trace_storage_path: str = "backend/traces"

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"  # json, text

    # Database
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
