"""Grading stress-test answers and auto-tuning settings by replaying the keep rule."""
from types import SimpleNamespace
from unittest.mock import patch

from app.services.pipeline import QueryResponse, QueryResult
from app.services.stress.grade import grade_item, summarize
from app.services.stress.tune import best_settings, replay_kept, should_recommend


def result(answer="Yogesh is an engineer.", status="answered", kept=("c1",), cands=(("c1", 0.9), ("c2", 0.05))):
    candidates = [{"chunk_id": cid, "jev": j, "status": "kept" if cid in kept else "dropped"} for cid, j in cands]
    response = QueryResponse(trace_id="t1", question="q", answer=answer, sources=[], answer_status=status,
                             usage={"total_tokens": 100, "cost_usd": 0.0001, "jev_cost_included": True})
    return QueryResult(response=response, trace=SimpleNamespace(candidates=candidates))


ANSWERABLE = {"id": "q1", "kind": "direct", "question": "Who?", "expected_answer": "an engineer", "source_chunk_id": "c1"}
UNANSWERABLE = {"id": "q2", "kind": "unanswerable", "question": "Salary?", "expected_answer": None, "source_chunk_id": None}


def test_answerable_graded_by_jev_and_retrieval_hit():
    with patch("app.services.stress.grade.jev.grade_answer", return_value=0.8):
        g = grade_item(ANSWERABLE, result(), api_key=None)
    assert (g["correct"], g["retrieval_hit"], g["hallucinated"], g["grade_score"]) == (True, True, False, 0.8)
    assert g["trace_id"] == "t1" and g["cost_usd"] == 0.0001 and g["tokens"] == 100
    assert g["candidates"] == [{"chunk_id": "c1", "jev": 0.9}, {"chunk_id": "c2", "jev": 0.05}]


def test_answerable_missed_and_ungradable():
    with patch("app.services.stress.grade.jev.grade_answer", return_value=0.2):
        assert grade_item(ANSWERABLE, result(kept=()), api_key=None)["retrieval_hit"] is False
    with patch("app.services.stress.grade.jev.grade_answer", return_value=None):
        assert grade_item(ANSWERABLE, result(), api_key=None)["correct"] is None


def test_unanswerable_correct_only_when_not_found():
    ok = grade_item(UNANSWERABLE, result(status="not_found", kept=()), api_key=None)
    bad = grade_item(UNANSWERABLE, result(status="answered"), api_key=None)
    assert (ok["correct"], ok["hallucinated"]) == (True, False)
    assert (bad["correct"], bad["hallucinated"]) == (False, True)


def test_summary_counts():
    items = [
        {"kind": "direct", "correct": True, "retrieval_hit": True, "hallucinated": False, "cost_usd": 0.001, "tokens": 10},
        {"kind": "messy", "correct": False, "retrieval_hit": False, "hallucinated": False, "cost_usd": None, "tokens": 5},
        {"kind": "unanswerable", "correct": False, "retrieval_hit": None, "hallucinated": True, "cost_usd": 0.002, "tokens": 7},
    ]
    s = summarize(items)
    assert (s["correct"], s["answerable"], s["retrieval_hits"]) == (1, 2, 1)
    assert (s["unanswerable"], s["unanswerable_handled"], s["hallucinations"]) == (1, 0, 1)
    assert s["cost_usd"] == 0.003 and s["tokens"] == 22
    assert s["by_kind"]["direct"] == {"correct": 1, "total": 1}


def cands(*scores):
    return [{"chunk_id": f"c{i}", "jev": s} for i, s in enumerate(scores)]


def test_replay_honours_min_keep_and_top_k():
    c = cands(0.9, 0.06, 0.04, 0.03, 0.01)
    assert replay_kept(c, 0.05, 10) == {"c0", "c1", "c2"}  # top passes -> best 3 kept
    assert replay_kept(c, 0.05, 2) == {"c0", "c1"}
    assert replay_kept(cands(0.04, 0.03), 0.05, 10) == set()  # nothing relevant -> nothing


def item(kind, source, scores):
    return {"kind": kind, "source_chunk_id": source, "candidates": cands(*scores)}


def test_best_settings_lowers_the_bar_when_answers_sit_just_below_it():
    # Source chunks score 0.07 / 0.08 (below the 0.1 default); unanswerable noise stays under 0.02
    items = [item("direct", "c0", [0.07, 0.01]), item("direct", "c0", [0.08, 0.01]),
             item("unanswerable", None, [0.015, 0.01])]
    assert best_settings(items, current=(0.1, 8)) == (0.05, 8)


def test_best_settings_keeps_current_on_ties_and_needs_jev_scores():
    items = [item("direct", "c0", [0.9, 0.01]), item("unanswerable", None, [0.01])]
    assert best_settings(items, current=(0.1, 8)) == (0.1, 8)
    no_jev = [{"kind": "direct", "source_chunk_id": "c0", "candidates": [{"chunk_id": "c0", "jev": None}]}]
    assert best_settings(no_jev, current=(0.1, 8)) is None


def test_recommend_only_on_validated_improvement():
    base = {"correct": 10, "hallucinations": 1}
    assert should_recommend(base, {"correct": 12, "hallucinations": 1})
    assert not should_recommend(base, {"correct": 12, "hallucinations": 2})
    assert not should_recommend(base, {"correct": 10, "hallucinations": 0})


def test_generation_error_on_unanswerable_is_not_a_hallucination():
    g = grade_item(UNANSWERABLE, result(status="error", kept=()), api_key=None)
    assert (g["correct"], g["hallucinated"]) == (None, False)
