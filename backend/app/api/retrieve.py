"""
Query API endpoints for RAG-TRACK.

Provides semantic search and question answering over uploaded documents.
"""

import logging
import re
from functools import lru_cache
from typing import Optional, Union

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, field_validator

from app.core.auth import check_document_access, get_api_key
from app.core.config import settings
from app.core.ratelimit import default_limit, limiter
from app.services import jev  # noqa: F401 (patch point: tests patch retrieve.jev.*)
from app.services.generation.generation_service import GenerationService
from app.services.generic import file_storage
from app.services.ingestion import jobs as ingest_jobs
from app.services.observability import trace_storage
from app.services.observability.trace_service import (
    TraceService,  # noqa: F401 (patch point)
)
from app.services.observability.trace_storage import (
    TraceStorage,  # noqa: F401 (patch point)
)
from app.services.pipeline import (  # noqa: F401 (re-exported for tests and callers)
    QueryResponse,
    Services,
    _retrieval_cache,
    answer_question,
    finish_transparency,
    select_overview_chunks,
)
from app.services.query.multi_query.multi_query_service import MultiQueryService
from app.services.query.query_decomposition.query_decomposition_service import (
    QueryDecompositionService,
)
from app.services.query.query_rewrite.query_rewrite_service import QueryRewriteService
from app.services.retrieval.hybrid_service import HybridRetrievalService
from app.services.retrieval.retrieval_service import RetrievalService

logger = logging.getLogger(__name__)

router = APIRouter()



# =============================================================================
# Request/Response Models
# =============================================================================


class QueryRequest(BaseModel):
    """Request model for query endpoint."""

    document_id: str = Field(
        ...,
        min_length=36,
        max_length=36,
        description="UUID of the uploaded document",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )
    question: str = Field(
        ...,
        min_length=3,
        max_length=2000,
        description="User question to ask about the document",
    )
    top_k: Optional[int] = Field(
        default=None,
        ge=1,
        le=20,
        description="Number of chunks to retrieve",
    )

    @field_validator("document_id")
    @classmethod
    def validate_document_id(cls, v: str) -> str:
        """Validate document_id format."""
        # Allow UUID format only
        if not re.match(r"^[a-f0-9-]{36}$", v):
            raise ValueError("Invalid document ID format")
        return v

    @field_validator("question")
    @classmethod
    def validate_question(cls, v: str) -> str:
        """Sanitize question input."""
        # Strip whitespace
        v = v.strip()
        if not v:
            raise ValueError("Question cannot be empty")

        # Remove potential prompt injection patterns
        v = re.sub(r"<\|.*?\|>", "", v)
        if re.search(r"^system:", v, re.IGNORECASE):
            raise ValueError("Invalid question content")

        return v


# =============================================================================
# Service Dependencies (with caching for performance)
# =============================================================================


@lru_cache(maxsize=1)
def get_retrieval_service() -> RetrievalService:
    """Get retrieval service singleton."""
    logger.debug("Creating RetrievalService instance")
    return RetrievalService()


@lru_cache(maxsize=1)
def get_hybrid_retrieval_service() -> HybridRetrievalService:
    """Get hybrid retrieval service singleton."""
    logger.debug("Creating HybridRetrievalService instance")
    return HybridRetrievalService()


@lru_cache(maxsize=1)
def get_llm_service():
    """Get LLM service singleton."""
    from app.services.llm import get_llm_service as _get_llm_service

    logger.debug("Creating LLM service instance")
    return _get_llm_service()


def get_query_rewrite_service() -> QueryRewriteService:
    """Get query rewrite service."""
    return QueryRewriteService()


def get_query_decomposition_service() -> QueryDecompositionService:
    """Get query decomposition service."""
    return QueryDecompositionService()


def get_multi_query_service() -> MultiQueryService:
    """Get multi-query service."""
    return MultiQueryService()


def get_generation_service() -> GenerationService:
    """Get generation service."""
    return GenerationService()


def get_retriever() -> Union[RetrievalService, HybridRetrievalService]:
    """Get appropriate retrieval service based on hybrid search setting."""
    if settings.enable_hybrid_search:
        return get_hybrid_retrieval_service()
    else:
        return get_retrieval_service()


# =============================================================================
# Endpoints
# =============================================================================


@router.post(
    "",
    response_model=QueryResponse,
    summary="Query documents",
    description="""
    Process a user question through the RAG pipeline:
    1. Decompose complex queries
    2. Rewrite for optimal retrieval
    3. Expand with multi-query
    4. Retrieve relevant chunks
    5. Generate answer with citations
    """,
    responses={
        200: {"description": "Successful response"},
        404: {"description": "Document not found"},
        422: {"description": "Invalid input"},
        429: {"description": "Rate limit exceeded"},
    },
)
@limiter.limit(default_limit)
async def query_documents(
    request: Request,
    query_request: QueryRequest,
    retriever: Union[RetrievalService, HybridRetrievalService] = Depends(get_retriever),
    rewriter: QueryRewriteService = Depends(get_query_rewrite_service),
    decomposer: QueryDecompositionService = Depends(get_query_decomposition_service),
    multi_query: MultiQueryService = Depends(get_multi_query_service),
    generator: GenerationService = Depends(get_generation_service),
):
    """Query uploaded documents with a question."""
    check_document_access(query_request.document_id, request)
    if ingest_jobs.is_processing(query_request.document_id):
        raise HTTPException(status_code=409, detail="Document is still processing")
    services = Services(retriever, rewriter, decomposer, multi_query, generator)
    result = await answer_question(
        query_request.document_id,
        query_request.question,
        services=services,
        api_key=request.headers.get("X-User-OpenRouter-Key", "").strip() or None,
        model=request.headers.get("X-User-OpenRouter-Model", "").strip() or None,
        top_k=query_request.top_k,
        overrides=file_storage.get_doc_settings(query_request.document_id),
    )
    return result.response


@router.get("/trace/{trace_id}")
async def get_trace(trace_id: str):
    """Retrieve a query trace by ID."""

    try:
        trace = trace_storage.TraceStorage.load(trace_id)  # looked up per call (patchable)
        if trace is None:
            raise HTTPException(status_code=404, detail="Trace not found")
        return trace.dict()
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Trace not found") from None


@router.get("/traces")
async def list_traces(limit: int = 50):
    """List recent traces."""

    traces = trace_storage.TraceStorage.list_traces(limit=limit)
    return {"traces": traces, "count": len(traces)}


@router.post("/traces/cleanup")
async def cleanup_traces(retention_days: int = 7, _: str = Depends(get_api_key)):
    """Remove traces older than retention_days."""

    removed = trace_storage.TraceStorage.cleanup_old_traces(retention_days=retention_days)
    return {"removed": removed, "retention_days": retention_days}
