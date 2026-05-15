""""
Retrieval service for RAG-TRACK.

Uses FAISS for fast similarity search, with optional production-grade
reranking to refine and reorder results.
"""

import json
import logging
from typing import Any, Dict, List, Optional

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

from app.core.config import settings
from app.services.reranking import RerankingService

logger = logging.getLogger(__name__)


class RetrievalService:
    """
    Handles semantic retrieval for a specific document.

    Uses FAISS index for fast similarity search, with optional reranking
    to refine results based on multiple ranking signals.
    """

    def __init__(self):
        """Initialize retrieval service."""
        logger.debug("Initializing RetrievalService")
        self.model = SentenceTransformer(settings.embedding_model)
        self.reranker = RerankingService() if settings.use_reranking else None

    def _load_index(self, document_id: str):
        """
        Load FAISS index and metadata for a specific document.

        Args:
            document_id: UUID of the document

        Returns:
            Tuple of (faiss_index, metadata_list)
        """
        index_path = settings.vector_store_dir / f"{document_id}.index"
        metadata_path = settings.vector_store_dir / f"{document_id}_metadata.json"

        if not index_path.exists():
            logger.warning(
                f"No FAISS index found for document {document_id} at {index_path}"
            )
            return None, []

        # Load index
        index = faiss.read_index(str(index_path))

        # Load metadata
        with open(metadata_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)

        logger.info(
            f"Loaded FAISS index for document {document_id}, vectors: {index.ntotal}"
        )
        return index, metadata

    def _search_vector_only(
        self,
        document_id: str,
        query: str,
        top_k: int = 3,
    ) -> List[Dict[str, Any]]:
        """
        Perform pure vector similarity search without reranking.

        Extracted for use in hybrid search (vector + BM25 fusion).

        Args:
            document_id: UUID of the document
            query: Search query string
            top_k: Number of results to return

        Returns:
            List of result dicts with score, chunk_text, metadata, etc.
        """
        index, metadata = self._load_index(document_id)

        if index is None:
            return []

        # Encode query
        logger.debug(f"Encoding query for vector search, length: {len(query)}")
        query_embedding = self.model.encode(query)
        query_embedding = query_embedding.astype("float32")
        query_embedding = query_embedding.reshape(1, -1)

        # Search
        distances, indices = index.search(query_embedding, top_k)

        # Format results
        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx < len(metadata):
                item = metadata[idx]
                score = 1.0 / (1.0 + dist)
                results.append(
                    {
                        "score": round(score, 4),
                        "chunk_text": item["chunk_text"],
                        "file_name": item["file_name"],
                        "page_number": item["page_number"],
                        "chunk_id": item["chunk_id"],
                        "metadata": {
                            "file_name": item.get("file_name"),
                            "page_number": item.get("page_number"),
                        },
                    }
                )

        logger.info(
            f"Vector search returned {len(results)} candidates for document {document_id}"
        )
        return results

    def search(
        self,
        document_id: str,
        query: str,
        top_k: int = 3,
        use_reranking: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """
        Performs semantic search inside ONE document using FAISS.

        Optionally applies production-grade reranking to refine results
        using multiple ranking signals (semantic similarity, keyword overlap,
        score calibration, and optional LLM-based relevance).

        Args:
            document_id: UUID of the uploaded document
            query: Search query string
            top_k: Number of results to return
            use_reranking: Override global reranking setting (None = use global)

        Returns:
            Dict with search results and ranking metadata
        """
        index, metadata = self._load_index(document_id)

        if index is None:
            return {
                "matches": [],
                "message": "No embeddings found for this document. Upload and ingest first.",
            }

        # Determine if reranking should be used
        should_rerank = (
            use_reranking
            if use_reranking is not None
            else (self.reranker is not None)
        )

        # Encode query
        logger.debug(f"Encoding query, length: {len(query)}")
        query_embedding = self.model.encode(query)
        query_embedding = query_embedding.astype("float32")
        query_embedding = query_embedding.reshape(1, -1)

        # Determine how many results to fetch for reranking
        fetch_k = top_k
        if should_rerank:
            # Fetch more candidates for reranking to have better selection
            fetch_k = min(settings.rerank_top_k, index.ntotal) if index.ntotal > 0 else top_k
            fetch_k = max(fetch_k, top_k)

        # Search
        distances, indices = index.search(query_embedding, fetch_k)

        # Format initial results
        initial_results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx < len(metadata):
                item = metadata[idx]
                score = 1.0 / (1.0 + dist)
                initial_results.append(
                    {
                        "score": round(score, 4),
                        "chunk_text": item["chunk_text"],
                        "file_name": item["file_name"],
                        "page_number": item["page_number"],
                        "chunk_id": item["chunk_id"],
                        "metadata": {
                            "file_name": item.get("file_name"),
                            "page_number": item.get("page_number"),
                        },
                    }
                )

        logger.info(
            f"Retrieved {len(initial_results)} candidates for document {document_id}"
        )

        # Apply reranking if enabled
        if should_rerank and self.reranker and len(initial_results) > 1:
            rerank_result = self.reranker.rerank(
                query=query,
                chunks=initial_results,
                top_k=top_k,
                return_all=False,
            )

            matches = rerank_result["top_k_items"]
            ranking_summary = rerank_result["ranking_summary"]
            signal_scores = rerank_result["signal_scores"]

            logger.info(
                f"Reranking applied: {len(initial_results)} -> {len(matches)} results, "
                f"mean_score={ranking_summary.get('mean_score', 0):.4f}"
            )

            return {
                "matches": matches,
                "reranking_applied": True,
                "ranking_summary": ranking_summary,
                "signal_scores": signal_scores,
                "weights_used": rerank_result.get("weights_used"),
                "total_candidates": len(initial_results),
            }

        # Fallback: return top-k without reranking
        matches = initial_results[:top_k]
        logger.info(f"Returning {len(matches)} results without reranking")

        return {
            "matches": matches,
            "reranking_applied": False,
            "total_candidates": len(initial_results),
        }

    def __repr__(self) -> str:
        """String representation."""
        rerank_status = "enabled" if self.reranker else "disabled"
        return (
            f"RetrievalService(model={settings.embedding_model}, "
            f"reranking={rerank_status})"
        )
