"""Error types shared across ghappkit packages."""

from __future__ import annotations

import re
from typing import Any


class GhappkitError(Exception):
    """Base error for ghappkit libraries."""

    def __str__(self) -> str:
        return redact_secrets(super().__str__())


class GitHubApiError(GhappkitError):
    """GitHub REST or GraphQL API returned an error response."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        request_id: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.request_id = request_id


class InstallationAuthError(GhappkitError):
    """Failed to obtain an installation access token."""


_SECRET_PATTERNS = (
    re.compile(r"(?:Authorization:\s*)(Bearer\s+)([^\s]+)", re.IGNORECASE),
    re.compile(r'("token"\s*:\s*")([^"]+)(")', re.IGNORECASE),
    re.compile(r"(gh[pousr]_[A-Za-z0-9_]+)", re.IGNORECASE),
    re.compile(r"(eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+)", re.IGNORECASE),
)


def redact_secrets(text: str) -> str:
    """Remove likely secrets from error strings and logs."""
    redacted = text
    for pattern in _SECRET_PATTERNS:
        redacted = pattern.sub(lambda m: m.group(0)[:20] + "[REDACTED]", redacted)
    return redacted


def safe_repr(value: Any, *, max_len: int = 200) -> str:
    """Short, redacted repr suitable for exceptions."""
    text = repr(value)
    if len(text) > max_len:
        text = text[:max_len] + "..."
    return redact_secrets(text)
