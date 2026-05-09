"""Tests for qualified event name resolution."""

from __future__ import annotations

from ghappkit.event_resolution import qualified_event_name, split_qualified_event


def test_qualified_event_with_action() -> None:
    assert qualified_event_name("issues", {"action": "opened"}) == "issues.opened"


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
