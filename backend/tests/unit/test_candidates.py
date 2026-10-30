"""Candidate funnel: every chunk found, with its scores and why it was kept or dropped."""
from app.services.generation.prompt_registry import NOT_FOUND_ANSWER, registry
from app.services.observability.candidates import (
    classify_candidates,
    merge_candidates,
    near_misses,
)


def cand(cid, jev=None, fused=0.5, vector=None, bm25=None, page=1, content="text"):
    return {"chunk_id": cid, "file_name": "f.pdf", "page_number": page, "content": content,
            "vector": vector, "bm25": bm25, "fused": fused, "jev": jev, "rerank_kept": False}


def by_id(items):
    return {c["chunk_id"]: c for c in items}


def test_status_and_reasons():
    out = by_id(classify_candidates(
        [cand("kept", jev=0.9), cand("low", jev=0.08), cand("cut", jev=0.5), cand("unscored", jev=None)],
        final_ids={"kept"},
        min_relevance=0.1,
    ))
    assert (out["kept"]["status"], out["kept"]["reason"]) == ("kept", None)
    assert (out["low"]["status"], out["low"]["reason"]) == ("dropped", "below_min_relevance")
    assert out["cut"]["reason"] == "beyond_top_k"
    assert out["unscored"]["reason"] == "beyond_top_k"


def test_kept_first_then_by_jev_then_fused():
    out = classify_candidates(
        [cand("a", jev=0.2), cand("b", jev=0.6), cand("k", jev=0.1), cand("n", jev=None, fused=0.9)],
        final_ids={"k"},
        min_relevance=0.1,
    )
    assert [c["chunk_id"] for c in out] == ["k", "b", "a", "n"]


def test_merge_unions_found_by_and_keeps_best_scores():
    merged = by_id(merge_candidates([
        ("q1", [cand("x", jev=0.3, fused=0.4, vector=0.7)]),
        ("q2", [cand("x", jev=0.6, fused=0.2, bm25=0.9), cand("y", jev=0.1)]),
    ]))
    x = merged["x"]
    assert x["found_by"] == ["q1", "q2"]
    assert (x["jev"], x["fused"], x["vector"], x["bm25"]) == (0.6, 0.4, 0.7, 0.9)
    assert merged["y"]["found_by"] == ["q2"]


def test_near_misses_top_three_dropped_with_short_preview():
    classified = classify_candidates(
        [cand("k", jev=0.9), *[cand(f"d{i}", jev=i / 100, content="w" * 500) for i in range(1, 6)]],
        final_ids={"k"},
        min_relevance=0.1,
    )
    misses = near_misses(classified)
    assert [m["jev"] for m in misses] == [0.05, 0.04, 0.03]
    assert all(len(m["preview"]) <= 200 for m in misses)
    assert set(misses[0]) == {"file_name", "page_number", "jev", "reason", "preview"}
    assert misses[0]["reason"] == "below_min_relevance"


def test_prompts_use_the_shared_not_found_sentence():
    # answer_status detects "not found" by this exact sentence; the prompts must not drift from it
    texts = [p.system_prompt + p.user_prompt_template for p in registry.list_prompts().values()]
    with_refusal = [t for t in texts if "could not find" in t]
    assert with_refusal and all(NOT_FOUND_ANSWER in t for t in with_refusal)


def test_rerank_kept_low_score_cut_by_final_top_k_is_beyond_top_k():
    # MIN_KEEP lets the reranker keep a chunk under the relevance bar; if the final
    # top-k then cuts it, the bar wasn't the reason
    c = {**cand("min_keep", jev=0.05), "rerank_kept": True}
    (out,) = classify_candidates([c], final_ids=set(), min_relevance=0.1)
    assert out["reason"] == "beyond_top_k"


def test_build_candidates_maps_scores_and_nulls_injected_block():
    from app.services.observability.candidates import build_candidates

    fused = [
        {"chunk_id": "a", "score": 0.8, "chunk_text": "A", "file_name": "f", "page_number": 1,
         "_component_scores": {"vector": 0.7, "bm25": 0.9}},
        {"chunk_id": "t", "score": 0.5, "chunk_text": "Title", "file_name": "f", "page_number": 1,
         "_component_scores": {"vector": 0.0, "bm25": 0.0, "injected": True}},
    ]
    rerank = {"ranked_items": [{"chunk_id": "a", "score": 0.92}, {"chunk_id": "t", "score": 0.3}],
              "top_k_items": [{"chunk_id": "a"}]}
    a, t = build_candidates(fused, rerank)
    assert (a["vector"], a["bm25"], a["fused"], a["jev"], a["rerank_kept"]) == (0.7, 0.9, 0.8, 0.92, True)
    # The injected title block was never scored by either retriever
    assert (t["vector"], t["bm25"], t["rerank_kept"]) == (None, None, False)
    assert build_candidates(fused, None)[0]["jev"] is None


def test_candidates_carry_the_ocr_flag():
    from app.services.observability.candidates import (
        build_candidates,
        candidates_from_matches,
    )

    m = {"chunk_id": "a", "chunk_text": "t", "score": 0.4, "metadata": {"ocr": True}}
    plain = {"chunk_id": "b", "chunk_text": "t", "score": 0.3, "metadata": {}}
    assert [c["ocr"] for c in candidates_from_matches([m, plain])] == [True, False]
    assert [c["ocr"] for c in build_candidates([m, plain], None)] == [True, False]
