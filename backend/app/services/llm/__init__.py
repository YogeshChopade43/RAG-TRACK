"""
LLM service factory for RAG-TRACK.

Provides access to the OpenRouter cloud LLM service.
"""

import logging

logger = logging.getLogger(__name__)


def get_llm_service():
    """Get the OpenRouter LLM service instance."""
    from app.services.llm.llm_service import LLMService

    return LLMService.get_instance()