"""Structured logging configuration using structlog."""

import logging
import re
import sys

import structlog

from app.config import get_settings

# ``?key=<secret>`` in provider URLs (LiteLLM/httpx log these) and Bearer tokens.
_SECRET_PARAM_RE = re.compile(r"(?i)(\bkey=|bearer\s+)[^&\s'\"]+")


class RedactingFormatter(logging.Formatter):
    """Strip API keys from every log line, including tracebacks."""

    def format(self, record: logging.LogRecord) -> str:
        """Format the record, then mask configured keys and ``key=`` params."""
        text = super().format(record)
        for secret in get_settings().llm_api_keys.values():
            if secret and len(secret) >= 8:
                text = text.replace(secret, "***")
        return _SECRET_PARAM_RE.sub(r"\1***", text)


def configure_logging(log_level: str = "INFO") -> None:
    """Configure structured logging for the application.

    Args:
        log_level: Logging level string (DEBUG, INFO, WARNING, ERROR).
    """
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper(), logging.INFO),
    )
    for handler in logging.getLogger().handlers:
        handler.setFormatter(RedactingFormatter("%(message)s"))

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Get a structured logger instance.

    Args:
        name: Logger name (typically __name__).

    Returns:
        Configured structlog bound logger.
    """
    return structlog.get_logger(name)
