"""Execution strategies for webhook handlers."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Protocol

from fastapi import BackgroundTasks


class DeliveryExecutor(Protocol):
    """Schedules webhook handler work."""

    async def enqueue(self, task: Callable[[], Awaitable[None]]) -> None:
        """Run or schedule handler execution."""


class InlineExecutor:
    """Await handlers in-process (tests and debugging)."""

    async def enqueue(self, task: Callable[[], Awaitable[None]]) -> None:
        await task()


class NoopExecutor:
    """Accept deliveries without invoking handlers."""

    async def enqueue(self, task: Callable[[], Awaitable[None]]) -> None:  # noqa: ARG002
        return


class FastAPIBackgroundExecutor:
    """Schedule work using FastAPI background tasks."""

    def __init__(self, tasks: BackgroundTasks) -> None:
        self._tasks = tasks

    async def enqueue(self, task: Callable[[], Awaitable[None]]) -> None:
        async def runner() -> None:
            await task()

        self._tasks.add_task(runner)
