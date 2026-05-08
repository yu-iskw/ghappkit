"""Lifecycle behavior for :class:`GitHubApp`."""

from __future__ import annotations

import asyncio

import httpx
from ghappkit_testing.test_settings import make_test_settings

from ghappkit.app import GitHubApp


def test_aclose_closes_owned_http_client() -> None:
    settings = make_test_settings()
    gh = GitHubApp(settings=settings)
    assert gh._owns_http_client is True

    async def shutdown() -> None:
        await gh.aclose()
        assert gh._http_client.is_closed

    asyncio.run(shutdown())


def test_aclose_does_not_close_injected_http_client() -> None:
    settings = make_test_settings()

    def noop_handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200)

    client = httpx.AsyncClient(transport=httpx.MockTransport(noop_handler))
    gh = GitHubApp(settings=settings, http_client=client)
    assert gh._owns_http_client is False

    async def shutdown() -> None:
        await gh.aclose()
        assert not client.is_closed

    asyncio.run(shutdown())
    asyncio.run(client.aclose())
