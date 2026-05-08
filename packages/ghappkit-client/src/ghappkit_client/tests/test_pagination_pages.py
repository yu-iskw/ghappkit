"""REST pagination across Link headers."""

from __future__ import annotations

import asyncio

import httpx

from ghappkit_client.pagination import iter_rest_pages


def test_iter_rest_pages_follows_next_link() -> None:
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        url = str(request.url)
        if "page=2" in url:
            return httpx.Response(200, json=[{"id": 3}])
        return httpx.Response(
            200,
            json=[{"id": 1}, {"id": 2}],
            headers={
                "Link": '<https://api.github.com/repos/acme/demo/issues?page=2>; rel="next"',
            },
        )

    async def run() -> None:
        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            pages = [
                page
                async for page in iter_rest_pages(
                    client,
                    "https://api.github.com",
                    "/repos/acme/demo/issues",
                    headers={"Authorization": "Bearer t"},
                )
            ]
            assert pages == [[{"id": 1}, {"id": 2}], [{"id": 3}]]
            assert calls["n"] == 2

    asyncio.run(run())
