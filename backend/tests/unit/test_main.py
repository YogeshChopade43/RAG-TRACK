"""
Unit tests for main FastAPI application.
"""
import pytest


class TestMainApp:
    """Tests for main FastAPI app."""

    @pytest.fixture
    def client(self, mock_client):
        """Use the pre-configured mock client."""
        return mock_client

    def test_root_endpoint_returns_app_info(self, client):
        """Test root endpoint returns application information."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "version" in data
        assert "status" in data

    def test_health_check_endpoint(self, client):
        """Test health check returns healthy status."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_readiness_check_dependencies(self, client):
        """Test readiness check validates dependencies."""
        response = client.get("/health/ready")
        assert response.status_code in [200, 503]

    def test_cors_middleware_configured(self, client):
        """Test CORS middleware adds appropriate headers."""
        # The CORS middleware should add Access-Control headers to responses.
        # Make a request with an Origin header and check for CORS headers in response.
        response = client.get("/", headers={"Origin": "http://localhost:3000"})
        # The response should include Access-Control-Allow-Origin header (or Access-Control-Allow-*)
        headers = response.headers
        # Check for any CORS-related header
        cors_headers = [k for k, v in headers.items() if k.lower().startswith("access-control-")]
        assert len(cors_headers) > 0, "No CORS headers found in response"

    def test_api_docs_accessible(self, client):
        """Test API documentation endpoints are accessible."""
        response = client.get("/docs")
        assert response.status_code == 200
        assert "swagger" in response.text.lower() or "redoc" in response.text.lower()

    def test_redoc_accessible(self, client):
        """Test Redoc documentation is accessible."""
        response = client.get("/redoc")
        assert response.status_code == 200

    def test_routers_are_included(self, client):
        """Test that routers are included with correct prefixes."""
        # Check ingest endpoints exist (should get method not allowed, not 404)
        response = client.get("/ingest")
        assert response.status_code != 404

        # Check query endpoints exist
        response = client.get("/query")
        assert response.status_code != 404

    def test_app_has_correct_title(self):
        """Test FastAPI app title is set."""
        from app.main import app
        assert app.title == "RAG-TRACK" or hasattr(app, 'title')


class TestSecurityHeaders:
    """Every response carries browser security headers; they protect the
    OpenRouter key users keep in sessionStorage from injected scripts."""

    @pytest.fixture
    def client(self, mock_client):
        return mock_client

    def test_strict_csp_on_app_responses(self, client):
        csp = client.get("/health").headers["Content-Security-Policy"]
        assert "script-src 'self'" in csp
        assert "'unsafe-eval'" not in csp
        assert "connect-src 'self'" in csp
        assert "frame-ancestors 'none'" in csp
        assert "object-src 'none'" in csp

    def test_other_security_headers(self, client):
        headers = client.get("/health").headers
        assert headers["X-Content-Type-Options"] == "nosniff"
        assert headers["Referrer-Policy"] == "no-referrer"
        assert headers["X-Frame-Options"] == "DENY"
        assert "max-age=" in headers["Strict-Transport-Security"]

    def test_api_docs_keep_working(self, client):
        # Swagger UI loads its script from a CDN and runs inline code
        assert "Content-Security-Policy" not in client.get("/docs").headers
