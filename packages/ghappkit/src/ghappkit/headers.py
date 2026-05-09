"""GitHub webhook HTTP header parsing."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from ghappkit.exceptions import WebhookHeaderError


def normalize_http_headers(headers: Mapping[str, str]) -> dict[str, str]:
    """Return headers with lower-cased names (HTTP field names are case-insensitive)."""
    return {k.lower(): v for k, v in headers.items()}


@dataclass(frozen=True)
class GitHubDeliveryHeaders:
    """Normalized webhook headers from GitHub."""

    event: str
    delivery_id: str
    signature_256: str | None
    hook_id: str | None
    user_agent: str | None


def parse_github_delivery_headers(headers: Mapping[str, str]) -> GitHubDeliveryHeaders:
    """Extract GitHub-specific headers (case-insensitive)."""
    lowered = normalize_http_headers(headers)
    event = lowered.get("x-github-event")
    delivery_id = lowered.get("x-github-delivery")
    if not event or not event.strip():
        raise WebhookHeaderError("missing X-GitHub-Event header")
    if not delivery_id or not delivery_id.strip():
        raise WebhookHeaderError("missing X-GitHub-Delivery header")
    event = event.strip()
    delivery_id = delivery_id.strip()
    return GitHubDeliveryHeaders(
        event=event,
        delivery_id=delivery_id,
        signature_256=lowered.get("x-hub-signature-256"),
        hook_id=lowered.get("x-github-hook-id"),
        user_agent=lowered.get("user-agent"),
    )
