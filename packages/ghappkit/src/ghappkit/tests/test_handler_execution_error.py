"""Handler failures surface as HandlerExecutionError."""

from __future__ import annotations

import asyncio
from typing import Any

from ghappkit_testing.fake_client import FakeGitHubClient
from ghappkit_testing.fixtures import issues_opened
from ghappkit_testing.simulator import GhappkitTestClient
from ghappkit_testing.test_settings import make_test_settings

from ghappkit.app import GitHubApp
from ghappkit.context import WebhookContext
from ghappkit.events import IssuesPayload
from ghappkit.exceptions import HandlerError, HandlerExecutionError
from ghappkit.execution import InlineExecutor


def test_failed_handler_wraps_with_handler_execution_error() -> None:
    settings = make_test_settings()

    async def factory(_installation_id: int | None) -> FakeGitHubClient:
        return FakeGitHubClient()

    app = GitHubApp(
        settings=settings,
        executor=InlineExecutor(),
        use_background_tasks=False,
        github_client_factory=factory,
    )

    captured: dict[str, object] = {}

    @app.on_error()
    async def on_err(err: HandlerError) -> None:
        captured["wrapped_type"] = type(err.exc)
        captured["cause_type"] = type(err.exc.__cause__) if err.exc.__cause__ else None

    @app.on("issues.opened")
    async def boom(ctx: WebhookContext[IssuesPayload, Any]) -> None:
        raise RuntimeError("boom")

    async def run() -> None:
        await GhappkitTestClient(app).deliver("issues.opened", issues_opened())

    asyncio.run(run())

    assert captured["wrapped_type"] is HandlerExecutionError
    assert captured["cause_type"] is RuntimeError
