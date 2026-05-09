"""Tests for guarded webhook handler delivery (inline vs background)."""

from __future__ import annotations

import asyncio
import json
from typing import Any

import pytest
from fastapi import HTTPException
from ghappkit_testing.fixtures import issues_opened
from ghappkit_testing.test_settings import make_test_settings

from ghappkit.app import GitHubApp
from ghappkit.context import WebhookContext
from ghappkit.execution import InlineExecutor


def test_inline_executor_surfaces_invoke_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """Misconfiguration or bugs before handlers run must not be swallowed with InlineExecutor."""
    settings = make_test_settings(require_signature=False)
    gh = GitHubApp(settings=settings, executor=InlineExecutor(), use_background_tasks=False)

    @gh.on("issues.opened")
    async def _noop(_ctx: WebhookContext[Any, Any]) -> None:
        return None

    async def boom(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("delivery pipeline failed")

    monkeypatch.setattr(gh, "_invoke_handlers", boom)

    async def run() -> None:
        body = json.dumps(issues_opened()).encode("utf-8")
        with pytest.raises(HTTPException) as exc_info:
            await gh.dispatch_for_tests(
                headers={
                    "X-GitHub-Event": "issues",
                    "X-GitHub-Delivery": "delivery-guard-1",
                    "Content-Type": "application/json",
                },
                body=body,
            )
        assert exc_info.value.status_code == 500
        assert isinstance(exc_info.value.__cause__, RuntimeError)

    asyncio.run(run())
