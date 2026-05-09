"""Event registry for webhook dispatch."""

from __future__ import annotations

import inspect
from collections import defaultdict
from collections.abc import Awaitable, Callable, Iterable, Sequence
from typing import Any

from ghappkit.exceptions import HandlerError

Handler = Callable[..., Awaitable[Any]]
ErrorHook = Callable[[HandlerError], Awaitable[None]]


def _require_async_callable(handler: Callable[..., Any], *, message: str) -> None:
    if not inspect.iscoroutinefunction(handler):
        raise TypeError(message)


class EventRegistry:
    """Maps qualified GitHub events to handlers."""

    def __init__(self) -> None:
        self._specific: dict[str, list[Handler]] = defaultdict(list)
        self._catch_all: list[Handler] = []
        self._error_hooks: list[ErrorHook] = []

    def add(self, names: str | Sequence[str], handler: Handler) -> None:
        """Register handler for one or more qualified names."""
        _require_async_callable(
            handler,
            message="webhook handlers must be async functions (def handler(ctx): ...)",
        )
        seq = [names] if isinstance(names, str) else list(names)
        for name in seq:
            self._specific[name].append(handler)

    def add_any(self, handler: Handler) -> None:
        """Register catch-all handler."""
        _require_async_callable(
            handler,
            message="webhook handlers must be async functions (def handler(ctx): ...)",
        )
        self._catch_all.append(handler)

    def add_error(self, handler: ErrorHook) -> None:
        """Register error hook."""
        _require_async_callable(
            handler,
            message="error hooks must be async functions (def hook(error): ...)",
        )
        self._error_hooks.append(handler)

    def handlers_for(self, qualified_event: str) -> list[Handler]:
        """Return handlers in deterministic registration order.

        P0 matching is limited to:
        1. Handlers registered for the qualified name (``event`` or ``event.action``).
        2. Catch-all handlers registered via :meth:`add_any`.

        Base-event-only registrations (for example ``issues``) do **not** run for
        qualified deliveries such as ``issues.opened``.
        """
        ordered: list[Handler] = []
        ordered.extend(self._specific.get(qualified_event, []))
        ordered.extend(self._catch_all)
        return ordered

    def error_handlers(self) -> Iterable[ErrorHook]:
        """Registered error hooks."""
        return list(self._error_hooks)
