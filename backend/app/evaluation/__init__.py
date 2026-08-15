"""
Evaluation framework for RAG-TRACK.

Provides tools and metrics for:
- Retrieval quality (Precision@K, Recall@K, MRR, nDCG, Hit Rate, MAP)
- Reranking impact analysis
- Generation quality (context utilization, citation accuracy, answer metrics)
- Pipeline performance (latency, throughput, error rate)
- End-to-end evaluation reporting
"""

from app.evaluation.dataset import EvalDataset, EvalQuery
from app.evaluation.generation_eval import GenerationEvaluator
from app.evaluation.metrics import (
    hit_rate,
    mrr,
    ndcg,
    precision_at_k,
    recall_at_k,
    retrieval_metrics_summary,
)
from app.evaluation.pipeline_eval import PipelineEvaluator
from app.evaluation.retrieval_eval import RetrievalEvaluator
from app.evaluation.runner import EvaluationReport, EvaluationRunner

__all__ = [
    "EvalDataset",
    "EvalQuery",
    "EvaluationReport",
    "EvaluationRunner",
    "GenerationEvaluator",
    "PipelineEvaluator",
    "RetrievalEvaluator",
    "hit_rate",
    "mrr",
    "ndcg",
    "precision_at_k",
    "recall_at_k",
    "retrieval_metrics_summary",
]
