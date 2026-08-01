"""
Production-grade reranking service for RAG-TRACK.

Provides multiple ranking strategies to refine and reorder retrieval results:
- Semantic similarity reranking (cross-encoder style using embeddings)
- Keyword overlap scoring
- Score-based normalization and calibration
- LLM-based relevance scoring
- Ensemble ranking combining multiple signals

The service evaluates each candidate chunk against the query using multiple
criteria, assigns normalized scores, and produces a final ranked list.
"""

import logging
import math
import re
from dataclasses import asdict, dataclass
from typing import Any, Optional

from sklearn.metrics.pairwise import cosine_similarity

from app.core.config import settings
from app.services.embedding.shared_model import get_shared_rerank_model

logger = logging.getLogger(__name__)

# Keywords that signal document-overview intent
# These are specific patterns that refer to the document as a whole,
# NOT generic "about" which could be part of "tell me about X"
_OVERVIEW_KEYWORDS = re.compile(
    r"\b(this document|this file|this pdf|this doc|this resume|this cv|"
    r"what is this|what's this|what is the document|what's the document|"
    r"summar|summariz|overview|tl;dr|gist|main idea|main point|"
    r"what is this document about|what is the document about|"
    r"what is this file about|what is this doc about|"
    r"what is this resume about|what is this cv about|"
    r"what is this pdf about|"
    r"tell me about this document|tell me about this file|"
    r"tell me about this pdf|tell me about this doc"
    r")\b",
    re.IGNORECASE,
)

# Keywords that signal section-level intent (e.g., "skills", "experience")
_SECTION_KEYWORDS = re.compile(
    r"\b(skill|technolog|experience|educat|project|certif|"
    r"work histor|contact|email|mobile|github|kaggle|"
    r"resnet|gesture|brain tumor|sentiment|hand gesture|"
    r"cnc|alarm|predictive|automation|test case|selenium|playwright|"
    r"ensemble|stacking|knn|svm|decision tree|data augmentation)\b",
    re.IGNORECASE,
)


@dataclass
class RankedItem:
    """Represents a ranked item with its score and ranking metadata."""
    chunk_id: str
    content: str
    final_score: float
    rank: int
    # Individual signal scores
    semantic_score: float
    keyword_score: float
    original_score: float
    llm_relevance_score: Optional[float] = None
    structural_score: float = 0.5
    # Metadata
    file_name: Optional[str] = None
    page_number: Optional[int] = None
    metadata: Optional[dict[str, Any]] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        d = asdict(self)
        # Include 'score' as an alias for 'final_score' for backward compatibility
        d["score"] = self.final_score
        return d


class RerankingService:
    """
    Production-grade reranking service with multiple ranking strategies.

    Strategies:
    1. Semantic Reranking: Uses embedding similarity between query and chunk
    2. Keyword Overlap: Measures term overlap and importance
    3. Score Calibration: Normalizes and calibrates original FAISS scores
    4. LLM Relevance: Optional LLM-based relevance assessment
    5. Ensemble: Combines multiple signals with weighted fusion

    The service refines the initial retrieval results by re-evaluating each
    candidate against the query using multiple criteria, producing a more
    accurate and reliable ranking.
    """

    def __init__(self):
        """
        Initialize reranking service with embedding model.
        """
        self.embedding_model = get_shared_rerank_model()
        self.use_llm_scoring = getattr(settings, 'use_llm_reranking', False)
        self.use_reranking = getattr(settings, 'use_reranking', False)
        logger.info(
            f"Initialized RerankingService with model={settings.embedding_model}, "
            f"reranking={self.use_reranking}, llm_scoring={self.use_llm_scoring}"
        )

    # ------------------------------------------------------------------
    # Semantic Similarity Reranking
    # ------------------------------------------------------------------
    def _compute_semantic_scores(
        self, query: str, chunks: list[dict[str, Any]]
    ) -> list[float]:
        """
        Compute semantic similarity scores between query and each chunk.

        Uses cosine similarity between query embedding and chunk text embedding.
        Scores are normalized to [0, 1] range.

        Args:
            query: The search query
            chunks: List of candidate chunks

        Returns:
            List of normalized semantic similarity scores
        """
        if not chunks:
            return []

        # Encode query
        query_embedding = self.embedding_model.encode([query])

        # Encode all chunk contents
        chunk_texts = [c.get("chunk_text", "") for c in chunks]
        chunk_embeddings = self.embedding_model.encode(chunk_texts)

        # Compute cosine similarities
        similarities = cosine_similarity(query_embedding, chunk_embeddings)[0]

        # Normalize to [0, 1] (cosine similarity is already in [-1, 1])
        # Shift and scale: (sim + 1) / 2 maps [-1,1] -> [0,1]
        normalized = [(s + 1) / 2 for s in similarities]

        return normalized

    # ------------------------------------------------------------------
    # Keyword Overlap Scoring
    # ------------------------------------------------------------------
    def _compute_keyword_scores(
        self, query: str, chunks: list[dict[str, Any]]
    ) -> list[float]:
        """
        Compute keyword overlap scores between query and chunks.

        Measures term frequency overlap, with emphasis on important query terms.
        Uses BM25-inspired scoring without full index.

        Args:
            query: The search query
            chunks: List of candidate chunks

        Returns:
            List of normalized keyword overlap scores
        """
        if not chunks:
            return []

        # Lightweight stopword removal (preserve technical terms/acronyms)
        stopwords = {
            'a', 'an', 'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
            'should', 'may', 'might', 'must', 'can', 'this', 'that', 'these',
            'those', 'it', 'its', 'as', 'by', 'from', 'about', 'into', 'than',
            'then', 'so', 'if', 'out', 'up', 'down', 'here', 'there', 'when',
            'where', 'why', 'how', 'all', 'each', 'few', 'more', 'most', 'other',
            'some', 'such', 'no', 'nor', 'not', 'only', 'own', 'same', 'very',
            'just', 'too', 'also', 'now',
        }

        query_terms = [t for t in query.lower().split() if t not in stopwords and len(t) >= 2]

        if not query_terms:
            # Fallback: use all terms
            query_terms = [t for t in query.lower().split() if len(t) > 1]

        scores = []
        for chunk in chunks:
            chunk_text = chunk.get("chunk_text", "").lower()
            if not chunk_text:
                scores.append(0.0)
                continue

            # Compute term frequency for query terms in chunk
            term_matches = 0
            weighted_matches = 0
            for term in query_terms:
                count = chunk_text.count(term)
                if count > 0:
                    term_matches += 1
                    # Weight by term rarity (inverse document frequency approximation)
                    # Shorter, more specific terms get higher weight
                    weight = 1.0 + (1.0 / len(term))
                    weighted_matches += count * weight

            # Normalize by number of query terms and chunk length
            if len(query_terms) > 0:
                coverage = term_matches / len(query_terms)
            else:
                coverage = 0.0

            # Length normalization (prefer medium-length chunks)
            chunk_len = len(chunk_text.split())
            length_factor = min(1.0, chunk_len / 100.0)  # Normalize around 100 words

            # Combined score
            score = 0.5 * coverage + 0.3 * min(1.0, weighted_matches / len(query_terms)) + 0.2 * length_factor
            scores.append(min(1.0, score))

        return scores

    # ------------------------------------------------------------------
    # Structural Metadata Scoring
    # ------------------------------------------------------------------
    def _compute_structural_scores(
        self, query: str, chunks: list[dict[str, Any]]
    ) -> list[float]:
        """
        Compute structural-position scores based on chunk metadata.

        Boosts title/header blocks for overview queries and section-relevant
        list items/paragraphs for targeted queries.

        Args:
            query: The search query
            chunks: List of candidate chunks with optional structural metadata

        Returns:
            List of structural signal scores in [0, 1]
        """
        if not chunks:
            return []

        q = query.lower().strip()
        is_overview = bool(_OVERVIEW_KEYWORDS.search(q))
        section_topics = [t.lower() for t in _SECTION_KEYWORDS.findall(q)] if q else []

        scores = []
        for i, chunk in enumerate(chunks):
            meta = chunk.get("metadata", {})
            is_title = meta.get("is_title_block", False)
            struct_type = meta.get("structural_type", "paragraph")
            reading_order = meta.get("reading_order", 0)
            heading_hierarchy = meta.get("heading_hierarchy", [])

            score = 0.5  # neutral baseline

            if is_overview:
                if is_title:
                    score = 1.0
                elif struct_type == "heading":
                    score = 0.8
                # Earlier chunks get slight boost for overview questions
                if reading_order == 0:
                    score = max(score, 0.8)
            else:
                if section_topics:
                    chunk_text_lower = chunk.get("chunk_text", chunk.get("content", "")).lower()
                    heading_text = " ".join(heading_hierarchy).lower() if heading_hierarchy else ""
                    combined = chunk_text_lower + " " + heading_text
                    topic_match = any(kw in combined for kw in section_topics)
                    if topic_match:
                        if struct_type == "heading":
                            score = 0.8
                        elif struct_type == "list_item":
                            score = 0.7
                        else:
                            score = 0.55

            scores.append(round(score, 4))

        return scores

    # ------------------------------------------------------------------
    # Original Score Calibration
    # ------------------------------------------------------------------
    def _calibrate_original_scores(
        self, chunks: list[dict[str, Any]]
    ) -> list[float]:
        """
        Calibrate original FAISS similarity scores.

        FAISS scores are already in [0, 1] range via 1/(1+dist). We clamp
        rather than min-max normalize to preserve magnitude differences
        and avoid extreme 0.0 / 1.0 gaps on small candidate sets.

        Args:
            chunks: List of chunks with 'score' field

        Returns:
            List of calibrated scores in [0, 1]
        """
        if not chunks:
            return []

        original_scores = [c.get("score", 0.0) for c in chunks]

        # Clamp to [0, 1] without aggressive min-max normalization
        # This preserves the raw semantic similarity magnitude
        return [max(0.0, min(1.0, s)) for s in original_scores]

    # ------------------------------------------------------------------
    # LLM-Based Relevance Scoring
    # ------------------------------------------------------------------
    def _compute_llm_relevance_scores(
        self, query: str, chunks: list[dict[str, Any]]
    ) -> list[float]:
        """
        Use LLM to assess relevance of each chunk to the query.

        This is an optional, more expensive scoring method that uses the
        LLM to evaluate how well each chunk answers the query.

        Args:
            query: The search query
            chunks: List of candidate chunks

        Returns:
            List of LLM-assessed relevance scores
        """
        if not self.use_llm_scoring:
            return [0.0 for _ in chunks]

        # Import here to avoid circular dependencies
        try:
            from app.services.llm import get_llm_service
            llm = get_llm_service()
        except Exception as e:
            logger.warning(f"LLM scoring unavailable: {e}")
            return [0.0 for _ in chunks]

        scores = []
        system_prompt = """
        You are a relevance assessor. Evaluate how well the given text chunk
        answers or relates to the query. Score from 0.0 to 1.0:
        - 1.0: Directly and completely answers the query
        - 0.7-0.9: Highly relevant, partial answer
        - 0.4-0.6: Somewhat relevant
        - 0.1-0.3: Barely relevant
        - 0.0: Not relevant at all

        Return only the numeric score (e.g., "0.85").
        """

        for chunk in chunks:
            chunk_text = chunk.get("chunk_text", "")
            user_prompt = f"""
            Query: {query}

            Chunk: {chunk_text[:500]}...

            Relevance score (0.0-1.0):
            """

            try:
                response = llm.chat(system_prompt, user_prompt)
                # Extract numeric score
                match = re.search(r'(\d+\.?\d*)', response)
                if match:
                    score = float(match.group(1))
                    score = max(0.0, min(1.0, score))  # Clamp to [0, 1]
                else:
                    score = 0.5
                scores.append(score)
            except Exception as e:
                logger.warning(f"LLM scoring failed for chunk: {e}")
                scores.append(0.5)

        return scores

    # ------------------------------------------------------------------
    # Ensemble Ranking
    # ------------------------------------------------------------------
    def _compute_ensemble_scores(
        self,
        query: str,
        chunks: list[dict[str, Any]],
        weights: Optional[dict[str, float]] = None,
    ) -> list[RankedItem]:
        """
        Compute final ensemble scores by combining multiple ranking signals.

        Uses weighted combination of:
        - Semantic similarity (40%)
        - Keyword overlap (25%)
        - Original score calibration (25%)
        - LLM relevance (10%, optional)

        Args:
            query: The search query
            chunks: List of candidate chunks
            weights: Optional custom weights for each signal

        Returns:
            List of RankedItem objects sorted by final score (descending)
        """
        if not chunks:
            return []

        # Default weights
        default_weights = {
            "semantic": 0.35,
            "keyword": 0.20,
            "original": 0.20,
            "llm": 0.05,
            "structural": 0.20,
        }

        if weights:
            default_weights.update(weights)

        w = default_weights

        # Compute individual scores
        semantic_scores = self._compute_semantic_scores(query, chunks)
        keyword_scores = self._compute_keyword_scores(query, chunks)
        original_scores = self._calibrate_original_scores(chunks)
        llm_scores = self._compute_llm_relevance_scores(query, chunks)
        structural_scores = self._compute_structural_scores(query, chunks)

        # Normalize weights if LLM scoring is disabled
        if not self.use_llm_scoring:
            total = w["semantic"] + w["keyword"] + w["original"] + w["structural"]
            w["semantic"] /= total
            w["keyword"] /= total
            w["original"] /= total
            w["structural"] /= total
            w["llm"] = 0.0

        # Compute ensemble scores
        ranked_items = []
        for i, chunk in enumerate(chunks):
            semantic = semantic_scores[i] if i < len(semantic_scores) else 0.0
            keyword = keyword_scores[i] if i < len(keyword_scores) else 0.0
            original = original_scores[i] if i < len(original_scores) else 0.0
            llm = llm_scores[i] if i < len(llm_scores) else 0.0
            structural = structural_scores[i] if i < len(structural_scores) else 0.5

            final_score = (
                w["semantic"] * semantic
                + w["keyword"] * keyword
                + w["original"] * original
                + w["llm"] * llm
                + w["structural"] * structural
            )

            ranked_item = RankedItem(
                chunk_id=chunk.get("chunk_id", f"unknown_{i}"),
                content=chunk.get("chunk_text", ""),
                final_score=round(final_score, 4),
                rank=0,  # Will be set after sorting
                semantic_score=round(semantic, 4),
                keyword_score=round(keyword, 4),
                original_score=round(original, 4),
                llm_relevance_score=round(llm, 4) if self.use_llm_scoring else None,
                structural_score=round(structural, 4),
                file_name=chunk.get("file_name"),
                page_number=chunk.get("page_number"),
                metadata=chunk.get("metadata", {}),
            )
            ranked_items.append(ranked_item)

        # Sort by final score (descending)
        ranked_items.sort(key=lambda x: x.final_score, reverse=True)

        # Assign ranks
        for rank, item in enumerate(ranked_items, 1):
            item.rank = rank

        return ranked_items

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def rerank(
        self,
        query: str,
        chunks: list[dict[str, Any]],
        top_k: Optional[int] = None,
        weights: Optional[dict[str, float]] = None,
        return_all: bool = False,
    ) -> dict[str, Any]:
        """
        Main reranking method.

        Takes initial retrieval results and produces a refined, ranked list.

        Args:
            query: The search query
            chunks: List of candidate chunks from initial retrieval
            top_k: Number of top results to return (None for all)
            weights: Optional custom weights for ranking signals
            return_all: If True, return all chunks; otherwise only top_k

        Returns:
            Dictionary with:
                - ranked_items: List of RankedItem objects
                - top_k_items: Top k items (if top_k specified)
                - ranking_summary: Summary statistics
                - signal_scores: Individual signal contributions
        """
        if not chunks:
            return {
                "ranked_items": [],
                "top_k_items": [],
                "ranking_summary": {
                    "total_candidates": 0,
                    "returned_count": 0,
                    "max_score": 0.0,
                    "min_score": 0.0,
                    "mean_score": 0.0,
                    "median_score": 0.0,
                    "score_std": 0.0,
                },
                "signal_scores": {
                    "semantic": 0.0,
                    "keyword": 0.0,
                    "original": 0.0,
                    "llm": None,
                    "structural": 0.0,
                },
                "weights_used": weights or {
                    "semantic": 0.35,
                    "keyword": 0.20,
                    "original": 0.20,
                    "llm": 0.05 if self.use_llm_scoring else 0.0,
                    "structural": 0.20,
                },
            }

        # Compute ensemble ranking
        ranked_items = self._compute_ensemble_scores(query, chunks, weights)

        # Apply top_k filter
        if top_k is not None and top_k > 0:
            top_k_items = ranked_items[:top_k]
        else:
            top_k_items = ranked_items

        # Compute ranking summary statistics
        scores = [item.final_score for item in ranked_items]
        ranking_summary = {
            "total_candidates": len(chunks),
            "returned_count": len(top_k_items),
            "max_score": max(scores) if scores else 0.0,
            "min_score": min(scores) if scores else 0.0,
            "mean_score": sum(scores) / len(scores) if scores else 0.0,
            "median_score": sorted(scores)[len(scores) // 2] if scores else 0.0,
            "score_std": (
                math.sqrt(sum((s - sum(scores) / len(scores)) ** 2 for s in scores) / len(scores))
                if scores
                else 0.0
            ),
        }

        # Signal score contributions (average per signal)
        signal_scores = {
            "semantic": sum(item.semantic_score for item in ranked_items) / len(ranked_items) if ranked_items else 0.0,
            "keyword": sum(item.keyword_score for item in ranked_items) / len(ranked_items) if ranked_items else 0.0,
            "original": sum(item.original_score for item in ranked_items) / len(ranked_items) if ranked_items else 0.0,
            "llm": sum(item.llm_relevance_score for item in ranked_items if item.llm_relevance_score) / len([i for i in ranked_items if i.llm_relevance_score]) if any(i.llm_relevance_score for i in ranked_items) else None,
            "structural": sum(item.structural_score for item in ranked_items) / len(ranked_items) if ranked_items else 0.0,
        }

        result = {
            "ranked_items": [item.to_dict() for item in ranked_items],
            "top_k_items": [item.to_dict() for item in top_k_items],
            "ranking_summary": ranking_summary,
            "signal_scores": signal_scores,
            "weights_used": weights or {
                "semantic": 0.35,
                "keyword": 0.20,
                "original": 0.20,
                "llm": 0.05 if self.use_llm_scoring else 0.0,
                "structural": 0.20,
            },
        }

        logger.info(
            f"Reranking completed: {len(chunks)} candidates -> {len(top_k_items)} top results, "
            f"mean_score={ranking_summary['mean_score']:.4f}, max_score={ranking_summary['max_score']:.4f}"
        )

        return result

    def rerank_simple(
        self,
        query: str,
        chunks: list[dict[str, Any]],
        top_k: Optional[int] = None,
    ) -> list[dict[str, Any]]:
        """
        Simplified reranking interface returning just the top-k items.

        Args:
            query: The search query
            chunks: List of candidate chunks
            top_k: Number of top results to return

        Returns:
            List of ranked chunk dictionaries
        """
        result = self.rerank(query, chunks, top_k=top_k)
        return result["top_k_items"]
