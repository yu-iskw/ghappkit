"""Tests for handler registry routing."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any, cast

import pytest

from ghappkit.routing import EventRegistry


async def _h1(_ctx: Any) -> None:
    return None


async def _h2(_ctx: Any) -> None:
    return None


def test_rejects_sync_handler() -> None:
    reg = EventRegistry()

    def sync_handler(_ctx: Any) -> None:
        return None

    with pytest.raises(TypeError, match="async"):
        reg.add("push", cast("Callable[..., Awaitable[Any]]", sync_handler))


def test_handlers_for_qualified_only() -> None:
    reg = EventRegistry()
    reg.add("issues.opened", _h1)
    assert reg.handlers_for("issues.opened") == [_h1]


def test_base_event_registration_does_not_match_qualified_action() -> None:
    reg = EventRegistry()
    reg.add("issues.opened", _h1)
    reg.add("issues", _h2)
    assert reg.handlers_for("issues.opened") == [_h1]


def test_handlers_for_legacy_base_event_after_qualified() -> None:
    reg = EventRegistry()
    reg.add("issues.opened", _h1)
    reg.add("issues", _h2)
    assert reg.handlers_for("issues.opened", base_event="issues") == [_h1, _h2]


def test_no_duplicate_when_qualified_equals_base() -> None:
    reg = EventRegistry()
    reg.add("push", _h1)
    assert reg.handlers_for("push") == [_h1]


def test_catch_all_appended() -> None:
    reg = EventRegistry()
    reg.add("ping", _h1)
    reg.add_any(_h2)
    assert reg.handlers_for("ping") == [_h1, _h2]


def test_registration_order_preserved() -> None:
    reg = EventRegistry()

    async def a(_: Any) -> None:
        return None

    async def b(_: Any) -> None:
        return None

    reg.add("issues.opened", a)
    reg.add("issues.opened", b)
    assert reg.handlers_for("issues.opened") == [a, b]


def test_on_registers_multiple_event_strings() -> None:
    reg = EventRegistry()

    async def multi(_: Any) -> None:
        return None

    reg.add(["issues.opened", "issues.closed"], multi)
    assert reg.handlers_for("issues.opened") == [multi]
    assert reg.handlers_for("issues.closed") == [multi]
    assert reg.handlers_for("issues.edited") == []
