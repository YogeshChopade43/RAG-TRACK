"""
BM25 retrieval service for hybrid search.

Manages per-document BM25 indexes with lazy loading from disk,
caching in memory, and search functionality.
"""

import json
import logging
import pickle
from pathlib import Path
from typing import Dict, List, Any, Optional

from rank_bm25 import BM25Okapi
from sklearn.metrics.pairwise import cosine_similarity

from app.core.config import settings
from app.services.retrieval.bm25.tokenizer import tokenize

logger = logging.getLogger(__name__)


class BM25Service:
    """
    Service for BM25 retrieval on a per-document basis.

    Maintains an in-memory cache of BM25 indexes and lazy-loads from
    disk on first search for each document. Indexes are built during
    ingestion and stored as pickle files.
    """

    def __init__(self):
        """Initialize BM25 service with empty cache."""
        self.indexes: Dict[str, BM25Okapi] = {}
        self.corpus_map: Dict[str, List[Dict[str, Any]]] = {}
        logger.info("BM25Service initialized")

    def build_index(
        self,
        chunks: List[Dict[str, Any]],
        document_id: str
    ) -> Optional[Path]:
        """
        Build and save BM25 index for a document during ingestion.

        Args:
            chunks: List of chunk dictionaries with chunk_text and metadata
            document_id: UUID of the document

        Returns:
            Path to saved BM25 index file, or None on failure
        """
        logger.info(f"[{document_id}] Building BM25 index")

        try:
            if not chunks:
                logger.warning(f"[{document_id}] No chunks provided for BM25 index")
                return None

            # Tokenize each chunk's text
            corpus = [tokenize(chunk["chunk_text"]) for chunk in chunks]

            # Build BM25 index
            bm25 = BM25Okapi(corpus)

            # Create index object with metadata
            index_data = {
                "bm25": bm25,
                "chunks": chunks,
                "document_id": document_id,
            }

            # Save to disk
            bm25_path = settings.vector_store_dir / f"{document_id}_bm25.pkl"
            with open(bm25_path, "wb") as f:
                pickle.dump(index_data, f, protocol=pickle.HIGHEST_PROTOCOL)

            logger.info(
                f"[{document_id}] BM25 index built with {len(chunks)} chunks, "
                f"vocab size: {len(bm25.f) if hasattr(bm25, 'f') else 'N/A'}"
            )

            return bm25_path

        except Exception as e:
            logger.exception(f"[{document_id}] BM25 index build failed: {e}")
            return None

    def load_index(self, document_id: str) -> bool:
        """
        Load BM25 index from disk into memory cache.

        Args:
            document_id: UUID of the document

        Returns:
            True if loaded successfully, False otherwise
        """
        # Return cached if already loaded
        if document_id in self.indexes:
            logger.debug(f"[{document_id}] BM25 index already in cache")
            return True

        bm25_path = settings.vector_store_dir / f"{document_id}_bm25.pkl"

        if not bm25_path.exists():
            logger.warning(f"[{document_id}] No BM25 index file found at {bm25_path}")
            return False

        try:
            with open(bm25_path, "rb") as f:
                index_data = pickle.load(f)

            self.indexes[document_id] = index_data["bm25"]
            self.corpus_map[document_id] = index_data["chunks"]

            logger.info(f"[{document_id}] BM25 index loaded from disk")
            return True

        except Exception as e:
            logger.exception(f"[{document_id}] BM25 index load failed: {e}")
            return False

    def search(
        self,
        document_id: str,
        query: str,
        top_k: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Search document using BM25 scoring.

        Args:
            document_id: UUID of the document
            query: Search query string
            top_k: Number of top results to return

        Returns:
            List of result dicts with chunk_id, score, chunk_text, metadata
        """
        logger.debug(f"[{document_id}] BM25 search: query='{query[:50]}', top_k={top_k}")

        # Lazy load index
        if document_id not in self.indexes:
            if not self.load_index(document_id):
                logger.warning(f"[{document_id}] Cannot search: BM25 index unavailable")
                return []

        bm25 = self.indexes[document_id]
        chunks = self.corpus_map[document_id]

        # Tokenize query
        query_tokens = tokenize(query)

        if not query_tokens:
            logger.warning(f"[{document_id}] Query yielded no tokens after stopword removal")
            return []

        # Get BM25 scores
        scores = bm25.get_scores(query_tokens)

        # Create (chunk, score) pairs and sort by score descending
        chunk_scores = list(zip(chunks, scores))
        chunk_scores.sort(key=lambda x: x[1], reverse=True)

        # Take top-k
        top_results = chunk_scores[:top_k]

        # Format results
        results = []
        for chunk, score in top_results:
            results.append({
                "chunk_id": chunk["chunk_id"],
                "score": float(round(score, 4)),
                "chunk_text": chunk["chunk_text"],
                "file_name": chunk.get("file_name"),
                "page_number": chunk.get("page_number"),
                "metadata": {
                    "file_name": chunk.get("file_name"),
                    "page_number": chunk.get("page_number"),
                },
            })

        logger.info(f"[{document_id}] BM25 returned {len(results)} results")
        return results

    def __repr__(self) -> str:
        return f"BM25Service(cached_docs={len(self.indexes)})"
