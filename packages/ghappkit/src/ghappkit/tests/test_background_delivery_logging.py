"""Background webhook delivery logs structured failure metadata."""

from __future__ import annotations

import json
import logging
from types import MethodType
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from ghappkit_testing.fixtures import issues_opened
from ghappkit_testing.test_settings import make_test_settings

from ghappkit.app import GitHubApp
from ghappkit.context import WebhookContext
from ghappkit.events import IssuesPayload


def test_background_executor_logs_failure_phase_on_github_client_failure(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    settings = make_test_settings(require_signature=False)
    gh = GitHubApp(settings=settings, use_background_tasks=True)

    async def boom(self: GitHubApp, installation_id: int | None) -> None:
        del self
        del installation_id
        raise RuntimeError("simulated token failure")

    monkeypatch.setattr(gh, "_create_github_client", MethodType(boom, gh))

    @gh.on("issues.opened")
    async def _handler(ctx: WebhookContext[IssuesPayload, Any]) -> None:
        del ctx

    api = FastAPI()
    api.include_router(gh.router())
    client = TestClient(api)
    caplog.set_level(logging.ERROR)
    body = json.dumps(issues_opened()).encode("utf-8")
    resp = client.post(
        "/webhooks",
        content=body,
        headers={
            "X-GitHub-Event": "issues",
            "X-GitHub-Delivery": "delivery-failure-phase",
            "Content-Type": "application/json",
        },
    )
    assert resp.status_code == 202
    matched = [
        r
        for r in caplog.records
        if getattr(r, "failure_phase", None) == "github_client"
        and getattr(r, "error_type", None) == "RuntimeError"
    ]
    assert matched
