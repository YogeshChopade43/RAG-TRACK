"""
Generation quality evaluation.

Evaluates the quality of generated answers against ground truth,
focusing on faithfulness, relevance, and citation accuracy.
"""

import logging
import re
from typing import Any, Dict, List, Optional, Union

from app.evaluation.dataset import EvalDataset, EvalQuery

logger = logging.getLogger(__name__)


class GenerationEvaluator:
    """
    Evaluates generation quality of RAG answers.

    Metrics include:
    - Answer length and structure
    - Citation accuracy (do cited pages actually contain the answer?)
    - Keyword overlap with expected answer
    - Faithfulness proxy (does the answer contain unsupported claims?)
    """

    def __init__(self):
        pass

    def evaluate_query(
        self,
        query: EvalQuery,
        answer: str,
        sources: List[Dict[str, Any]],
        retrieved_chunks: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Evaluate generation quality for a single query.

        Args:
            query: EvalQuery with expected answer keywords.
            answer: Generated answer text.
            sources: List of cited sources {file_name, page_number}.
            retrieved_chunks: Optional list of chunks used for generation.

        Returns:
            Dict with generation quality metrics.
        """
        result = {
            "query_id": query.query_id,
            "question": query.question,
            "answer": answer,
            "answer_length": len(answer),
            "word_count": len(answer.split()),
            "metrics": {},
        }

        # Keyword overlap with expected keywords
        if query.expected_answer_keywords:
            answer_lower = answer.lower()
            matched_keywords = [
                kw for kw in query.expected_answer_keywords
                if kw.lower() in answer_lower
            ]
            result["metrics"]["keyword_coverage"] = len(matched_keywords) / len(query.expected_answer_keywords)
            result["metrics"]["matched_keywords"] = matched_keywords
        else:
            result["metrics"]["keyword_coverage"] = None
            result["metrics"]["matched_keywords"] = []

        # Citation accuracy
        if sources and retrieved_chunks:
            citation_accuracy = self._compute_citation_accuracy(
                answer, sources, retrieved_chunks
            )
            result["metrics"]["citation_accuracy"] = citation_accuracy
        else:
            result["metrics"]["citation_accuracy"] = None

        # Answer structure quality
        result["metrics"]["has_multiple_paragraphs"] = len(re.split(r'\n\s*\n', answer.strip())) > 1
        result["metrics"]["starts_with_answer"] = not re.match(
            r'^(answer|here is|based on)', answer.lower().strip()
        )

        # Error detection
        error_indicators = [
            "i encountered an error",
            "i could not find relevant information",
            "i do not have access",
            "i'm sorry, i cannot",
        ]
        result["metrics"]["has_error"] = any(
            ind in answer.lower() for ind in error_indicators
        )

        # Faithfulness proxy: does the answer introduce claims not in context?
        if retrieved_chunks:
            context_text = " ".join(
                c.get("chunk_text", c.get("content", "")) for c in retrieved_chunks
            ).lower()
            # Simple heuristic: check for numbers/names in answer that aren't in context
            answer_numbers = set(re.findall(r'\b\d+(?:\.\d+)?%?\b', answer))
            context_numbers = set(re.findall(r'\b\d+(?:\.\d+)?%?\b', context_text))
            numbers_in_answer_not_in_context = answer_numbers - context_numbers
            result["metrics"]["unsupported_numbers"] = list(numbers_in_answer_not_in_context)
            result["metrics"]["faithfulness_score"] = (
                1.0 - len(numbers_in_answer_not_in_context) / max(len(answer_numbers), 1)
                if answer_numbers
                else 1.0
            )
        else:
            result["metrics"]["unsupported_numbers"] = []
            result["metrics"]["faithfulness_score"] = None

        return result

    def evaluate_dataset(
        self,
        dataset: EvalDataset,
        answers: Dict[str, str],
        sources: Dict[str, List[Dict[str, Any]]],
        retrieved_chunks: Optional[Dict[str, List[Dict[str, Any]]]] = None,
    ) -> Dict[str, Any]:
        """
        Evaluate generation across all queries.

        Args:
            dataset: EvalDataset with ground truth.
            answers: Dict mapping query_id -> generated answer.
            sources: Dict mapping query_id -> list of cited sources.
            retrieved_chunks: Optional dict mapping query_id -> list of chunks.

        Returns:
            Dict with aggregated generation metrics.
        """
        results = []
        keyword_coverages = []
        citation_accuracies = []
        faithfulness_scores = []
        answer_lengths = []
        error_count = 0

        for query in dataset.queries:
            answer = answers.get(query.query_id, "")
            src = sources.get(query.query_id, [])
            chunks = retrieved_chunks.get(query.query_id) if retrieved_chunks else None

            result = self.evaluate_query(query, answer, src, chunks)
            results.append(result)

            metrics = result["metrics"]
            if metrics.get("keyword_coverage") is not None:
                keyword_coverages.append(metrics["keyword_coverage"])
            if metrics.get("citation_accuracy") is not None:
                citation_accuracies.append(metrics["citation_accuracy"])
            if metrics.get("faithfulness_score") is not None:
                faithfulness_scores.append(metrics["faithfulness_score"])
            answer_lengths.append(result["word_count"])
            if metrics.get("has_error"):
                error_count += 1

        aggregated = {
            "avg_keyword_coverage": (
                sum(keyword_coverages) / len(keyword_coverages) if keyword_coverages else None
            ),
            "avg_citation_accuracy": (
                sum(citation_accuracies) / len(citation_accuracies) if citation_accuracies else None
            ),
            "avg_faithfulness_score": (
                sum(faithfulness_scores) / len(faithfulness_scores) if faithfulness_scores else None
            ),
            "avg_answer_length_words": (
                sum(answer_lengths) / len(answer_lengths) if answer_lengths else None
            ),
            "error_rate": error_count / len(dataset.queries) if dataset.queries else 0.0,
            "total_queries": len(dataset.queries),
            "errors": error_count,
        }

        return {
            "dataset_name": dataset.name,
            "aggregated_metrics": aggregated,
            "per_query_results": results,
        }

    def _compute_citation_accuracy(
        self,
        answer: str,
        sources: List[Dict[str, Any]],
        retrieved_chunks: List[Dict[str, Any]],
    ) -> float:
        """
        Compute citation accuracy: do cited sources actually contain relevant info?

        For each cited source, check if any retrieved chunk from that source/page
        has a relevance score above a threshold.
        """
        if not sources or not retrieved_chunks:
            return 0.0

        chunk_by_source = {}
        for chunk in retrieved_chunks:
            key = (
                chunk.get("file_name", ""),
                chunk.get("page_number", 0),
            )
            chunk_by_source.setdefault(key, []).append(chunk)

        correct_citations = 0
        for source in sources:
            key = (source.get("file_name", ""), source.get("page_number", 0))
            chunks = chunk_by_source.get(key, [])
            if chunks:
                max_score = max(c.get("score", 0.0) for c in chunks)
                if max_score >= 0.2:
                    correct_citations += 1

        return correct_citations / len(sources) if sources else 0.0
