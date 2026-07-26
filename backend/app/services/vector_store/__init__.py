"""
Vector store abstraction for RAG-TRACK.

Provides pluggable vector store implementations.
"""
import logging
import os
import tempfile
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import faiss
import numpy as np

from app.core.config import settings

logger = logging.getLogger(__name__)


def _atomic_write(file_path: Path, data: bytes) -> None:
    """Write binary data atomically using a temp file and rename."""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=file_path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        os.replace(str(tmp_path), str(file_path))
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


class VectorStore(ABC):
    """Abstract base class for vector stores."""

    @abstractmethod
    def add_vectors(
        self,
        vectors: np.ndarray,
        metadata: list[dict[str, Any]],
        document_id: str,
    ) -> dict[str, str]:
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
    ) -> list[dict[str, Any]]:
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
        logger.info("Initialized FAISS vector store at %s", self.storage_dir)

    def _create_index(self, dim: int) -> faiss.Index:
        """Create a FAISS index based on settings."""
        if settings.faiss_index_type == "hnsw":
            index = faiss.IndexHNSWFlat(dim, settings.faiss_hnsw_m)
            index.hnsw.efConstruction = settings.faiss_hnsw_ef_construction
            return index
        return faiss.IndexFlatL2(dim)

    def _get_index_path(self, document_id: str) -> Path:
        """Get path to index file."""
        return self.storage_dir / f"{document_id}.index"

    def _get_metadata_path(self, document_id: str) -> Path:
        """Get path to metadata file."""
        return self.storage_dir / f"{document_id}_metadata.json"

    def add_vectors(
        self,
        vectors: np.ndarray,
        metadata: list[dict[str, Any]],
        document_id: str,
    ) -> dict[str, str]:
        """Add vectors using FAISS."""
        import json

        # Create index
        dim = vectors.shape[1]
        index = self._create_index(dim)
        index.add(vectors.astype("float32"))

        # Save index atomically
        index_path = self._get_index_path(document_id)
        index_path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(dir=index_path.parent, suffix=".tmp")
        try:
            with os.fdopen(fd, "wb") as f:
                faiss.write_index(index, f)
            os.replace(tmp_path, str(index_path))
        except Exception:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

        # Save metadata atomically
        metadata_path = self._get_metadata_path(document_id)
        metadata_bytes = json.dumps(metadata, indent=2).encode("utf-8")
        _atomic_write(metadata_path, metadata_bytes)

        logger.info(
            "Added vectors",
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
    ) -> list[dict[str, Any]]:
        """Search using FAISS."""
        import json

        index_path = self._get_index_path(document_id)
        metadata_path = self._get_metadata_path(document_id)

        if not index_path.exists():
            return []

        # Load index
        index = faiss.read_index(str(index_path))

        if hasattr(index, "hnsw"):
            index.hnsw.efSearch = settings.faiss_hnsw_ef_search

        # Load metadata
        with open(metadata_path, encoding="utf-8") as f:
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
            logger.info("Deleted vectors for document: %s", document_id)

        return deleted

    def exists(self, document_id: str) -> bool:
        """Check if document exists."""
        return self._get_index_path(document_id).exists()


def get_vector_store() -> VectorStore:
    """Get configured vector store instance."""
    store_type = settings.vector_store_type

    if store_type == "faiss":
        return FaissVectorStore(settings.vector_store_dir)

    # Default to FAISS
    logger.warning("Unknown store type: %s, defaulting to FAISS", store_type)
    return FaissVectorStore(settings.vector_store_dir)
