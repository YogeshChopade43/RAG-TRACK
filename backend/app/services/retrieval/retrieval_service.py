"""
Retrieval service for RAG-TRACK.

Uses FAISS for fast similarity search.
"""

import json
import logging
from typing import Any, Dict

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

from app.core.config import settings

logger = logging.getLogger(__name__)


class RetrievalService:
    """
    Handles semantic retrieval for a specific document.

    Uses FAISS index for fast similarity search.
    """

    def __init__(self):
        """Initialize retrieval service."""
        logger.debug("Initializing RetrievalService")
        self.model = SentenceTransformer(settings.embedding_model)

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

    def search(
        self,
        document_id: str,
        query: str,
        top_k: int = 3,
    ) -> Dict[str, Any]:
        """
        Performs semantic search inside ONE document using FAISS.

        Args:
            document_id: UUID of the uploaded document
            query: Search query string
            top_k: Number of results to return

        Returns:
            Dict with search results
        """
        index, metadata = self._load_index(document_id)

        if index is None:
            return {
                "matches": [],
                "message": "No embeddings found for this document. Upload and ingest first.",
            }

        # Encode query
        logger.debug(f"Encoding query, length: {len(query)}")
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
                    }
                )

        logger.info(
            f"Retrieval completed for document {document_id}, results: {len(results)}"
        )
        return {"matches": results}

    def __repr__(self) -> str:
        """String representation."""
        return f"RetrievalService(model={settings.embedding_model})"
