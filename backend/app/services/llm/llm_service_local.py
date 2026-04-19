"""
LLM service for RAG-TRACK using Ollama (local models).

Provides LLM integration with Ollama's local API.
"""

import logging
import os
from typing import Optional

import requests
from dotenv import load_dotenv
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from app.core.config import settings

logger = logging.getLogger(__name__)

load_dotenv()


class LLMError(Exception):
    """Base exception for LLM errors."""

    pass


class LLMTimeoutError(LLMError):
    """LLM request timed out."""

    pass


class LLMAPIError(LLMError):
    """LLM API returned an error."""

    pass


class LLMServiceLocal:
    """Service for interacting with Ollama local LLM API."""

    _instance: Optional["LLMServiceLocal"] = None

    def __init__(self):
        """Initialize LLM service."""
        self.base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip(
            "/v1"
        )
        self.model = os.getenv("OLLAMA_MODEL", "deepseek-r1:1.5b")
        self.temperature = settings.llm_temperature
        self.max_tokens = settings.llm_max_tokens
        self.timeout = settings.llm_timeout_seconds
        logger.info(f"LLM service (Ollama) initialized with model: {self.model}")

    @classmethod
    def get_instance(cls) -> "LLMServiceLocal":
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(Exception),
        reraise=True,
    )
    def chat(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        """
        Send a chat request to the Ollama LLM.

        Args:
            system_prompt: System prompt context
            user_prompt: User prompt/query

        Returns:
            LLM response text

        Raises:
            LLMError: If request fails after retries
        """
        try:
            logger.debug(
                f"Sending request to Ollama",
                model=self.model,
                prompt_length=len(user_prompt),
            )

            url = f"{self.base_url.rstrip('/')}/api/generate"
            payload = {
                "model": self.model,
                "prompt": user_prompt,
                "system": system_prompt,
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
                "stream": False,
            }

            response = requests.post(
                url,
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()

            data = response.json()

            text = (
                data.get("response")
                or data.get("message", {}).get("content")
                or data.get("content")
                or ""
            ).strip()

            if not text:
                logger.warning(f"Ollama raw response: {data}")
                return "The model returned an empty response."

            return text

        except requests.exceptions.Timeout:
            logger.error(f"Ollama request timed out after {self.timeout}s")
            raise LLMTimeoutError(f"Request timed out after {self.timeout} seconds")
        except requests.exceptions.RequestException as e:
            logger.error(f"Ollama request failed: {str(e)}")
            raise LLMAPIError(f"Ollama API error: {str(e)}")
        except Exception as e:
            logger.error(f"LLM request failed: {str(e)}")
            raise

    def __repr__(self) -> str:
        """String representation."""
        return f"LLMServiceLocal(model={self.model})"
