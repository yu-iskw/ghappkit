"""GraphQL client helper."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import httpx

from ghappkit_client.transport import graphql_api_url, raise_for_github_status, send_request


class GitHubGraphQLClient:
    """Minimal GraphQL caller."""

    def __init__(
        self,
        *,
        http_client: httpx.AsyncClient,
        api_base_url: str,
        auth_header: str,
    ) -> None:
        self._http = http_client
        self._api_base = api_base_url.rstrip("/")
        self._auth_header = auth_header

    async def execute(
        self,
        query: str,
        *,
        variables: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute a GraphQL query."""
        url = graphql_api_url(self._api_base)
        headers = {
            "Authorization": self._auth_header,
            "Accept": "application/vnd.github+json",
        }
        body: dict[str, Any] = {"query": query}
        if variables is not None:
            body["variables"] = dict(variables)
        resp = await send_request(self._http, "POST", url, headers=headers, json=body)
        raise_for_github_status(resp, operation="graphql")
        data = resp.json_data
        if not isinstance(data, dict):
            raise ValueError("graphql response must be a JSON object")
        errs = data.get("errors")
        if errs:
            raise ValueError(f"graphql errors: {errs!r}")
        inner = data.get("data")
        if not isinstance(inner, dict):
            raise ValueError("graphql data missing")
        return inner
