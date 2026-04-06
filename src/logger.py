"""Centralized logging configuration for AI Research Telegram Digest."""

import logging
import os
import re
import sys
from typing import Optional


class _SecretFilter(logging.Filter):
    """Redact potential secrets from log output."""

    _PATTERNS = [
        (re.compile(r"sk-[a-zA-Z0-9\-_]{20,}"), "[REDACTED_KEY]"),
        (re.compile(r"Bearer\s+[a-zA-Z0-9\-_.]{10,}"), "Bearer [REDACTED]"),
        (re.compile(r"(?i)(api[_-]?key|token|secret|password)\s*[:=]\s*\S+"), r"\1=[REDACTED]"),
    ]

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            for pattern, replacement in self._PATTERNS:
                record.msg = pattern.sub(replacement, record.msg)
        return True


def setup_logger(
    name: str = "ai_research_digest",
    level: Optional[str] = None,
    log_format: Optional[str] = None,
) -> logging.Logger:
    """
    Set up and return a configured logger.

    Args:
        name: Logger name (defaults to root logger for the app)
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
               Falls back to LOG_LEVEL env var, then INFO
        log_format: Custom log format string

    Returns:
        Configured logger instance
    """
    # Determine log level from parameter, env var, or default
    if level is None:
        level = os.getenv("LOG_LEVEL", "INFO").upper()

    numeric_level = getattr(logging, level, logging.INFO)

    # Default format includes timestamp, level, module, and message
    if log_format is None:
        log_format = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"

    # Get or create logger
    logger = logging.getLogger(name)
    logger.setLevel(numeric_level)

    # Avoid duplicate handlers if logger already configured
    if logger.handlers:
        return logger

    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)

    # Create formatter
    formatter = logging.Formatter(log_format, datefmt="%Y-%m-%d %H:%M:%S")
    console_handler.setFormatter(formatter)

    # Add secret filter and handler to logger
    console_handler.addFilter(_SecretFilter())
    logger.addHandler(console_handler)

    # Prevent propagation to root logger to avoid duplicate logs
    logger.propagate = False

    return logger


def get_logger(module_name: str) -> logging.Logger:
    """
    Get a logger for a specific module.

    This creates a child logger under the main app logger,
    allowing module-specific logging while inheriting config.

    Args:
        module_name: Name of the module (typically __name__)

    Returns:
        Logger instance for the module
    """
    # Extract just the module name from full path
    short_name = module_name.split(".")[-1]
    return logging.getLogger(f"ai_research_digest.{short_name}")


# Initialize the root logger when module is imported
_root_logger = setup_logger()
