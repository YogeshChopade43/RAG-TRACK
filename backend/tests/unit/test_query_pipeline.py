"""
Regression tests for the /query pipeline wiring.
"""
from unittest.mock import Mock

import pytest

from app.api import retrieve
from app.services.query.query_decomposition.query_decomposition_service import (
    QueryDecompositionService,
)

DOC_ID = "550e8400-e29b-41d4-a716-446655440000"


@pytest.fixture
def services(mock_client):
    from app.main import app

    retriever = Mock()
    retriever.search.side_effect = lambda doc_id, q, top_k: {
        "matches": [{"chunk_id": q, "chunk_text": q, "file_name": "f.pdf", "page_number": 1, "score": 0.9}]
    }
    rewriter = Mock(is_overview_question=Mock(return_value=False))
    rewriter.rewrite.side_effect = lambda q, **_: q
    decomposer = Mock()
    decomposer.decompose.return_value = ["first part", "second part"]
    multi = Mock()
    multi.generate_queries.side_effect = lambda q, **_: [q]
    generator = Mock()

    app.dependency_overrides.update({
        retrieve.get_retriever: lambda: retriever,
        retrieve.get_query_rewrite_service: lambda: rewriter,
        retrieve.get_query_decomposition_service: lambda: decomposer,
        retrieve.get_multi_query_service: lambda: multi,
        retrieve.get_generation_service: lambda: generator,
    })
    retrieve._retrieval_cache.clear()
    yield mock_client, retriever, generator
    app.dependency_overrides.clear()
    retrieve._retrieval_cache.clear()


def test_every_sub_query_is_retrieved(services):
    client, retriever, generator = services
    generator.generate.return_value = "answer"

    res = client.post("/query", json={"document_id": DOC_ID, "question": "first part and second part"})

    assert res.status_code == 200
    searched = [c.args[1] for c in retriever.search.call_args_list]
    assert searched == ["first part", "second part"]


def test_generation_failure_is_not_cached(services):
    client, _, generator = services
    generator.generate.side_effect = [RuntimeError("rate limited"), "real answer"]
    body = {"document_id": DOC_ID, "question": "what is the budget?"}

    first = client.post("/query", json=body).json()
    second = client.post("/query", json=body).json()

    assert "error" in first["answer"]
    assert second["answer"] == "real answer"


@pytest.mark.parametrize("query,expected", [
    ("what is this for", False),
    ("how does the work get more funding", False),
    ("I understand the brand", False),
    ("skills and experience", True),
    ("is it red or blue", True),
])
def test_should_decompose_uses_word_boundaries(query, expected):
    assert QueryDecompositionService.should_decompose(None, query) is expected
