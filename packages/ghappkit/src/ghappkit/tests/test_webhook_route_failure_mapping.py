"""Contract tests for GitHub webhook HTTP ``detail`` mapping.

Uses :func:`ghappkit.app._raise_http_for_webhook_route_failure` (the implementation
behind :meth:`ghappkit.app.GitHubApp.router`) so stable ``detail`` strings are checked
without a full HTTP stack for every case. Mapped 500 pairs stay aligned with
``_WEBHOOK_MAPPED_INTERNAL_ERRORS`` in ``ghappkit.app``.

Probe instances for mapped internal errors are built via ``_MAPPED_INTERNAL_PROBE_BY_TYPE``:
when you add a row to ``_WEBHOOK_MAPPED_INTERNAL_ERRORS``, add a matching factory here
so constructor drift is caught immediately (instead of assuming ``exc_cls("probe")`` works).
"""

from __future__ import annotations

import json
from collections.abc import Callable
from types import MethodType
from typing import Any, NoReturn

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from ghappkit_client.client import GitHubClient
from ghappkit_client.errors import GitHubApiError, InstallationAuthError
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
    ErrorHookExecutionError,
    EventModelError,
    HandlerExecutionError,
    MissingWebhookSignatureError,
    PayloadParseError,
    RepoConfigError,
    WebhookHeaderError,
)
from ghappkit.execution import InlineExecutor

_MAPPED_INTERNAL_PROBE_BY_TYPE: dict[type[BaseException], Callable[[], BaseException]] = {
    HandlerExecutionError: lambda: HandlerExecutionError("mapper probe"),
    ErrorHookExecutionError: lambda: ErrorHookExecutionError("mapper probe"),
    EventModelError: lambda: EventModelError("mapper probe"),
    GitHubApiError: lambda: GitHubApiError("mapper probe", status_code=None),
    InstallationAuthError: lambda: InstallationAuthError("mapper probe"),
    RepoConfigError: lambda: RepoConfigError("mapper probe"),
}


def test_mapped_internal_errors_have_explicit_probe_factory() -> None:
    """Each mapped row has a probe factory, and probe keys match mapped types (no orphans)."""
    mapped_types = {exc_cls for exc_cls, _ in _WEBHOOK_MAPPED_INTERNAL_ERRORS}
    probe_types = set(_MAPPED_INTERNAL_PROBE_BY_TYPE)
    assert mapped_types == probe_types, (
        "keep _WEBHOOK_MAPPED_INTERNAL_ERRORS and _MAPPED_INTERNAL_PROBE_BY_TYPE in sync: "
        f"only in mapped={mapped_types - probe_types!r}, only in probes={probe_types - mapped_types!r}"
    )


def _probe_for_mapped_internal(exc_cls: type[BaseException]) -> BaseException:
    return _MAPPED_INTERNAL_PROBE_BY_TYPE[exc_cls]()


@pytest.mark.parametrize(
    ("exc", "expected_status", "expected_detail"),
    [
        (MissingWebhookSignatureError("missing"), 401, "invalid_webhook_signature"),
        (WebhookHeaderError("missing event"), 400, "invalid_webhook_headers"),
        (PayloadParseError("bad json", kind="json"), 400, "invalid_webhook_payload_json"),
        (
            PayloadParseError("payload must be utf-8", kind="utf8"),
            400,
            "invalid_webhook_payload_encoding",
        ),
        (
            PayloadParseError("payload JSON must be an object", kind="not_object"),
            400,
            "invalid_webhook_payload_not_object",
        ),
        *[
            (_probe_for_mapped_internal(cls), 500, detail)
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


class _InstallationTokenProbeExplodes:
    """Minimal token provider used only to force ``InstallationAuthError`` in tests."""

    async def get_token(
        self,
        installation_id: int,
        *,
        permissions: dict[str, str] | None = None,
        repository_ids: list[int] | None = None,
    ) -> NoReturn:
        del installation_id, permissions, repository_ids
        raise InstallationAuthError("unit test installation auth failure")


def test_router_webhook_without_api_credentials_returns_202_when_handler_skips_github() -> None:
    """Installation metadata without a token provider still yields a stub client (P0 webhook path)."""
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
    assert resp.status_code == status.HTTP_202_ACCEPTED


def test_router_installation_auth_error_detail() -> None:
    """``InstallationAuthError`` from token exchange maps to ``webhook_installation_auth_error``."""
    settings = make_test_settings(require_signature=True)
    github = GitHubApp(
        settings=settings,
        executor=InlineExecutor(),
        use_background_tasks=False,
        token_provider=_InstallationTokenProbeExplodes(),  # type: ignore[arg-type]
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
            "X-GitHub-Delivery": "d-install-auth",
            "X-Hub-Signature-256": sig,
        },
    )
    assert resp.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert resp.json()["detail"] == "webhook_installation_auth_error"


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


def test_router_repo_config_error_detail(monkeypatch: pytest.MonkeyPatch) -> None:
    """``RepoConfigError`` raised before handlers still maps to ``webhook_repo_config_error``."""
    settings = make_test_settings(require_signature=True)
    github = GitHubApp(
        settings=settings,
        executor=InlineExecutor(),
        use_background_tasks=False,
    )

    async def boom_repo_config(
        _self: GitHubApp,
        installation_id: int | None,
    ) -> GitHubClient:
        del installation_id
        raise RepoConfigError("unit test repo config failure")

    monkeypatch.setattr(github, "_create_github_client", MethodType(boom_repo_config, github))

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
            "X-GitHub-Delivery": "d-repo-cfg",
            "X-Hub-Signature-256": sig,
        },
    )
    assert resp.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert resp.json()["detail"] == "webhook_repo_config_error"
