"""
The question-answering pipeline behind POST /query, shared with the document stress test.

answer_question runs one question end to end (Jev analysis, decompose/rewrite/expand,
hybrid search + Jev rerank, generation, Jev guard) and records the trace. Callers pass
the services to use (FastAPI injects them for /query) and optional per-document settings.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Optional

from fastapi import HTTPException
from pydantic import BaseModel, Field

from app.core.config import settings
from app.services import jev
from app.services.doc_settings import DocSettings
from app.services.generation.prompt_registry import NOT_FOUND_ANSWER
from app.services.observability.call_log import start_call_log
from app.services.observability.candidates import (
    candidates_from_matches,
    classify_candidates,
    merge_candidates,
    near_misses,
    summarize_usage,
)
from app.services.observability.trace_service import TraceService
from app.services.observability.trace_storage import TraceStorage

logger = logging.getLogger(__name__)

_retrieval_cache: dict = {}


class QueryResponse(BaseModel):
    """Response model for query endpoint."""

    trace_id: str
    question: str
    answer: str
    sources: list[dict]
    # Transparency: what this answer cost, whether it was reused, and why it may be "not found"
    cached: bool = False
    answer_status: str = "answered"  # answered | not_found | error
    usage: Optional[dict] = None  # total_tokens, cost_usd, jev_cost_included
    near_misses: list[dict] = Field(default_factory=list)
    fallbacks: list[str] = Field(default_factory=list)  # decisions made by heuristics instead of Jev


@dataclass
class Services:
    retriever: Any
    rewriter: Any
    decomposer: Any
    multi_query: Any
    generator: Any


@dataclass
class QueryResult:
    response: QueryResponse
    trace: Any = None  # the TraceModel (None for cache hits)
    extra: dict = field(default_factory=dict)


FALLBACK_SOURCES = ("heuristic", "fusion", "unavailable")
CACHED_USAGE = {"total_tokens": 0, "cost_usd": 0.0, "jev_cost_included": True}


def finish_transparency(
    trace_service: TraceService,
    *,
    runs: list[tuple[str, list[dict]]],
    final_chunks: list[dict],
    expanded_queries: list[str],
    decision_sources: dict[str, str],
    calls: list[dict],
    status: str,
    min_relevance: float,
) -> tuple[list[dict], list[str]]:
    """Record the candidate funnel, calls and decision sources on the trace.
    Returns (near_misses, fallbacks) for the response."""
    classified = classify_candidates(
        merge_candidates(runs), {c["chunk_id"] for c in final_chunks}, min_relevance
    )
    trace = trace_service.get_trace()
    trace.candidates = classified
    trace.expanded_queries = expanded_queries
    trace.calls = list(calls)
    trace.decision_sources = dict(decision_sources)
    trace.answer_status = status
    misses = near_misses(classified) if status == "not_found" else []
    fallbacks = [name for name, src in decision_sources.items() if src in FALLBACK_SOURCES]
    return misses, fallbacks


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


async def answer_question(
    document_id: str,
    question: str,
    *,
    services: Services,
    api_key: Optional[str],
    model: Optional[str],
    overrides: Optional[DocSettings] = None,
    use_cache: bool = True,
    top_k: Optional[int] = None,
) -> QueryResult:
    """Answer one question about a document. Raises HTTPException(400) for blocked
    questions and HTTPException(500) on pipeline failure, as /query always has."""
    out: dict = {}
    response = await _answer_question(
        document_id, question, services=services, api_key=api_key, model=model,
        overrides=overrides, use_cache=use_cache, top_k=top_k, _out=out,
    )
    return QueryResult(response=response, trace=out.get("trace"))


async def _answer_question(
    document_id: str,
    question: str,
    *,
    services: Services,
    api_key: Optional[str],
    model: Optional[str],
    overrides: Optional[DocSettings],
    use_cache: bool,
    top_k: Optional[int],
    _out: dict,
) -> QueryResponse:
    # Use configured top_k or request value
    base_top_k = top_k or (overrides.top_k if overrides else settings.top_k_retrieval)
    min_relevance = overrides.min_relevance if overrides else settings.jev_min_relevance
    top_k = base_top_k

    # Per-user LLM credentials (session-only, not stored in DB)
    user_api_key = api_key
    user_model = model

    # Detect document-overview / summary intent
    is_overview = services.rewriter.is_overview_question(question)
    if is_overview:
        # Pull more candidates so we can build a representative document-wide spread
        top_k = max(base_top_k, settings.top_k_retrieval * 2)

    cache_key = (document_id, question.lower(), base_top_k, min_relevance, user_model)
    cached = _retrieval_cache.get(cache_key) if use_cache else None
    # A cached answer is only reusable while its trace still exists: retention
    # cleanup deletes trace files, and the UI would show "Trace not available"
    if cached and settings.trace_enabled and not TraceStorage.exists(cached["trace_id"]):
        _retrieval_cache.pop(cache_key, None)
        cached = None
    if cached:
        logger.info(f"Cache hit for query on {document_id}")
        return QueryResponse(
            trace_id=cached["trace_id"],  # the trace of the run that produced this answer
            question=question,
            answer=cached["answer"],
            sources=cached["sources"],
            cached=True,
            answer_status=cached.get("answer_status", "answered"),
            usage=CACHED_USAGE,
            near_misses=cached.get("near_misses", []),
            fallbacks=cached.get("fallbacks", []),
        )

    logger.info(
        f"Processing query for document: {document_id} "
        f"(overview={is_overview})"
    )

    trace_service = TraceService()
    trace_id = trace_service.start_trace(question)
    _out["trace"] = trace_service.get_trace()
    trace_service.get_trace().settings_used = {
        "top_k": base_top_k,
        "min_relevance": min_relevance,
        "source": "document" if overrides else "default",
    }
    calls = start_call_log()  # llm_service and jev record every model call here

    # Step 0: Jev query analysis — input guardrails + decompose/rewrite decisions in one call.
    # None when Jev is unavailable: services then fall back to their heuristics.
    analysis = await asyncio.to_thread(jev.analyze_query, question, user_api_key)
    decision_sources = {"analysis": "jev" if analysis else "heuristic"}
    if analysis:
        trace_service.add_metadata("jev_query_analysis", analysis.scores)
        if analysis.blocked:
            logger.warning(f"Query blocked by Jev input guard: {analysis.scores}")
            raise HTTPException(status_code=400, detail="This question was blocked by the safety filter.")

    try:
        # Step 1: Decompose query (fallback to original question on failure)
        trace_service.start_timer("decomposition")
        try:
            sub_queries = services.decomposer.decompose(
                question,
                api_key=user_api_key,
                model=user_model,
                needed=analysis.needs_decomposition if analysis else None,
            )
        except Exception as e:
            logger.warning(f"Query decomposition failed, using original question: {e}")
            sub_queries = [question]
        trace_service.set_decomposed_queries(sub_queries)
        trace_service.end_timer("decomposition")

        logger.debug(f"Decomposed into {len(sub_queries)} sub-queries")

        all_chunks = []
        all_formatted_chunks = []
        runs: list[tuple[str, list[dict]]] = []  # (expanded query, candidates it found)
        all_expanded: list[str] = []
        rerank_used = False  # Jev reranked at least one search
        rerank_failed = False  # Jev was asked to rerank and was unavailable

        # Rewrite decisions: reuse the analysis for the original question,
        # ask Jev once for all sub-queries after decomposition.
        if is_overview:
            rewrite_needed = [False] * len(sub_queries)
        elif sub_queries == [question]:
            rewrite_needed = [analysis.needs_rewrite if analysis else None]
        else:
            rewrite_needed = await asyncio.to_thread(
                jev.rewrite_decisions, question, sub_queries, user_api_key
            ) or [None] * len(sub_queries)

        # Step 2: Process each sub-query
        for q, needs_rewrite in zip(sub_queries, rewrite_needed):
            logger.debug(f"Processing sub-query: {q}")

            # Step 2a: Rewrite (fallback to sub-query on failure)
            trace_service.start_timer("rewrite")
            try:
                rewritten_query = services.rewriter.rewrite(q, api_key=user_api_key, model=user_model, needed=needs_rewrite)
            except Exception as e:
                logger.warning(f"Query rewrite failed for '{q}', using original: {e}")
                rewritten_query = q
            trace_service.set_rewritten_query(rewritten_query)
            trace_service.end_timer("rewrite")

            # Step 2b: Multi-query expansion (fallback to just rewritten query on failure)
            try:
                expanded_queries = services.multi_query.generate_queries(
                    rewritten_query, total_sub_queries=len(sub_queries), api_key=user_api_key, model=user_model
                )
            except Exception as e:
                logger.warning(f"Multi-query expansion failed, using single query: {e}")
                expanded_queries = [rewritten_query]
            all_expanded.extend(expanded_queries)

            # Step 2c: Retrieval for each expanded query
            for eq in expanded_queries:
                trace_service.start_timer("retrieval")
                # Jev reranks against the sub-question (natural language), not the
                # keyword rewrite; overview questions keep a document-wide spread instead.
                result = await asyncio.to_thread(
                    services.retriever.search,
                    document_id,
                    eq,
                    top_k,
                    use_reranking=False if is_overview else None,
                    rerank_query=q,
                    api_key=user_api_key,
                    min_relevance=min_relevance,
                )
                matches = result.get("matches", [])
                trace_service.end_timer("retrieval")
                runs.append((eq, result.get("candidates") or candidates_from_matches(matches)))
                applied = bool(result.get("reranking_applied"))
                rerank_used = rerank_used or applied
                rerank_failed = rerank_failed or (bool(result.get("rerank_attempted")) and not applied)

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
        # "fusion" (a fallback) only when Jev was asked and failed; not asked at all is "skipped"
        decision_sources["rerank"] = "fusion" if rerank_failed else ("jev" if rerank_used else "skipped")

        # Safety check
        if not retrieved_chunks:
            answer = "I could not find relevant information in the document."
            trace_service.set_response(answer)
            decision_sources["guard"] = "skipped"
            misses, fallbacks = finish_transparency(
                trace_service, runs=runs, final_chunks=[], expanded_queries=all_expanded,
                decision_sources=decision_sources, calls=calls, status="not_found", min_relevance=min_relevance,
            )
            if settings.trace_enabled:
                TraceStorage.save(trace_service.get_trace())
            return QueryResponse(
                trace_id=trace_id,
                question=question,
                answer=answer,
                sources=[],
                answer_status="not_found",
                usage=summarize_usage(calls),
                near_misses=misses,
                fallbacks=fallbacks,
            )

        # Build context
        context = "\n".join([chunk["chunk_text"] for chunk in retrieved_chunks])
        trace_service.set_final_context(context)

        # Step 6: Generate answer
        trace_service.start_timer("generation")

        trace_service.set_llm_settings(
            provider="openrouter",
            model=user_model or settings.llm_model,
            temperature=settings.llm_temperature,
            max_tokens=settings.llm_max_tokens,
            timeout_seconds=settings.llm_timeout_seconds,
        )

        generation_failed = False
        guard_scores: dict = {}
        try:
            answer = await asyncio.to_thread(
                services.generator.generate,
                question,
                retrieved_chunks,
                is_overview=is_overview,
                api_key=user_api_key,
                model=user_model,
            )
            answer, guard_scores = await asyncio.to_thread(
                jev.guard_answer, question, retrieved_chunks, answer, user_api_key
            )
            if guard_scores:
                trace_service.add_metadata("jev_answer_guard", guard_scores)
            trace_service.set_response(answer)
        except Exception as e:
            logger.error(f"Generation failed: {str(e)}")
            answer = (
                "I encountered an error while generating the answer. Please try again."
            )
            trace_service.set_error(str(e))
            generation_failed = True

        trace_service.end_timer("generation")
        decision_sources["guard"] = "jev" if guard_scores else ("skipped" if generation_failed else "unavailable")
        if generation_failed:
            status = "error"
        elif answer.strip().startswith(NOT_FOUND_ANSWER):
            status = "not_found"
        else:
            status = "answered"
        misses, fallbacks = finish_transparency(
            trace_service, runs=runs, final_chunks=retrieved_chunks, expanded_queries=all_expanded,
            decision_sources=decision_sources, calls=calls, status=status, min_relevance=min_relevance,
        )

        # Step 7: Deduplicate citations
        unique_sources = {}
        for chunk in retrieved_chunks:
            key = (chunk["file_name"], chunk["page_number"])
            unique_sources[key] = {
                "file_name": chunk["file_name"],
                "page_number": chunk["page_number"],
            }

        sources = list(unique_sources.values())

        # Don't cache failures, otherwise a transient LLM error sticks forever
        if use_cache and not generation_failed:
            _retrieval_cache[cache_key] = {
                "answer": answer, "sources": sources, "trace_id": trace_id,
                "answer_status": status, "near_misses": misses, "fallbacks": fallbacks,
            }
            if len(_retrieval_cache) > 128:
                _retrieval_cache.pop(next(iter(_retrieval_cache)))

        # Save trace
        if settings.trace_enabled:
            TraceStorage.save(trace_service.get_trace())

        logger.info(f"Query completed successfully, trace_id: {trace_id}")

        return QueryResponse(
            trace_id=trace_id,
            question=question,
            answer=answer,
            sources=sources,
            answer_status=status,
            usage=summarize_usage(calls),
            near_misses=misses,
            fallbacks=fallbacks,
        )

    except Exception as e:
        logger.exception(f"Query processing failed: {str(e)}")
        trace_service.set_response(str(e))
        trace_service.get_trace().calls = list(calls)
        trace_service.get_trace().answer_status = "error"
        if settings.trace_enabled:
            TraceStorage.save(trace_service.get_trace())
        raise HTTPException(status_code=500, detail="Query processing failed") from None
