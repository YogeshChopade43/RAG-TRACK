"""
Candidate funnel for the trace: every chunk retrieval found, its scores, and
whether it reached the LLM (and if not, why).
"""
from typing import Any, Optional

SCORES = ("vector", "bm25", "fused", "jev")
PREVIEW_CHARS = 200


def candidates_from_matches(matches: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Fallback for retrievers that don't report candidates: their matches, fused score only."""
    return [
        {
            "chunk_id": m["chunk_id"],
            "file_name": m.get("file_name"),
            "page_number": m.get("page_number"),
            "content": m.get("chunk_text") or m.get("content", ""),
            "vector": None,
            "bm25": None,
            "fused": m.get("score"),
            "jev": None,
            "rerank_kept": False,
            "ocr": bool((m.get("metadata") or {}).get("ocr")),
        }
        for m in matches
    ]


def build_candidates(fused: list[dict[str, Any]], rerank_result: Optional[dict[str, Any]]) -> list[dict[str, Any]]:
    """Every fused chunk with its retriever scores and (if reranked) Jev's probability."""
    rerank_result = rerank_result or {}
    jev_scores = {it["chunk_id"]: it["score"] for it in rerank_result.get("ranked_items", [])}
    kept_ids = {it["chunk_id"] for it in rerank_result.get("top_k_items", [])}
    out = []
    for item in fused:
        comp = item.get("_component_scores") or {}
        injected = comp.get("injected", False)  # overview title block: neither retriever scored it
        out.append({
            "chunk_id": item["chunk_id"],
            "file_name": item.get("file_name"),
            "page_number": item.get("page_number"),
            "content": item.get("chunk_text", ""),
            "vector": None if injected else comp.get("vector"),
            "bm25": None if injected else comp.get("bm25"),
            "fused": item["score"],
            "jev": jev_scores.get(item["chunk_id"]),
            "rerank_kept": item["chunk_id"] in kept_ids,
            "ocr": bool((item.get("metadata") or {}).get("ocr")),
        })
    return out


def _max(a: Optional[float], b: Optional[float]) -> Optional[float]:
    return b if a is None else a if b is None else max(a, b)


def merge_candidates(runs: list[tuple[str, list[dict[str, Any]]]]) -> list[dict[str, Any]]:
    """Merge (query, candidates) runs by chunk: union of queries that found it, best of each score."""
    merged: dict[str, dict[str, Any]] = {}
    for query, candidates in runs:
        for c in candidates:
            m = merged.get(c["chunk_id"])
            if m is None:
                merged[c["chunk_id"]] = {**c, "found_by": [query]}
                continue
            if query not in m["found_by"]:
                m["found_by"].append(query)
            for s in SCORES:
                m[s] = _max(m.get(s), c.get(s))
            m["rerank_kept"] = m.get("rerank_kept") or c.get("rerank_kept", False)
    return list(merged.values())


def classify_candidates(
    candidates: list[dict[str, Any]], final_ids: set[str], min_relevance: float
) -> list[dict[str, Any]]:
    """Mark each candidate kept (in the final context) or dropped with a reason; kept first, best first."""
    out = []
    for c in candidates:
        kept = c["chunk_id"] in final_ids
        jev = c.get("jev")
        # A chunk the reranker kept (MIN_KEEP) despite a low score was cut by top-k, not the bar
        below_bar = jev is not None and jev < min_relevance and not c.get("rerank_kept")
        reason = None if kept else ("below_min_relevance" if below_bar else "beyond_top_k")
        out.append({**c, "status": "kept" if kept else "dropped", "reason": reason})

    def rank(c: dict[str, Any]) -> tuple:
        jev = c.get("jev")
        return (c["status"] != "kept", jev is None, -(jev if jev is not None else c.get("fused") or 0))

    return sorted(out, key=rank)


def near_misses(classified: list[dict[str, Any]], n: int = 3) -> list[dict[str, Any]]:
    """The best dropped candidates, for explaining a 'not found' answer."""
    dropped = [c for c in classified if c["status"] == "dropped"]
    return [
        {
            "file_name": c.get("file_name"),
            "page_number": c.get("page_number"),
            "jev": c.get("jev"),
            "reason": c.get("reason"),
            "preview": (c.get("content") or "")[:PREVIEW_CHARS],
        }
        for c in dropped[:n]
    ]


def summarize_usage(calls: list[dict[str, Any]]) -> dict[str, Any]:
    """Totals across a request's calls. cost_usd is None when no call reported a cost."""
    tokens = [(c.get("prompt_tokens") or 0) + (c.get("completion_tokens") or 0) for c in calls]
    costs = [c["cost_usd"] for c in calls if c.get("cost_usd") is not None]
    has_tokens = any(c.get("prompt_tokens") is not None or c.get("completion_tokens") is not None for c in calls)
    return {
        "total_tokens": sum(tokens) if has_tokens else None,
        "cost_usd": round(sum(costs), 6) if costs else None,
        "jev_cost_included": all(c.get("cost_usd") is not None for c in calls if c.get("kind") == "jev"),
    }
