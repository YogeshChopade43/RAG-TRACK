import logging
from functools import lru_cache
from typing import Optional

from sentence_transformers import SentenceTransformer

from app.core.config import settings

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_shared_embedding_model() -> SentenceTransformer:
    """Get the shared cached embedding model instance."""
    logger.info(f"Loading shared embedding model: {settings.embedding_model}")
    model = SentenceTransformer(settings.embedding_model)
    logger.info("Shared embedding model loaded successfully")
    return model


@lru_cache(maxsize=1)
def get_shared_rerank_model() -> Optional[SentenceTransformer]:
    """Get the shared cached rerank embedding model instance."""
    logger.info(f"Loading shared rerank model: {settings.embedding_model}")
    model = SentenceTransformer(settings.embedding_model)
    logger.info("Shared rerank model loaded successfully")
    return model
