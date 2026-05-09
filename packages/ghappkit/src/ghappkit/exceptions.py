"""Framework-specific errors (client base: :class:`ghappkit_client.errors.GhappkitError`)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from ghappkit_client.errors import GhappkitError


class WebhookSignatureError(GhappkitError):
    """Invalid or missing GitHub webhook signature."""


class MissingWebhookSignatureError(WebhookSignatureError):
    """``X-Hub-Signature-256`` header absent or empty."""


class MalformedWebhookSignatureError(WebhookSignatureError):
    """Signature header is not ``sha256=<hex>`` with a 32-byte digest."""


class InvalidWebhookSignatureError(WebhookSignatureError):
    """HMAC digest comparison failed."""


class WebhookHeaderError(GhappkitError):
    """Malformed or incomplete GitHub webhook headers."""


class PayloadParseError(GhappkitError):
    """Payload is not valid JSON."""


class EventModelError(GhappkitError):
    """Typed event model validation failed."""


class RepoConfigError(GhappkitError):
    """Repository configuration could not be loaded or validated."""


class HandlerExecutionError(GhappkitError):
    """User handler raised an exception (after wrapping).

    This type must remain a direct subclass of :class:`GhappkitError` (not of
    :class:`WebhookSignatureError` or other webhook transport errors) so
    :meth:`GitHubApp.router` can map it to HTTP 500 before broader ``Exception``
    handlers.
    """


class ErrorHookExecutionError(GhappkitError):
    """A registered ``@github.on_error`` hook raised an exception."""
@dataclass(frozen=True)
class HandlerError:
    """Error details passed to ``@github.on_error`` hooks."""

    exc: BaseException
    context: Any
    handler: Callable[..., Any]
    qualified_event: str
