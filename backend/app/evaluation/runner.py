"""
Evaluation runner and reporting.

Orchestrates evaluation runs across retrieval, generation, and pipeline
dimensions, and produces structured evaluation reports.
"""

import logging
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Optional

from app.evaluation.dataset import EvalDataset
from app.evaluation.generation_eval import GenerationEvaluator
from app.evaluation.pipeline_eval import PipelineEvaluator
from app.evaluation.retrieval_eval import RetrievalEvaluator

logger = logging.getLogger(__name__)


@dataclass
class EvaluationReport:
    """Complete evaluation report across all dimensions."""

    dataset_name: str
    timestamp: str = ""
    retrieval: dict[str, Any] = field(default_factory=dict)
    generation: dict[str, Any] = field(default_factory=dict)
    pipeline: dict[str, Any] = field(default_factory=dict)
    reranking_comparison: dict[str, Any] = field(default_factory=dict)
    overall_score: float = 0.0
    summary: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def print_summary(self) -> None:
        """Print a human-readable summary of the evaluation report."""
        print("\n" + "=" * 60)
        print(f"EVALUATION REPORT: {self.dataset_name}")
        print("=" * 60)

        if self.retrieval:
            agg = self.retrieval.get("aggregated_metrics", {})
            print("\n[RETRIEVAL METRICS]")
            for k, v in agg.items():
                if isinstance(v, float):
                    print(f"  {k}: {v:.4f}")

        if self.reranking_comparison:
            print("\n[RERANKING IMPACT]")
            deltas = self.reranking_comparison.get("deltas", {})
            for key, delta in deltas.items():
                if isinstance(delta, dict) and "delta" in delta:
                    print(
                        f"  {key}: {delta['with_rerank']:.4f} "
                        f"(was {delta['without_rerank']:.4f}, "
                        f"delta: {delta['delta']:+.4f}, "
                        f"{delta['delta_pct']:+.1f}%)"
                    )

        if self.generation:
            agg = self.generation.get("aggregated_metrics", {})
            print("\n[GENERATION METRICS]")
            for k, v in agg.items():
                if isinstance(v, float):
                    print(f"  {k}: {v:.4f}")
                elif v is not None:
                    print(f"  {k}: {v}")

        if self.pipeline:
            agg = self.pipeline.get("aggregated_metrics", {})
            print("\n[PIPELINE PERFORMANCE]")
            latency = agg.get("latency", {})
            if latency:
                print("  End-to-end latency (ms):")
                print(f"    p50: {latency.get('p50', 0):.1f}")
                print(f"    p95: {latency.get('p95', 0):.1f}")
                print(f"    p99: {latency.get('p99', 0):.1f}")
            print(f"  Error rate: {agg.get('error_rate', 0):.2%}")
            print(f"  Avg chunks used: {agg.get('avg_chunks_used', 0):.1f}")

        print(f"\n[OVERALL SCORE: {self.overall_score:.2%}]")
        print("=" * 60 + "\n")

    def save(self, path: str) -> None:
        """Save report to JSON file."""
        import json
        from datetime import datetime

        report_dict = self.to_dict()
        report_dict["timestamp"] = (
            self.timestamp or datetime.utcnow().isoformat() + "Z"
        )

        with open(path, "w", encoding="utf-8") as f:
            json.dump(report_dict, f, indent=2, ensure_ascii=False, default=str)


class EvaluationRunner:
    """
    Orchestrates evaluation runs and collects results.

    Supports running individual evaluations or full suites.
    """

    def __init__(
        self,
        top_k: int = 5,
        use_reranking: Optional[bool] = None,
    ):
        self.top_k = top_k
        self.use_reranking = use_reranking
        self.retrieval_eval = RetrievalEvaluator(top_k_values=[1, 3, 5, 10])
        self.generation_eval = GenerationEvaluator()
        self.pipeline_eval = PipelineEvaluator(top_k=top_k, use_reranking=use_reranking)

    def run_retrieval_evaluation(
        self,
        dataset: EvalDataset,
        compare_reranking: bool = True,
    ) -> dict[str, Any]:
        """
        Run retrieval evaluation.

        Args:
            dataset: EvalDataset with ground truth.
            compare_reranking: Whether to compare with/without reranking.

        Returns:
            Retrieval evaluation results.
        """
        logger.info("Running retrieval evaluation...")
        start = time.perf_counter()

        result = self.retrieval_eval.evaluate_dataset(
            dataset, top_k=self.top_k, use_reranking=self.use_reranking
        )
        result["wall_time_seconds"] = time.perf_counter() - start

        if compare_reranking:
            result["reranking_comparison"] = (
                self.retrieval_eval.compare_with_and_without_reranking(
                    dataset, top_k=self.top_k
                )
            )

        logger.info(f"Retrieval evaluation completed in {result['wall_time_seconds']:.2f}s")
        return result

    def run_generation_evaluation(
        self,
        dataset: EvalDataset,
        answers: dict[str, str],
        sources: dict[str, list[dict[str, Any]]],
        retrieved_chunks: Optional[dict[str, list[dict[str, Any]]]] = None,
    ) -> dict[str, Any]:
        """
        Run generation evaluation.

        Args:
            dataset: EvalDataset with ground truth.
            answers: Generated answers per query_id.
            sources: Cited sources per query_id.
            retrieved_chunks: Retrieved chunks per query_id.

        Returns:
            Generation evaluation results.
        """
        logger.info("Running generation evaluation...")
        start = time.perf_counter()

        result = self.generation_eval.evaluate_dataset(
            dataset, answers, sources, retrieved_chunks
        )
        result["wall_time_seconds"] = time.perf_counter() - start

        logger.info(f"Generation evaluation completed in {result['wall_time_seconds']:.2f}s")
        return result

    def run_pipeline_evaluation(
        self,
        dataset: EvalDataset,
    ) -> dict[str, Any]:
        """
        Run pipeline performance evaluation.

        Args:
            dataset: EvalDataset with test queries.

        Returns:
            Pipeline evaluation results.
        """
        logger.info("Running pipeline evaluation...")
        start = time.perf_counter()

        result = self.pipeline_eval.evaluate_dataset(dataset)
        result["wall_time_seconds"] = time.perf_counter() - start

        logger.info(f"Pipeline evaluation completed in {result['wall_time_seconds']:.2f}s")
        return result

    def run_full_evaluation(
        self,
        dataset: EvalDataset,
        answers: Optional[dict[str, str]] = None,
        sources: Optional[dict[str, list[dict[str, Any]]]] = None,
        retrieved_chunks: Optional[dict[str, list[dict[str, Any]]]] = None,
        compare_reranking: bool = True,
    ) -> EvaluationReport:
        """
        Run full evaluation suite and produce a comprehensive report.

        Args:
            dataset: EvalDataset with ground truth.
            answers: Optional generated answers (for generation eval).
            sources: Optional cited sources (for generation eval).
            retrieved_chunks: Optional retrieved chunks (for generation eval).
            compare_reranking: Whether to compare reranking impact.

        Returns:
            EvaluationReport with all metrics.
        """
        logger.info(f"Starting full evaluation on dataset: {dataset.name}")
        start = time.perf_counter()

        retrieval = self.run_retrieval_evaluation(dataset, compare_reranking)

        if answers and sources:
            generation = self.run_generation_evaluation(
                dataset, answers, sources, retrieved_chunks
            )
        else:
            generation = {}
            logger.info("Skipping generation evaluation (no answers/sources provided)")

        pipeline = self.run_pipeline_evaluation(dataset)

        reranking = retrieval.get("reranking_comparison", {})

        # Compute overall score
        score_components = []

        # Retrieval contribution (40% weight)
        if retrieval.get("aggregated_metrics"):
            p5 = retrieval["aggregated_metrics"].get("precision@5", 0.0)
            r5 = retrieval["aggregated_metrics"].get("recall@5", 0.0)
            ndcg5 = retrieval["aggregated_metrics"].get("ndcg@5", 0.0)
            retrieval_score = (p5 + r5 + ndcg5) / 3.0
            score_components.append(("retrieval", retrieval_score, 0.4))

        # Reranking impact (20% weight)
        if reranking.get("deltas"):
            deltas = reranking["deltas"]
            improvement = sum(
                d.get("delta", 0.0)
                for d in deltas.values()
                if isinstance(d, dict) and "delta" in d
            )
            avg_delta = improvement / len(deltas) if deltas else 0.0
            reranking_score = max(0.0, min(1.0, 0.5 + avg_delta))
            score_components.append(("reranking", reranking_score, 0.2))

        # Pipeline reliability (20% weight)
        if pipeline.get("aggregated_metrics"):
            pipeline_agg = pipeline["aggregated_metrics"]
            error_rate = pipeline_agg.get("error_rate", 0.0)
            reliability_score = 1.0 - error_rate
            score_components.append(("reliability", reliability_score, 0.2))

        # Generation quality (20% weight)
        if generation.get("aggregated_metrics"):
            gen_agg = generation["aggregated_metrics"]
            keyword_cov = gen_agg.get("avg_keyword_coverage") or 0.0
            citation_acc = gen_agg.get("avg_citation_accuracy") or 0.0
            faithfulness = gen_agg.get("avg_faithfulness_score") or 0.0
            generation_score = (keyword_cov + citation_acc + faithfulness) / 3.0
            score_components.append(("generation", generation_score, 0.2))

        # Renormalize weights so missing components don't drag down the score
        total_weight = sum(weight for _, _, weight in score_components)
        if total_weight > 0:
            overall = sum(score * weight for score, _, weight in score_components) / total_weight
        else:
            overall = 0.0

        report = EvaluationReport(
            dataset_name=dataset.name,
            retrieval=retrieval,
            generation=generation,
            pipeline=pipeline,
            reranking_comparison=reranking,
            overall_score=overall,
            summary={
                "total_queries": len(dataset.queries),
                "wall_time_seconds": time.perf_counter() - start,
                "score_components": {
                    name: {"score": score, "weight": round(weight / total_weight, 4) if total_weight > 0 else 0.0}
                    for name, score, weight in score_components
                },
            },
        )

        logger.info(
            f"Full evaluation completed in {report.summary['wall_time_seconds']:.2f}s. "
            f"Overall score: {overall:.2%}"
        )
        return report
