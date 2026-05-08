"""GraphQL endpoint URL derivation for GitHub.com vs Enterprise Server."""

from __future__ import annotations

from ghappkit_client.transport import graphql_api_url


def test_graphql_api_url_github_com() -> None:
    assert graphql_api_url("https://api.github.com") == "https://api.github.com/graphql"


def test_graphql_api_url_github_com_trailing_slash() -> None:
    assert graphql_api_url("https://api.github.com/") == "https://api.github.com/graphql"


def test_graphql_api_url_ghes_rest_v3_base() -> None:
    assert (
        graphql_api_url("https://github.myenterprise.example/api/v3")
        == "https://github.myenterprise.example/api/graphql"
    )


def test_graphql_api_url_ghes_rest_v3_base_trailing_slash() -> None:
    assert (
        graphql_api_url("https://github.myenterprise.example/api/v3/")
        == "https://github.myenterprise.example/api/graphql"
    )
