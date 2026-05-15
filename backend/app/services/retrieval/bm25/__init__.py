"""
BM25 retrieval service for hybrid search.

Provides BM25 indexing and search functionality per document,
with lazy loading from disk and in-memory caching.
"""

from .service import BM25Service

__all__ = ["BM25Service"]
