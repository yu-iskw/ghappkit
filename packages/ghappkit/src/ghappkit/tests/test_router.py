"""HTTP mapping tests for the FastAPI router."""

from __future__ import annotations

import asyncio
import json
from typing import Any

import pytest
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
from ghappkit.exceptions import HandlerError
from ghappkit.execution import InlineExecutor, NoopExecutor
from ghappkit.webhooks import parse_delivery_after_optional_signature


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
    client, _ = _make_client(require_signature=True)
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

    async def client_factory(_installation_id: int | None) -> FakeGitHubClient:
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
    async def handler(ctx: WebhookContext[Any, Any]) -> None:  # pylint: disable=unused-argument
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


def test_json_array_body_returns_400() -> None:
    settings = make_test_settings(require_signature=True)
    github = GitHubApp(
        settings=settings,
        executor=InlineExecutor(),
        use_background_tasks=False,
    )

    api = FastAPI()
    api.include_router(github.router(), prefix="/api")
    client = TestClient(api)
    body = json.dumps([1, 2, 3]).encode("utf-8")
    secret = settings.webhook_secret.get_secret_value()
    sig = sign_sha256_payload(secret, body)
    resp = client.post(
        "/api/webhooks",
        content=body,
        headers={
            "X-GitHub-Event": "issues",
            "X-GitHub-Delivery": "delivery-array-json",
            "X-Hub-Signature-256": sig,
        },
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert resp.json()["detail"] == "invalid_webhook_payload_not_object"


def test_on_list_registers_same_handler_for_multiple_events() -> None:
    settings = make_test_settings(require_signature=True)

    async def client_factory(_installation_id: int | None) -> FakeGitHubClient:
        return FakeGitHubClient()

    github = GitHubApp(
        settings=settings,
        executor=InlineExecutor(),
        use_background_tasks=False,
        github_client_factory=client_factory,
    )
    seen: list[str] = []

    @github.on(["issues.opened", "issues.closed"])
    async def both(ctx: WebhookContext[Any, Any]) -> None:
        seen.append(ctx.qualified_event)

    api = FastAPI()
    api.include_router(github.router(), prefix="/api")
    client = TestClient(api)
    secret = settings.webhook_secret.get_secret_value()

    opened_body = json.dumps(issues_opened()).encode("utf-8")
    r1 = client.post(
        "/api/webhooks",
        content=opened_body,
        headers={
            "X-GitHub-Event": "issues",
            "X-GitHub-Delivery": "d-multi-1",
            "X-Hub-Signature-256": sign_sha256_payload(secret, opened_body),
        },
    )
    assert r1.status_code == status.HTTP_202_ACCEPTED

    closed = issues_opened()
    closed["action"] = "closed"
    closed_body = json.dumps(closed).encode("utf-8")
    r2 = client.post(
        "/api/webhooks",
        content=closed_body,
        headers={
            "X-GitHub-Event": "issues",
            "X-GitHub-Delivery": "d-multi-2",
            "X-Hub-Signature-256": sign_sha256_payload(secret, closed_body),
        },
    )
    assert r2.status_code == status.HTTP_202_ACCEPTED
    assert seen == ["issues.opened", "issues.closed"]


def test_exact_handler_receives_context_fields() -> None:
    settings = make_test_settings(require_signature=True)

    async def client_factory(_installation_id: int | None) -> FakeGitHubClient:
        return FakeGitHubClient()

    github = GitHubApp(
        settings=settings,
        executor=InlineExecutor(),
        use_background_tasks=False,
        github_client_factory=client_factory,
    )

    @github.on("ping")
    async def handler(ctx: WebhookContext[Any, Any]) -> None:
        assert ctx.delivery_id == "delivery-ctx"
        assert ctx.event == "ping"
        assert ctx.qualified_event == "ping"
        assert ctx.action is None
        assert isinstance(ctx.payload, dict)
        assert ctx.raw_payload == ctx.payload
        assert ctx.request is not None

    api = FastAPI()
    api.include_router(github.router(), prefix="/api")
    client = TestClient(api)
    raw = {"zen": "listening"}
    body = json.dumps(raw).encode("utf-8")
    secret = settings.webhook_secret.get_secret_value()
    resp = client.post(
        "/api/webhooks",
        content=body,
        headers={
            "X-GitHub-Event": "ping",
            "X-GitHub-Delivery": "delivery-ctx",
            "X-Hub-Signature-256": sign_sha256_payload(secret, body),
        },
    )
    assert resp.status_code == status.HTTP_202_ACCEPTED


def test_invalid_json_returns_400_when_parse_is_inline() -> None:
    settings = make_test_settings(require_signature=True)
    github = GitHubApp(
        settings=settings,
        executor=InlineExecutor(),
        use_background_tasks=False,
    )

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
    assert resp.json()["detail"] == "invalid_webhook_payload_json"


def test_invalid_utf8_body_returns_400_when_parse_is_inline() -> None:
    settings = make_test_settings(require_signature=True)
    github = GitHubApp(
        settings=settings,
        executor=InlineExecutor(),
        use_background_tasks=False,
    )
    api = FastAPI()
    api.include_router(github.router(), prefix="/api")
    client = TestClient(api)
    body = b"\xff\xfe\xfd"
    secret = settings.webhook_secret.get_secret_value()
    sig = sign_sha256_payload(secret, body)
    resp = client.post(
        "/api/webhooks",
        content=body,
        headers={
            "X-GitHub-Event": "issues",
            "X-GitHub-Delivery": "delivery-bad-utf8",
            "X-Hub-Signature-256": sig,
        },
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert resp.json()["detail"] == "invalid_webhook_payload_encoding"


def test_ack_before_dispatch_returns_202_for_invalid_json() -> None:
    """Contract: fast-ack + background defers JSON parse; GitHub gets 202, not 400.

    This intentionally differs from the default inline path (see
    ``test_invalid_json_returns_400_when_parse_is_inline``), where invalid JSON
    is rejected with HTTP 400 before any handler runs.
    """
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


def test_invalid_signature_returns_401() -> None:
    settings = make_test_settings(require_signature=True)
    github = GitHubApp(settings=settings, executor=InlineExecutor(), use_background_tasks=False)
    api = FastAPI()
    api.include_router(github.router(), prefix="/api")
    client = TestClient(api)
    body = json.dumps({"zen": "listening"}).encode("utf-8")
    resp = client.post(
        "/api/webhooks",
        content=body,
        headers={
            "X-GitHub-Event": "ping",
            "X-GitHub-Delivery": "d-bad-sig",
            "X-Hub-Signature-256": "sha256=" + "b" * 64,
        },
    )
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


def test_missing_event_header_returns_400() -> None:
    settings = make_test_settings(require_signature=True)
    github = GitHubApp(settings=settings, executor=InlineExecutor(), use_background_tasks=False)
    api = FastAPI()
    api.include_router(github.router(), prefix="/api")
    client = TestClient(api)
    body = b"{}"
    secret = settings.webhook_secret.get_secret_value()
    sig = sign_sha256_payload(secret, body)
    resp = client.post(
        "/api/webhooks",
        content=body,
        headers={
            "X-GitHub-Delivery": "d-no-event",
            "X-Hub-Signature-256": sig,
        },
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert resp.json()["detail"] == "invalid_webhook_headers"


def test_missing_delivery_header_returns_400() -> None:
    settings = make_test_settings(require_signature=True)
    github = GitHubApp(settings=settings, executor=InlineExecutor(), use_background_tasks=False)
    api = FastAPI()
    api.include_router(github.router(), prefix="/api")
    client = TestClient(api)
    body = b"{}"
    secret = settings.webhook_secret.get_secret_value()
    sig = sign_sha256_payload(secret, body)
    resp = client.post(
        "/api/webhooks",
        content=body,
        headers={
            "X-GitHub-Event": "ping",
            "X-Hub-Signature-256": sig,
        },
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert resp.json()["detail"] == "invalid_webhook_headers"


def test_no_matching_handler_returns_202() -> None:
    settings = make_test_settings(require_signature=True)
    github = GitHubApp(settings=settings, executor=InlineExecutor(), use_background_tasks=False)
    api = FastAPI()
    api.include_router(github.router(), prefix="/api")
    client = TestClient(api)
    body = json.dumps({"zen": "listening"}).encode("utf-8")
    secret = settings.webhook_secret.get_secret_value()
    sig = sign_sha256_payload(secret, body)
    resp = client.post(
        "/api/webhooks",
        content=body,
        headers={
            "X-GitHub-Event": "ping",
            "X-GitHub-Delivery": "d-no-handler",
            "X-Hub-Signature-256": sig,
        },
    )
    assert resp.status_code == status.HTTP_202_ACCEPTED


def test_catch_all_handler_invoked() -> None:
    settings = make_test_settings(require_signature=True)

    async def client_factory(_installation_id: int | None) -> FakeGitHubClient:
        return FakeGitHubClient()

    github = GitHubApp(
        settings=settings,
        executor=InlineExecutor(),
        use_background_tasks=False,
        github_client_factory=client_factory,
    )
    seen: list[str] = []

    @github.on_any()
    async def catch_all(ctx: WebhookContext[Any, Any]) -> None:
        seen.append(ctx.qualified_event)

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
            "X-GitHub-Delivery": "d-catch",
            "X-Hub-Signature-256": sig,
        },
    )
    assert resp.status_code == status.HTTP_202_ACCEPTED
    assert seen == ["issues.opened"]


def test_base_event_registration_does_not_invoke_for_qualified_action() -> None:
    """Only exact qualified names match; ``issues`` does not receive ``issues.opened``."""
    settings = make_test_settings(require_signature=True)

    async def client_factory(_installation_id: int | None) -> FakeGitHubClient:
        return FakeGitHubClient()

    github = GitHubApp(
        settings=settings,
        executor=InlineExecutor(),
        use_background_tasks=False,
        github_client_factory=client_factory,
    )
    hits: list[str] = []

    @github.on("issues")
    async def on_issues(ctx: WebhookContext[Any, Any]) -> None:
        hits.append(ctx.qualified_event)

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
            "X-GitHub-Delivery": "d-base",
            "X-Hub-Signature-256": sig,
        },
    )
    assert resp.status_code == status.HTTP_202_ACCEPTED
    assert hits == []


def test_legacy_base_event_setting_runs_base_handler_after_qualified() -> None:
    """``webhook_match_legacy_base_event_handlers`` restores pre-P0 dispatch ordering."""
    settings = make_test_settings(
        require_signature=True,
        webhook_match_legacy_base_event_handlers=True,
    )

    async def client_factory(_installation_id: int | None) -> FakeGitHubClient:
        return FakeGitHubClient()

    github = GitHubApp(
        settings=settings,
        executor=InlineExecutor(),
        use_background_tasks=False,
        github_client_factory=client_factory,
    )
    hits: list[str] = []

    @github.on("issues.opened")
    async def qualified_first(_ctx: WebhookContext[Any, Any]) -> None:
        hits.append("qualified")

    @github.on("issues")
    async def base_second(_ctx: WebhookContext[Any, Any]) -> None:
        hits.append("base")

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
            "X-GitHub-Delivery": "d-legacy-base",
            "X-Hub-Signature-256": sig,
        },
    )
    assert resp.status_code == status.HTTP_202_ACCEPTED
    assert hits == ["qualified", "base"]


def test_multiple_handlers_preserve_registration_order() -> None:
    settings = make_test_settings(require_signature=True)

    async def client_factory(_installation_id: int | None) -> FakeGitHubClient:
        return FakeGitHubClient()

    github = GitHubApp(
        settings=settings,
        executor=InlineExecutor(),
        use_background_tasks=False,
        github_client_factory=client_factory,
    )
    order: list[str] = []

    @github.on("issues.opened")
    async def first(ctx: WebhookContext[Any, Any]) -> None:
        order.append("first")

    @github.on("issues.opened")
    async def second(ctx: WebhookContext[Any, Any]) -> None:
        order.append("second")

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
            "X-GitHub-Delivery": "d-order",
            "X-Hub-Signature-256": sig,
        },
    )
    assert resp.status_code == status.HTTP_202_ACCEPTED
    assert order == ["first", "second"]


def test_handler_failure_returns_500_after_error_hook() -> None:
    settings = make_test_settings(require_signature=True)

    async def client_factory(_installation_id: int | None) -> FakeGitHubClient:
        return FakeGitHubClient()

    github = GitHubApp(
        settings=settings,
        executor=InlineExecutor(),
        use_background_tasks=False,
        github_client_factory=client_factory,
    )
    errors: list[str] = []

    @github.on_error()
    async def on_err(_err: HandlerError) -> None:
        errors.append("hook")

    @github.on("issues.opened")
    async def boom(ctx: WebhookContext[Any, Any]) -> None:
        assert ctx.qualified_event == "issues.opened"
        raise RuntimeError("handler boom")

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
            "X-GitHub-Delivery": "d-err",
            "X-Hub-Signature-256": sig,
        },
    )
    assert resp.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert resp.json()["detail"] == "webhook_handler_failed"
    assert errors == ["hook"]


def test_error_hook_failure_is_not_swallowed() -> None:
    """Broken ``on_error`` hooks propagate so regressions are visible (HTTP 500)."""
    settings = make_test_settings(require_signature=True)

    async def client_factory(_installation_id: int | None) -> FakeGitHubClient:
        return FakeGitHubClient()

    github = GitHubApp(
        settings=settings,
        executor=InlineExecutor(),
        use_background_tasks=False,
        github_client_factory=client_factory,
    )

    @github.on_error()
    async def broken_hook(_err: HandlerError) -> None:
        raise ValueError("error hook regression")

    @github.on("issues.opened")
    async def boom(_ctx: WebhookContext[Any, Any]) -> None:
        raise RuntimeError("handler boom")

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
            "X-GitHub-Delivery": "d-hook-fail",
            "X-Hub-Signature-256": sig,
        },
    )
    assert resp.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert resp.json()["detail"] == "webhook_error_hook_failed"


def test_dispatch_for_tests_uses_parse_delivery_entrypoint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Regression: tests should exercise the same verify-then-parse helper as production."""
    calls = {"n": 0}
    real = parse_delivery_after_optional_signature

    def _spy(*args: object, **kwargs: object) -> object:
        calls["n"] += 1
        return real(*args, **kwargs)

    monkeypatch.setattr("ghappkit.app.parse_delivery_after_optional_signature", _spy)
    settings = make_test_settings(require_signature=False)
    github = GitHubApp(
        settings=settings,
        executor=InlineExecutor(),
        use_background_tasks=False,
    )

    async def run() -> None:
        body = json.dumps({"zen": "x"}).encode("utf-8")
        await github.dispatch_for_tests(
            headers={
                "X-GitHub-Event": "ping",
                "X-GitHub-Delivery": "d-spy",
            },
            body=body,
        )

    asyncio.run(run())
    assert calls["n"] == 1
