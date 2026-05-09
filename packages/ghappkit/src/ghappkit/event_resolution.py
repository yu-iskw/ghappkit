"""Qualified GitHub webhook event names from headers and payload."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def github_payload_action(payload: Mapping[str, Any]) -> str | None:
    """Return ``payload['action']`` when it is a non-empty string (leading/trailing space stripped)."""
    raw = payload.get("action")
    if not isinstance(raw, str):
        return None
    stripped = raw.strip()
    return stripped or None


def qualified_event_name(event: str, payload: Mapping[str, Any]) -> str:
    """Compute ghappkit qualified event name (``event`` or ``event.action``)."""
    action = github_payload_action(payload)
    if action:
        return f"{event}.{action}"
    return event


def split_qualified_event(name: str) -> tuple[str, str | None]:
    """Split a qualified name for tests and simulators (first ``.`` only).

    ``issues.opened`` → ``("issues", "opened")``; ``push`` → ``("push", None)``.
    """
    if "." not in name:
        return name, None
    event, remainder = name.split(".", 1)
    return event, remainder
