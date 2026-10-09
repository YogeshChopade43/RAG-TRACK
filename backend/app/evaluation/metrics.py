"""
Core metrics for RAG evaluation.

Implements standard information retrieval and ranking metrics:
- Precision@K
- Recall@K
- Mean Reciprocal Rank (MRR)
- Normalized Discounted Cumulative Gain (nDCG)
- Hit Rate@K
- Mean Average Precision (MAP)
"""

import math
from collections.abc import Sequence
from typing import Any, Optional


def precision_at_k(relevant: set[str], retrieved: Sequence[str], k: int) -> float:
    """
    Compute Precision@K.

    Args:
        relevant: Set of relevant item IDs.
        retrieved: Ordered list of retrieved item IDs.
        k: Number of top results to consider.

    Returns:
        Precision@K score in [0, 1].
    """
    if k <= 0:
        return 0.0
    top_k = retrieved[:k]
    if not top_k:
        return 0.0
    hits = sum(1 for item in top_k if item in relevant)
    return hits / len(top_k)


def recall_at_k(relevant: set[str], retrieved: Sequence[str], k: int) -> float:
    """
    Compute Recall@K.

    Args:
        relevant: Set of relevant item IDs.
        retrieved: Ordered list of retrieved item IDs.
        k: Number of top results to consider.

    Returns:
        Recall@K score in [0, 1].
    """
    if not relevant:
        return 0.0
    top_k = retrieved[:k]
    hits = sum(1 for item in top_k if item in relevant)
    return hits / len(relevant)


def mrr(relevant: set[str], retrieved: Sequence[str]) -> float:
    """
    Compute Mean Reciprocal Rank.

    The reciprocal of the rank of the first relevant document.
    Returns 0 if no relevant document is retrieved.

    Args:
        relevant: Set of relevant item IDs.
        retrieved: Ordered list of retrieved item IDs.

    Returns:
        MRR score in [0, 1].
    """
    for rank, item in enumerate(retrieved, start=1):
        if item in relevant:
            return 1.0 / rank
    return 0.0


def dcg(scores: Sequence[float], k: int) -> float:
    """
    Compute Discounted Cumulative Gain.

    Args:
        scores: Ordered list of relevance scores.
        k: Number of top results to consider.

    Returns:
        DCG score.
    """
    return sum(
        score / math.log2(rank + 1)
        for rank, score in enumerate(scores[:k], start=2)
    )


def ndcg(relevant: set[str], retrieved: Sequence[str], k: int) -> float:
    """
    Compute Normalized Discounted Cumulative Gain@K.

    Uses binary relevance: 1 if item is relevant, 0 otherwise.

    Args:
        relevant: Set of relevant item IDs.
        retrieved: Ordered list of retrieved item IDs.
        k: Number of top results to consider.

    Returns:
        nDCG@K score in [0, 1].
    """
    top_k = retrieved[:k]
    relevance_scores = [1.0 if item in relevant else 0.0 for item in top_k]

    actual_dcg = dcg(relevance_scores, k)

    ideal_order = sorted(relevance_scores, reverse=True)
    ideal_dcg = dcg(ideal_order, k)

    if ideal_dcg == 0:
        return 0.0

    return actual_dcg / ideal_dcg


def hit_rate(relevant: set[str], retrieved: Sequence[str], k: int) -> float:
    """
    Compute Hit Rate@K.

    Returns 1 if at least one relevant document is in the top-K, else 0.

    Args:
        relevant: Set of relevant item IDs.
        retrieved: Ordered list of retrieved item IDs.
        k: Number of top results to consider.

    Returns:
        Hit Rate@K score (0.0 or 1.0).
    """
    top_k = retrieved[:k]
    return 1.0 if any(item in relevant for item in top_k) else 0.0


def average_precision(relevant: set[str], retrieved: Sequence[str], k: int) -> float:
    """
    Compute Average Precision@K.

    Args:
        relevant: Set of relevant item IDs.
        retrieved: Ordered list of retrieved item IDs.
        k: Number of top results to consider.

    Returns:
        Average Precision@K score in [0, 1].
    """
    if not relevant:
        return 0.0

    top_k = retrieved[:k]
    hits = 0
    sum_precisions = 0.0

    for rank, item in enumerate(top_k, start=1):
        if item in relevant:
            hits += 1
            precision_at_current_rank = hits / rank
            sum_precisions += precision_at_current_rank

    if hits == 0:
        return 0.0

    return sum_precisions / len(relevant)


def map_at_k(all_relevant: list[set[str]], all_retrieved: list[list[str]], k: int) -> float:
    """
    Compute Mean Average Precision@K across multiple queries.

    Args:
        all_relevant: List of sets of relevant item IDs, one per query.
        all_retrieved: List of ordered lists of retrieved item IDs, one per query.
        k: Number of top results to consider.

    Returns:
        MAP@K score in [0, 1].
    """
    if not all_relevant:
        return 0.0

    aps = [
        average_precision(rel, ret, k)
        for rel, ret in zip(all_relevant, all_retrieved)
    ]
    return sum(aps) / len(aps)


def retrieval_metrics_summary(
    relevant: set[str],
    retrieved: list[str],
    k_values: Optional[list[int]] = None,
) -> dict[str, Any]:
    """
    Compute a comprehensive retrieval metrics summary.

    Args:
        relevant: Set of relevant item IDs.
        retrieved: Ordered list of retrieved item IDs.
        k_values: List of K values to compute metrics for. Defaults to [1, 3, 5, 10].

    Returns:
        Dict with metric names and values.
    """
    if k_values is None:
        k_values = [1, 3, 5, 10]

    summary = {
        "mrr": mrr(relevant, retrieved),
        "hit_rate_at_1": hit_rate(relevant, retrieved, 1),
    }

    for k in k_values:
        summary[f"precision@{k}"] = precision_at_k(relevant, retrieved, k)
        summary[f"recall@{k}"] = recall_at_k(relevant, retrieved, k)
        summary[f"ndcg@{k}"] = ndcg(relevant, retrieved, k)
        summary[f"hit_rate@{k}"] = hit_rate(relevant, retrieved, k)
        summary[f"map@{k}"] = average_precision(relevant, retrieved, k)

    return summary
