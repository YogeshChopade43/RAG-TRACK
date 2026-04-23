"""
Query API endpoints for RAG-TRACK.

Provides semantic search and question answering over uploaded documents.
"""

import logging
import re
from functools import lru_cache
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, field_validator
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import settings
from app.core.ratelimit import default_limit
from app.core.auth import get_api_key
from app.services.retrieval.retrieval_service import RetrievalService
from app.services.generation.generation_service import GenerationService
from app.services.query.query_rewrite.query_rewrite_service import QueryRewriteService
from app.services.query.query_decomposition.query_decomposition_service import (
    QueryDecompositionService,
)
from app.services.query.multi_query.multi_query_service import MultiQueryService
from app.services.observability.trace_service import TraceService
from app.services.observability.trace_storage import TraceStorage

logger = logging.getLogger(__name__)

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


def require_auth(api_key: str = Depends(get_api_key)) -> str:
    """Dependency to require API authentication."""
    return api_key


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


class QueryResponse(BaseModel):
    """Response model for query endpoint."""

    trace_id: str
    question: str
    answer: str
    sources: List[dict]


# =============================================================================
# Service Dependencies (with caching for performance)
# =============================================================================


@lru_cache(maxsize=1)
def get_retrieval_service() -> RetrievalService:
    """Get retrieval service singleton."""
    logger.debug("Creating RetrievalService instance")
    return RetrievalService()


@lru_cache(maxsize=1)
def get_llm_service():
    """Get LLM service singleton."""
    from app.services.llm.llm_service import LLMService

    logger.debug("Creating LLMService instance")
    return LLMService()


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
    retriever: RetrievalService = Depends(get_retrieval_service),
    rewriter: QueryRewriteService = Depends(get_query_rewrite_service),
    decomposer: QueryDecompositionService = Depends(get_query_decomposition_service),
    multi_query: MultiQueryService = Depends(get_multi_query_service),
    generator: GenerationService = Depends(get_generation_service),
):
    """Query uploaded documents with a question."""
    # Use configured top_k or request value
    top_k = query_request.top_k or settings.top_k_retrieval

    logger.info(f"Processing query for document: {query_request.document_id}")

    trace_service = TraceService()
    trace_id = trace_service.start_trace(query_request.question)

    try:
        # Step 1: Decompose query
        trace_service.start_timer("decomposition")
        sub_queries = decomposer.decompose(query_request.question)
        trace_service.set_decomposed_queries(sub_queries)
        trace_service.end_timer("decomposition")

        logger.debug(f"Decomposed into {len(sub_queries)} sub-queries")

        all_chunks = []

        # Step 2: Process each sub-query
        for q in sub_queries:
            logger.debug(f"Processing sub-query: {q}")

            # Step 2a: Rewrite
            trace_service.start_timer("rewrite")
            rewritten_query = rewriter.rewrite(q)
            trace_service.set_rewritten_query(rewritten_query)
            trace_service.end_timer("rewrite")

            # Step 2b: Multi-query expansion
            expanded_queries = multi_query.generate_queries(
                rewritten_query, total_sub_queries=len(sub_queries)
            )

            # Step 2c: Retrieval for each expanded query
            for eq in expanded_queries:
                trace_service.start_timer("retrieval")
                result = retriever.search(query_request.document_id, eq, top_k=top_k)
                matches = result.get("matches", [])
                trace_service.end_timer("retrieval")

                # Convert to trace format
                formatted_chunks = [
                    {
                        "chunk_id": chunk["chunk_id"],
                        "content": chunk["chunk_text"],
                        "score": chunk["score"],
                        "metadata": {
                            "file_name": chunk.get("file_name"),
                            "page_number": chunk.get("page_number"),
                        },
                    }
                    for chunk in matches
                ]

                trace_service.append_retrieved_chunks(formatted_chunks)
                all_chunks.extend(matches)

        # Step 3: Deduplicate chunks
        unique_chunks = {c["chunk_id"]: c for c in all_chunks}.values()

        # Step 4: Sort by score
        sorted_chunks = sorted(unique_chunks, key=lambda x: x["score"], reverse=True)

        # Step 5: Take top-k
        retrieved_chunks = sorted_chunks[:top_k]

        logger.debug(f"Retrieved {len(retrieved_chunks)} unique chunks")

        # Safety check
        if not retrieved_chunks:
            return QueryResponse(
                trace_id=trace_id,
                question=query_request.question,
                answer="I could not find relevant information in the document.",
                sources=[],
            )

        # Build context
        context = "\n".join([chunk["chunk_text"] for chunk in retrieved_chunks])
        trace_service.set_final_context(context)

        # Step 6: Generate answer
        trace_service.start_timer("generation")

        try:
            answer = generator.generate(query_request.question, retrieved_chunks)
            trace_service.set_response(answer)
        except Exception as e:
            logger.error(f"Generation failed: {str(e)}")
            answer = (
                "I encountered an error while generating the answer. Please try again."
            )
            trace_service.set_error(str(e))

        trace_service.end_timer("generation")

        # Step 7: Deduplicate citations
        unique_sources = {}
        for chunk in retrieved_chunks:
            key = (chunk["file_name"], chunk["page_number"])
            unique_sources[key] = {
                "file_name": chunk["file_name"],
                "page_number": chunk["page_number"],
            }

        sources = list(unique_sources.values())

        # Save trace
        if settings.trace_enabled:
            TraceStorage.save(trace_service.get_trace())

        logger.info(f"Query completed successfully, trace_id: {trace_id}")

        return QueryResponse(
            trace_id=trace_id,
            question=query_request.question,
            answer=answer,
            sources=sources,
        )

    except Exception as e:
        logger.exception(f"Query processing failed: {str(e)}")
        trace_service.set_response(str(e))
        if settings.trace_enabled:
            TraceStorage.save(trace_service.get_trace())
        raise HTTPException(status_code=500, detail="Query processing failed")


@router.get("/trace/{trace_id}")
async def get_trace(trace_id: str):
    """Retrieve a query trace by ID."""
    from app.services.observability.trace_storage import TraceStorage

    try:
        trace = TraceStorage.load(trace_id)
        if trace is None:
            raise HTTPException(status_code=404, detail="Trace not found")
        return trace.dict()
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Trace not found")
