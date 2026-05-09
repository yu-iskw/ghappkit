"""Minimal GitHub App that comments on new issues using repo configuration."""

from __future__ import annotations

from typing import Any, cast

from fastapi import FastAPI
from ghappkit import GitHubApp, GitHubAppSettings
from ghappkit.context import WebhookContext
from ghappkit.events import IssuesPayload
from pydantic import BaseModel, Field


class AppConfig(BaseModel):
    """Example repository configuration schema."""

    enabled: bool = Field(default=True)
    issue_greeting: str = Field(default="Thanks for opening this issue!")
    default_labels: list[str] = Field(default_factory=list)


def create_app() -> FastAPI:
    settings = GitHubAppSettings.from_env()
    github = GitHubApp(settings=settings)

    @github.on("issues.opened")
    async def on_issue_opened(ctx: WebhookContext[IssuesPayload, Any]) -> None:
        payload = ctx.payload
        config = cast(AppConfig | None, await ctx.config(AppConfig))
        if config is not None and not config.enabled:
            ctx.log.info("issue_commenter_disabled")
            return
        greeting = config.issue_greeting if config else "Thanks for filing this issue!"
        if ctx.repo is None:
            return
        await ctx.github.rest.issues.create_comment(
            owner=ctx.repo.owner,
            repo=ctx.repo.name,
            issue_number=payload.issue.number,
            body=greeting,
        )
        if config and config.default_labels:
            await ctx.github.rest.issues.add_labels(
                owner=ctx.repo.owner,
                repo=ctx.repo.name,
                issue_number=payload.issue.number,
                labels=config.default_labels,
            )

    api = FastAPI(title="issue-commenter-example")
    api.include_router(github.router(), prefix="/github")
    return api


app = create_app()
