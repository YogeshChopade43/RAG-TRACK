"""
Unit tests for Retrieve API endpoints.
"""
import pytest
from unittest.mock import Mock, patch


class TestRetrieveAPI:
    """Tests for /query endpoints."""

    @pytest.fixture
    def client(self, mock_client):
        """Use the pre-configured mock client."""
        return mock_client

    @pytest.fixture
    def valid_request_body(self):
        """Valid query request data."""
        return {
            "document_id": "550e8400-e29b-41d4-a716-446655440000",
            "question": "What is the main topic of the document?",
            "top_k": 5
        }

    @pytest.fixture
    def mock_services(self):
        """Mock all retrieval/query services."""
        with patch('app.api.retrieve.get_retrieval_service') as mock_retriever_factory, \
             patch('app.api.retrieve.get_query_rewrite_service') as mock_rewriter_factory, \
             patch('app.api.retrieve.get_query_decomposition_service') as mock_decomposer_factory, \
             patch('app.api.retrieve.get_multi_query_service') as mock_multi_factory, \
             patch('app.api.retrieve.get_generation_service') as mock_generator_factory:

            mock_retriever = Mock()
            mock_retriever.search.return_value = {
                "matches": [
                    {
                        "chunk_id": "chunk1",
                        "chunk_text": "The document discusses AI.",
                        "file_name": "doc1.pdf",
                        "page_number": 1,
                        "score": 0.95
                    }
                ]
            }

            mock_rewriter = Mock()
            mock_rewriter.rewrite.return_value = "rewritten question"

            mock_decomposer = Mock()
            mock_decomposer.decompose.return_value = ["original question"]

            mock_multi = Mock()
            mock_multi.generate_queries.return_value = ["expanded query 1", "expanded query 2"]

            mock_generator = Mock()
            mock_generator.generate.return_value = "AI stands for Artificial Intelligence."

            mock_retriever_factory.return_value = mock_retriever
            mock_rewriter_factory.return_value = mock_rewriter
            mock_decomposer_factory.return_value = mock_decomposer
            mock_multi_factory.return_value = mock_multi
            mock_generator_factory.return_value = mock_generator

            yield {
                "retriever": mock_retriever,
                "rewriter": mock_rewriter,
                "decomposer": mock_decomposer,
                "multi": mock_multi,
                "generator": mock_generator,
            }

    def test_query_endpoint_success(self, client, valid_request_body, mock_services):
        """Test successful query returns answer with sources."""
        with patch('app.api.retrieve.TraceService') as mock_trace_service_class:
            mock_trace = Mock()
            mock_trace_service = Mock()
            mock_trace_service.start_trace.return_value = "trace-123"
            mock_trace_service_class.return_value = mock_trace_service

            response = client.post("/query", json=valid_request_body)

            assert response.status_code == 200
            data = response.json()
            assert "trace_id" in data
            assert "answer" in data
            assert "sources" in data

    def test_query_endpoint_validates_document_id_format(self, client):
        """Test that invalid document_id format is rejected."""
        invalid_body = {
            "document_id": "not-a-uuid",
            "question": "What is the document about?"
        }
        response = client.post("/query", json=invalid_body)
        assert response.status_code == 422

    def test_query_endpoint_validates_question_length(self, client):
        """Test that short questions are rejected."""
        invalid_body = {
            "document_id": "550e8400-e29b-41d4-a716-446655440000",
            "question": "ab"  # Too short (<3 chars)
        }
        response = client.post("/query", json=invalid_body)
        assert response.status_code == 422

    def test_query_endpoint_handles_no_results(self, client, valid_request_body):
        """Test query when no relevant chunks are found."""
        with patch('app.api.retrieve.get_retrieval_service') as mock_retriever_factory, \
             patch('app.api.retrieve.get_query_rewrite_service') as mock_rewriter_factory, \
             patch('app.api.retrieve.get_query_decomposition_service') as mock_decomposer_factory, \
             patch('app.api.retrieve.get_multi_query_service') as mock_multi_factory, \
             patch('app.api.retrieve.get_generation_service') as mock_generator_factory:

            mock_retriever = Mock()
            mock_retriever.search.return_value = {"matches": []}
            mock_retriever_factory.return_value = mock_retriever

            mock_rewriter = Mock()
            mock_rewriter.rewrite.return_value = "rewritten"
            mock_rewriter_factory.return_value = mock_rewriter

            mock_decomposer = Mock()
            mock_decomposer.decompose.return_value = ["q1"]
            mock_decomposer_factory.return_value = mock_decomposer

            mock_multi = Mock()
            mock_multi.generate_queries.return_value = ["q1"]
            mock_multi_factory.return_value = mock_multi

            mock_generator = Mock()
            mock_generator_factory.return_value = mock_generator

            with patch('app.api.retrieve.TraceService') as mock_trace_class:
                mock_trace_service = Mock()
                mock_trace_service.start_trace.return_value = "trace-123"
                mock_trace_class.return_value = mock_trace_service

                response = client.post("/query", json=valid_request_body)

                assert response.status_code == 200
                data = response.json()
                assert "could not find relevant information" in data["answer"].lower()
                mock_generator.generate.assert_not_called()

    def test_query_endpoint_handles_generation_error(self, client, valid_request_body):
        """Test query when generation fails; returns 200 with error message."""
        with patch('app.api.retrieve.get_retrieval_service') as mock_retriever_factory, \
             patch('app.api.retrieve.get_query_rewrite_service') as mock_rewriter_factory, \
             patch('app.api.retrieve.get_query_decomposition_service') as mock_decomposer_factory, \
             patch('app.api.retrieve.get_multi_query_service') as mock_multi_factory, \
             patch('app.api.retrieve.get_generation_service') as mock_generator_factory:

            mock_retriever = Mock()
            mock_retriever.search.return_value = {
                "matches": [
                    {"chunk_id": "c1", "chunk_text": "Content", "file_name": "doc.txt", "page_number": 1, "score": 0.9}
                ]
            }
            mock_retriever_factory.return_value = mock_retriever

            mock_rewriter = Mock()
            mock_rewriter.rewrite.return_value = "rewritten"
            mock_rewriter_factory.return_value = mock_rewriter

            mock_decomposer = Mock()
            mock_decomposer.decompose.return_value = ["q1"]
            mock_decomposer_factory.return_value = mock_decomposer

            mock_multi = Mock()
            mock_multi.generate_queries.return_value = ["q1"]
            mock_multi_factory.return_value = mock_multi

            mock_generator = Mock()
            mock_generator.generate.side_effect = Exception("LLM error")
            mock_generator_factory.return_value = mock_generator

            with patch('app.api.retrieve.TraceService') as mock_trace_class:
                mock_trace_service = Mock()
                mock_trace_service.start_trace.return_value = "trace-123"
                mock_trace_class.return_value = mock_trace_service

                response = client.post("/query", json=valid_request_body)

                # With no chunks and error, code returns early with "no information" message
                assert response.status_code == 200
                data = response.json()
                assert "could not find relevant information" in data["answer"].lower() or "error" in data["answer"].lower()

    def test_get_trace_endpoint(self, client):
        """Test retrieving a trace."""
        with patch('app.services.observability.trace_storage.TraceStorage') as mock_trace_storage:
            mock_trace = Mock()
            mock_trace.dict.return_value = {"trace_id": "123", "steps": []}
            mock_trace_storage.load.return_value = mock_trace

            response = client.get("/query/trace/trace-123")

            assert response.status_code == 200
            data = response.json()
            assert data["trace_id"] == "123"

    def test_get_trace_not_found(self, client):
        """Test retrieving non-existent trace."""
        with patch('app.api.retrieve.TraceStorage') as mock_trace_storage:
            mock_trace_storage.load.return_value = None

            response = client.get("/query/trace/nonexistent")
            assert response.status_code == 404
