"""Qualified GitHub webhook event names from headers and payload."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def qualified_event_name(event: str, payload: Mapping[str, Any]) -> str:
    """Compute ghappkit qualified event name (``event`` or ``event.action``)."""
    action = payload.get("action")
    if isinstance(action, str) and action:
        return f"{event}.{action}"
    return event


def split_qualified_event(name: str) -> tuple[str, str | None]:
    """Inverse of :func:`qualified_event_name` for tests and simulators.

    ``issues.opened`` → ``("issues", "opened")``; ``push`` → ``("push", None)``.
    """
    if "." not in name:
        return name, None
    event, remainder = name.split(".", 1)
    return event, remainder
