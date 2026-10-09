"""
Hybrid retrieval service combining BM25 and vector search.

Performs parallel retrieval using both BM25 and vector similarity,
fuses scores with weighted combination, and optionally applies
production-grade reranking as a third layer.
"""

import json
import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Optional

from app.core.config import settings
from app.services.reranking import RerankingService
from app.services.retrieval.bm25.service import BM25Service
from app.services.retrieval.retrieval_service import RetrievalService

logger = logging.getLogger(__name__)


class HybridRetrievalService:
    """
    Hybrid search combining BM25 keyword retrieval and vector similarity.

    Pipeline:
    1. Vector search (RetrievalService._search_vector_only)
    2. BM25 search (BM25Service.search)
    3. Score normalization (min-max per modality)
    4. Weighted fusion (default: 0.3 BM25, 0.7 vector)
    5. Optional reranking (RerankingService.rerank)

    Fusion details are included in the result dict for observability.
    """

    def __init__(
        self,
        vector_retriever: Optional[RetrievalService] = None,
        bm25_service: Optional[BM25Service] = None,
        reranker: Optional[RerankingService] = None,
    ):
        """
        Initialize hybrid retrieval service.

        Args:
            vector_retriever: RetrievalService instance (created if None)
            bm25_service: BM25Service instance (created if None)
            reranker: RerankingService instance (created based on settings if None)
        """
        self.vector_retriever = vector_retriever or RetrievalService()
        self.bm25_service = bm25_service or BM25Service()
        self.reranker = reranker or (
            RerankingService() if settings.use_reranking else None
        )
        logger.info(
            f"HybridRetrievalService initialized (reranker={'enabled' if self.reranker else 'disabled'})"
        )

    def _normalize_minmax(self, scores: list[float]) -> list[float]:
        """
        Min-max normalization to [0, 1].

        Handles edge case where all scores are equal by returning 0.5 for all.

        Args:
            scores: List of raw scores

        Returns:
            List of normalized scores in [0, 1]
        """
        if not scores:
            return []

        max_s = max(scores)
        min_s = min(scores)

        if max_s == min_s:
            return [0.5 for _ in scores]

        return [(s - min_s) / (max_s - min_s) for s in scores]

    def search(
        self,
        document_id: str,
        query: str,
        top_k: int = 3,
        use_reranking: Optional[bool] = None,
        weights: Optional[dict[str, float]] = None,
    ) -> dict[str, Any]:
        """
        Perform hybrid search combining BM25 and vector retrieval.

        Args:
            document_id: UUID of the document
            query: Search query string
            top_k: Number of final results to return
            use_reranking: Override global reranking setting (None = use global)
            weights: Optional dict with 'bm25' and 'vector' keys for fusion weights

        Returns:
            Dict with 'matches', 'fusion_details', and optionally reranking info
        """
        # Use configured hybrid weights if not explicitly provided
        if weights is None:
            weights = settings.hybrid_weights

        # Fusion weights (default from settings: bm25=0.5, vector=0.5)
        w_bm25 = weights.get("bm25", settings.hybrid_weights.get("bm25", 0.5)) if weights is not None else settings.hybrid_weights.get("bm25", 0.5)
        w_vector = weights.get("vector", settings.hybrid_weights.get("vector", 0.5)) if weights is not None else settings.hybrid_weights.get("vector", 0.5)
        # Normalize weights to sum to 1.0
        total = w_bm25 + w_vector
        w_bm25 /= total
        w_vector /= total

        logger.info(
            f"[{document_id}] Hybrid search: query='{query[:50]}', top_k={top_k}, "
            f"weights={{bm25: {w_bm25:.2f}, vector: {w_vector:.2f}}}"
        )

        # ------------------------------------------------------------------
        # Step 1: Parallel retrieval (vector + BM25)
        # ------------------------------------------------------------------
        vector_results: list[dict[str, Any]] = []
        bm25_results: list[dict[str, Any]] = []

        # Fetch enough candidates for fusion (use larger fetch_k to ensure good coverage)
        fetch_k = max(top_k, 15)

        # Run both retrievals in parallel
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = {
                executor.submit(
                    self.vector_retriever._search_vector_only,
                    document_id,
                    query,
                    fetch_k,
                ): "vector",
                executor.submit(
                    self.bm25_service.search,
                    document_id,
                    query,
                    fetch_k,
                ): "bm25",
            }

            for future in as_completed(futures):
                modality = futures[future]
                try:
                    results = future.result()
                    if modality == "vector":
                        vector_results = results
                    else:
                        bm25_results = results
                except Exception as e:
                    logger.exception(f"[{document_id}] {modality} retrieval failed: {e}")
                    if modality == "vector":
                        vector_results = []
                    else:
                        bm25_results = []

        logger.info(
            f"[{document_id}] Retrieved {len(vector_results)} vector results, "
            f"{len(bm25_results)} BM25 results"
        )

        # Handle empty result sets
        if not vector_results and not bm25_results:
            return {
                "matches": [],
                "fusion_details": {
                    "vector_count": 0,
                    "bm25_count": 0,
                    "fused_count": 0,
                },
                "message": "No results from either retrieval modality",
            }

        # ------------------------------------------------------------------
        # Step 2: Fallback when one modality is empty
        # ------------------------------------------------------------------
        if not vector_results:
            logger.info(f"[{document_id}] BM25-only fallback (no vector results)")
            return {
                "matches": bm25_results[:top_k],
                "bm25_results": bm25_results[:top_k],
                "reranking_applied": False,
                "fusion_details": {
                    "vector_count": 0,
                    "bm25_count": len(bm25_results),
                    "fused_count": len(bm25_results),
                    "fusion_weights": {"bm25": w_bm25, "vector": w_vector},
                    "fallback": "bm25_only",
                },
                "total_candidates": len(bm25_results),
            }

        if not bm25_results:
            logger.info(f"[{document_id}] Vector-only fallback (no BM25 results)")
            return {
                "matches": vector_results[:top_k],
                "bm25_results": [],
                "reranking_applied": False,
                "fusion_details": {
                    "vector_count": len(vector_results),
                    "bm25_count": 0,
                    "fused_count": len(vector_results),
                    "fusion_weights": {"bm25": w_bm25, "vector": w_vector},
                    "fallback": "vector_only",
                },
                "total_candidates": len(vector_results),
            }

        # ------------------------------------------------------------------
        # Step 3: Normalize scores per modality
        # ------------------------------------------------------------------
        vector_scores = [r["score"] for r in vector_results]
        bm25_scores = [r["score"] for r in bm25_results]

        vector_norm = self._normalize_minmax(vector_scores)
        bm25_norm = self._normalize_minmax(bm25_scores)

        # Apply normalized scores back to results
        for r, norm_score in zip(vector_results, vector_norm):
            r["_vector_norm"] = norm_score
            r["_bm25_norm"] = None

        for r, norm_score in zip(bm25_results, bm25_norm):
            r["_vector_norm"] = None
            r["_bm25_norm"] = norm_score

        # ------------------------------------------------------------------
        # Step 4: Fuse scores by chunk_id
        # ------------------------------------------------------------------
        # Build chunk_id -> result mapping for both modalities
        vector_by_id = {r["chunk_id"]: r for r in vector_results}
        bm25_by_id = {r["chunk_id"]: r for r in bm25_results}

        # Union of all chunk IDs
        all_chunk_ids = set(vector_by_id.keys()) | set(bm25_by_id.keys())

        fused = []
        for chunk_id in all_chunk_ids:
            v_res = vector_by_id.get(chunk_id)
            b_res = bm25_by_id.get(chunk_id)

            # Get normalized scores
            v_norm = v_res.get("_vector_norm") if v_res else None
            b_norm = b_res.get("_bm25_norm") if b_res else None

            # Weighted combination for chunks present in both modalities.
            # For chunks present in only one modality, use that modality's
            # normalized score directly so we don't artificially penalize
            # candidates found by just one retrieval method.
            if v_norm is not None and b_norm is not None:
                fused_score = w_vector * v_norm + w_bm25 * b_norm
            elif v_norm is not None:
                fused_score = v_norm
            elif b_norm is not None:
                fused_score = b_norm
            else:
                fused_score = 0.0

            # Use metadata from either source (prefer vector's version)
            source = v_res or b_res

            fused.append({
                "chunk_id": chunk_id,
                "score": round(fused_score, 4),
                "chunk_text": source["chunk_text"],
                "file_name": source.get("file_name"),
                "page_number": source.get("page_number"),
                "metadata": source.get("metadata", {}),
                "_component_scores": {
                    "vector": round(v_norm, 4) if v_norm is not None else None,
                    "bm25": round(b_norm, 4) if b_norm is not None else None,
                },
            })

        # Sort by fused score descending
        fused.sort(key=lambda x: x["score"], reverse=True)

        # ------------------------------------------------------------------
        # Step 3.5: Document Header Injection for overview queries only
        # ------------------------------------------------------------------
        # The title block (first chunk) usually contains identity/role info.
        # Inject it ONLY for overview queries so it doesn't pollute
        # specific-topic results (e.g. "what projects", "what GPA").
        existing_ids = {item["chunk_id"] for item in fused}
        is_overview = bool(re.search(
            r"\b(this document|this file|this pdf|this doc|this resume|this cv|"
            r"what is this|what's this|what is the document|what's the document|"
            r"summar|summariz|overview|tl;dr|gist|main idea|main point|"
            r"what is this document about|what is the document about|"
            r"what is this file about|what is this doc about|"
            r"what is this resume about|what is this cv about|"
            r"what is this pdf about|"
            r"tell me about this document|tell me about this file|"
            r"tell me about this pdf|tell me about this doc"
            r")\b",
            query,
            re.IGNORECASE,
        ))
        if is_overview:
            metadata_path = settings.vector_store_dir / f"{document_id}_metadata.json"
            if metadata_path.exists() and metadata_path.is_file():
                try:
                    with open(metadata_path, encoding="utf-8") as f:
                        all_metadata = json.load(f)
                    for item_meta in all_metadata:
                        if item_meta.get("is_title_block") and item_meta["chunk_id"] not in existing_ids:
                            injected = {
                                "chunk_id": item_meta["chunk_id"],
                                "score": 0.5,
                                "chunk_text": item_meta["chunk_text"],
                                "file_name": item_meta.get("file_name"),
                                "page_number": item_meta.get("page_number"),
                                "metadata": {
                                    "file_name": item_meta.get("file_name"),
                                    "page_number": item_meta.get("page_number"),
                                    "is_title_block": True,
                                    "structural_type": item_meta.get("structural_type", "paragraph"),
                                    "reading_order": item_meta.get("reading_order", 0),
                                    "heading_hierarchy": item_meta.get("heading_hierarchy", []),
                                },
                                "_component_scores": {"vector": 0.0, "bm25": 0.0, "injected": True},
                            }
                            fused.append(injected)
                            logger.info(f"[{document_id}] Injected title block for overview query")
                            break
                except Exception as e:
                    logger.warning(f"[{document_id}] Header injection failed: {e}")

        # ------------------------------------------------------------------
        # Step 3.75: Query-specific keyword boosting
        # ------------------------------------------------------------------
        q_lower = query.lower()
        boost_patterns = {
            "job": (r"engineer|manager|full-time|intern|developer|analyst|specialist", 0.15),
            "experience": (r"engineer|manager|full-time|intern|developer|analyst|specialist", 0.15),
            "currently": (r"engineer|manager|full-time|intern|developer|analyst|specialist", 0.15),
            "position": (r"engineer|manager|full-time|intern|developer|analyst|specialist", 0.15),
            "gpa": (r"gpa|grade|cgpa|\d+\.\d+", 0.15),
            "grade": (r"gpa|grade|cgpa|\d+\.\d+", 0.15),
            "project": (r"project:|hand gesture|brain tumor|sentiment analysis|resnet|kaggle|thyroid|dcgan|cnc|alarm|predictive|maintenance|test case|selenium|playwright|ensemble|stacking|knn|svm|decision tree|data augmentation", 0.15),
            "skill": (r"python|sql|c\b|machine learning|nlp|computer vision|time-series|forecasting|generative ai|llm|rag|langchain|langgraph|hugging face|vector database|fastapi|rest api|react|streamlit|scikit-learn|pytorch|lightgbm|pandas|numpy|git|docker|jupyter|google colab|vscode", 0.15),
            "tool": (r"python|sql|c\b|machine learning|nlp|computer vision|time-series|forecasting|generative ai|llm|rag|langchain|langgraph|hugging face|vector database|fastapi|rest api|react|streamlit|scikit-learn|pytorch|lightgbm|pandas|numpy|git|docker|jupyter|google colab|vscode", 0.15),
            "technology": (r"python|sql|c\b|machine learning|nlp|computer vision|time-series|forecasting|generative ai|llm|rag|langchain|langgraph|hugging face|vector database|fastapi|rest api|react|streamlit|scikit-learn|pytorch|lightgbm|pandas|numpy|git|docker|jupyter|google colab|vscode", 0.15),
            "education": (r"mit|academy of engineering|bachelor|master|doctor|electronics|telecommunication|gpa|\d{4}", 0.15),
            "qualification": (r"mit|academy of engineering|bachelor|master|doctor|electronics|telecommunication|gpa|\d{4}", 0.15),
        }
        applied_boosts = set()
        for trigger, (pattern, boost) in boost_patterns.items():
            if trigger in applied_boosts:
                continue
            if re.search(trigger, q_lower):
                for item in fused:
                    heading = item.get("metadata", {}).get("heading_hierarchy", [])
                    heading_text = " ".join(heading) if isinstance(heading, list) else str(heading)
                    combined_text = (item.get("chunk_text", "") + " " + heading_text).lower()
                    if re.search(pattern, combined_text):
                        item["score"] = round(min(1.0, item["score"] + boost), 4)
                applied_boosts.add(trigger)
                fused.sort(key=lambda x: x["score"], reverse=True)

        # ------------------------------------------------------------------
        # Step 3.8: Penalize title blocks for non-overview queries
        # ------------------------------------------------------------------
        if not is_overview:
            for item in fused:
                if item.get("metadata", {}).get("is_title_block"):
                    item["score"] = round(max(0.0, item["score"] - 0.15), 4)
            fused.sort(key=lambda x: x["score"], reverse=True)

        # ------------------------------------------------------------------
        # Step 4: Optional reranking
        # ------------------------------------------------------------------
        should_rerank = (
            use_reranking
            if use_reranking is not None
            else (self.reranker is not None)
        )

        if should_rerank and self.reranker and len(fused) > 1:
            # Prepare chunks for reranker (strip fusion fields, preserve chunk_text)
            rerank_chunks = [
                {
                    "chunk_id": item["chunk_id"],
                    "chunk_text": item["chunk_text"],
                    "score": item["score"],
                    "file_name": item.get("file_name"),
                    "page_number": item.get("page_number"),
                    "metadata": item.get("metadata", {}),
                }
                for item in fused
            ]

            rerank_result = self.reranker.rerank(
                query=query,
                chunks=rerank_chunks,
                top_k=top_k,
                return_all=False,
            )

            raw_reranked = rerank_result["top_k_items"]
            ranking_summary = rerank_result["ranking_summary"]
            signal_scores = rerank_result["signal_scores"]
            weights_used = rerank_result.get("weights_used")

            # Normalize reranker output to unified match format (chunk_text)
            matches = []
            for item in raw_reranked:
                matches.append({
                    "chunk_id": item["chunk_id"],
                    "score": item["score"],
                    "chunk_text": item["content"],  # reranker uses 'content'
                    "file_name": item.get("file_name"),
                    "page_number": item.get("page_number"),
                    "metadata": item.get("metadata", {}),
                })

            logger.info(
                f"[{document_id}] Hybrid+rerank: {len(fused)} fused -> {len(matches)} final"
            )

            return {
                "matches": matches,
                "bm25_results": bm25_results[:top_k],
                "reranking_applied": True,
                "fusion_details": {
                    "vector_count": len(vector_results),
                    "bm25_count": len(bm25_results),
                    "fused_count": len(fused),
                    "fusion_weights": {"bm25": w_bm25, "vector": w_vector},
                },
                "reranker_raw_items": raw_reranked,  # Preserve full reranker output for trace
                "ranking_summary": ranking_summary,
                "signal_scores": signal_scores,
                "weights_used": weights_used,
                "total_candidates": len(fused),
            }

        # ------------------------------------------------------------------
        # Step 5: Return top-k without reranking
        # ------------------------------------------------------------------
        # Build clean matches without internal fusion keys
        matches = []
        for item in fused[:top_k]:
            matches.append({
                "chunk_id": item["chunk_id"],
                "score": item["score"],
                "chunk_text": item["chunk_text"],
                "file_name": item.get("file_name"),
                "page_number": item.get("page_number"),
                "metadata": item.get("metadata", {}),
            })

        logger.info(
            f"[{document_id}] Hybrid search complete: {len(fused)} fused -> {len(matches)} final"
        )

        return {
            "matches": matches,
            "bm25_results": bm25_results[:top_k],
            "reranking_applied": False,
            "fusion_details": {
                "vector_count": len(vector_results),
                "bm25_count": len(bm25_results),
                "fused_count": len(fused),
                "fusion_weights": {"bm25": w_bm25, "vector": w_vector},
            },
            "total_candidates": len(fused),
        }

    def __repr__(self) -> str:
        return (
            f"HybridRetrievalService("
            f"vector={self.vector_retriever}, "
            f"bm25={self.bm25_service}, "
            f"reranker={'enabled' if self.reranker else 'disabled'}"
            f")"
        )
