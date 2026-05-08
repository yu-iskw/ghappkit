"""Cursor-based REST pagination using Link headers."""

from __future__ import annotations

import re
from collections.abc import AsyncIterator, Mapping
from typing import Any

import httpx

from ghappkit_client.transport import join_api_url, raise_for_github_status, send_request

_REL_NEXT = re.compile(r'<([^>]+)>;\s*rel="next"', re.IGNORECASE)


async def iter_rest_pages(
    client: httpx.AsyncClient,
    base_url: str,
    path: str,
    *,
    headers: Mapping[str, str],
    params: Mapping[str, Any] | None = None,
) -> AsyncIterator[list[Any]]:
    """Yield each page of a GitHub REST collection as a JSON array."""
    url = join_api_url(base_url, path)
    query_params = dict(params) if params else None
    while True:
        resp = await send_request(
            client,
            "GET",
            url,
            headers=headers,
            params=query_params,
        )
        raise_for_github_status(resp, operation="paginated GET")
        if not isinstance(resp.json_data, list):
            raise ValueError("pagination expected a JSON array response")
        yield resp.json_data
        next_url = _parse_next_link(resp.headers)
        if not next_url:
            break
        url = next_url
        query_params = None


def _parse_next_link(headers: Mapping[str, str]) -> str | None:
    link = headers.get("Link") or headers.get("link")
    if not link:
        return None
    match = _REL_NEXT.search(link)
    if not match:
        return None
    return match.group(1)
