"""Low-level HTTP transport for GitHub APIs."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from urllib.parse import urljoin

import httpx

from ghappkit_client.errors import GitHubApiError, redact_secrets
from ghappkit_client.models import GitHubResponse


def join_api_url(base: str, path: str) -> str:
    """Join GitHub API base URL with a path starting with '/'."""
    if not path.startswith("/"):
        path = "/" + path
    return urljoin(base.rstrip("/") + "/", path.lstrip("/"))


async def send_request(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    *,
    headers: Mapping[str, str] | None = None,
    params: Mapping[str, Any] | None = None,
    json: Any | None = None,
    content: bytes | None = None,
) -> GitHubResponse:
    """Send an HTTP request and normalize the response."""
    try:
        response = await client.request(
            method.upper(),
            url,
            headers=dict(headers) if headers else None,
            params=dict(params) if params else None,
            json=json,
            content=content,
        )
    except httpx.HTTPError as exc:
        raise GitHubApiError(redact_secrets(str(exc))) from exc

    text = response.text
    json_data: Any | None
    try:
        json_data = response.json()
    except ValueError:
        json_data = None

    hdrs = dict(response.headers.items())
    return GitHubResponse(
        status_code=response.status_code,
        headers=hdrs,
        json_data=json_data,
        text=text,
    )


def raise_for_github_status(resp: GitHubResponse, *, operation: str) -> None:
    """Raise GitHubApiError when response is not OK."""
    if resp.ok:
        return
    req_id = resp.headers.get("X-GitHub-Request-Id") or resp.headers.get("x-github-request-id")
    detail = resp.json_data if isinstance(resp.json_data, dict) else resp.text[:500]
    msg = f"{operation} failed ({resp.status_code}): {detail!s}"
    raise GitHubApiError(
        redact_secrets(msg),
        status_code=resp.status_code,
        request_id=req_id,
    )
