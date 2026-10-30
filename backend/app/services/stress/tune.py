"""
Auto-tune: find the relevance bar and top-k that would have served the stress test best.

Free to compute: each graded item stores Jev's score for every candidate chunk, so the
keep rule can be replayed for any setting without calling a model. This approximates the
pipeline (which reranks per expanded query, then merges); the job validates the winner
with a real re-run before recommending it.
"""
from typing import Any, Optional

from app.services.jev import MIN_KEEP

BARS = (0.02, 0.05, 0.1, 0.15, 0.2, 0.3)
TOP_KS = (3, 4, 5, 6, 8, 10, 12)


def replay_kept(candidates: list[dict[str, Any]], min_relevance: float, top_k: int) -> set[str]:
    """The keep rule of JevReranker: best first; if the top passes the bar keep the best
    MIN_KEEP regardless, plus anything else over the bar; at most top_k."""
    ranked = sorted((c for c in candidates if c.get("jev") is not None), key=lambda c: c["jev"], reverse=True)
    if not ranked or ranked[0]["jev"] < min_relevance:
        return set()
    kept = [c for i, c in enumerate(ranked) if c["jev"] >= min_relevance or i < MIN_KEEP]
    return {c["chunk_id"] for c in kept[:top_k]}


def _has_scores(item: dict[str, Any]) -> bool:
    return any(c.get("jev") is not None for c in item.get("candidates", []))


def best_settings(items: list[dict[str, Any]], current: tuple[float, int]) -> Optional[tuple[float, int]]:
    """Grid point maximising (source chunk kept on answerable) − (anything kept on unanswerable).
    Ties: fewer chunks sent to the model, then closest to the current settings.
    None when too few items carry Jev scores to judge."""
    answerable = [i for i in items if i["kind"] != "unanswerable"]
    scored = [i for i in answerable if _has_scores(i)]
    if not scored or len(scored) < len(answerable) / 2:
        return None
    unanswerable = [i for i in items if i["kind"] == "unanswerable" and _has_scores(i)]
    pool = scored + unanswerable

    def rank(point: tuple[float, int]) -> tuple:
        bar, k = point
        kept = {id(i): replay_kept(i["candidates"], bar, k) for i in pool}
        hit = sum(i["source_chunk_id"] in kept[id(i)] for i in scored) / len(scored)
        leak = sum(bool(kept[id(i)]) for i in unanswerable) / len(unanswerable) if unanswerable else 0.0
        avg_kept = sum(len(v) for v in kept.values()) / len(pool)
        distance = abs(bar - current[0]) / 0.3 + abs(k - current[1]) / 12
        return (-(hit - leak), avg_kept, distance)

    return min(((b, k) for b in BARS for k in TOP_KS), key=rank)


def should_recommend(baseline: dict[str, Any], validation: dict[str, Any]) -> bool:
    """Only recommend settings that measurably answered more and hallucinated no more."""
    return validation["correct"] > baseline["correct"] and validation["hallucinations"] <= baseline["hallucinations"]
