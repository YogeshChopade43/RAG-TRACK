"""
Embedding service for RAG-TRACK.

Generates embeddings for text chunks using sentence transformers.
"""

import json
import logging
from functools import lru_cache
from typing import Any, Dict, List

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

from app.core.config import settings

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_embedding_model() -> SentenceTransformer:
    """
    Get cached embedding model.

    Uses lru_cache to ensure model is loaded only once.
    """
    logger.info(f"Loading embedding model: {settings.embedding_model}")
    model = SentenceTransformer(settings.embedding_model)
    logger.info("Embedding model loaded successfully")
    return model


class EmbeddingService:
    """
    Converts chunks -> embeddings (vectors).

    Creates FAISS index for fast similarity search.
    """

    def __init__(self):
        """Initialize embedding service with lazy model loading."""
        logger.debug("Initializing EmbeddingService")
        self.model = get_embedding_model()
        settings.vector_store_dir.mkdir(parents=True, exist_ok=True)

    def embed(self, chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate embeddings for chunks and build FAISS index.

        Args:
            chunks: List of chunk dictionaries

        Returns:
            Dict with index path, metadata path, and chunk count

        Raises:
            ValueError: If no chunks provided
        """
        if not chunks:
            raise ValueError("No chunks provided for embedding")

        document_id = chunks[0]["document_id"]

        logger.info(
            f"Generating embeddings for document {document_id}, chunks: {len(chunks)}"
        )

        # Extract texts
        texts = [chunk["chunk_text"] for chunk in chunks]

        # Generate embeddings
        vectors = self.model.encode(
            texts,
            convert_to_numpy=True,
            show_progress_bar=True,
        )

        # Convert to float32 for FAISS
        vectors = vectors.astype("float32")

        # Create FAISS index
        dim = vectors.shape[1]
        index = faiss.IndexFlatL2(dim)
        index.add(vectors)

        # Save index
        index_path = settings.vector_store_dir / f"{document_id}.index"
        faiss.write_index(index, str(index_path))

        # Prepare metadata
        metadata = []
        for chunk in chunks:
            metadata.append(
                {
                    "chunk_id": chunk["chunk_id"],
                    "document_id": chunk["document_id"],
                    "file_name": chunk["file_name"],
                    "page_number": chunk["page_number"],
                    "char_start": chunk["char_start"],
                    "char_end": chunk["char_end"],
                    "chunk_text": chunk["chunk_text"],
                }
            )

        # Save metadata
        metadata_path = settings.vector_store_dir / f"{document_id}_metadata.json"
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)

        logger.info(f"Embeddings generated and saved for document {document_id}")

        return {
            "index_path": str(index_path),
            "metadata_path": str(metadata_path),
            "chunks": len(metadata),
        }

    def __repr__(self) -> str:
        """String representation."""
        return f"EmbeddingService(model={settings.embedding_model})"
