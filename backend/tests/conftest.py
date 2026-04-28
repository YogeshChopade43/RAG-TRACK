"""
Pytest configuration and test fixtures.
"""

import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir.parent))


@pytest.fixture
def mock_settings(monkeypatch):
    """Use test settings."""
    from app.core.config import Settings

    # Override settings for testing
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")

    return Settings()


@pytest.fixture
def sample_pdf_content() -> bytes:
    """Sample PDF content for testing."""
    # Minimal valid PDF
    return b"""%PDF-1.4
1 0 obj<</Type/Catalog>>endobj
2 0 obj<</Type/Pages/Count 1>>endobj
xref
0 3
0000000000 65535 f
0000000015 00000 n
0000000068 00000 n
trailer<</Size 3/Root 1 0 R>>
startxref
125
%%EOF"""


@pytest.fixture
def sample_text_content() -> bytes:
    """Sample text content for testing."""
    return b"""This is a sample document for testing.
It contains multiple paragraphs.

This is the second paragraph with some more text.
And another line.

Third paragraph here.
"""


@pytest.fixture
def sample_chunks() -> list:
    """Sample chunks for testing."""
    return [
        {
            "chunk_id": "doc1_chunk_1",
            "document_id": "test-doc-1",
            "file_name": "test.txt",
            "page_number": 1,
            "chunk_text": "This is a sample document.",
            "char_start": 0,
            "char_end": 28,
        },
        {
            "chunk_id": "doc1_chunk_2",
            "document_id": "test-doc-1",
            "file_name": "test.txt",
            "page_number": 1,
            "chunk_text": "It contains multiple paragraphs.",
            "char_start": 29,
            "char_end": 60,
        },
    ]


@pytest.fixture
def temp_data_dir(tmp_path):
    """Create temporary data directory."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    # Create subdirectories
    (data_dir / "raw").mkdir()
    (data_dir / "vector_store").mkdir()
    (data_dir / "parsed").mkdir()

    return data_dir


@pytest.fixture
def mock_client():
    """Create test client with mocked dependencies."""
    from unittest.mock import patch, MagicMock

    from app.main import app

    with patch("app.services.llm.llm_service_local.LLMServiceLocal") as mock_llm:
        mock_instance = MagicMock()
        mock_instance.chat.return_value = "Test response"
        mock_llm.return_value = mock_instance

        with patch("app.services.retrieval.retrieval_service.SentenceTransformer"):
            with patch("app.services.embedding.embedding_service.SentenceTransformer"):
                yield TestClient(app)
