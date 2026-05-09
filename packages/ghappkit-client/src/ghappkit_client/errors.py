"""Error types shared across ghappkit packages."""

from __future__ import annotations

import re


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


class RepositoryFileDecodeError(GhappkitError):
    """Contents API returned a file payload that could not be decoded safely."""


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
        redacted = pattern.sub("[REDACTED]", redacted)
    return redacted
