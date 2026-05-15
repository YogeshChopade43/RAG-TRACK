"""
Hybrid retrieval service combining BM25 and vector search.

Performs parallel retrieval using both BM25 and vector similarity,
fuses scores with weighted combination, and optionally applies
production-grade reranking as a third layer.
"""

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Any, Optional

from app.core.config import settings
from app.services.retrieval.bm25.service import BM25Service
from app.services.retrieval.retrieval_service import RetrievalService
from app.services.reranking import RerankingService

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

    def _normalize_minmax(self, scores: List[float]) -> List[float]:
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
        weights: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
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

        # Fusion weights (default 0.3 BM25, 0.7 vector)
        w_bm25 = weights.get("bm25", 0.3)
        w_vector = weights.get("vector", 0.7)
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
        vector_results: List[Dict[str, Any]] = []
        bm25_results: List[Dict[str, Any]] = []

        # Fetch enough candidates for fusion (use larger fetch_k to ensure good fusion)
        fetch_k = max(top_k, 10)

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
        # Step 2: Normalize scores per modality
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
        # Step 3: Fuse scores by chunk_id
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

            # Get normalized scores (default to 0.0 if missing from either modality)
            v_norm = v_res["_vector_norm"] if v_res else 0.0
            b_norm = b_res["_bm25_norm"] if b_res else 0.0

            # Weighted combination
            fused_score = w_vector * v_norm + w_bm25 * b_norm

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
                    "vector": round(v_norm, 4),
                    "bm25": round(b_norm, 4),
                },
            })

        # Sort by fused score descending
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
