"""
Ingestion API endpoints for RAG-TRACK.

Provides document upload and processing endpoints.
"""

import logging
import os
import re
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from pydantic import BaseModel

from app.core.auth import check_document_access, get_api_key, get_optional_user_id
from app.core.config import settings
from app.core.ratelimit import default_limit, limiter
from app.services.generic.file_storage import save_owner, save_raw_file
from app.services.ingestion import jobs
from app.services.ingestion.ingestion_service import remove_document_files

logger = logging.getLogger(__name__)

router = APIRouter()


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
    status: str  # queued, parsing, chunking, embedding, ready, failed
    error: Optional[str] = None
    pages: Optional[int] = None


BUSY = "Document is still processing"


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
    Upload a document (PDF, DOCX, PPTX, HTML or TXT). Returns immediately; the document
    is parsed, chunked and embedded in the background (poll GET /ingest/{id}/status).
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
        raise HTTPException(status_code=400, detail=str(e)) from None

    # Validate extension
    try:
        validate_file_extension(safe_filename)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from None

    # Read file content
    try:
        content = await file.read()
    except Exception:
        raise HTTPException(status_code=400, detail="Failed to read file") from None

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
        save_raw_file(
            document_id=document_id,
            filename=safe_filename,
            content=content,
        )
        # Logged-in uploads are private to their owner; anonymous ones stay open
        user_id = get_optional_user_id(request)
        if user_id:
            save_owner(document_id, user_id)
    except Exception as e:
        logger.exception(f"Saving upload failed for {document_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to process document") from None

    jobs.start(document_id, safe_filename)
    return IngestResponse(filename=safe_filename, document_id=document_id, status="processing")


# Not rate limited: the upload screen polls it every second
@router.get("/{document_id}/status", response_model=IngestStatusResponse)
async def get_ingest_status(document_id: str, request: Request):
    """Where a document's ingestion is: queued, parsing, chunking, embedding, ready or failed."""
    if not re.match(r"^[a-f0-9-]{36}$", document_id):
        raise HTTPException(status_code=400, detail="Invalid document ID format")
    check_document_access(document_id, request)
    status = jobs.get_status(document_id)
    if status is None:
        if not (settings.raw_dir / document_id).exists():
            raise HTTPException(status_code=404, detail="Document not found")
        # Uploaded before background ingestion existed: it finished synchronously
        status = {"document_id": document_id, "status": "ready", "error": None, "pages": None}
    return status


@router.get("/{document_id}")
async def get_document(document_id: str, request: Request):
    """Get document metadata by ID."""
    # Validate document_id format
    if not re.match(r"^[a-f0-9-]{36}$", document_id):
        raise HTTPException(status_code=400, detail="Invalid document ID format")
    check_document_access(document_id, request)

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
async def delete_document(document_id: str, request: Request, _: str = Depends(get_api_key)):
    """Delete a document and its embeddings."""
    import shutil

    # Validate document_id format
    if not re.match(r"^[a-f0-9-]{36}$", document_id):
        raise HTTPException(status_code=400, detail="Invalid document ID format")
    check_document_access(document_id, request)
    if jobs.is_processing(document_id):
        raise HTTPException(status_code=409, detail=BUSY)

    # Delete raw file
    raw_dir = settings.raw_dir / document_id
    if raw_dir.exists():
        shutil.rmtree(raw_dir)
        logger.info(f"Deleted raw files for document: {document_id}")

    # Delete parsed text, FAISS index, metadata and BM25 index
    deleted_count = remove_document_files(document_id)
    from app.services.stress.jobs import delete_document_reports

    delete_document_reports(document_id)
    jobs.delete_status(document_id)

    logger.info(f"Deleted {deleted_count} files for document: {document_id}")

    return {
        "document_id": document_id,
        "status": "deleted",
        "files_deleted": deleted_count,
    }
