"""
LLM service for RAG-TRACK.

Provides LLM integration with OpenAI-compatible APIs.
"""
import logging
import os
from typing import Optional

from openai import OpenAI
from openai.types.responses import Response
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


class LLMService:
    """Service for interacting with LLM APIs."""

    _instance: Optional["LLMService"] = None

    def __init__(self):
        """Initialize LLM service."""
        self.client = OpenAI(
            api_key=settings.openrouter_api_key or os.getenv("OPENROUTER_API_KEY"),
            base_url=settings.openrouter_base_url or os.getenv("OPENROUTER_BASE_URL"),
            timeout=settings.llm_timeout_seconds,
        )
        self.model = settings.llm_model
        self.temperature = settings.llm_temperature
        self.max_tokens = settings.llm_max_tokens
        logger.info(f"LLM service initialized with model: {self.model}")

    @classmethod
    def get_instance(cls) -> "LLMService":
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
        Send a chat request to the LLM.

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
                f"Sending request to LLM",
                model=self.model,
                prompt_length=len(user_prompt),
            )

            response: Response = self.client.responses.create(
                model=self.model,
                input=[
                    {"role": "system", "text": system_prompt},
                    {"role": "user", "text": user_prompt},
                ],
                temperature=self.temperature,
                max_output_tokens=self.max_tokens,
            )

            # Extract text from response
            if not response.output:
                logger.warning("LLM returned empty response")
                return "The model returned an empty response."

            # Get first text output
            for item in response.output:
                if hasattr(item, "type") and item.type == "message":
                    if item.content and hasattr(item.content[0], "text"):
                        text = item.content[0].text
                        logger.debug(
                            f"LLM response received",
                            text_length=len(text),
                        )
                        return text.strip()

            # Fallback
            logger.warning("No text content in LLM response")
            return "The model returned no text content."

        except Exception as e:
            logger.error(f"LLM request failed: {str(e)}")
            raise

    def __repr__(self) -> str:
        """String representation."""
        return f"LLMService(model={self.model})"