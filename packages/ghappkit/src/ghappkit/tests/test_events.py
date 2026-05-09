"""Tests for qualified event name resolution."""

from __future__ import annotations

from ghappkit.event_resolution import (
    qualified_event_name,
    resolve_qualified_webhook_event,
    split_qualified_event,
)


def test_resolve_qualified_webhook_event_matches_qualified_event_name() -> None:
    payload = {"action": "opened"}
    q1, action = resolve_qualified_webhook_event("issues", payload)
    assert action == "opened"
    assert q1 == qualified_event_name("issues", payload)

    q2, none_action = resolve_qualified_webhook_event("push", {})
    assert none_action is None
    assert q2 == "push"


def test_qualified_event_action_is_stripped() -> None:
    assert qualified_event_name("issues", {"action": "  opened  "}) == "issues.opened"


def test_qualified_event_without_action() -> None:
    assert qualified_event_name("push", {}) == "push"


def test_action_non_string_ignored() -> None:
    assert qualified_event_name("workflow_run", {"action": 1}) == "workflow_run"


def test_action_empty_string_ignored() -> None:
    assert qualified_event_name("issues", {"action": ""}) == "issues"


def test_action_whitespace_only_ignored() -> None:
    assert qualified_event_name("issues", {"action": "   "}) == "issues"


def test_split_qualified_event() -> None:
    assert split_qualified_event("issues.opened") == ("issues", "opened")
    assert split_qualified_event("push") == ("push", None)
