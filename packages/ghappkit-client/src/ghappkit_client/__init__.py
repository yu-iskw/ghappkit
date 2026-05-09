"""GitHub API client package for ghappkit."""

from ghappkit_client.auth import create_app_jwt, load_private_key_pem
from ghappkit_client.client import DefaultGitHubClient, GitHubClient
from ghappkit_client.errors import (
    GhappkitError,
    GitHubApiError,
    InstallationAuthError,
    RepositoryFileDecodeError,
    redact_secrets,
)
from ghappkit_client.graphql import GitHubGraphQLClient
from ghappkit_client.models import GitHubResponse, InstallationToken
from ghappkit_client.pagination import iter_rest_pages
from ghappkit_client.rate_limit import RateLimitInfo, parse_rate_limit
from ghappkit_client.rest import GitHubRestClient
from ghappkit_client.token_provider import InstallationTokenProvider
from ghappkit_client.transport import graphql_api_url, join_api_url, send_request

__all__ = [
    "DefaultGitHubClient",
    "GhappkitError",
    "GitHubApiError",
    "GitHubClient",
    "GitHubGraphQLClient",
    "GitHubResponse",
    "GitHubRestClient",
    "InstallationAuthError",
    "InstallationToken",
    "InstallationTokenProvider",
    "RateLimitInfo",
    "RepositoryFileDecodeError",
    "create_app_jwt",
    "graphql_api_url",
    "iter_rest_pages",
    "join_api_url",
    "load_private_key_pem",
    "parse_rate_limit",
    "redact_secrets",
    "send_request",
]
