"""HTTP mapping tests for the FastAPI router."""

from __future__ import annotations

import json
from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient
from ghappkit_testing.fake_client import FakeGitHubClient
from ghappkit_testing.fixtures import issues_opened
from ghappkit_testing.signatures import sign_sha256_payload
from ghappkit_testing.test_settings import make_test_settings
from starlette import status

from ghappkit.app import GitHubApp
from ghappkit.context import WebhookContext
from ghappkit.events import IssuesPayload
from ghappkit.execution import InlineExecutor, NoopExecutor


def _make_client(*, require_signature: bool = True) -> tuple[TestClient, GitHubApp]:
    settings = make_test_settings(require_signature=require_signature)
    github = GitHubApp(
        settings=settings,
        executor=InlineExecutor(),
        use_background_tasks=False,
    )

    @github.on("issues.opened")
    async def _on_issue(ctx: WebhookContext[IssuesPayload, Any]) -> None:
        ctx.log.info("test_issue_event")

    api = FastAPI()
    api.include_router(github.router(), prefix="/gh")
    return TestClient(api), github


def test_unauthorized_on_missing_signature() -> None:
    client, _github = _make_client(require_signature=True)
    body = json.dumps(issues_opened()).encode("utf-8")
    response = client.post(
        "/gh/webhooks",
        content=body,
        headers={
            "X-GitHub-Event": "issues",
            "X-GitHub-Delivery": "delivery-1",
            "Content-Type": "application/json",
        },
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_success_path_with_signature_and_fake_client() -> None:
    settings = make_test_settings(require_signature=True)

    async def client_factory(installation_id: int | None) -> FakeGitHubClient:
        return FakeGitHubClient()

    github = GitHubApp(
        settings=settings,
        executor=InlineExecutor(),
        use_background_tasks=False,
        github_client_factory=client_factory,
    )

    hits = {"count": 0}

    @github.on("issues.opened")
    async def handler(ctx: WebhookContext[IssuesPayload, Any]) -> None:
        hits["count"] += 1
        assert ctx.repo is not None
        await ctx.github.rest.issues.create_comment(
            owner=ctx.repo.owner,
            repo=ctx.repo.name,
            issue_number=ctx.payload.issue.number,
            body="hello",
        )

    api = FastAPI()
    api.include_router(github.router(), prefix="/github")
    client = TestClient(api)

    raw = issues_opened()
    body = json.dumps(raw).encode("utf-8")
    secret = settings.webhook_secret.get_secret_value()
    sig = sign_sha256_payload(secret, body)
    response = client.post(
        "/github/webhooks",
        content=body,
        headers={
            "X-GitHub-Event": "issues",
            "X-GitHub-Delivery": "delivery-2",
            "X-Hub-Signature-256": sig,
            "Content-Type": "application/json",
        },
    )
    assert response.status_code == status.HTTP_202_ACCEPTED
    assert hits["count"] == 1


def test_noop_executor_skips_handlers() -> None:
    settings = make_test_settings(require_signature=True)
    github = GitHubApp(settings=settings, executor=NoopExecutor())
    hits = {"n": 0}

    @github.on("issues.opened")
    async def handler(_ctx: WebhookContext[Any, Any]) -> None:
        hits["n"] += 1

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
            "X-GitHub-Delivery": "delivery-3",
            "X-Hub-Signature-256": sig,
        },
    )
    assert resp.status_code == status.HTTP_202_ACCEPTED
    assert hits["n"] == 0


def test_invalid_json_returns_400_when_parse_is_inline() -> None:
    settings = make_test_settings(require_signature=True)
    github = GitHubApp(
        settings=settings,
        executor=InlineExecutor(),
        use_background_tasks=False,
    )

    @github.on("issues.opened")
    async def _handler(ctx: WebhookContext[IssuesPayload, Any]) -> None:
        assert ctx.repo is not None

    api = FastAPI()
    api.include_router(github.router(), prefix="/api")
    client = TestClient(api)
    body = b"{not-json"
    secret = settings.webhook_secret.get_secret_value()
    sig = sign_sha256_payload(secret, body)
    resp = client.post(
        "/api/webhooks",
        content=body,
        headers={
            "X-GitHub-Event": "issues",
            "X-GitHub-Delivery": "delivery-bad-json",
            "X-Hub-Signature-256": sig,
        },
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST


def test_ack_before_dispatch_returns_202_for_invalid_json() -> None:
    """Throughput mode: JSON validation happens after 202 (parse failures are logged only)."""
    settings = make_test_settings(
        require_signature=True,
        webhook_ack_before_dispatch=True,
    )
    hits = {"n": 0}
    github = GitHubApp(settings=settings, use_background_tasks=True)

    @github.on("issues.opened")
    async def _handler(ctx: WebhookContext[IssuesPayload, Any]) -> None:
        hits["n"] += 1
        assert ctx.repo is not None

    api = FastAPI()
    api.include_router(github.router(), prefix="/api")
    client = TestClient(api)
    body = b"{not-json"
    secret = settings.webhook_secret.get_secret_value()
    sig = sign_sha256_payload(secret, body)
    resp = client.post(
        "/api/webhooks",
        content=body,
        headers={
            "X-GitHub-Event": "issues",
            "X-GitHub-Delivery": "delivery-fast-ack",
            "X-Hub-Signature-256": sig,
        },
    )
    assert resp.status_code == status.HTTP_202_ACCEPTED
    assert hits["n"] == 0
