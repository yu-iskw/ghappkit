"""FastAPI-native GitHub App framework."""

from ghappkit_client.errors import GhappkitError

from ghappkit.app import GitHubApp
from ghappkit.context import RepositoryRef, SenderRef, WebhookContext
from ghappkit.exceptions import (
    EventModelError,
    HandlerError,
    HandlerExecutionError,
    PayloadParseError,
    RepoConfigError,
    WebhookHeaderError,
    WebhookSignatureError,
)
from ghappkit.execution import (
    DeliveryExecutor,
    FastAPIBackgroundExecutor,
    InlineExecutor,
    NoopExecutor,
)
from ghappkit.routing import ErrorHook
from ghappkit.settings import GitHubAppSettings

# RFC-compatible aliases (prefer Ghappkit* names for new code).
OctoflowError = GhappkitError

__all__ = [
    "DeliveryExecutor",
    "ErrorHook",
    "EventModelError",
    "FastAPIBackgroundExecutor",
    "GhappkitError",
    "GitHubApp",
    "GitHubAppSettings",
    "HandlerError",
    "HandlerExecutionError",
    "InlineExecutor",
    "NoopExecutor",
    "OctoflowError",
    "PayloadParseError",
    "RepoConfigError",
    "RepositoryRef",
    "SenderRef",
    "WebhookContext",
    "WebhookHeaderError",
    "WebhookSignatureError",
]
