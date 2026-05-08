"""FastAPI-native GitHub App framework."""

from ghappkit_client.errors import GhappkitError

from ghappkit.app import GitHubApp
from ghappkit.context import RepositoryRef, SenderRef, WebhookContext
from ghappkit.exceptions import (
    EventModelError,
    HandlerError,
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
from ghappkit.settings import GitHubAppSettings

# RFC-compatible aliases (prefer Ghappkit* names for new code).
OctoflowError = GhappkitError

__all__ = [
    "DeliveryExecutor",
    "EventModelError",
    "FastAPIBackgroundExecutor",
    "GhappkitError",
    "GitHubApp",
    "GitHubAppSettings",
    "HandlerError",
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
