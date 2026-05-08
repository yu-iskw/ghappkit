"""Parse GitHub webhook headers and payloads."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from ghappkit.exceptions import PayloadParseError, WebhookHeaderError


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
    lowered = {k.lower(): v for k, v in headers.items()}
    event = lowered.get("x-github-event")
    delivery_id = lowered.get("x-github-delivery")
    if not event:
        raise WebhookHeaderError("missing X-GitHub-Event header")
    if not delivery_id:
        raise WebhookHeaderError("missing X-GitHub-Delivery header")
    return GitHubDeliveryHeaders(
        event=event,
        delivery_id=delivery_id,
        signature_256=lowered.get("x-hub-signature-256"),
        hook_id=lowered.get("x-github-hook-id"),
        user_agent=lowered.get("user-agent"),
    )


def parse_json_payload(body: bytes) -> dict[str, Any]:
    """Parse JSON object payloads."""
    try:
        text = body.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise PayloadParseError("payload must be utf-8") from exc
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise PayloadParseError("payload is not valid JSON") from exc
    if not isinstance(data, dict):
        raise PayloadParseError("payload JSON must be an object")
    return data


def qualified_event_name(event: str, payload: Mapping[str, Any]) -> str:
    """Compute ghappkit qualified event name."""
    action = payload.get("action")
    if isinstance(action, str) and action:
        return f"{event}.{action}"
    return event
