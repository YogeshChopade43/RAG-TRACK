"""
LLM service for RAG-TRACK.

Provides LLM integration with OpenAI-compatible APIs.
"""
import logging
import os
from typing import Optional

from dotenv import load_dotenv
from openai import OpenAI
from openai.types.chat import ChatCompletion
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
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
        api_key = settings.openrouter_api_key or os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            logger.warning(
                "OPENROUTER_API_KEY not configured — "
                "LLM-dependent features will use fallbacks. "
                "Set OPENROUTER_API_KEY for full functionality."
            )
            api_key = "no-key-configured"
        self.client = OpenAI(
            api_key=api_key,
            base_url=settings.openrouter_base_url or "https://openrouter.ai/api/v1",
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
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ) -> str:
        """
        Send a chat request to the LLM.

        Args:
            system_prompt: System prompt context
            user_prompt: User prompt/query
            api_key: Optional user-provided API key (overrides env)
            model: Optional user-provided model name (overrides env default)

        Returns:
            LLM response text

        Raises:
            LLMError: If request fails after retries
        """
        try:
            llm_model = model or self.model
            logger.debug(
                "Sending request to LLM",
                model=llm_model,
                prompt_length=len(user_prompt),
            )

            client = self.client
            if api_key:
                client = OpenAI(
                    api_key=api_key,
                    base_url=settings.openrouter_base_url or os.getenv("OPENROUTER_BASE_URL"),
                    timeout=settings.llm_timeout_seconds,
                    default_headers={
                        "HTTP-Referer": "http://localhost:8000",
                        "X-Title": "RAG-TRACK",
                    },
                )

            response: ChatCompletion = client.chat.completions.create(
                model=llm_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )

            # Extract text from response
            if not response.choices:
                logger.warning("LLM returned empty response")
                return "The model returned an empty response."

            text = response.choices[0].message.content
            logger.debug(
                "LLM response received",
                text_length=len(text) if text else 0,
            )
            return text.strip() if text else "The model returned no text content."

        except Exception as e:
            logger.error(f"LLM request failed: {str(e)}")
            raise

    def __repr__(self) -> str:
        """String representation."""
        return f"LLMService(model={self.model})"
