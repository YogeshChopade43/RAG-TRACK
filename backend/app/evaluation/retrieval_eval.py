"""
Retrieval evaluation.

Evaluates the retrieval quality of the RAG system by comparing
retrieved chunks against ground truth relevance judgments.
"""

import logging
from typing import Any, Optional

from app.evaluation.dataset import EvalDataset, EvalQuery
from app.evaluation.metrics import (
    average_precision,
    hit_rate,
    mrr,
    ndcg,
    precision_at_k,
    recall_at_k,
    retrieval_metrics_summary,
)
from app.services.retrieval.hybrid_service import HybridRetrievalService
from app.services.retrieval.retrieval_service import RetrievalService

logger = logging.getLogger(__name__)


class RetrievalEvaluator:
    """
    Evaluates retrieval quality using ground truth relevance judgments.

    Runs retrieval for each query in the dataset and computes
    standard IR metrics against known relevant chunks.
    """

    def __init__(
        self,
        vector_retriever: Optional[RetrievalService] = None,
        bm25_service: Optional[Any] = None,
        reranker: Optional[Any] = None,
        top_k_values: Optional[list[int]] = None,
    ):
        self.vector_retriever = vector_retriever or RetrievalService()
        self.bm25_service = bm25_service
        self.reranker = reranker
        self.top_k_values = top_k_values or [1, 3, 5, 10]
        self.hybrid = HybridRetrievalService(
            vector_retriever=self.vector_retriever,
            bm25_service=self.bm25_service,
            reranker=self.reranker,
        )

    def evaluate_query(
        self,
        query: EvalQuery,
        top_k: int = 5,
        use_reranking: Optional[bool] = None,
    ) -> dict[str, Any]:
        """
        Evaluate retrieval for a single query.

        Args:
            query: EvalQuery with ground truth relevant_chunk_ids.
            top_k: Number of chunks to retrieve.
            use_reranking: Override reranking setting.

        Returns:
            Dict with retrieved chunk IDs and metric scores.
        """
        result = self.hybrid.search(
            document_id=query.document_id,
            query=query.question,
            top_k=top_k,
            use_reranking=use_reranking,
        )

        matches = result.get("matches", [])
        retrieved_ids = [m["chunk_id"] for m in matches]
        relevant = query.relevant_chunk_ids

        metrics = retrieval_metrics_summary(
            relevant=relevant,
            retrieved=retrieved_ids,
            k_values=self.top_k_values,
        )

        return {
            "query_id": query.query_id,
            "question": query.question,
            "retrieved_ids": retrieved_ids,
            "retrieved_scores": [m["score"] for m in matches],
            "relevant_count": len(relevant),
            "retrieved_count": len(retrieved_ids),
            "metrics": metrics,
            "reranking_applied": result.get("reranking_applied", False),
            "fusion_details": result.get("fusion_details", {}),
        }

    def evaluate_dataset(
        self,
        dataset: EvalDataset,
        top_k: int = 5,
        use_reranking: Optional[bool] = None,
    ) -> dict[str, Any]:
        """
        Evaluate retrieval across all queries in a dataset.

        Args:
            dataset: EvalDataset with ground truth.
            top_k: Number of chunks to retrieve per query.
            use_reranking: Override reranking setting.

        Returns:
            Dict with per-query results and aggregated metrics.
        """
        results = []
        all_relevant = []
        all_retrieved = []

        for query in dataset.queries:
            result = self.evaluate_query(query, top_k=top_k, use_reranking=use_reranking)
            results.append(result)
            all_relevant.append(query.relevant_chunk_ids)
            all_retrieved.append(result["retrieved_ids"])

        aggregated = {}
        for k in self.top_k_values:
            aggregated[f"precision@{k}"] = sum(
                precision_at_k(rel, ret, k) for rel, ret in zip(all_relevant, all_retrieved)
            ) / len(all_relevant)
            aggregated[f"recall@{k}"] = sum(
                recall_at_k(rel, ret, k) for rel, ret in zip(all_relevant, all_retrieved)
            ) / len(all_relevant)
            aggregated[f"ndcg@{k}"] = sum(
                ndcg(rel, ret, k) for rel, ret in zip(all_relevant, all_retrieved)
            ) / len(all_relevant)
            aggregated[f"hit_rate@{k}"] = sum(
                hit_rate(rel, ret, k) for rel, ret in zip(all_relevant, all_retrieved)
            ) / len(all_relevant)
            aggregated[f"map@{k}"] = map_at_k(all_relevant, all_retrieved, k)

        aggregated["mrr"] = sum(
            mrr(rel, ret) for rel, ret in zip(all_relevant, all_retrieved)
        ) / len(all_relevant)

        return {
            "dataset_name": dataset.name,
            "num_queries": len(dataset.queries),
            "top_k": top_k,
            "use_reranking": use_reranking,
            "aggregated_metrics": aggregated,
            "per_query_results": results,
        }

    def compare_with_and_without_reranking(
        self,
        dataset: EvalDataset,
        top_k: int = 5,
    ) -> dict[str, Any]:
        """
        Compare retrieval metrics with reranking enabled vs disabled.

        Args:
            dataset: EvalDataset with ground truth.
            top_k: Number of chunks to retrieve.

        Returns:
            Dict with before/after reranking metrics and deltas.
        """
        with_rerank = self.evaluate_dataset(dataset, top_k=top_k, use_reranking=True)
        without_rerank = self.evaluate_dataset(dataset, top_k=top_k, use_reranking=False)

        with_metrics = with_rerank["aggregated_metrics"]
        without_metrics = without_rerank["aggregated_metrics"]

        deltas = {}
        for key in with_metrics:
            deltas[key] = {
                "with_rerank": with_metrics[key],
                "without_rerank": without_metrics[key],
                "delta": with_metrics[key] - without_metrics[key],
                "delta_pct": (
                    ((with_metrics[key] - without_metrics[key]) / without_metrics[key] * 100)
                    if without_metrics[key] > 0
                    else 0.0
                ),
            }

        return {
            "dataset_name": dataset.name,
            "top_k": top_k,
            "with_reranking": with_rerank,
            "without_reranking": without_rerank,
            "deltas": deltas,
        }


def map_at_k(
    all_relevant: list[set[str]],
    all_retrieved: list[list[str]],
    k: int,
) -> float:
    """Compute Mean Average Precision@K across queries."""
    if not all_relevant:
        return 0.0
    aps = [
        average_precision(rel, ret, k) for rel, ret in zip(all_relevant, all_retrieved)
    ]
    return sum(aps) / len(aps)
