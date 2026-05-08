"""HMAC signing helpers for webhook tests."""

from __future__ import annotations

import hashlib
import hmac


def sign_sha256_payload(secret: str, body: bytes) -> str:
    """Return the ``X-Hub-Signature-256`` header value for payload bytes."""
    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"
