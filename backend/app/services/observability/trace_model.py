from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime


class RetrievalChunk(BaseModel):
    chunk_id: str
    content: str
    score: float
    metadata: Dict[str, Any]


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
    decomposed_queries: List[str] = []

    # Retrieval
    retrieved_chunks: List[RetrievalChunk] = []
    bm25_results: List[RetrievalChunk] = []  # Raw BM25 results before fusion
    fusion_details: Optional[Dict[str, Any]] = None  # Fusion weights and counts
    reranked_chunks: List[RankedChunk] = []
    ranking_summary: Optional[RankingSummary] = None
    ranking_weights: Optional[Dict[str, float]] = None
    signal_scores: Optional[Dict[str, float]] = None

    # Context
    final_context: Optional[str] = None

    # Generation
    llm_response: Optional[str] = None

    # Metrics
    latency: Dict[str, float] = {}

    # Errors
    error: Optional[str] = None