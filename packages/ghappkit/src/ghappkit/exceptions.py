"""Framework-specific errors (client base: :class:`ghappkit_client.errors.GhappkitError`)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Literal

from ghappkit_client.errors import GhappkitError

PayloadParseFailureKind = Literal["utf8", "json", "not_object"]


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
    """Webhook body could not be decoded or parsed as a JSON object."""

    def __init__(
        self,
        message: str,
        *,
        kind: PayloadParseFailureKind = "json",
    ) -> None:
        super().__init__(message)
        self.kind: PayloadParseFailureKind = kind


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
    """Error details passed to ``@github.on_error`` hooks.

    ``exc`` is normally a :class:`HandlerExecutionError` wrapping the user handler's
    failure. Inspect ``exc.__cause__`` for the original exception raised by the handler
    when present.
    """

    exc: BaseException
    context: Any
    handler: Callable[..., Any]
    qualified_event: str
