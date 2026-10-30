"""Grade one stress-test answer and summarise a run."""
from typing import Any, Optional

from app.services import jev

GRADE_THRESHOLD = 0.5
KINDS = ("direct", "reworded", "messy", "unanswerable")


def grade_item(item: dict[str, Any], result, *, api_key: Optional[str]) -> dict[str, Any]:
    """Item + what happened. Answerable: retrieval hit (source chunk kept) and a Jev grade
    against the expected answer. Unanswerable: correct only if the system said not found."""
    response = result.response
    candidates = (getattr(result.trace, "candidates", None) or []) if result.trace is not None else []
    kept = {c["chunk_id"] for c in candidates if c.get("status") == "kept"}
    usage = response.usage or {}
    graded: dict[str, Any] = {
        **item,
        "trace_id": response.trace_id,
        "answer": response.answer,
        "answer_status": response.answer_status,
        "cost_usd": usage.get("cost_usd"),
        "tokens": usage.get("total_tokens"),
        # Compact scores per candidate: all auto-tune needs to replay other settings
        "candidates": [{"chunk_id": c["chunk_id"], "jev": c.get("jev")} for c in candidates],
        "grade_score": None,
        "retrieval_hit": None,
        "hallucinated": False,
    }
    if response.answer_status == "error":
        # Generation failed: neither correct nor a hallucination, just unknown
        graded["correct"] = None
        if item["kind"] != "unanswerable":
            graded["retrieval_hit"] = item["source_chunk_id"] in kept
        return graded
    if item["kind"] == "unanswerable":
        graded["correct"] = response.answer_status == "not_found"
        graded["hallucinated"] = not graded["correct"]
        return graded

    graded["retrieval_hit"] = item["source_chunk_id"] in kept
    score = jev.grade_answer(item["question"], item["expected_answer"], response.answer, api_key)
    graded["grade_score"] = score
    graded["correct"] = None if score is None else score >= GRADE_THRESHOLD
    return graded


def summarize(items: list[dict[str, Any]]) -> dict[str, Any]:
    answerable = [i for i in items if i["kind"] != "unanswerable"]
    unanswerable = [i for i in items if i["kind"] == "unanswerable"]
    costs = [i["cost_usd"] for i in items if i.get("cost_usd") is not None]
    return {
        "correct": sum(1 for i in answerable if i.get("correct")),
        "answerable": len(answerable),
        "retrieval_hits": sum(1 for i in answerable if i.get("retrieval_hit")),
        "unanswerable": len(unanswerable),
        "unanswerable_handled": sum(1 for i in unanswerable if i.get("correct")),
        "hallucinations": sum(1 for i in unanswerable if i.get("hallucinated")),
        "cost_usd": round(sum(costs), 6) if costs else None,
        "tokens": sum(i.get("tokens") or 0 for i in items),
        "by_kind": {
            k: {"correct": sum(1 for i in items if i["kind"] == k and i.get("correct")),
                "total": sum(1 for i in items if i["kind"] == k)}
            for k in KINDS
            if any(i["kind"] == k for i in items)
        },
    }
