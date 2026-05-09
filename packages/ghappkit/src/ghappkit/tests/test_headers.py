"""Tests for GitHub webhook header parsing."""

from __future__ import annotations

import pytest

from ghappkit.exceptions import WebhookHeaderError
from ghappkit.headers import (
    normalize_http_headers,
    parse_github_delivery_headers,
    parse_github_delivery_headers_normalized,
)


def test_parses_required_headers_case_insensitive() -> None:
    headers = parse_github_delivery_headers(
        {
            "x-github-event": "issues",
            "x-github-delivery": "abc-123",
            "X-Hub-Signature-256": "sha256=dead",
        },
    )
    assert headers.event == "issues"
    assert headers.delivery_id == "abc-123"
    assert headers.signature_256 == "sha256=dead"


def test_missing_event_header() -> None:
    with pytest.raises(WebhookHeaderError, match="missing X-GitHub-Event"):
        parse_github_delivery_headers({"X-GitHub-Delivery": "d1"})


def test_blank_event_header() -> None:
    with pytest.raises(WebhookHeaderError, match="missing X-GitHub-Event"):
        parse_github_delivery_headers(
            {"X-GitHub-Event": "   ", "X-GitHub-Delivery": "d1"},
        )


def test_missing_delivery_header() -> None:
    with pytest.raises(WebhookHeaderError, match="missing X-GitHub-Delivery"):
        parse_github_delivery_headers({"X-GitHub-Event": "push"})


def test_optional_headers() -> None:
    headers = parse_github_delivery_headers(
        {
            "X-GitHub-Event": "ping",
            "X-GitHub-Delivery": "d",
            "X-GitHub-Hook-ID": "99",
            "User-Agent": "GitHub-Hookshot/test",
        },
    )
    assert headers.hook_id == "99"
    assert headers.user_agent == "GitHub-Hookshot/test"


def test_parse_github_delivery_headers_normalized_skips_second_normalize() -> None:
    lowered = normalize_http_headers(
        {"X-GitHub-Event": "ping", "X-GitHub-Delivery": "d-x"},
    )
    headers = parse_github_delivery_headers_normalized(lowered)
    assert headers.event == "ping"
    assert headers.delivery_id == "d-x"


def test_normalize_http_headers_lowercases_names() -> None:
    lowered = normalize_http_headers({"X-GitHub-Event": "push", "X-Foo": "bar"})
    assert lowered == {"x-github-event": "push", "x-foo": "bar"}
