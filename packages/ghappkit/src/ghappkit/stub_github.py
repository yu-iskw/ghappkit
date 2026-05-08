"""GitHub client placeholder when installation tokens are unavailable."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from ghappkit_client.errors import GitHubApiError

_MISSING_INSTALLATION_MSG = "GitHub API call attempted without installation credentials"


class _Unavailable:
    """Nested helper that raises on async calls."""

    def __getattr__(self, _name: str) -> Any:
        async def _raise(*_args: Any, **_kwargs: Any) -> Any:
            raise GitHubApiError(
                _MISSING_INSTALLATION_MSG,
                status_code=None,
            )

        return _raise


class MissingInstallationGitHubClient:
    """Minimal stub used when payloads omit installation metadata."""

    def __init__(self) -> None:
        unavailable = _Unavailable()
        self.rest = SimpleNamespace(issues=unavailable)
        self.graphql = unavailable

    async def request(self, *_args: Any, **_kwargs: Any) -> Any:
        raise GitHubApiError(
            _MISSING_INSTALLATION_MSG,
            status_code=None,
        )
