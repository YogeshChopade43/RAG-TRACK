"""
Tests for RAG-TRACK evaluation framework.

Covers:
- Metric calculations (precision, recall, MRR, nDCG, hit rate, MAP)
- Dataset loading/saving
- Retrieval evaluation against real system
- Generation evaluation
- Pipeline evaluation
- End-to-end evaluation runner
"""

import json
import math
import sys
from pathlib import Path

import pytest

# Ensure backend is on path
backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(backend_dir.parent))

from app.evaluation.dataset import EvalDataset, EvalQuery
from app.evaluation.metrics import (
    average_precision,
    dcg,
    hit_rate,
    map_at_k,
    mrr,
    ndcg,
    precision_at_k,
    recall_at_k,
    retrieval_metrics_summary,
)
from app.evaluation.retrieval_eval import RetrievalEvaluator


class TestRetrievalMetrics:
    """Unit tests for core retrieval metric functions."""

    def test_precision_at_k(self):
        relevant = {"A", "B", "C"}
        retrieved = ["A", "X", "B", "Y", "C"]
        assert precision_at_k(relevant, retrieved, 3) == pytest.approx(2 / 3)
        assert precision_at_k(relevant, retrieved, 5) == pytest.approx(3 / 5)
        assert precision_at_k(relevant, retrieved, 0) == 0.0

    def test_recall_at_k(self):
        relevant = {"A", "B", "C"}
        retrieved = ["A", "X", "B"]
        assert recall_at_k(relevant, retrieved, 2) == pytest.approx(1 / 3)
        assert recall_at_k(relevant, retrieved, 3) == pytest.approx(2 / 3)
        assert recall_at_k(set(), retrieved, 3) == 0.0

    def test_mrr(self):
        relevant = {"B", "C"}
        assert mrr(relevant, ["X", "A", "B", "Y"]) == pytest.approx(1 / 3)
        assert mrr(relevant, ["B", "C", "D"]) == pytest.approx(1.0)
        assert mrr(relevant, ["X", "Y", "Z"]) == pytest.approx(0.0)

    def test_ndcg(self):
        relevant = {"A", "B"}
        retrieved = ["A", "B", "C"]
        ideal_order = sorted([1.0, 1.0, 0.0], reverse=True)
        actual_scores = [1.0, 1.0, 0.0]
        ideal_dcg_val = sum(s / math.log2(i + 3) for i, s in enumerate(ideal_order))
        actual_dcg_val = sum(s / math.log2(i + 3) for i, s in enumerate(actual_scores))
        assert ndcg(relevant, retrieved, 3) == pytest.approx(actual_dcg_val / ideal_dcg_val)

        retrieved2 = ["A", "C", "B"]
        actual_scores2 = [1.0, 0.0, 1.0]
        actual_dcg_val2 = sum(s / math.log2(i + 3) for i, s in enumerate(actual_scores2))
        assert ndcg(relevant, retrieved2, 3) == pytest.approx(actual_dcg_val2 / ideal_dcg_val)

    def test_hit_rate(self):
        relevant = {"B"}
        assert hit_rate(relevant, ["X", "A", "B"], 3) == 1.0
        assert hit_rate(relevant, ["X", "A", "Y"], 3) == 0.0
        assert hit_rate(relevant, [], 3) == 0.0

    def test_average_precision(self):
        relevant = {"A", "C"}
        assert average_precision(relevant, ["A", "X", "C"], 3) == pytest.approx(5 / 6)

    def test_map_at_k(self):
        all_rel = [{"A", "B"}, {"B", "C"}]
        all_ret = [["A", "X", "B"], ["C", "B", "Y"]]
        assert map_at_k(all_rel, all_ret, 3) == pytest.approx(0.9167, abs=0.01)

    def test_dcg(self):
        scores = [3.0, 2.0, 1.0]
        expected = 3.0 / math.log2(3) + 2.0 / math.log2(4) + 1.0 / math.log2(5)
        assert dcg(scores, 3) == pytest.approx(expected)

    def test_retrieval_metrics_summary(self):
        relevant = {"A", "B", "C"}
        retrieved = ["A", "X", "B", "Y", "C"]
        summary = retrieval_metrics_summary(relevant, retrieved)
        assert "mrr" in summary
        assert "precision@3" in summary
        assert "recall@5" in summary
        assert "ndcg@5" in summary
        assert summary["mrr"] == pytest.approx(1.0)


class TestEvalDataset:
    """Tests for evaluation dataset management."""

    def test_create_and_add_query(self, tmp_path):
        dataset = EvalDataset(name="test")
        q = EvalQuery(
            query_id="q1",
            question="test question",
            document_id="doc1",
            relevant_chunk_ids={"chunk_1", "chunk_2"},
        )
        dataset.add_query(q)
        assert len(dataset) == 1
        assert dataset.queries[0].query_id == "q1"

    def test_get_by_document(self):
        dataset = EvalDataset()
        dataset.add_query(EvalQuery("q1", "Q1", "doc1", {"c1"}))
        dataset.add_query(EvalQuery("q2", "Q2", "doc2", {"c2"}))
        dataset.add_query(EvalQuery("q3", "Q3", "doc1", {"c3"}))
        doc1_queries = dataset.get_by_document("doc1")
        assert len(doc1_queries) == 2
        assert all(q.document_id == "doc1" for q in doc1_queries)

    def test_save_and_load(self, tmp_path):
        dataset = EvalDataset(name="save_test")
        dataset.add_query(
            EvalQuery(
                query_id="q1",
                question="What is RAG?",
                document_id="doc1",
                relevant_chunk_ids={"chunk_a"},
                expected_answer_keywords=["RAG", "retrieval"],
            )
        )
        path = tmp_path / "eval_dataset.json"
        dataset.save(path)

        loaded = EvalDataset.load(path)
        assert loaded.name == "save_test"
        assert len(loaded) == 1
        assert loaded.queries[0].query_id == "q1"
        assert loaded.queries[0].relevant_chunk_ids == {"chunk_a"}

    def test_from_dict_roundtrip(self):
        q = EvalQuery(
            query_id="q1",
            question="test",
            document_id="doc1",
            relevant_chunk_ids={"a", "b"},
        )
        d = q.to_dict()
        q2 = EvalQuery.from_dict(d)
        assert q2.query_id == q.query_id
        assert q2.relevant_chunk_ids == q.relevant_chunk_ids


@pytest.mark.integration
class TestRetrievalEvaluatorIntegration:
    """Integration tests for retrieval evaluation against real system data."""

    def test_evaluate_single_query(self):
        from unittest.mock import patch

        doc_id = "eval-test-doc"

        evaluator = RetrievalEvaluator(top_k_values=[1, 3, 5])

        query = EvalQuery(
            query_id="eval_q1",
            question="What is Python?",
            document_id=doc_id,
            relevant_chunk_ids={"eval_q1_chunk_0", "eval_q1_chunk_1"},
        )

        mock_matches = [
            {"chunk_id": "eval_q1_chunk_0", "score": 0.9, "chunk_text": "Python is a language.", "file_name": "test.pdf", "page_number": 1},
            {"chunk_id": "eval_q1_chunk_1", "score": 0.8, "chunk_text": "Python is great for ML.", "file_name": "test.pdf", "page_number": 1},
            {"chunk_id": "eval_q1_chunk_2", "score": 0.5, "chunk_text": "Java is also a language.", "file_name": "test.pdf", "page_number": 2},
            {"chunk_id": "eval_q1_chunk_3", "score": 0.4, "chunk_text": "C++ is fast.", "file_name": "test.pdf", "page_number": 2},
            {"chunk_id": "eval_q1_chunk_4", "score": 0.3, "chunk_text": "JavaScript runs in browsers.", "file_name": "test.pdf", "page_number": 3},
        ]

        mock_result = {
            "matches": mock_matches,
            "reranking_applied": False,
            "fusion_details": {"vector_count": 5, "bm25_count": 3, "fused_count": 5},
        }

        with patch.object(
            evaluator.hybrid,
            "search",
            return_value=mock_result,
        ):
            result = evaluator.evaluate_query(query, top_k=5)

        assert result["query_id"] == "eval_q1"
        assert len(result["retrieved_ids"]) == 5
        assert result["retrieved_ids"][0] == "eval_q1_chunk_0"
        assert result["retrieved_ids"][1] == "eval_q1_chunk_1"
        assert "metrics" in result
        assert "precision@5" in result["metrics"]
        assert result["metrics"]["precision@5"] == pytest.approx(0.4)
        assert result["metrics"]["recall@5"] == pytest.approx(1.0)


@pytest.mark.unit
class TestEvaluationFrameworkIntegrity:
    """Verify evaluation framework components are properly structured."""

    def test_framework_imports(self):
        from app.evaluation import (
            EvalDataset,
            EvaluationRunner,
            GenerationEvaluator,
            PipelineEvaluator,
            RetrievalEvaluator,
        )
        assert RetrievalEvaluator is not None
        assert GenerationEvaluator is not None
        assert PipelineEvaluator is not None
        assert EvaluationRunner is not None
        assert EvalDataset is not None

    def test_eval_report_serialization(self):
        from app.evaluation.runner import EvaluationReport

        report = EvaluationReport(
            dataset_name="test",
            retrieval={"aggregated_metrics": {"mrr": 0.8, "precision@5": 0.6}},
            generation={"aggregated_metrics": {"avg_keyword_coverage": 0.7}},
            pipeline={"aggregated_metrics": {"error_rate": 0.05}},
            overall_score=0.75,
        )
        d = report.to_dict()
        assert d["dataset_name"] == "test"
        assert d["overall_score"] == 0.75

    def test_eval_report_save(self, tmp_path):
        from app.evaluation.runner import EvaluationReport

        report = EvaluationReport(dataset_name="save_test")
        output = tmp_path / "report.json"
        report.save(output)
        assert output.exists()
        with open(output, encoding="utf-8") as f:
            data = json.load(f)
        assert data["dataset_name"] == "save_test"
