"""answer_question: the shared /query pipeline, with per-document settings overrides."""
import asyncio
from unittest.mock import Mock, patch

import pytest

from app.core.config import settings
from app.services import jev
from app.services.doc_settings import DocSettings
from app.services.pipeline import Services, _retrieval_cache, answer_question

DOC_ID = "550e8400-e29b-41d4-a716-446655440000"


@pytest.fixture
def services():
    retriever = Mock()
    retriever.search.return_value = {
        "matches": [{"chunk_id": "c1", "chunk_text": "t", "file_name": "f.pdf", "page_number": 1, "score": 0.9}],
    }
    rewriter = Mock(is_overview_question=Mock(return_value=False))
    rewriter.rewrite.side_effect = lambda q, **_: q
    decomposer = Mock()
    decomposer.decompose.side_effect = lambda q, **_: [q]
    multi = Mock()
    multi.generate_queries.side_effect = lambda q, **_: [q]
    generator = Mock()
    generator.generate.return_value = "answer"
    _retrieval_cache.clear()
    with patch("app.services.pipeline.jev.analyze_query", return_value=None), \
         patch("app.services.pipeline.jev.guard_answer", side_effect=lambda q, c, a, k=None: (a, {})), \
         patch("app.services.pipeline.TraceStorage.save"), \
         patch("app.services.pipeline.TraceStorage.exists", return_value=True):
        yield Services(retriever, rewriter, decomposer, multi, generator)
    _retrieval_cache.clear()


def run(services, **kw):
    return asyncio.run(answer_question(DOC_ID, "Who is Yogesh?", services=services, api_key=None, model=None, **kw))


def test_overrides_reach_search_and_are_recorded(services):
    result = run(services, overrides=DocSettings(top_k=4, min_relevance=0.05))
    kwargs = services.retriever.search.call_args
    assert kwargs.args[2] == 4 and kwargs.kwargs["min_relevance"] == 0.05
    assert result.trace.settings_used == {"top_k": 4, "min_relevance": 0.05, "source": "document"}


def test_defaults_recorded_without_overrides(services):
    result = run(services)
    assert result.trace.settings_used == {
        "top_k": settings.top_k_retrieval, "min_relevance": settings.jev_min_relevance, "source": "default",
    }


def test_without_cache_every_call_runs_the_pipeline(services):
    first, second = run(services, use_cache=False), run(services, use_cache=False)
    assert services.generator.generate.call_count == 2
    assert second.response.cached is False and first.response.trace_id != second.response.trace_id


def test_changed_settings_are_not_served_from_the_cache(services):
    run(services, overrides=DocSettings(top_k=4, min_relevance=0.05))
    second = run(services, overrides=DocSettings(top_k=6, min_relevance=0.1))
    assert services.generator.generate.call_count == 2 and second.response.cached is False


def test_reranker_uses_given_min_relevance(monkeypatch):
    scores = {"c0": 0.07, "c1": 0.06, "c2": 0.02, "c3": 0.01, "c4": 0.005}
    monkeypatch.setattr(jev, "decide", lambda state, questions, api_key=None, purpose="": scores)
    chunks = [{"chunk_id": f"id{i}", "chunk_text": f"t{i}", "score": 0.5} for i in range(5)]
    result = jev.JevReranker().rerank("q", chunks, top_k=10, min_relevance=0.05)
    # Top chunk passes 0.05 so MIN_KEEP (3) applies; then only scores >= 0.05
    assert [it["chunk_id"] for it in result["top_k_items"]] == ["id0", "id1", "id2"]
    strict = jev.JevReranker().rerank("q", chunks, top_k=10, min_relevance=0.1)
    assert strict["top_k_items"] == []  # nothing relevant -> nothing kept
