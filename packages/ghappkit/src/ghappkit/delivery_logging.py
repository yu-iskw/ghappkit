"""Structured logging helpers with conservative redaction."""

from __future__ import annotations

import logging
import re

_LOGGER_MARK_ATTR = "_ghappkit_delivery_sanitize_filter_installed"

# Word boundaries avoid matching substrings like ``nobody`` for ``body``.
_FORBIDDEN_FIELDS = re.compile(
    r"(?:"
    r"\b(?:authorization|token|secret|password)\b|"
    r"\bbody\b|"
    r"issue\.body|comment\.body"
    r")",
    re.IGNORECASE,
)


def sanitize_record(record: logging.LogRecord) -> bool:
    """Return False when a message likely contains sensitive material."""
    msg = str(record.msg)
    return _FORBIDDEN_FIELDS.search(msg) is None


class DeliveryLogSanitizeFilter(logging.Filter):
    """Drop log records whose message matches sensitive patterns."""

    def filter(self, record: logging.LogRecord) -> bool:
        return sanitize_record(record)


def ensure_delivery_log_sanitize_filter(logger: logging.Logger) -> None:
    """Attach :class:`DeliveryLogSanitizeFilter` once per logger instance."""

    if getattr(logger, _LOGGER_MARK_ATTR, False):
        return
    logger.addFilter(DeliveryLogSanitizeFilter())
    setattr(logger, _LOGGER_MARK_ATTR, True)


def delivery_logger(
    base: logging.Logger,
    *,
    delivery_id: str,
    qualified_event: str,
    installation_id: int | None,
    repository: str | None,
    sender: str | None,
) -> logging.LoggerAdapter[logging.Logger]:
    """Bind minimal structured fields for observability."""
    extra = {
        "component": "ghappkit",
        "delivery_id": delivery_id,
        "qualified_event": qualified_event,
        "installation_id": installation_id,
        "repository": repository,
        "sender": sender,
    }
    return logging.LoggerAdapter(base, extra)
