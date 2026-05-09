"""Ordered webhook request lifecycle (signature before header validation)."""

from __future__ import annotations

from collections.abc import Mapping

from ghappkit.headers import GitHubDeliveryHeaders, parse_github_delivery_headers
from ghappkit.security import verify_github_signature_from_headers


def parse_delivery_after_optional_signature(
    *,
    raw_body: bytes,
    header_map: Mapping[str, str],
    webhook_secret: str,
    require_signature: bool,
) -> GitHubDeliveryHeaders:
    """Verify HMAC on raw bytes first, then parse required GitHub headers.

    Invalid signatures must be detected before JSON parsing or handler dispatch.
    """
    if require_signature:
        verify_github_signature_from_headers(
            secret=webhook_secret,
            body=raw_body,
            headers=header_map,
        )
    return parse_github_delivery_headers(header_map)
