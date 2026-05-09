"""Qualified GitHub webhook event names from headers and payload.

Architecture docs refer to this as ``events.py``; this repository already ships a
``ghappkit.events`` *package* for typed payload models, so a sibling ``events.py``
module would collide on import. Keep qualified-name helpers here.
"""

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
    """Split a synthetic qualified name on the first ``.`` (tests / simulators).

    GitHub sends ``X-GitHub-Event`` as the base name and ``action`` in the JSON body;
    ghappkit forms ``event`` or ``event.action``. This helper only splits the first
    segment so ``issues.opened`` → ``("issues", "opened")``; it does not interpret
    multi-dot names beyond that first split.
    """
    if "." not in name:
        return name, None
    event, remainder = name.split(".", 1)
    return event, remainder
