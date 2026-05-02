"""
Integration tests for API endpoints.
"""

import pytest
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient


@pytest.mark.integration
class TestHealthEndpoints:
    """Tests for health check endpoints."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        from app.main import app
        return TestClient(app)

    def test_root_endpoint(self, client):
        """Test root endpoint."""
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "RAG-TRACK"
        assert "version" in data

    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_ready_check(self, client):
        """Test readiness check endpoint."""
        response = client.get("/health/ready")

        assert response.status_code in [200, 503]


@pytest.mark.integration
class TestQueryEndpoint:
    """Tests for query endpoint."""

    @pytest.fixture
    def client(self):
        """Create test client with mocked services."""
        with patch("app.services.llm.get_llm_service") as mock_get_llm:
            mock_llm = MagicMock()
            mock_llm.chat.return_value = "Test answer"
            mock_get_llm.return_value = mock_llm

            with patch("app.services.retrieval.retrieval_service.SentenceTransformer"):
                with patch(
                    "app.services.embedding.embedding_service.SentenceTransformer"
                ):
                    with patch("app.services.llm.get_llm_service") as mock_llm2:
                        mock_llm2.return_value = MagicMock()
                        from app.main import app
                        yield TestClient(app)

    def test_query_requires_document_id(self, client):
        """Test query requires document_id."""
        response = client.post("/query", json={"question": "What is in the document?"})

        assert response.status_code == 422

    def test_query_requires_question(self, client):
        """Test query requires question."""
        response = client.post(
            "/query", json={"document_id": "550e8400-e29b-41d4-a716-446655440000"}
        )

        assert response.status_code == 422

    def test_query_validates_uuid(self, client):
        """Test query validates UUID format."""
        response = client.post(
            "/query",
            json={
                "document_id": "invalid-uuid",
                "question": "What is in the document?",
            },
        )

        assert response.status_code == 422

    def test_query_validates_question_length(self, client):
        """Test query validates question length."""
        response = client.post(
            "/query",
            json={
                "document_id": "550e8400-e29b-41d4-a716-446655440000",
                "question": "ab",  # Too short
            },
        )

        assert response.status_code == 422
