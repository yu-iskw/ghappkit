"""Ordered webhook request lifecycle (signature before header validation)."""

from __future__ import annotations

from collections.abc import Mapping

from ghappkit.headers import (
    GitHubDeliveryHeaders,
    normalize_http_headers,
    parse_github_delivery_headers_normalized,
)
from ghappkit.security import verify_github_signature


def parse_delivery_after_optional_signature(
    *,
    raw_body: bytes,
    header_map: Mapping[str, str],
    webhook_secret: str,
    require_signature: bool,
) -> GitHubDeliveryHeaders:
    """Verify HMAC on raw bytes first, then parse required GitHub headers.

    Invalid signatures must be detected before JSON parsing or handler dispatch.
    Header names are normalized once for both signature lookup and structured parsing.
    """
    lowered = normalize_http_headers(header_map)
    if require_signature:
        verify_github_signature(
            secret=webhook_secret,
            body=raw_body,
            signature_header=lowered.get("x-hub-signature-256"),
        )
    return parse_github_delivery_headers_normalized(lowered)
