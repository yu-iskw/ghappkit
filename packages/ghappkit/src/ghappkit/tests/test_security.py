"""Tests for webhook signature verification."""

# Synthetic secrets for HMAC verification tests only.
# ruff: noqa: S105, S106

from __future__ import annotations

import hashlib
import hmac

import pytest

from ghappkit.exceptions import (
    InvalidWebhookSignatureError,
    MalformedWebhookSignatureError,
    MissingWebhookSignatureError,
    WebhookSignatureError,
)
from ghappkit.security import verify_github_signature


def _sig(secret: str, body: bytes) -> str:
    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def test_accepts_valid_signature() -> None:
    secret = "hunter2"
    body = b'{"hello":"world"}'
    verify_github_signature(secret=secret, body=body, signature_header=_sig(secret, body))


def test_rejects_invalid_signature() -> None:
    with pytest.raises(InvalidWebhookSignatureError):
        verify_github_signature(
            secret="a",
            body=b"{}",
            signature_header="sha256=" + "a" * 64,
        )


def test_rejects_missing_header() -> None:
    with pytest.raises(MissingWebhookSignatureError):
        verify_github_signature(secret="a", body=b"{}", signature_header=None)
    with pytest.raises(MissingWebhookSignatureError):
        verify_github_signature(secret="a", body=b"{}", signature_header="   ")


def test_rejects_wrong_algorithm() -> None:
    with pytest.raises(MalformedWebhookSignatureError):
        verify_github_signature(
            secret="a",
            body=b"{}",
            signature_header="md5=abc",
        )


def test_rejects_digest_wrong_length() -> None:
    with pytest.raises(MalformedWebhookSignatureError):
        verify_github_signature(
            secret="a",
            body=b"{}",
            signature_header="sha256=ab",
        )


def test_rejects_non_hex_digest() -> None:
    bad = "sha256=" + "g" * 64
    with pytest.raises(MalformedWebhookSignatureError):
        verify_github_signature(secret="a", body=b"{}", signature_header=bad)


def test_empty_body_with_valid_hmac() -> None:
    secret = "k"
    body = b""
    verify_github_signature(secret=secret, body=body, signature_header=_sig(secret, body))


def test_non_ascii_utf8_payload() -> None:
    secret = "s"
    body = '{"snowman":"\u2603"}'.encode("utf-8")
    verify_github_signature(secret=secret, body=body, signature_header=_sig(secret, body))


def test_subclasses_are_webhook_signature_errors() -> None:
    with pytest.raises(WebhookSignatureError):
        verify_github_signature(secret="x", body=b"x", signature_header=None)
