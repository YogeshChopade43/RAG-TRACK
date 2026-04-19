import uuid
import time
from datetime import datetime
from typing import List

from .trace_model import TraceModel, RetrievalChunk


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
        formatted_chunks = [
            RetrievalChunk(
                chunk_id=chunk.get("chunk_id", ""),
                content=chunk.get("content", ""),
                score=chunk.get("score", 0.0),
                metadata=chunk.get("metadata", {})
            )
            for chunk in chunks
        ]
        self.trace.reranked_chunks = formatted_chunks

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