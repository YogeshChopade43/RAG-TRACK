"""
Ingestion service for RAG-TRACK.

Orchestrates the document ingestion pipeline: parse → chunk → embed → store.
Includes comprehensive error handling and cleanup for partial files.
"""

import logging
import os
from pathlib import Path

from app.core.config import settings
from app.core.exceptions import (
    ChunkingError,
    EmbeddingError,
    IngestionError,
    ParsingError,
)
from app.services.chunking.chunking_service import ChunkingService
from app.services.embedding.embedding_service import EmbeddingService
from app.services.generic.update_vector_store import save_document_vector_store
from app.services.generic.utils.parser_utils import get_page_text
from app.services.parsing.parsing_service import ParsingService
from app.services.retrieval.bm25.service import BM25Service

logger = logging.getLogger(__name__)

# Service instances
parsing_service = ParsingService()
chunking_service = ChunkingService()
embedding_service = EmbeddingService()
bm25_service = BM25Service()


def _cleanup_partial_files(document_id: str) -> None:
    """Remove partial files created during failed ingestion."""
    paths_to_remove = [
        settings.parsed_dir / f"{document_id}.json",
        settings.vector_store_dir / f"{document_id}.index",
        settings.vector_store_dir / f"{document_id}_metadata.json",
        settings.vector_store_dir / f"{document_id}.json",
        settings.vector_store_dir / f"{document_id}_bm25.pkl",
    ]

    for path in paths_to_remove:
        try:
            if path.exists():
                path.unlink()
                logger.debug(f"Cleaned up partial file: {path}")
        except Exception as e:
            logger.warning(f"Failed to cleanup {path}: {e}")


def ingest(document_id: str, filename: str) -> dict:
    """
    Orchestrate the ingestion pipeline for a document.

    Steps:
    1. Parse raw file into structured text
    2. Chunk parsed text into manageable segments
    3. Generate embeddings for chunks
    4. Save embeddings to vector store

    Args:
        document_id: Unique identifier for the document
        filename: Original filename

    Returns:
        dict: Ingestion result with extracted text preview

    Raises:
        IngestionError: If any stage of the pipeline fails
    """
    logger.info(f"Starting ingestion for document {document_id} ({filename})")

    try:
        # Stage 1: Parse raw file
        logger.debug(f"[{document_id}] Parsing stage starting")
        try:
            parsed_load = parsing_service.parse(document_id)
        except Exception as e:
            logger.error(f"[{document_id}] Parsing failed: {e}")
            raise IngestionError(
                message=f"Failed to parse document: {str(e)}",
                stage="parsing",
                document_id=document_id,
            ) from e

        text = get_page_text(parsed_load["pages"])
        logger.info(
            f"[{document_id}] Parsed {len(parsed_load['pages'])} pages, "
            f"total {len(text)} characters"
        )

        # Stage 2: Chunk text
        logger.debug(f"[{document_id}] Chunking stage starting")
        try:
            chunks = chunking_service.chunk(parsed_load)
        except Exception as e:
            logger.error(f"[{document_id}] Chunking failed: {e}")
            raise IngestionError(
                message=f"Failed to chunk document: {str(e)}",
                stage="chunking",
                document_id=document_id,
            ) from e

        logger.info(f"[{document_id}] Created {len(chunks)} chunks")

        # Stage 3: Generate embeddings
        logger.debug(f"[{document_id}] Embedding stage starting")
        try:
            embedded_chunks = embedding_service.embed(chunks)
        except Exception as e:
            logger.error(f"[{document_id}] Embedding failed: {e}")
            raise IngestionError(
                message=f"Failed to generate embeddings: {str(e)}",
                stage="embedding",
                document_id=document_id,
            ) from e

        logger.info(
            f"[{document_id}] Generated embeddings for {embedded_chunks['chunks']} chunks"
        )

        # Stage 4: Save to vector store
        logger.debug(f"[{document_id}] Vector store save starting")
        try:
            save_document_vector_store(document_id, embedded_chunks)
        except Exception as e:
            logger.error(f"[{document_id}] Vector store save failed: {e}")
            raise IngestionError(
                message=f"Failed to save to vector store: {str(e)}",
                stage="vector_store",
                document_id=document_id,
            ) from e

        logger.info(f"[{document_id}] Vector store saved successfully")

        # Stage 5: Build BM25 index (best-effort, don't fail ingestion if this fails)
        logger.debug(f"[{document_id}] BM25 index build starting")
        try:
            bm25_path = bm25_service.build_index(chunks, document_id)
            if bm25_path:
                logger.info(f"[{document_id}] BM25 index built at {bm25_path}")
            else:
                logger.warning(f"[{document_id}] BM25 index build returned no path")
        except Exception as e:
            # Log warning but don't fail ingestion - hybrid search can degrade gracefully
            logger.warning(f"[{document_id}] BM25 index build failed (non-critical): {e}")

        logger.info(f"[{document_id}] Ingestion completed successfully")

        # Return text preview (first 200 chars)
        return {"text_preview": text[:200], "chunks_count": len(chunks)}

    except IngestionError:
        # Already logged with context, cleanup and re-raise
        _cleanup_partial_files(document_id)
        raise

    except Exception as e:
        # Catch-all for unexpected errors
        logger.exception(f"[{document_id}] Unexpected error during ingestion: {e}")
        _cleanup_partial_files(document_id)
        raise IngestionError(
            message=f"Unexpected ingestion error: {str(e)}",
            document_id=document_id,
        ) from e
