"""Event registry for webhook dispatch."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Awaitable, Callable, Iterable, Sequence
from typing import Any

Handler = Callable[..., Awaitable[Any]]


class EventRegistry:
    """Maps qualified GitHub events to handlers."""

    def __init__(self) -> None:
        self._specific: dict[str, list[Handler]] = defaultdict(list)
        self._catch_all: list[Handler] = []
        self._error_hooks: list[Handler] = []

    def add(self, names: str | Sequence[str], handler: Handler) -> None:
        """Register handler for one or more qualified names."""
        seq = [names] if isinstance(names, str) else list(names)
        for name in seq:
            self._specific[name].append(handler)

    def add_any(self, handler: Handler) -> None:
        """Register catch-all handler."""
        self._catch_all.append(handler)

    def add_error(self, handler: Handler) -> None:
        """Register error hook."""
        self._error_hooks.append(handler)

    def handlers_for(self, qualified_event: str) -> list[Handler]:
        """Return handlers in deterministic registration order."""
        return list(self._specific.get(qualified_event, [])) + list(self._catch_all)

    def error_handlers(self) -> Iterable[Handler]:
        """Registered error hooks."""
        return list(self._error_hooks)
