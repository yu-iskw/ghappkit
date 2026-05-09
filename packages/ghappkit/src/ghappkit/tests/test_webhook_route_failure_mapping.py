"""Contract tests for :func:`ghappkit.app._raise_http_for_webhook_route_failure`."""

from __future__ import annotations

import json
from typing import Any

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from ghappkit_client.errors import GitHubApiError, InstallationAuthError
from ghappkit_testing.fake_client import FakeGitHubClient
from ghappkit_testing.fixtures import issues_opened
from ghappkit_testing.signatures import sign_sha256_payload
from ghappkit_testing.test_settings import make_test_settings
from starlette import status

from ghappkit.app import GitHubApp, _raise_http_for_webhook_route_failure
from ghappkit.exceptions import (
    ErrorHookExecutionError,
    EventModelError,
    HandlerExecutionError,
    MissingWebhookSignatureError,
    PayloadParseError,
    RepoConfigError,
    WebhookHeaderError,
)
from ghappkit.execution import InlineExecutor


@pytest.mark.parametrize(
    ("exc", "expected_status", "expected_detail"),
    [
        (MissingWebhookSignatureError("missing"), 401, "invalid_webhook_signature"),
        (WebhookHeaderError("missing event"), 400, "missing event"),
        (PayloadParseError("bad json"), 400, "bad json"),
        (HandlerExecutionError("wrapped"), 500, "webhook_handler_failed"),
        (ErrorHookExecutionError("hook"), 500, "webhook_error_hook_failed"),
        (EventModelError("model"), 500, "webhook_event_model_invalid"),
        (GitHubApiError("api", status_code=None), 500, "webhook_github_api_error"),
        (InstallationAuthError("auth"), 500, "webhook_installation_auth_error"),
        (RepoConfigError("repo"), 500, "webhook_repo_config_error"),
        (ValueError("surprise"), 500, "webhook delivery failed (ValueError)"),
    ],
)
def test_raise_http_maps_delivery_exceptions(
    exc: Exception,
    expected_status: int,
    expected_detail: str,
) -> None:
    with pytest.raises(HTTPException) as ctx:
        _raise_http_for_webhook_route_failure(exc)
    assert ctx.value.status_code == expected_status
    assert ctx.value.detail == expected_detail


def test_router_github_api_error_detail_without_client_factory() -> None:
    """Missing app credentials with installation in payload maps to ``webhook_github_api_error``."""
    settings = make_test_settings(require_signature=True)
    github = GitHubApp(
        settings=settings,
        executor=InlineExecutor(),
        use_background_tasks=False,
    )

    @github.on("issues.opened")
    async def _h(_ctx: Any) -> None:
        return None

    api = FastAPI()
    api.include_router(github.router(), prefix="/api")
    client = TestClient(api)
    body = json.dumps(issues_opened()).encode("utf-8")
    secret = settings.webhook_secret.get_secret_value()
    sig = sign_sha256_payload(secret, body)
    resp = client.post(
        "/api/webhooks",
        content=body,
        headers={
            "X-GitHub-Event": "issues",
            "X-GitHub-Delivery": "d-gh-api",
            "X-Hub-Signature-256": sig,
        },
    )
    assert resp.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert resp.json()["detail"] == "webhook_github_api_error"


def test_router_event_model_invalid_detail() -> None:
    """Invalid typed ``issues.opened`` payload maps to ``webhook_event_model_invalid``."""
    settings = make_test_settings(require_signature=True)

    async def factory(_installation_id: int | None) -> FakeGitHubClient:
        return FakeGitHubClient()

    github = GitHubApp(
        settings=settings,
        executor=InlineExecutor(),
        use_background_tasks=False,
        github_client_factory=factory,
    )

    @github.on("issues.opened")
    async def _h(_ctx: Any) -> None:
        return None

    bad = issues_opened()
    bad["issue"] = "not-a-valid-issue-object"
    body = json.dumps(bad).encode("utf-8")
    secret = settings.webhook_secret.get_secret_value()
    sig = sign_sha256_payload(secret, body)

    api = FastAPI()
    api.include_router(github.router(), prefix="/api")
    client = TestClient(api)
    resp = client.post(
        "/api/webhooks",
        content=body,
        headers={
            "X-GitHub-Event": "issues",
            "X-GitHub-Delivery": "d-model",
            "X-Hub-Signature-256": sig,
        },
    )
    assert resp.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert resp.json()["detail"] == "webhook_event_model_invalid"
