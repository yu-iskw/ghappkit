"""Tests for GhappkitTestClient."""

from __future__ import annotations

import asyncio
from typing import Any

from ghappkit.app import GitHubApp
from ghappkit.context import WebhookContext
from ghappkit.execution import InlineExecutor

from ghappkit_testing.fake_client import FakeGitHubClient
from ghappkit_testing.fixtures import issues_opened
from ghappkit_testing.simulator import GhappkitTestClient
from ghappkit_testing.test_settings import make_test_settings


def test_simulator_delivers_event() -> None:
    settings = make_test_settings()
    hits = {"n": 0}

    async def factory(_installation_id: int | None) -> FakeGitHubClient:
        return FakeGitHubClient()

    app = GitHubApp(
        settings=settings,
        executor=InlineExecutor(),
        use_background_tasks=False,
        github_client_factory=factory,
    )

    @app.on("issues.opened")
    async def on_issue(ctx: WebhookContext[Any, Any]) -> None:  # pylint: disable=unused-argument
        hits["n"] += 1

    async def run() -> None:
        sim = GhappkitTestClient(app)
        await sim.deliver("issues.opened", issues_opened())

    asyncio.run(run())
    assert hits["n"] == 1
