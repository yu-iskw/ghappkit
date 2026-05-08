"""GitHub client protocol and default httpx-backed implementation."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol, runtime_checkable

import httpx

from ghappkit_client.graphql import GitHubGraphQLClient
from ghappkit_client.models import GitHubResponse
from ghappkit_client.rest import GitHubRestClient
from ghappkit_client.transport import join_api_url, raise_for_github_status, send_request


@runtime_checkable
class GitHubClient(Protocol):
    """Framework-facing GitHub client protocol."""

    rest: Any
    graphql: Any

    async def request(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, Any] | None = None,
        json: Any | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> GitHubResponse:
        """Perform a REST request relative to the GitHub API base URL."""
        raise NotImplementedError


class DefaultGitHubClient:
    """Installation-scoped REST/GraphQL client."""

    def __init__(
        self,
        *,
        http_client: httpx.AsyncClient,
        api_base_url: str,
        token: str,
    ) -> None:
        auth = f"Bearer {token}"
        self._http = http_client
        self._api_base = api_base_url.rstrip("/")
        self._auth_header = auth
        self.rest = GitHubRestClient(
            http_client=http_client,
            api_base_url=api_base_url,
            auth_header=auth,
        )
        self.graphql = GitHubGraphQLClient(
            http_client=http_client,
            api_base_url=api_base_url,
            auth_header=auth,
        )

    async def request(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, Any] | None = None,
        json: Any | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> GitHubResponse:
        """HTTP request with Bearer installation token."""
        url = join_api_url(self._api_base, path)
        merged_headers: dict[str, str] = {
            "Authorization": self._auth_header,
            "Accept": "application/vnd.github+json",
        }
        if headers:
            merged_headers.update(headers)
        resp = await send_request(
            self._http,
            method,
            url,
            headers=merged_headers,
            params=params,
            json=json,
        )
        raise_for_github_status(resp, operation=f"{method} {path}")
        return resp
