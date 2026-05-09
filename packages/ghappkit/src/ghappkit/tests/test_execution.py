"""Tests for delivery executor behavior."""

from __future__ import annotations

import asyncio

import pytest

from ghappkit.execution import InlineExecutor


def test_inline_executor_runs_task_inline() -> None:
    ex = InlineExecutor()
    seen: list[str] = []

    async def task() -> None:
        seen.append("done")

    asyncio.run(ex.enqueue(task))
    assert seen == ["done"]


def test_inline_executor_propagates_exceptions() -> None:
    ex = InlineExecutor()

    async def boom() -> None:
        msg = "boom"
        raise RuntimeError(msg)

    with pytest.raises(RuntimeError, match="boom"):
        asyncio.run(ex.enqueue(boom))
