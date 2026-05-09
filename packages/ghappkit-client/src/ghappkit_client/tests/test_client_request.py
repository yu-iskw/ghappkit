"""Tests for DefaultGitHubClient.request header merging."""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

import pytest

import ghappkit_client.client as client_mod
from ghappkit_client.client import DefaultGitHubClient
from ghappkit_client.models import GitHubResponse


def test_request_overrides_caller_authorization_with_installation_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, dict[str, str]] = {}

    async def fake_send(
        client: object,
        method: str,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        params: object = None,
        json: object = None,
        content: object = None,
    ) -> GitHubResponse:
        del client, params, json, content
        captured["headers"] = dict(headers or {})
        return GitHubResponse(status_code=200, headers={}, json_data={}, text="{}")

    monkeypatch.setattr(client_mod, "send_request", fake_send)

    gh = DefaultGitHubClient(
        http_client=MagicMock(),
        api_base_url="https://api.github.com",
        token="installation-token",  # noqa: S106
    )

    async def run() -> None:
        await gh.request(
            "GET",
            "/repos/o/r",
            headers={"Authorization": "Bearer attacker-supplied", "X-Custom": "1"},
        )

    asyncio.run(run())

    assert captured["headers"]["Authorization"] == "Bearer installation-token"
    assert captured["headers"]["Accept"] == "application/vnd.github+json"
    assert captured["headers"]["X-Custom"] == "1"
