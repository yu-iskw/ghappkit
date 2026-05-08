"""Structured logging helpers with conservative redaction."""

from __future__ import annotations

import logging
import re

_FORBIDDEN_FIELDS = re.compile(
    r"(authorization|token|secret|password|body|issue\.body|comment\.body)",
    re.IGNORECASE,
)


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


def sanitize_record(record: logging.LogRecord) -> bool:
    """Return False when a message likely contains sensitive material."""
    msg = str(record.msg)
    return _FORBIDDEN_FIELDS.search(msg) is None
