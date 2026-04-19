from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime


class RetrievalChunk(BaseModel):
    chunk_id: str
    content: str
    score: float
    metadata: Dict[str, Any]


class TraceModel(BaseModel):
    trace_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    # Query
    original_query: str
    rewritten_query: Optional[str] = None
    decomposed_queries: List[str] = []

    # Retrieval
    retrieved_chunks: List[RetrievalChunk] = []
    reranked_chunks: List[RetrievalChunk] = []

    # Context
    final_context: Optional[str] = None

    # Generation
    llm_response: Optional[str] = None

    # Metrics
    latency: Dict[str, float] = {}

    # Errors
    error: Optional[str] = None