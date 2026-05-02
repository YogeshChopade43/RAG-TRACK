"""
LLM service factory for RAG-TRACK.

Provides unified access to LLM services - either local Ollama or cloud API.
"""

import logging
import os

logger = logging.getLogger(__name__)

USE_LOCAL_LLM = os.getenv("USE_LOCAL_LLM", "false").lower() == "true"


def get_llm_service():
    """
    Get LLM service based on configuration.

    Uses Ollama (local) if USE_LOCAL_LLM=true or OLLAMA_BASE_URL is set,
    otherwise uses OpenRouter.
    
    Returns:
        LLMService or LLMServiceLocal instance
    """
    from app.core.config import settings
    
    if USE_LOCAL_LLM or settings.ollama_base_url:
        logger.info("Using local LLM (Ollama)")
        from app.services.llm.llm_service_local import LLMServiceLocal
        return LLMServiceLocal.get_instance()
    else:
        logger.info("Using cloud LLM (OpenRouter)")
        from app.services.llm.llm_service import LLMService
        return LLMService.get_instance()