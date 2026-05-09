"""Tests for ordered webhook lifecycle helpers."""

# Synthetic webhook secrets for lifecycle ordering tests only.
# ruff: noqa: S105, S106

from __future__ import annotations

import pytest
from ghappkit_testing.signatures import sign_sha256_payload

from ghappkit.exceptions import InvalidWebhookSignatureError, MissingWebhookSignatureError
from ghappkit.webhooks import parse_delivery_after_optional_signature


def test_signature_checked_before_header_validation() -> None:
    """Wrong digest must fail even when GitHub event headers are absent."""
    with pytest.raises(InvalidWebhookSignatureError):
        parse_delivery_after_optional_signature(
            raw_body=b"{}",
            header_map={"X-Hub-Signature-256": "sha256=" + "a" * 64},
            webhook_secret="secret",
            require_signature=True,
        )


def test_missing_signature_before_header_errors() -> None:
    with pytest.raises(MissingWebhookSignatureError):
        parse_delivery_after_optional_signature(
            raw_body=b"{}",
            header_map={"X-GitHub-Event": "issues"},
            webhook_secret="s",
            require_signature=True,
        )


def test_skip_signature_parses_headers() -> None:
    headers = parse_delivery_after_optional_signature(
        raw_body=b"{}",
        header_map={
            "X-GitHub-Event": "ping",
            "X-GitHub-Delivery": "d-1",
        },
        webhook_secret="ignored",
        require_signature=False,
    )
    assert headers.event == "ping"
    assert headers.delivery_id == "d-1"


def test_valid_signature_then_headers() -> None:
    secret = "s3cret"
    body = b'{"action":"opened"}'
    headers = parse_delivery_after_optional_signature(
        raw_body=body,
        header_map={
            "X-GitHub-Event": "issues",
            "X-GitHub-Delivery": "del",
            "X-Hub-Signature-256": sign_sha256_payload(secret, body),
        },
        webhook_secret=secret,
        require_signature=True,
    )
    assert headers.event == "issues"
