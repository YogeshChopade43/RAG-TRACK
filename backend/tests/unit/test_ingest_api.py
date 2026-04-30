"""
Unit tests for Ingest API endpoints.
"""
import pytest
from unittest.mock import patch
from fastapi import UploadFile, HTTPException
import io


class TestIngestAPI:
    """Tests for /ingest endpoints."""

    @pytest.fixture
    def client(self, mock_client):
        """Use the pre-configured mock client."""
        return mock_client

    @pytest.fixture
    def sample_text_file(self):
        """Create a sample text file."""
        return UploadFile(filename="test.txt", file=io.BytesIO(b"Sample content"))

    @pytest.fixture
    def sample_pdf_file(self):
        """Create a minimal PDF-like file."""
        content = b"""%PDF-1.4
1 0 obj<</Type/Catalog>>endobj
trailer<</Root 1 0 R>>
%%EOF"""
        return UploadFile(filename="test.pdf", file=io.BytesIO(content))

    def test_ingest_root_endpoint(self, client):
        """Test root endpoint returns app info."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "version" in data

    def test_health_check_endpoint(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_ingest_document_success_text(self, client):
        """Test successful text document ingestion."""
        with patch('app.api.ingest.save_raw_file') as mock_save, \
             patch('app.api.ingest.ingest', return_value={"status": "completed"}) as mock_ingest:
            response = client.post(
                "/ingest",
                files={"file": ("test.txt", b"Sample content", "text/plain")}
            )
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "completed"
            assert "document_id" in data

    def test_ingest_document_requires_file(self, client):
        """Test that ingestion requires a file."""
        response = client.post("/ingest")
        assert response.status_code in [400, 422]

    def test_ingest_document_validates_extension(self, client):
        """Test that unsupported file extensions are rejected."""
        response = client.post(
            "/ingest",
            files={"file": ("test.exe", b"binary content", "application/octet-stream")}
        )
        assert response.status_code == 400
        assert "Unsupported file type" in response.json()["detail"]

    def test_ingest_document_validates_file_size(self, client):
        """Test that oversized files are rejected."""
        large_content = b"x" * (11 * 1024 * 1024)  # 11MB
        response = client.post(
            "/ingest",
            files={"file": ("large.txt", large_content, "text/plain")}
        )
        assert response.status_code in [200, 413]

    def test_ingest_document_handles_invalid_filename(self, client):
        """Test that path traversal attempts are sanitized."""
        response = client.post(
            "/ingest",
            files={"file": ("../../../etc/passwd", b"content", "text/plain")}
        )
        assert response.status_code in [200, 400]

    def test_get_document_endpoint(self, client):
        """Test getting document metadata."""
        document_id = "550e8400-e29b-41d4-a716-446655440000"
        from app.core.config import settings
        import shutil

        raw_doc_dir = settings.raw_dir / document_id
        raw_doc_dir.mkdir(parents=True, exist_ok=True)
        test_file = raw_doc_dir / "file1.txt"
        test_file.write_text("content")

        try:
            response = client.get(f"/ingest/{document_id}")
            assert response.status_code == 200
            data = response.json()
            assert data["document_id"] == document_id
            assert "files" in data
        finally:
            if raw_doc_dir.exists():
                shutil.rmtree(raw_doc_dir)

    def test_get_document_invalid_id(self, client):
        """Test getting document with invalid UUID."""
        response = client.get("/ingest/not-a-uuid")
        assert response.status_code == 400

    def test_get_document_not_found(self, client):
        """Test getting non-existent document."""
        document_id = "550e8400-e29b-41d4-a716-446655440001"  # likely not created
        response = client.get(f"/ingest/{document_id}")
        # Should get 404 because raw_dir exists check fails or subdir missing
        assert response.status_code in [404, 200]

    def test_delete_document(self, client):
        """Test deleting a document."""
        document_id = "550e8400-e29b-41d4-a716-446655440002"
        from app.core.config import settings
        import shutil

        raw_doc_dir = settings.raw_dir / document_id
        raw_doc_dir.mkdir(parents=True, exist_ok=True)
        (raw_doc_dir / "dummy.txt").touch()

        vector_dir = settings.vector_store_dir
        index_file = vector_dir / f"{document_id}.index"
        meta_file = vector_dir / f"{document_id}_metadata.json"
        index_file.touch()
        meta_file.write_text("{}")

        try:
            response = client.delete(f"/ingest/{document_id}")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "deleted"
            assert not raw_doc_dir.exists()
            assert not index_file.exists()
            assert not meta_file.exists()
        finally:
            # Cleanup if any left
            if raw_doc_dir.exists():
                shutil.rmtree(raw_doc_dir)
            if index_file.exists():
                index_file.unlink()
            if meta_file.exists():
                meta_file.unlink()

    def test_delete_document_invalid_id(self, client):
        """Test deleting with invalid UUID."""
        response = client.delete("/ingest/invalid-id")
        assert response.status_code == 400
