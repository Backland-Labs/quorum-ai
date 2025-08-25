"""
Pearl-compliant logging infrastructure for autonomous AI agents.

This module provides logging functionality that meets Pearl platform requirements,
producing log.txt file in the exact format required for agent monitoring and debugging.
"""

import logging
import logging.handlers
import os
import re
from contextlib import contextmanager
from datetime import datetime
from typing import Any


class PearlFormatter(logging.Formatter):
    """
    Custom formatter for Pearl platform compliance.

    Produces log messages in the exact format required by Pearl:
    [YYYY-MM-DD HH:MM:SS,mmm] [LOG_LEVEL] [agent] Message

    Pearl platform monitors this specific format for agent health and debugging.
    """

    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record according to Pearl requirements.

        Args:
            record: Python logging record to format

        Returns:
            Formatted log string with Pearl-compliant timestamp, level, and agent prefix
        """
        # Convert timestamp to Pearl format: YYYY-MM-DD HH:MM:SS,mmm
        timestamp = datetime.fromtimestamp(record.created).strftime(
            "%Y-%m-%d %H:%M:%S,%f"
        )[:-3]

        # Convert Python log levels to Pearl format
        level_mapping = {
            "WARNING": "WARN",  # Pearl uses WARN instead of WARNING
            "CRITICAL": "ERROR",  # Map CRITICAL to ERROR for Pearl
        }
        level_name = level_mapping.get(record.levelname, record.levelname)

        # Get the formatted message (handles % formatting)
        message = record.getMessage()

        # Build Pearl-compliant log line
        formatted_message = f"[{timestamp}] [{level_name}] [agent] {message}"

        # If there's exception info, append it
        if record.exc_info and record.exc_info != (None, None, None):
            # Use standard formatter for exception text
            exc_text = self.formatException(record.exc_info)
            formatted_message = f"{formatted_message}\n{exc_text}"

        return formatted_message


class StructuredAdapter(logging.LoggerAdapter):
    """
    Adapter for structured logging with Pearl compliance.

    Provides additional context and structured logging capabilities
    while maintaining Pearl format compatibility.
    """

    def __init__(self, logger: logging.Logger, extra: dict[str, Any] | None = None):
        """
        Initialize structured adapter.

        Args:
            logger: Base logger instance
            extra: Additional context to include in log records
        """
        super().__init__(logger, extra or {})

    def process(self, msg: str, kwargs: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        """
        Process log message with additional context.

        Args:
            msg: Log message
            kwargs: Additional keyword arguments

        Returns:
            Tuple of processed message and updated kwargs
        """
        # Add any structured data to the message if needed
        # For now, keep it simple to maintain Pearl compliance
        return msg, kwargs


def setup_pearl_logger(
    name: str = "agent",
    level: int = logging.INFO,
    log_file_path: str | None = None,
    store_path: str | None = None,
) -> logging.Logger:
    """
    Configure logging for Pearl platform compliance.

    Creates a logger that writes to log.txt file in Pearl-required format.

    Args:
        name: Logger name (default: 'agent')
        level: Logging level (default: INFO)
        log_file_path: Custom log file path (default: log.txt in current directory)
        store_path: Pearl STORE_PATH environment variable value

    Returns:
        Configured logger instance ready for Pearl deployment
    """
    logger = logging.getLogger(name)

    # Clear existing handlers to avoid duplicates
    for handler in logger.handlers[:]:
        handler.close()
        logger.removeHandler(handler)

    logger.setLevel(level)

    # Determine log file location
    if log_file_path is None:
        # Use STORE_PATH if provided by Pearl, otherwise current directory
        base_path = store_path or os.getcwd()
        log_file_path = os.path.join(base_path, "log.txt")

    # Ensure log file directory exists
    log_dir = os.path.dirname(log_file_path)
    if log_dir:  # Only create directory if there is one
        os.makedirs(log_dir, exist_ok=True)

    # Create file handler for log.txt
    handler = logging.FileHandler(log_file_path, mode="a", encoding="utf-8")

    # Apply Pearl-compliant formatter
    formatter = PearlFormatter()
    handler.setFormatter(formatter)

    logger.addHandler(handler)

    # Log initialization
    logger.info("Pearl logger initialized successfully")

    return logger


@contextmanager
def log_span(logger: logging.Logger, operation: str, **context):
    """
    Context manager for operation logging (replaces Logfire spans).

    Provides structured operation logging while maintaining Pearl compliance.
    Logs operation start, duration, and completion status.

    Args:
        logger: Logger instance to use
        operation: Name of the operation being performed
        **context: Additional context to include in logs

    Yields:
        Dictionary for adding span-specific data
    """
    start_time = datetime.now()
    span_data = {}

    # Log operation start
    context_str = ", ".join(f"{k}={v}" for k, v in context.items()) if context else ""
    start_msg = f"Starting {operation}"
    if context_str:
        start_msg += f" ({context_str})"
    logger.info(start_msg)

    try:
        yield span_data

        # Log successful completion
        duration = (datetime.now() - start_time).total_seconds()
        success_msg = f"Completed {operation} successfully in {duration:.3f}s"
        if span_data:
            span_context = ", ".join(f"{k}={v}" for k, v in span_data.items())
            success_msg += f" ({span_context})"
        logger.info(success_msg)

    except Exception as e:
        # Log failure
        duration = (datetime.now() - start_time).total_seconds()
        error_msg = f"Failed {operation} after {duration:.3f}s: {e!s}"
        logger.exception(error_msg)
        raise


def validate_log_format(log_line: str) -> bool:
    """
    Validate that log line matches Pearl required format.

    Used for testing and debugging to ensure Pearl compliance.

    Args:
        log_line: Log line to validate

    Returns:
        True if line matches Pearl format, False otherwise
    """
    pattern = r"^\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}\] \[(ERROR|WARN|INFO|DEBUG|TRACE)\] \[agent\] .*"
    return bool(re.match(pattern, log_line))


def ensure_log_file_exists(log_file_path: str = "log.txt") -> bool:
    """
    Ensure log.txt exists and is writable.

    Creates log file if it doesn't exist and writes initialization message.

    Args:
        log_file_path: Path to log file

    Returns:
        True if log file is ready, False if there were issues
    """
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(log_file_path) or ".", exist_ok=True)

        # Test write access
        with open(log_file_path, "a", encoding="utf-8") as f:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S,%f")[:-3]
            f.write(f"[{timestamp}] [INFO] [agent] Log file initialized\n")
        return True
    except Exception as e:
        # Fallback to stderr if logging isn't set up yet
        import sys

        sys.stderr.write(f"Failed to initialize log file {log_file_path}: {e}\n")
        return False
