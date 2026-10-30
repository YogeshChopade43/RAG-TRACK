"""/query transparency: usage, answer status, near misses, cached and fallback flags, trace funnel."""
from unittest.mock import Mock, patch

import pytest

from app.api import retrieve
from app.services.jev import QueryAnalysis
from app.services.observability.call_log import call_entry, record_call

DOC_ID = "550e8400-e29b-41d4-a716-446655440000"


def candidate(cid, jev, fused=0.5):
    return {"chunk_id": cid, "file_name": "f.pdf", "page_number": 2, "content": f"text of {cid}",
            "vector": 0.4, "bm25": None, "fused": fused, "jev": jev, "rerank_kept": jev >= 0.1}


def search_result(kept, dropped, reranked=True, attempted=None):
    matches = [{"chunk_id": c, "chunk_text": f"text of {c}", "file_name": "f.pdf", "page_number": 2, "score": 0.9}
               for c in kept]
    return {
        "matches": matches,
        "reranking_applied": reranked,
        "rerank_attempted": reranked if attempted is None else attempted,
        "candidates": [candidate(c, 0.9) for c in kept] + [candidate(c, j) for c, j in dropped],
    }


@pytest.fixture
def pipeline(mock_client):
    from app.main import app

    retriever = Mock()
    rewriter = Mock(is_overview_question=Mock(return_value=False))
    rewriter.rewrite.side_effect = lambda q, **_: q
    decomposer = Mock()
    decomposer.decompose.side_effect = lambda q, **_: [q]
    multi = Mock()
    multi.generate_queries.side_effect = lambda q, **_: [q]
    generator = Mock()

    def answer(*_a, **_k):
        # what LLMService.chat would record for the answer call
        record_call(call_entry("llm", "answer", "m", 0.0, prompt_tokens=1500, completion_tokens=400, cost_usd=0.0004))
        return generator.answer_text

    generator.generate.side_effect = answer
    generator.answer_text = "Yogesh is an engineer."

    app.dependency_overrides.update({
        retrieve.get_retriever: lambda: retriever,
        retrieve.get_query_rewrite_service: lambda: rewriter,
        retrieve.get_query_decomposition_service: lambda: decomposer,
        retrieve.get_multi_query_service: lambda: multi,
        retrieve.get_generation_service: lambda: generator,
    })
    retrieve._retrieval_cache.clear()
    saved = []
    with patch("app.api.retrieve.TraceStorage.save", side_effect=saved.append), \
         patch("app.api.retrieve.TraceStorage.exists", return_value=True):
        yield mock_client, retriever, rewriter, generator, saved
    app.dependency_overrides.clear()
    retrieve._retrieval_cache.clear()


def jev_on():
    analysis = QueryAnalysis(needs_decomposition=False, needs_rewrite=False, blocked=False, scores={"jailbreak": 0.01})
    return (
        patch("app.api.retrieve.jev.analyze_query", return_value=analysis),
        patch("app.api.retrieve.jev.guard_answer", side_effect=lambda q, c, a, k=None: (a, {"unsupported": 0.05})),
    )


def ask(client, question="Who is Yogesh?"):
    return client.post("/query", json={"document_id": DOC_ID, "question": question}).json()


def test_answered_reports_usage_and_no_fallbacks(pipeline):
    client, retriever, _, _, saved = pipeline
    retriever.search.return_value = search_result(["c1"], [("c2", 0.05)])
    a, g = jev_on()
    with a, g:
        res = ask(client)

    assert res["answer_status"] == "answered" and res["cached"] is False
    assert res["usage"]["total_tokens"] == 1900 and res["usage"]["cost_usd"] == pytest.approx(0.0004)
    assert res["fallbacks"] == [] and res["near_misses"] == []
    trace = saved[-1]
    assert trace.decision_sources == {"analysis": "jev", "rerank": "jev", "guard": "jev"}
    assert {c["chunk_id"]: c["status"] for c in trace.candidates} == {"c1": "kept", "c2": "dropped"}
    assert trace.expanded_queries == ["Who is Yogesh?"]
    assert [c["purpose"] for c in trace.calls] == ["answer"]


def test_nothing_kept_is_not_found_with_near_misses(pipeline):
    client, retriever, _, generator, saved = pipeline
    retriever.search.return_value = search_result([], [("c2", 0.08), ("c3", 0.05), ("c4", 0.02), ("c5", 0.01)])
    a, g = jev_on()
    with a, g:
        res = ask(client)

    assert res["answer_status"] == "not_found"
    assert [m["jev"] for m in res["near_misses"]] == [0.08, 0.05, 0.02]
    generator.generate.assert_not_called()
    trace = saved[-1]
    assert trace.answer_status == "not_found"
    assert {c["reason"] for c in trace.candidates} == {"below_min_relevance"}


def test_model_refusal_is_not_found(pipeline):
    from app.services.generation.prompt_registry import NOT_FOUND_ANSWER

    client, retriever, _, generator, _ = pipeline
    retriever.search.return_value = search_result(["c1"], [("c2", 0.05)])
    generator.answer_text = NOT_FOUND_ANSWER
    a, g = jev_on()
    with a, g:
        res = ask(client)
    assert res["answer_status"] == "not_found"
    assert [m["jev"] for m in res["near_misses"]] == [0.05]


def test_jev_unavailable_is_reported_as_fallback(pipeline):
    client, retriever, _, _, saved = pipeline
    retriever.search.return_value = search_result(["c1"], [], reranked=False, attempted=True)
    with patch("app.api.retrieve.jev.analyze_query", return_value=None), \
         patch("app.api.retrieve.jev.guard_answer", side_effect=lambda q, c, a, k=None: (a, {})):
        res = ask(client)
    assert res["fallbacks"] == ["analysis", "rerank", "guard"]
    assert saved[-1].decision_sources == {"analysis": "heuristic", "rerank": "fusion", "guard": "unavailable"}


def test_overview_skips_rerank_without_reporting_a_fallback(pipeline):
    client, retriever, rewriter, _, saved = pipeline
    rewriter.is_overview_question.return_value = True
    retriever.search.return_value = search_result(["c1"], [], reranked=False)
    a, g = jev_on()
    with a, g:
        res = ask(client, "Summarise this document")
    assert saved[-1].decision_sources["rerank"] == "skipped"
    assert res["fallbacks"] == []


def test_retriever_without_candidates_still_lists_matches(pipeline):
    client, retriever, _, _, saved = pipeline
    retriever.search.return_value = {"matches": [
        {"chunk_id": "c1", "chunk_text": "t", "file_name": "f.pdf", "page_number": 1, "score": 0.7}]}
    a, g = jev_on()
    with a, g:
        ask(client)
    (c,) = saved[-1].candidates
    assert (c["chunk_id"], c["fused"], c["jev"], c["status"]) == ("c1", 0.7, None, "kept")


def test_cache_hit_is_flagged_and_costs_nothing(pipeline):
    client, retriever, _, _, _ = pipeline
    retriever.search.return_value = search_result(["c1"], [])
    a, g = jev_on()
    with a, g:
        first = ask(client)
        second = ask(client)
    assert first["cached"] is False and second["cached"] is True
    assert second["usage"]["cost_usd"] == 0 and second["usage"]["total_tokens"] == 0
    assert second["answer_status"] == first["answer_status"]


def test_rerank_not_attempted_is_not_a_fallback(pipeline):
    # e.g. only one retriever returned results, or a single candidate: Jev was never asked
    client, retriever, _, _, saved = pipeline
    retriever.search.return_value = search_result(["c1"], [], reranked=False, attempted=False)
    a, g = jev_on()
    with a, g:
        res = ask(client)
    assert saved[-1].decision_sources["rerank"] == "skipped"
    assert res["fallbacks"] == []


def test_partial_rerank_failure_is_a_fallback(pipeline):
    from app.main import app

    client, retriever, _, _, saved = pipeline
    two_variants = Mock()
    two_variants.generate_queries.side_effect = lambda q, **_: [q, q + " variant"]
    app.dependency_overrides[retrieve.get_multi_query_service] = lambda: two_variants
    retriever.search.side_effect = [
        search_result(["c1"], []),
        search_result(["c2"], [], reranked=False, attempted=True),
    ]
    a, g = jev_on()
    with a, g:
        res = ask(client)
    assert saved[-1].decision_sources["rerank"] == "fusion"
    assert res["fallbacks"] == ["rerank"]
