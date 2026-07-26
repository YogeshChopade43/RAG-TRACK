"""
Query API endpoints for RAG-TRACK.

Provides semantic search and question answering over uploaded documents.
"""

import asyncio
import logging
import re
import uuid
from functools import lru_cache
from typing import Optional, Union

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, field_validator
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.auth import get_api_key
from app.core.config import settings
from app.core.ratelimit import default_limit
from app.services.generation.generation_service import GenerationService
from app.services.observability.trace_service import TraceService
from app.services.observability.trace_storage import TraceStorage
from app.services.query.multi_query.multi_query_service import MultiQueryService
from app.services.query.query_decomposition.query_decomposition_service import (
    QueryDecompositionService,
)
from app.services.query.query_rewrite.query_rewrite_service import QueryRewriteService
from app.services.retrieval.hybrid_service import HybridRetrievalService
from app.services.retrieval.retrieval_service import RetrievalService

logger = logging.getLogger(__name__)

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


def require_auth(api_key: str = Depends(get_api_key)) -> str:
    """Dependency to require API authentication."""
    return api_key


_retrieval_cache: dict = {}


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
    sources: list[dict]


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


def select_overview_chunks(chunks: list[dict], top_k: int) -> list[dict]:
    """
    Build a representative, document-wide spread of chunks for overview/summary
    questions (instead of only the top-relevance chunks).

    Ensures the document's opening chunk (usually the title/author/header) is
    included and that selected chunks are spread across the whole document so
    the generator can produce a balanced summary rather than over-focusing on
    a single high-scoring section.

    Args:
        chunks: Deduplicated candidate chunks (any order).
        top_k: Number of chunks to select.

    Returns:
        List of selected chunk dicts ordered for context building.
    """
    if not chunks:
        return []

    # Deduplicate by chunk_id, preserving order of first appearance
    seen = set()
    unique = []
    for c in chunks:
        cid = c.get("chunk_id")
        if cid not in seen:
            seen.add(cid)
            unique.append(c)

    # Sort by document position (page first, then chunk id) for a coherent spread
    def _sort_key(c):
        page = c.get("page_number") or 0
        # Extract trailing numeric index from chunk_id if present
        cid = c.get("chunk_id", "")
        suffix = cid.rsplit("_chunk_", 1)[-1] if "_chunk_" in cid else "0"
        try:
            chunk_idx = int(suffix)
        except ValueError:
            chunk_idx = 0
        return (page, chunk_idx)

    ordered = sorted(unique, key=_sort_key)

    if len(ordered) <= top_k:
        return ordered

    # Always include the first chunk (header/title), then evenly spread the rest
    step = len(ordered) / top_k
    selected = [ordered[0]]
    picked = {0}
    for i in range(1, top_k):
        idx = min(len(ordered) - 1, int(round(i * step)))
        if idx not in picked:
            selected.append(ordered[idx])
            picked.add(idx)

    # Re-sort selected by document position for coherent context
    return sorted(selected, key=_sort_key)


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
    # Use configured top_k or request value
    base_top_k = query_request.top_k or settings.top_k_retrieval
    top_k = base_top_k

    # Detect document-overview / summary intent
    is_overview = rewriter.is_overview_question(query_request.question)
    if is_overview:
        # Pull more candidates so we can build a representative document-wide spread
        top_k = max(base_top_k, settings.top_k_retrieval * 2)

    cache_key = (query_request.document_id, query_request.question.strip().lower(), base_top_k)
    if cache_key in _retrieval_cache:
        cached = _retrieval_cache[cache_key]
        logger.info(f"Cache hit for query on {query_request.document_id}")
        return QueryResponse(
            trace_id=str(uuid.uuid4()),
            question=query_request.question,
            answer=cached["answer"],
            sources=cached["sources"],
        )

    logger.info(
        f"Processing query for document: {query_request.document_id} "
        f"(overview={is_overview})"
    )

    trace_service = TraceService()
    trace_id = trace_service.start_trace(query_request.question)

    # Per-user OpenRouter API key (session-only, not stored in DB)
    user_api_key = request.headers.get("X-User-OpenRouter-Key", "").strip() or None

    try:
        # Step 1: Decompose query (fallback to original question on failure)
        trace_service.start_timer("decomposition")
        try:
            sub_queries = decomposer.decompose(query_request.question)
        except Exception as e:
            logger.warning(f"Query decomposition failed, using original question: {e}")
            sub_queries = [query_request.question]
        trace_service.set_decomposed_queries(sub_queries)
        trace_service.end_timer("decomposition")

        logger.debug(f"Decomposed into {len(sub_queries)} sub-queries")

        all_chunks = []
        all_formatted_chunks = []

        # Step 2: Process each sub-query
        for q in sub_queries:
            logger.debug(f"Processing sub-query: {q}")

            # Step 2a: Rewrite (fallback to sub-query on failure)
            trace_service.start_timer("rewrite")
            try:
                rewritten_query = rewriter.rewrite(q)
            except Exception as e:
                logger.warning(f"Query rewrite failed for '{q}', using original: {e}")
                rewritten_query = q
            trace_service.set_rewritten_query(rewritten_query)
            trace_service.end_timer("rewrite")

            # Step 2b: Multi-query expansion (fallback to just rewritten query on failure)
            try:
                expanded_queries = multi_query.generate_queries(
                    rewritten_query, total_sub_queries=len(sub_queries)
                )
            except Exception as e:
                logger.warning(f"Multi-query expansion failed, using single query: {e}")
                expanded_queries = [rewritten_query]

        # Step 2c: Retrieval for each expanded query
        for eq in expanded_queries:
            trace_service.start_timer("retrieval")
            result = await asyncio.to_thread(
                retriever.search,
                query_request.document_id,
                eq,
                top_k,
            )
            matches = result.get("matches", [])
            trace_service.end_timer("retrieval")

            # Hybrid search: trace BM25 results and fusion metadata
            bm25_results = result.get("bm25_results", [])
            if bm25_results:
                trace_service.set_bm25_results(bm25_results)

            fusion_details = result.get("fusion_details", {})
            if fusion_details:
                trace_service.set_fusion_info(fusion_details)

            # Track reranking if hybrid service applied it
            if result.get("reranking_applied"):
                raw_reranked = result.get("reranker_raw_items", matches)
                trace_service.set_reranked_chunks(raw_reranked)
                ranking_summary = result.get("ranking_summary", {})
                trace_service.set_ranking_summary(ranking_summary)
                trace_service.set_signal_scores(
                    result.get("signal_scores", {})
                )
                trace_service.set_ranking_weights(
                    result.get("weights_used", {})
                )

            # Convert to trace format (always)
            formatted_chunks = [
                {
                    "chunk_id": chunk["chunk_id"],
                    "content": chunk.get("chunk_text") or chunk.get("content", ""),
                    "score": chunk["score"],
                    "metadata": {
                        "file_name": chunk.get("file_name"),
                        "page_number": chunk.get("page_number"),
                    },
                }
                for chunk in matches
            ]
            all_formatted_chunks.extend(formatted_chunks)
            all_chunks.extend(matches)

        # Deduplicate retrieved chunks before saving to trace
        unique_trace_chunks = list(
            {c["chunk_id"]: c for c in all_formatted_chunks}.values()
        )
        trace_service.append_retrieved_chunks(unique_trace_chunks)

        # Step 3: Deduplicate chunks
        unique_chunks = list({c["chunk_id"]: c for c in all_chunks}.values())

        # Step 4/5: Select chunks for context
        if is_overview:
            # Overview/summary: use a document-wide spread instead of top-score
            retrieved_chunks = select_overview_chunks(unique_chunks, base_top_k)
        else:
            sorted_chunks = sorted(unique_chunks, key=lambda x: x["score"], reverse=True)
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

        llm_provider = "ollama" if settings.use_local_llm else "openrouter"
        trace_service.set_llm_settings(
            provider=llm_provider,
            model=settings.llm_model,
            temperature=settings.llm_temperature,
            max_tokens=settings.llm_max_tokens,
            timeout_seconds=settings.llm_timeout_seconds,
        )

        try:
            answer = await asyncio.to_thread(
                generator.generate,
                query_request.question,
                retrieved_chunks,
                is_overview=is_overview,
                api_key=user_api_key,
            )
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

        _retrieval_cache[cache_key] = {"answer": answer, "sources": sources}
        if len(_retrieval_cache) > 128:
            _retrieval_cache.pop(next(iter(_retrieval_cache)))

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
        raise HTTPException(status_code=500, detail="Query processing failed") from None


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
        raise HTTPException(status_code=404, detail="Trace not found") from None


@router.get("/traces")
async def list_traces(limit: int = 50):
    """List recent traces."""
    from app.services.observability.trace_storage import TraceStorage

    traces = TraceStorage.list_traces(limit=limit)
    return {"traces": traces, "count": len(traces)}


@router.post("/traces/cleanup")
async def cleanup_traces(retention_days: int = 7):
    """Remove traces older than retention_days."""
    from app.services.observability.trace_storage import TraceStorage

    removed = TraceStorage.cleanup_old_traces(retention_days=retention_days)
    return {"removed": removed, "retention_days": retention_days}
