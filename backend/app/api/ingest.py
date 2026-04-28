"""
Ingestion API endpoints for RAG-TRACK.

Provides document upload and processing endpoints.
"""

import logging
import os
import re
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, Request
from pydantic import BaseModel, Field
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import settings
from app.core.ratelimit import default_limit
from app.core.auth import get_api_key
from app.services.generic.file_storage import save_raw_file
from app.services.ingestion.ingestion_service import ingest

logger = logging.getLogger(__name__)

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


def require_auth(api_key: str = Depends(get_api_key)) -> str:
    """Dependency to require API authentication."""
    return api_key


# =============================================================================
# Request/Response Models
# =============================================================================


class IngestResponse(BaseModel):
    """Response model for ingestion endpoint."""

    filename: str
    document_id: str
    status: str
    message: Optional[str] = None


class IngestStatusResponse(BaseModel):
    """Response model for ingestion status check."""

    document_id: str
    status: str  # processing, completed, failed
    progress: Optional[int] = None
    error: Optional[str] = None


# =============================================================================
# Helper Functions
# =============================================================================


def secure_filename(filename: str) -> str:
    """Sanitize and secure a filename."""
    # Get only the basename to prevent path traversal
    filename = os.path.basename(filename)

    # Remove any non-alphanumeric characters except . - _
    filename = re.sub(r"[^\w\-.]", "_", filename)

    # Ensure we have a valid extension
    if "." not in filename:
        raise ValueError("Filename must have an extension")

    return filename


def validate_file_extension(filename: str) -> str:
    """Validate file extension against allowed list."""
    if "." not in filename:
        raise HTTPException(status_code=400, detail="File must have an extension")

    ext = filename.rsplit(".", 1)[-1].lower()

    if ext not in settings.allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Allowed: {', '.join(settings.allowed_extensions)}",
        )

    return ext


# =============================================================================
# Endpoints
# =============================================================================


@router.post(
    "",
    response_model=IngestResponse,
    summary="Upload and ingest document",
    description="""
    Upload a document (PDF or TXT) for processing.
    The document will be parsed, chunked, and embedded for semantic search.
    """,
    responses={
        200: {"description": "Document uploaded successfully"},
        400: {"description": "Invalid file or file type"},
        413: {"description": "File too large"},
        429: {"description": "Rate limit exceeded"},
    },
)
@limiter.limit(default_limit)
async def ingest_document(
    request: Request,
    file: UploadFile = File(...),
):
    """Upload and process a document."""
    # Validate file is provided
    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    # Secure filename
    try:
        safe_filename = secure_filename(file.filename)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Validate extension
    try:
        ext = validate_file_extension(safe_filename)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Read file content
    try:
        content = await file.read()
    except Exception:
        raise HTTPException(status_code=400, detail="Failed to read file")

    # Validate file size
    size_bytes = len(content)
    if size_bytes > settings.max_file_size_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size: {settings.max_file_size_mb}MB",
        )

    # Generate document ID
    document_id = str(uuid.uuid4())

    logger.info(f"Uploading document: {safe_filename}, size: {size_bytes} bytes")

    try:
        # Save raw file
        save_raw_file(
            document_id=document_id,
            filename=safe_filename,
            content=content,
        )

        # Trigger ingestion pipeline
        # Note: For large files, this should be async with task queue
        result = ingest(document_id, filename=safe_filename)

        logger.info(f"Document ingested successfully: {document_id}")

        return IngestResponse(
            filename=safe_filename,
            document_id=document_id,
            status="completed",
            message="Document processed successfully",
        )

    except ValueError as e:
        logger.warning(f"Validation error during ingestion: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"Ingestion failed for {document_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to process document")


@router.get("/{document_id}")
async def get_document(document_id: str):
    """Get document metadata by ID."""
    # Validate document_id format
    if not re.match(r"^[a-f0-9-]{36}$", document_id):
        raise HTTPException(status_code=400, detail="Invalid document ID format")

    # Check if document exists
    raw_dir = settings.raw_dir / document_id
    if not raw_dir.exists():
        raise HTTPException(status_code=404, detail="Document not found")

    # List files
    files = list(raw_dir.iterdir())

    return {
        "document_id": document_id,
        "files": [f.name for f in files],
    }


@router.delete("/{document_id}")
async def delete_document(document_id: str):
    """Delete a document and its embeddings."""
    import shutil

    # Validate document_id format
    if not re.match(r"^[a-f0-9-]{36}$", document_id):
        raise HTTPException(status_code=400, detail="Invalid document ID format")

    # Delete raw file
    raw_dir = settings.raw_dir / document_id
    if raw_dir.exists():
        shutil.rmtree(raw_dir)
        logger.info(f"Deleted raw files for document: {document_id}")

    # Delete vector store
    vector_store_dir = settings.vector_store_dir
    index_file = vector_store_dir / f"{document_id}.index"
    metadata_file = vector_store_dir / f"{document_id}_metadata.json"

    deleted_count = 0
    if index_file.exists():
        index_file.unlink()
        deleted_count += 1
    if metadata_file.exists():
        metadata_file.unlink()
        deleted_count += 1

    logger.info(f"Deleted {deleted_count} files for document: {document_id}")

    return {
        "document_id": document_id,
        "status": "deleted",
        "files_deleted": deleted_count,
    }
