"""
Logging configuration for RAG-TRACK application.

Provides structured logging with JSON support for production observability.
"""

import json
import logging
import logging.config
import sys
import traceback
from typing import Any

from app.core.config import settings


class JsonFormatter(logging.Formatter):
    """Format log records as JSON."""

    def format(self, record: logging.LogRecord) -> str:
        log_data: dict[str, Any] = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        if record.exc_info:
            log_data["exception"] = traceback.format_exception(*record.exc_info)

        if record.stack_info:
            log_data["stack_info"] = record.stack_info

        extra = {
            key: value
            for key, value in record.__dict__.items()
            if key
            not in (
                "name",
                "msg",
                "args",
                "created",
                "relativeCreated",
                "exc_info",
                "exc_text",
                "stack_info",
                "lineno",
                "funcName",
                "pathname",
                "filename",
                "module",
                "levelname",
                "levelno",
                "thread",
                "threadName",
                "process",
                "processName",
                "msecs",
                "message",
                "taskName",
            )
            and not key.startswith("_")
        }
        if extra:
            log_data.update(extra)

        return json.dumps(log_data, default=str)


def setup_logging() -> None:
    """Configure application logging based on settings."""
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)

    if settings.log_format == "json":
        formatter = JsonFormatter()
    else:
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    logging.basicConfig(level=log_level, handlers=[handler])

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
