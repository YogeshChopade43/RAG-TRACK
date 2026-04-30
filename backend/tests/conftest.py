"""
Pytest configuration and test fixtures.
"""

import os
import sys
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir.parent))

# ============================================================
# Early mocking of heavy ML dependencies to avoid import errors
# ============================================================

class DummySentenceTransformer:
    """Lightweight stub for SentenceTransformer."""
    def __init__(self, model_name=None):
        self.model_name = model_name or "dummy"
    def encode(self, sentences, convert_to_numpy=True, show_progress_bar=False, **kwargs):
        if isinstance(sentences, str):
            sentences = [sentences]
        # Return deterministic dummy embeddings
        return np.random.rand(len(sentences), 384).astype('float32')

class DummyPdfplumber:
    """Stub for pdfplumber."""
    class PDF:
        def __init__(self, pages_data):
            self.pages = pages_data
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
    @staticmethod
    def open(file_path):
        # Return dummy PDF with no pages by default; tests will override
        return DummyPdfplumber.PDF([])

# Insert dummy modules before any app imports
_dummy_st = MagicMock()
_dummy_st.SentenceTransformer = DummySentenceTransformer
sys.modules['sentence_transformers'] = _dummy_st

_dummy_pdf = MagicMock()
_dummy_pdfplumber = MagicMock()
_dummy_pdfplumber.open = DummyPdfplumber.open
sys.modules['pdfplumber'] = _dummy_pdfplumber

# Also stub transformers to avoid import errors
_dummy_transformers = MagicMock()
sys.modules['transformers'] = _dummy_transformers
sys.modules['torch'] = MagicMock()
sys.modules['tensorflow'] = MagicMock()
sys.modules['absl'] = MagicMock()

# ============================================================
# Fixtures
# ============================================================

@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    """Clean environment variables that interfere with settings."""
    # Remove Ollama environment variables that cause validation errors
    monkeypatch.delenv("OLLAMA_BASE_URL", raising=False)
    monkeypatch.delenv("OLLAMA_MODEL", raising=False)
    
    # Set test environment
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")


@pytest.fixture
def mock_settings(clean_env):
    """Use test settings."""
    from app.core.config import Settings
    return Settings()


@pytest.fixture
def sample_pdf_content() -> bytes:
    """Sample PDF content for testing."""
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
    from app.core.config import settings
    # Temporarily override data_dir
    data_dir = tmp_path / "data"
    data_dir.mkdir()
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
