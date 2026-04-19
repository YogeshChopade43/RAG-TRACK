"""
Logging configuration for RAG-TRACK application.

Provides structured logging with JSON support for production observability.
"""

import logging
import logging.config
import sys
from typing import Any, Dict

from app.core.config import settings


def setup_logging() -> None:
    """Configure application logging based on settings."""
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)

    if settings.log_format == "json":
        # Use standard logging for now - JSON formatting can be added with python-json-logger
        logging.basicConfig(
            level=log_level,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[logging.StreamHandler(sys.stdout)],
        )
    else:
        logging.basicConfig(
            level=log_level,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[logging.StreamHandler(sys.stdout)],
        )

    # Set specific loggers
    logging.getLogger("uvicorn").setLevel(log_level)
    logging.getLogger("fastapi").setLevel(log_level)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the given name."""
    return logging.getLogger(name)


class StructuredLogger:
    """Structured logger wrapper for consistent logging format."""

    def __init__(self, name: str):
        self.logger = logging.getLogger(name)

    def info(self, message: str, **kwargs: Any) -> None:
        """Log info message with additional context."""
        self.logger.info(self._format_message(message, **kwargs))

    def debug(self, message: str, **kwargs: Any) -> None:
        """Log debug message with additional context."""
        self.logger.debug(self._format_message(message, **kwargs))

    def warning(self, message: str, **kwargs: Any) -> None:
        """Log warning message with additional context."""
        self.logger.warning(self._format_message(message, **kwargs))

    def error(self, message: str, **kwargs: Any) -> None:
        """Log error message with additional context."""
        self.logger.error(self._format_message(message, **kwargs))

    def exception(self, message: str, **kwargs: Any) -> None:
        """Log exception with traceback."""
        self.logger.exception(self._format_message(message, **kwargs))

    def _format_message(self, message: str, **kwargs: Any) -> str:
        """Format message with additional context."""
        if kwargs:
            context = ", ".join(f"{k}={v}" for k, v in kwargs.items())
            return f"{message} ({context})"
        return message
