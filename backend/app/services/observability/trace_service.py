import uuid
import time
from datetime import datetime
from typing import List, Dict, Any, Optional

from .trace_model import (
    TraceModel,
    RetrievalChunk,
    RankedChunk,
    RankingSummary,
)


class TraceService:

    def __init__(self):
        self.trace: TraceModel | None = None
        self.start_times = {}

    # ---------- TRACE LIFECYCLE ----------

    def start_trace(self, query: str) -> str:
        self.trace = TraceModel(
            trace_id=str(uuid.uuid4()),
            timestamp=datetime.utcnow(),
            original_query=query
        )
        return self.trace.trace_id

    def get_trace(self) -> TraceModel:
        return self.trace

    # ---------- TIMER ----------

    def start_timer(self, step: str):
        self.start_times[step] = time.time()

    def end_timer(self, step: str):
        if step in self.start_times:
            duration = (time.time() - self.start_times[step]) * 1000
            self.trace.latency[step] = round(duration, 2)

    # ---------- SETTERS ----------

    def set_rewritten_query(self, query: str):
        self.trace.rewritten_query = query

    def set_decomposed_queries(self, queries: List[str]):
        self.trace.decomposed_queries = queries

    def set_retrieved_chunks(self, chunks: List[dict]):
        formatted_chunks = [
            RetrievalChunk(
                chunk_id=chunk.get("chunk_id", ""),
                content=chunk.get("content", ""),
                score=chunk.get("score", 0.0),
                metadata=chunk.get("metadata", {})
            )
            for chunk in chunks
        ]
        self.trace.retrieved_chunks = formatted_chunks

    def set_reranked_chunks(self, chunks: List[dict]):
        """Set reranked chunks with full ranking metadata."""
        formatted_chunks = []
        for chunk in chunks:
            rc = RankedChunk(
                chunk_id=chunk.get("chunk_id", ""),
                content=chunk.get("content", ""),
                score=chunk.get("score", 0.0),
                metadata=chunk.get("metadata", {}),
                rank=chunk.get("rank", 0),
                final_score=chunk.get("final_score", 0.0),
                semantic_score=chunk.get("semantic_score"),
                keyword_score=chunk.get("keyword_score"),
                original_score=chunk.get("original_score"),
                llm_relevance_score=chunk.get("llm_relevance_score"),
            )
            formatted_chunks.append(rc)
        self.trace.reranked_chunks = formatted_chunks

    def set_ranking_summary(self, summary: Dict[str, Any]):
        """Set ranking summary statistics."""
        if summary:
            self.trace.ranking_summary = RankingSummary(
                total_candidates=summary.get("total_candidates", 0),
                returned_count=summary.get("returned_count", 0),
                max_score=summary.get("max_score", 0.0),
                min_score=summary.get("min_score", 0.0),
                mean_score=summary.get("mean_score", 0.0),
                median_score=summary.get("median_score", 0.0),
                score_std=summary.get("score_std", 0.0),
            )

    def set_ranking_weights(self, weights: Dict[str, float]):
        """Set ranking weights used."""
        self.trace.ranking_weights = weights

    def set_signal_scores(self, scores: Dict[str, float]):
        """Set average signal scores."""
        self.trace.signal_scores = scores

    def add_metadata(self, key: str, value: Any):
        """Add arbitrary metadata to trace."""
        if not hasattr(self.trace, "metadata"):
            self.trace.metadata = {}
        self.trace.metadata[key] = value

    def set_final_context(self, context: str):
        self.trace.final_context = context

    def set_response(self, response: str):
        self.trace.llm_response = response

    def set_error(self, error: str):
        self.trace.error = error

    def append_retrieved_chunks(self, chunks: list):
        formatted_chunks = [
            RetrievalChunk(
                chunk_id=chunk.get("chunk_id", ""),
                content=chunk.get("content", ""),
                score=chunk.get("score", 0.0),
                metadata=chunk.get("metadata", {})
            )
            for chunk in chunks
        ]

        if self.trace.retrieved_chunks:
            self.trace.retrieved_chunks.extend(formatted_chunks)
        else:
            self.trace.retrieved_chunks = formatted_chunks