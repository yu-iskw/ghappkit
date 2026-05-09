"""Contract tests for GitHub webhook HTTP ``detail`` mapping.

Uses :func:`ghappkit.app._raise_http_for_webhook_route_failure` (the implementation
behind :meth:`ghappkit.app.GitHubApp.router`) so stable ``detail`` strings are checked
without a full HTTP stack for every case. Mapped 500 pairs stay aligned with
``_WEBHOOK_MAPPED_INTERNAL_ERRORS`` in ``ghappkit.app``.
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from ghappkit_client.errors import GitHubApiError
from ghappkit_testing.fake_client import FakeGitHubClient
from ghappkit_testing.fixtures import issues_opened
from ghappkit_testing.signatures import sign_sha256_payload
from ghappkit_testing.test_settings import make_test_settings
from starlette import status

from ghappkit.app import (
    _WEBHOOK_MAPPED_INTERNAL_ERRORS,
    GitHubApp,
    _raise_http_for_webhook_route_failure,
)
from ghappkit.exceptions import (
    MissingWebhookSignatureError,
    PayloadParseError,
    WebhookHeaderError,
)
from ghappkit.execution import InlineExecutor


def _make_mapped_internal_instance(exc_cls: type[BaseException]) -> BaseException:
    if exc_cls is GitHubApiError:
        return GitHubApiError("probe", status_code=None)
    return exc_cls("probe")


@pytest.mark.parametrize(
    ("exc", "expected_status", "expected_detail"),
    [
        (MissingWebhookSignatureError("missing"), 401, "invalid_webhook_signature"),
        (WebhookHeaderError("missing event"), 400, "missing event"),
        (PayloadParseError("bad json"), 400, "bad json"),
        *[
            (_make_mapped_internal_instance(cls), 500, detail)
            for cls, detail in _WEBHOOK_MAPPED_INTERNAL_ERRORS
        ],
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
