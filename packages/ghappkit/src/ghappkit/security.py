"""Webhook signature verification."""

from __future__ import annotations

import hashlib
import hmac

from ghappkit.exceptions import WebhookSignatureError


def verify_github_signature(
    *,
    secret: str,
    body: bytes,
    signature_header: str | None,
) -> None:
    """Verify ``X-Hub-Signature-256`` using the webhook secret.

    Raises:
        WebhookSignatureError: secret comparisons failures never echo secrets.
    """
    if not signature_header:
        raise WebhookSignatureError("missing X-Hub-Signature-256 header")
    header = signature_header.strip()
    prefix = "sha256="
    if not header.startswith(prefix):
        raise WebhookSignatureError("signature must use sha256 algorithm")
    digest_hex = header[len(prefix) :]
    expected = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, digest_hex):
        raise WebhookSignatureError("signature mismatch")
