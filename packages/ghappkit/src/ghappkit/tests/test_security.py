"""Tests for webhook signature verification."""

# Synthetic secrets for HMAC verification tests only.
# ruff: noqa: S105, S106

from __future__ import annotations

import hashlib
import hmac

import pytest

from ghappkit.exceptions import WebhookSignatureError
from ghappkit.security import verify_github_signature


def _sig(secret: str, body: bytes) -> str:
    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def test_accepts_valid_signature() -> None:
    secret = "hunter2"
    body = b'{"hello":"world"}'
    verify_github_signature(secret=secret, body=body, signature_header=_sig(secret, body))


def test_rejects_invalid_signature() -> None:
    with pytest.raises(WebhookSignatureError):
        verify_github_signature(
            secret="a",
            body=b"{}",
            signature_header="sha256=deadbeef",
        )


def test_rejects_missing_header() -> None:
    with pytest.raises(WebhookSignatureError):
        verify_github_signature(secret="a", body=b"{}", signature_header=None)


def test_rejects_malformed_prefix() -> None:
    with pytest.raises(WebhookSignatureError):
        verify_github_signature(
            secret="a",
            body=b"{}",
            signature_header="md5=abc",
        )
