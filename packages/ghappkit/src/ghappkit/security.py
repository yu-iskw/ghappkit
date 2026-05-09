"""Webhook signature verification."""

from __future__ import annotations

import hashlib
import hmac
from collections.abc import Mapping

from ghappkit.exceptions import (
    InvalidWebhookSignatureError,
    MalformedWebhookSignatureError,
    MissingWebhookSignatureError,
)

HUB_SIGNATURE_SHA256_PREFIX = "sha256="


def verify_github_signature_from_headers(
    *,
    secret: str,
    body: bytes,
    headers: Mapping[str, str],
) -> None:
    """Read ``X-Hub-Signature-256`` case-insensitively and verify ``body``."""
    lowered = {k.lower(): v for k, v in headers.items()}
    signature_header = lowered.get("x-hub-signature-256")
    verify_github_signature(secret=secret, body=body, signature_header=signature_header)


def verify_github_signature(
    *,
    secret: str,
    body: bytes,
    signature_header: str | None,
) -> None:
    """Verify ``X-Hub-Signature-256`` using the webhook secret.

    Raises:
        MissingWebhookSignatureError: header missing or blank.
        MalformedWebhookSignatureError: not ``sha256=`` + 64 hex chars.
        InvalidWebhookSignatureError: digest mismatch (constant-time compare).
    """
    if not signature_header or not signature_header.strip():
        raise MissingWebhookSignatureError("missing X-Hub-Signature-256 header")
    header = signature_header.strip()
    prefix = HUB_SIGNATURE_SHA256_PREFIX
    if not header.startswith(prefix):
        raise MalformedWebhookSignatureError("signature must use sha256 algorithm")
    digest_hex = header[len(prefix) :]
    if len(digest_hex) != 64:
        raise MalformedWebhookSignatureError("signature digest must be 64 hex characters")
    try:
        provided = bytes.fromhex(digest_hex)
    except ValueError as exc:
        raise MalformedWebhookSignatureError("signature digest is not valid hex") from exc
    if len(provided) != 32:
        raise MalformedWebhookSignatureError("signature digest must be 32 bytes")
    expected = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).digest()
    if not hmac.compare_digest(expected, provided):
        raise InvalidWebhookSignatureError("signature mismatch")
