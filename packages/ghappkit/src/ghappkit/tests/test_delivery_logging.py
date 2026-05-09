"""Tests for delivery log redaction filter."""

from __future__ import annotations

import logging

from ghappkit.delivery_logging import (
    DeliveryLogSanitizeFilter,
    ensure_delivery_log_sanitize_filter,
    sanitize_record,
)


def _record(msg: str) -> logging.LogRecord:
    return logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="x",
        lineno=1,
        msg=msg,
        args=(),
        exc_info=None,
    )


def test_sanitize_record_blocks_sensitive_substrings() -> None:
    assert sanitize_record(_record("authorization bearer x")) is False
    assert sanitize_record(_record("issue.body")) is False


def test_sanitize_record_allows_normal_messages() -> None:
    assert sanitize_record(_record("github_handler_completed")) is True


def test_sanitize_record_does_not_match_body_inside_unrelated_words() -> None:
    assert sanitize_record(_record("nobody matched the filter incorrectly")) is True


def test_ensure_delivery_log_sanitize_filter_is_idempotent() -> None:
    log = logging.getLogger("ghappkit.tests.delivery_logging.once")
    log.handlers.clear()
    ensure_delivery_log_sanitize_filter(log)
    ensure_delivery_log_sanitize_filter(log)
    filters = [f for f in log.filters if isinstance(f, DeliveryLogSanitizeFilter)]
    assert len(filters) == 1
