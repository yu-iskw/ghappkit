"""GitHub GraphQL client behavior."""

from __future__ import annotations

import asyncio

import httpx
import pytest

from ghappkit_client.graphql import GitHubGraphQLClient


def test_graphql_execute_returns_data_subset() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert "/graphql" in str(request.url)
        return httpx.Response(200, json={"data": {"viewer": {"login": "pat"}}})

    async def run() -> None:
        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            gql = GitHubGraphQLClient(
                http_client=client,
                api_base_url="https://api.github.com",
                auth_header="Bearer tok",
            )
            result = await gql.execute("{ viewer { login } }")
            assert result == {"viewer": {"login": "pat"}}

    asyncio.run(run())


def test_graphql_execute_posts_to_ghes_graphql_endpoint() -> None:
    """GHES REST base is /api/v3; GraphQL must be /api/graphql (not /api/v3/graphql)."""

    seen: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        return httpx.Response(200, json={"data": {"viewer": {"login": "pat"}}})

    async def run() -> None:
        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            gql = GitHubGraphQLClient(
                http_client=client,
                api_base_url="https://github.enterprise.example/api/v3",
                auth_header="Bearer tok",
            )
            await gql.execute("{ viewer { login } }")

    asyncio.run(run())
    assert seen["url"] == "https://github.enterprise.example/api/graphql"


def test_graphql_execute_raises_on_graphql_errors() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"errors": [{"message": "Something went wrong"}], "data": None},
        )

    async def run() -> None:
        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            gql = GitHubGraphQLClient(
                http_client=client,
                api_base_url="https://api.github.com",
                auth_header="Bearer tok",
            )
            with pytest.raises(ValueError, match=r"(?i)graphql errors"):
                await gql.execute("{ dummy }")

    asyncio.run(run())
