from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class RetrievalChunk(BaseModel):
    chunk_id: str
    content: str
    score: float
    metadata: dict[str, Any] = Field(default_factory=dict)


class RankingSignal(BaseModel):
    """Individual ranking signal contribution."""
    semantic_score: Optional[float] = None
    keyword_score: Optional[float] = None
    original_score: Optional[float] = None
    llm_relevance_score: Optional[float] = None


class RankedChunk(RetrievalChunk):
    """Chunk with ranking metadata."""
    rank: int
    final_score: float
    semantic_score: Optional[float] = None
    keyword_score: Optional[float] = None
    original_score: Optional[float] = None
    llm_relevance_score: Optional[float] = None


class RankingSummary(BaseModel):
    """Summary statistics for ranking."""
    total_candidates: int = 0
    returned_count: int = 0
    max_score: float = 0.0
    min_score: float = 0.0
    mean_score: float = 0.0
    median_score: float = 0.0
    score_std: float = 0.0


class TraceModel(BaseModel):
    trace_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    # Query
    original_query: str
    rewritten_query: Optional[str] = None
    decomposed_queries: list[str] = Field(default_factory=list)

    # Retrieval
    retrieved_chunks: list[RetrievalChunk] = Field(default_factory=list)
    bm25_results: list[RetrievalChunk] = Field(default_factory=list)
    fusion_details: Optional[dict[str, Any]] = None
    reranked_chunks: list[RankedChunk] = Field(default_factory=list)
    ranking_summary: Optional[RankingSummary] = None
    ranking_weights: Optional[dict[str, float]] = None
    signal_scores: Optional[dict[str, Optional[float]]] = None

    # Context
    final_context: Optional[str] = None

    # Generation
    llm_response: Optional[str] = None
    llm_provider: Optional[str] = None
    llm_model: Optional[str] = None
    llm_temperature: Optional[float] = None
    llm_max_tokens: Optional[int] = None
    llm_timeout_seconds: Optional[int] = None

    # Metrics
    latency: dict[str, float] = Field(default_factory=dict)

    # Errors
    error: Optional[str] = None
