"""Event registry for webhook dispatch."""

from __future__ import annotations

import inspect
from collections import defaultdict
from collections.abc import Awaitable, Callable, Iterable, Sequence
from typing import Any

from ghappkit.exceptions import HandlerError

Handler = Callable[..., Awaitable[Any]]
ErrorHook = Callable[[HandlerError], Awaitable[None]]


class EventRegistry:
    """Maps qualified GitHub events to handlers."""

    def __init__(self) -> None:
        self._specific: dict[str, list[Handler]] = defaultdict(list)
        self._catch_all: list[Handler] = []
        self._error_hooks: list[ErrorHook] = []

    def add(self, names: str | Sequence[str], handler: Handler) -> None:
        """Register handler for one or more qualified names."""
        if not inspect.iscoroutinefunction(handler):
            msg = "webhook handlers must be async functions (def handler(ctx): ...)"
            raise TypeError(msg)
        seq = [names] if isinstance(names, str) else list(names)
        for name in seq:
            self._specific[name].append(handler)

    def add_any(self, handler: Handler) -> None:
        """Register catch-all handler."""
        if not inspect.iscoroutinefunction(handler):
            msg = "webhook handlers must be async functions (def handler(ctx): ...)"
            raise TypeError(msg)
        self._catch_all.append(handler)

    def add_error(self, handler: ErrorHook) -> None:
        """Register error hook."""
        if not inspect.iscoroutinefunction(handler):
            msg = "error hooks must be async functions (def hook(error): ...)"
            raise TypeError(msg)
        self._error_hooks.append(handler)

    def handlers_for(self, qualified_event: str, base_event: str) -> list[Handler]:
        """Return handlers in deterministic registration order.

        Order: handlers for the qualified name, then handlers registered only for
        the base ``X-GitHub-Event`` value (when it differs from the qualified name),
        then catch-all handlers.
        """
        ordered: list[Handler] = []
        ordered.extend(self._specific.get(qualified_event, []))
        if base_event != qualified_event:
            ordered.extend(self._specific.get(base_event, []))
        ordered.extend(self._catch_all)
        return ordered

    def error_handlers(self) -> Iterable[ErrorHook]:
        """Registered error hooks."""
        return list(self._error_hooks)
