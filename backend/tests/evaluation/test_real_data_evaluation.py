"""
End-to-end evaluation tests using real RAG-TRACK system data.

Runs evaluation against the actual resume document in the vector store
and produces a full evaluation report.
"""

import json
import sys
from pathlib import Path

import pytest

backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(backend_dir.parent))

from app.evaluation.dataset import EvalDataset
from app.evaluation.runner import EvaluationRunner

RESUME_DOC_ID = "ab738a78-52ba-4dfb-925f-ee8d4f166628"
DATA_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data"
VECTOR_STORE_DIR = DATA_DIR / "vector_store"


@pytest.mark.skipif(
    not (VECTOR_STORE_DIR / f"{RESUME_DOC_ID}_metadata.json").exists(),
    reason="Resume document not found in vector store",
)
class TestRealDataEvaluation:
    """Evaluation against real system data."""

    def test_load_and_run_resume_evaluation(self, tmp_path):
        dataset_path = (
            Path(__file__).resolve().parent / "datasets" / "resume_eval_v1.json"
        )
        if not dataset_path.exists():
            pytest.skip(f"Evaluation dataset not found at {dataset_path}")

        dataset = EvalDataset.load(dataset_path)
        assert len(dataset) > 0

        runner = EvaluationRunner(top_k=5, use_reranking=True)
        report = runner.run_full_evaluation(dataset)

        assert report.dataset_name == "resume_eval_v1"
        assert report.overall_score > 0.0
        assert "retrieval" in report.to_dict()
        assert "pipeline" in report.to_dict()

        report_path = tmp_path / "evaluation_report.json"
        report.save(report_path)
        assert report_path.exists()

        with open(report_path, encoding="utf-8") as f:
            saved = json.load(f)
        assert saved["dataset_name"] == "resume_eval_v1"
        assert "overall_score" in saved

    def test_retrieval_on_real_resume_document(self):
        from app.evaluation.retrieval_eval import RetrievalEvaluator

        dataset_path = (
            Path(__file__).resolve().parent / "datasets" / "resume_eval_v1.json"
        )
        if not dataset_path.exists():
            pytest.skip(f"Evaluation dataset not found at {dataset_path}")

        dataset = EvalDataset.load(dataset_path)
        resume_queries = dataset.get_by_document(RESUME_DOC_ID)
        if not resume_queries:
            pytest.skip("No queries for resume document in dataset")

        small_dataset = EvalDataset(name="resume_real")
        for q in resume_queries:
            small_dataset.add_query(q)

        evaluator = RetrievalEvaluator(top_k_values=[1, 3, 5, 10])
        result = evaluator.evaluate_dataset(
            small_dataset,
            top_k=5,
            use_reranking=True,
        )

        assert result["num_queries"] > 0
        assert "aggregated_metrics" in result
        agg = result["aggregated_metrics"]

        assert "precision@5" in agg
        assert "recall@5" in agg
        assert "mrr" in agg
        assert "ndcg@5" in agg

        for key, value in agg.items():
            assert 0.0 <= value <= 1.0, f"{key} = {value} out of range [0,1]"

    def test_reranking_comparison_on_real_document(self):
        from app.evaluation.retrieval_eval import RetrievalEvaluator

        dataset_path = (
            Path(__file__).resolve().parent / "datasets" / "resume_eval_v1.json"
        )
        if not dataset_path.exists():
            pytest.skip(f"Evaluation dataset not found at {dataset_path}")

        dataset = EvalDataset.load(dataset_path)
        resume_queries = dataset.get_by_document(RESUME_DOC_ID)
        if not resume_queries:
            pytest.skip("No queries for resume document in dataset")

        small_dataset = EvalDataset(name="resume_real")
        for q in resume_queries:
            small_dataset.add_query(q)

        evaluator = RetrievalEvaluator(top_k_values=[1, 3, 5])
        comparison = evaluator.compare_with_and_without_reranking(
            small_dataset,
            top_k=5,
        )

        assert "deltas" in comparison
        deltas = comparison["deltas"]
        assert "precision@5" in deltas
        assert "recall@5" in deltas
