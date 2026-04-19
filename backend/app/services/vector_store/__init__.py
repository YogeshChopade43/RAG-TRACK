"""
Vector store abstraction for RAG-TRACK.

Provides pluggable vector store implementations.
"""
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional

import faiss
import numpy as np

logger = logging.getLogger(__name__)


class VectorStore(ABC):
    """Abstract base class for vector stores."""

    @abstractmethod
    def add_vectors(
        self,
        vectors: np.ndarray,
        metadata: List[Dict[str, Any]],
        document_id: str,
    ) -> Dict[str, str]:
        """
        Add vectors to the store.

        Args:
            vectors: Embedding vectors
            metadata: Associated metadata
            document_id: Document identifier

        Returns:
            Dict with paths to saved data
        """
        pass

    @abstractmethod
    def search(
        self,
        query_vector: np.ndarray,
        document_id: str,
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Search for similar vectors.

        Args:
            query_vector: Query embedding
            document_id: Document to search in
            top_k: Number of results

        Returns:
            List of search results with scores
        """
        pass

    @abstractmethod
    def delete(self, document_id: str) -> bool:
        """
        Delete vectors for a document.

        Args:
            document_id: Document to delete

        Returns:
            True if deleted
        """
        pass

    @abstractmethod
    def exists(self, document_id: str) -> bool:
        """
        Check if document exists.

        Args:
            document_id: Document to check

        Returns:
            True if exists
        """
        pass


class FaissVectorStore(VectorStore):
    """FAISS-based vector store implementation."""

    def __init__(self, storage_dir: Path):
        """
        Initialize FAISS vector store.

        Args:
            storage_dir: Directory for storing indices
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Initialized FAISS vector store at {self.storage_dir}")

    def _get_index_path(self, document_id: str) -> Path:
        """Get path to index file."""
        return self.storage_dir / f"{document_id}.index"

    def _get_metadata_path(self, document_id: str) -> Path:
        """Get path to metadata file."""
        return self.storage_dir / f"{document_id}_metadata.json"

    def add_vectors(
        self,
        vectors: np.ndarray,
        metadata: List[Dict[str, Any]],
        document_id: str,
    ) -> Dict[str, str]:
        """Add vectors using FAISS."""
        import json

        # Create index
        dim = vectors.shape[1]
        index = faiss.IndexFlatL2(dim)
        index.add(vectors.astype("float32"))

        # Save index
        index_path = self._get_index_path(document_id)
        faiss.write_index(index, str(index_path))

        # Save metadata
        metadata_path = self._get_metadata_path(document_id)
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)

        logger.info(
            f"Added vectors",
            document_id=document_id,
            count=len(metadata),
        )

        return {
            "index_path": str(index_path),
            "metadata_path": str(metadata_path),
        }

    def search(
        self,
        query_vector: np.ndarray,
        document_id: str,
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """Search using FAISS."""
        import json

        index_path = self._get_index_path(document_id)
        metadata_path = self._get_metadata_path(document_id)

        if not index_path.exists():
            return []

        # Load index
        index = faiss.read_index(str(index_path))

        # Load metadata
        with open(metadata_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)

        # Search
        query_vector = query_vector.reshape(1, -1).astype("float32")
        distances, indices = index.search(query_vector, top_k)

        # Format results
        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx < len(metadata):
                score = 1.0 / (1.0 + dist)
                results.append({
                    "score": round(score, 4),
                    **metadata[idx],
                })

        return results

    def delete(self, document_id: str) -> bool:
        """Delete vector store files."""
        index_path = self._get_index_path(document_id)
        metadata_path = self._get_metadata_path(document_id)

        deleted = False
        if index_path.exists():
            index_path.unlink()
            deleted = True
        if metadata_path.exists():
            metadata_path.unlink()
            deleted = True

        if deleted:
            logger.info(f"Deleted vectors for document: {document_id}")

        return deleted

    def exists(self, document_id: str) -> bool:
        """Check if document exists."""
        return self._get_index_path(document_id).exists()


def get_vector_store() -> VectorStore:
    """Get configured vector store instance."""
    from app.core.config import settings

    store_type = settings.vector_store_type

    if store_type == "faiss":
        return FaissVectorStore(settings.vector_store_dir)

    # Default to FAISS
    logger.warning(f"Unknown store type: {store_type}, defaulting to FAISS")
    return FaissVectorStore(settings.vector_store_dir)