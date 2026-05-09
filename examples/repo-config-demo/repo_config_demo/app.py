"""Demonstrates repository YAML configuration access."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from ghappkit import GitHubApp, GitHubAppSettings
from ghappkit.context import WebhookContext
from pydantic import BaseModel, Field


class DemoConfig(BaseModel):
    """Example ``ghappkit.yml`` schema."""

    enabled: bool = Field(default=True)
    note: str = Field(default="configured")


def create_app() -> FastAPI:
    settings = GitHubAppSettings.from_env()
    github = GitHubApp(settings=settings)

    @github.on("push")
    async def on_push(ctx: WebhookContext[dict[str, Any], Any]) -> None:
        cfg = await ctx.config(DemoConfig)
        ctx.log.info(
            "repo_config_demo_push",
            extra={"configured": cfg is not None},
        )

    api = FastAPI(title="repo-config-demo")
    api.include_router(github.router(), prefix="/github")
    return api


app = create_app()
