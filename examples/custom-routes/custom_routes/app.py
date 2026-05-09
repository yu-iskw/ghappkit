"""Compose ghappkit with additional FastAPI routes."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from ghappkit import GitHubApp, GitHubAppSettings
from ghappkit.context import WebhookContext


def create_app() -> FastAPI:
    settings = GitHubAppSettings.from_env()
    github = GitHubApp(settings=settings)

    @github.on_any()
    async def audit(ctx: WebhookContext[Any, Any]) -> None:
        ctx.log.info("custom_routes_audit_event")

    api = FastAPI(title="custom-routes-example")

    @api.get("/healthz")
    async def healthcheck() -> dict[str, str]:
        return {"status": "ok"}

    api.include_router(github.router(), prefix="/hooks")
    return api


app = create_app()
