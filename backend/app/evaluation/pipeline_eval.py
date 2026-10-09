"""
Pipeline performance evaluation.

Evaluates end-to-end RAG pipeline performance including latency,
throughput, error rates, and stage-level breakdowns.
"""

import logging
import time
from typing import Any, Optional

from app.evaluation.dataset import EvalDataset, EvalQuery
from app.services.generation.generation_service import GenerationService
from app.services.query.multi_query.multi_query_service import MultiQueryService
from app.services.query.query_decomposition.query_decomposition_service import (
    QueryDecompositionService,
)
from app.services.query.query_rewrite.query_rewrite_service import QueryRewriteService
from app.services.retrieval.hybrid_service import HybridRetrievalService

logger = logging.getLogger(__name__)


class PipelineEvaluator:
    """
    Evaluates end-to-end pipeline performance and quality.

    Measures:
    - End-to-end latency (p50, p95, p99)
    - Stage-level latencies
    - Error/failure rate
    - Retrieval coverage
    - Chunk utilization
    """

    def __init__(
        self,
        top_k: int = 5,
        use_reranking: Optional[bool] = None,
    ):
        self.top_k = top_k
        self.use_reranking = use_reranking
        self.retriever = HybridRetrievalService()
        self.rewriter = QueryRewriteService()
        self.decomposer = QueryDecompositionService()
        self.multi_query = MultiQueryService()
        self.generator = GenerationService()

    def evaluate_query(
        self,
        query: EvalQuery,
    ) -> dict[str, Any]:
        """
        Run full pipeline for a single query and collect metrics.

        Args:
            query: EvalQuery with question and document_id.

        Returns:
            Dict with pipeline results and latency metrics.
        """
        timings = {}
        errors = []

        try:
            # Decomposition
            start = time.perf_counter()
            try:
                sub_queries = self.decomposer.decompose(query.question)
            except Exception as e:
                errors.append(f"decomposition: {e}")
                sub_queries = [query.question]
            timings["decomposition_ms"] = (time.perf_counter() - start) * 1000

            all_chunks = []
            all_matches = []

            for sq in sub_queries:
                # Rewrite
                start = time.perf_counter()
                try:
                    rewritten = self.rewriter.rewrite(sq)
                except Exception as e:
                    errors.append(f"rewrite: {e}")
                    rewritten = sq
                timings["rewrite_ms"] = (time.perf_counter() - start) * 1000

                # Multi-query expansion
                start = time.perf_counter()
                try:
                    expanded = self.multi_query.generate_queries(
                        rewritten, total_sub_queries=len(sub_queries)
                    )
                except Exception as e:
                    errors.append(f"multi_query: {e}")
                    expanded = [rewritten]
                timings["multi_query_ms"] = (time.perf_counter() - start) * 1000

                # Retrieval for each expanded query (mirrors the /query endpoint)
                start = time.perf_counter()
                for eq in expanded:
                    result = self.retriever.search(
                        query.document_id,
                        eq,
                        top_k=self.top_k,
                        use_reranking=self.use_reranking,
                    )
                    matches = result.get("matches", [])
                    all_matches.extend(matches)
                    all_chunks.extend(result.get("reranker_raw_items", matches))
                timings["retrieval_ms"] = (time.perf_counter() - start) * 1000

            # Deduplicate
            seen = set()
            unique_chunks = []
            for c in all_chunks:
                cid = c.get("chunk_id", c.get("content", "")[:50])
                if cid not in seen:
                    seen.add(cid)
                    unique_chunks.append(c)

            # Sort and select top-k
            unique_chunks.sort(key=lambda x: x.get("score", 0.0), reverse=True)
            selected = unique_chunks[: self.top_k]

            # Generation
            start = time.perf_counter()
            try:
                answer = self.generator.generate(
                    query.question, selected, is_overview=query.is_overview
                )
            except Exception as e:
                errors.append(f"generation: {e}")
                answer = "Generation failed."
            timings["generation_ms"] = (time.perf_counter() - start) * 1000

            timings["total_ms"] = sum(timings.values())

            return {
                "query_id": query.query_id,
                "question": query.question,
                "answer": answer,
                "retrieved_chunks": selected,
                "sources": [
                    {
                        "file_name": c.get("file_name"),
                        "page_number": c.get("page_number"),
                    }
                    for c in selected
                ],
                "timings": timings,
                "errors": errors,
                "success": len(errors) == 0,
                "num_chunks_used": len(selected),
                "reranking_applied": self.use_reranking,
            }

        except Exception as e:
            logger.exception(f"Pipeline evaluation failed for query {query.query_id}")
            return {
                "query_id": query.query_id,
                "question": query.question,
                "answer": f"Pipeline error: {e}",
                "retrieved_chunks": [],
                "sources": [],
                "timings": {},
                "errors": [str(e)],
                "success": False,
                "num_chunks_used": 0,
                "reranking_applied": self.use_reranking,
            }

    def evaluate_dataset(
        self,
        dataset: EvalDataset,
    ) -> dict[str, Any]:
        """
        Evaluate pipeline across all queries in a dataset.

        Args:
            dataset: EvalDataset with test queries.

        Returns:
            Dict with per-query results and aggregated pipeline metrics.
        """
        results = []
        latencies = []
        stage_latencies = {
            "decomposition_ms": [],
            "rewrite_ms": [],
            "multi_query_ms": [],
            "retrieval_ms": [],
            "generation_ms": [],
        }
        error_count = 0
        chunks_used = []

        for query in dataset.queries:
            result = self.evaluate_query(query)
            results.append(result)

            timings = result.get("timings", {})
            if timings:
                latencies.append(timings.get("total_ms", 0))
                for stage in stage_latencies:
                    if stage in timings:
                        stage_latencies[stage].append(timings[stage])

            if not result.get("success", False):
                error_count += 1
            chunks_used.append(result.get("num_chunks_used", 0))

        aggregated = {
            "total_queries": len(dataset.queries),
            "successful_queries": len(dataset.queries) - error_count,
            "failed_queries": error_count,
            "error_rate": error_count / len(dataset.queries) if dataset.queries else 0.0,
            "latency": self._percentiles(latencies),
            "stage_latency": {
                stage: self._percentiles(values)
                for stage, values in stage_latencies.items()
                if values
            },
            "avg_chunks_used": (
                sum(chunks_used) / len(chunks_used) if chunks_used else 0.0
            ),
        }

        return {
            "dataset_name": dataset.name,
            "aggregated_metrics": aggregated,
            "per_query_results": results,
        }

    def _percentiles(self, values: list[float]) -> dict[str, float]:
        """Compute latency percentiles."""
        if not values:
            return {"p50": 0.0, "p95": 0.0, "p99": 0.0, "mean": 0.0, "min": 0.0, "max": 0.0}

        sorted_vals = sorted(values)
        n = len(sorted_vals)

        def percentile(p):
            idx = int(p / 100.0 * (n - 1))
            return sorted_vals[idx]

        return {
            "p50": percentile(50),
            "p95": percentile(95),
            "p99": percentile(99),
            "mean": sum(values) / len(values),
            "min": min(values),
            "max": max(values),
        }
