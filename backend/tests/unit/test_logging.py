"""
Unit tests for logging configuration.
"""
import logging
import pytest
from app.core.logging import setup_logging, get_logger, StructuredLogger


class TestLogging:
    """Tests for logging module."""

    def test_setup_logging_configures_handler(self):
        """Test that setup_logging configures logging without error."""
        setup_logging()
        root_logger = logging.getLogger()
        # Should have at least one handler
        assert len(root_logger.handlers) > 0

    def test_get_logger_returns_logger_instance(self):
        """Test get_logger returns a Logger."""
        logger = get_logger("test.module")
        assert isinstance(logger, logging.Logger)
        assert logger.name == "test.module"

    def test_structured_logger_info(self, caplog):
        """Test StructuredLogger info method."""
        logger = StructuredLogger("test")
        with caplog.at_level(logging.INFO):
            logger.info("Test message", key="value", count=5)
        # Verify message logged
        assert any("Test message" in record.getMessage() for record in caplog.records)

    def test_structured_logger_error(self):
        """Test StructuredLogger error method does not raise."""
        logger = StructuredLogger("test")
        logger.error("Error occurred", risk="high")  # Should not raise

    def test_structured_logger_format_message_with_kwargs(self):
        """Test message formatting with keyword args."""
        logger = StructuredLogger("test")
        formatted = logger._format_message("Hello", user="alice", action="login")
        assert "Hello" in formatted
        assert "user=alice" in formatted
        assert "action=login" in formatted

    def test_structured_logger_format_message_without_kwargs(self):
        """Test message formatting without kwargs."""
        logger = StructuredLogger("test")
        formatted = logger._format_message("Simple message")
        assert formatted == "Simple message"
