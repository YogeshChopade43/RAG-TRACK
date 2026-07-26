"""Basic Locust load test for the /query endpoint."""
import sys
from unittest.mock import MagicMock, patch

from locust import HttpUser, between, task

# Stub heavy third-party dependencies so app can be imported without them.
sys.modules.setdefault("sentence_transformers", MagicMock())
sys.modules.setdefault("pdfplumber", MagicMock())
sys.modules.setdefault("transformers", MagicMock())
sys.modules.setdefault("torch", MagicMock())
sys.modules.setdefault("tensorflow", MagicMock())
sys.modules.setdefault("absl", MagicMock())

# Mock LLM and retrieval services so load tests do not depend on real models.
_llm_patcher = patch("app.services.llm.get_llm_service")
_mock_llm = _llm_patcher.start()
_mock_llm.return_value.chat.return_value = "Mocked load-test response"

_retrieval_patcher = patch("app.services.retrieval.get_retrieval_service")
_mock_retrieval = _retrieval_patcher.start()
_mock_retrieval.return_value.search.return_value = []


class QueryUser(HttpUser):
    host = "http://127.0.0.1:8000"
    wait_time = between(1, 3)

    @task
    def post_query(self):
        self.client.post(
            "/query",
            json={
                "document_id": "integration-test-doc",
                "question": "What is this document about?",
            },
        )
