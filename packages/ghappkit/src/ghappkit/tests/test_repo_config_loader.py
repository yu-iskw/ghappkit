"""Repository YAML configuration loading."""

from __future__ import annotations

import asyncio
import logging
from collections import deque
from types import SimpleNamespace
from typing import Any

import pytest
from pydantic import BaseModel, SecretStr

from ghappkit.context import BoundLogger, RepositoryRef, WebhookContext
from ghappkit.exceptions import RepoConfigError
from ghappkit.repo_config import RepoConfigLoader
from ghappkit.settings import GitHubAppSettings


class SampleCfg(BaseModel):
    enabled: bool = True


class _StubIssues:
    """Minimal ``rest.issues`` surface for config loader tests."""

    def __init__(self, responses: list[str | None]) -> None:
        self._pending: deque[str | None] = deque(responses)

    async def fetch_repo_text_file(
        self,
        *,
        owner: str,
        repo: str,
        path: str,
        ref: str | None = None,
    ) -> str | None:
        del owner, repo, path, ref
        return self._pending.popleft() if self._pending else None


def _stub_github(responses: list[str | None]) -> Any:
    return SimpleNamespace(rest=SimpleNamespace(issues=_StubIssues(responses)))


def test_repo_config_loads_yaml_model() -> None:
    settings = GitHubAppSettings(
        app_id=1,
        webhook_secret=SecretStr("s"),
        config_file=".github/ghappkit.yml",
    )
    loader = RepoConfigLoader(settings)

    async def run() -> None:
        ctx = WebhookContext(
            delivery_id="d",
            event="push",
            action=None,
            payload={},
            raw_payload={
                "repository": {
                    "name": "demo",
                    "owner": {"login": "acme"},
                    "default_branch": "main",
                },
            },
            installation_id=1,
            repo=RepositoryRef(owner="acme", name="demo"),
            sender=None,
            github=_stub_github(["enabled: true\n"]),
            log=BoundLogger(logging.getLogger("ghappkit.tests.repo_cfg"), {}),
            request=None,
            _config_loader=loader,
        )
        cfg = await loader.load(ctx, model=SampleCfg, file_name=None, default=None)
        assert cfg is not None
        assert cfg.enabled is True

    asyncio.run(run())


def test_repo_config_invalid_yaml_raises() -> None:
    settings = GitHubAppSettings(app_id=1, webhook_secret=SecretStr("s"))
    loader = RepoConfigLoader(settings)

    async def run() -> None:
        ctx = WebhookContext(
            delivery_id="d",
            event="push",
            action=None,
            payload={},
            raw_payload={
                "repository": {
                    "name": "demo",
                    "owner": {"login": "acme"},
                    "default_branch": "main",
                },
            },
            installation_id=1,
            repo=RepositoryRef(owner="acme", name="demo"),
            sender=None,
            github=_stub_github(["bad: [\n"]),
            log=BoundLogger(logging.getLogger("ghappkit.tests.repo_cfg2"), {}),
            request=None,
            _config_loader=loader,
        )
        with pytest.raises(RepoConfigError):
            await loader.load(ctx, model=SampleCfg, file_name=None, default=None)

    asyncio.run(run())


def test_repo_config_validation_error_raises() -> None:
    settings = GitHubAppSettings(app_id=1, webhook_secret=SecretStr("s"))
    loader = RepoConfigLoader(settings)

    async def run() -> None:
        ctx = WebhookContext(
            delivery_id="d",
            event="push",
            action=None,
            payload={},
            raw_payload={
                "repository": {
                    "name": "demo",
                    "owner": {"login": "acme"},
                    "default_branch": "main",
                },
            },
            installation_id=1,
            repo=RepositoryRef(owner="acme", name="demo"),
            sender=None,
            github=_stub_github(["enabled: not-a-bool\n"]),
            log=BoundLogger(logging.getLogger("ghappkit.tests.repo_cfg3"), {}),
            request=None,
            _config_loader=loader,
        )
        with pytest.raises(RepoConfigError):
            await loader.load(ctx, model=SampleCfg, file_name=None, default=None)

    asyncio.run(run())


def test_repo_config_ttl_returns_independent_copies() -> None:
    """Regression: mutating one delivery's config must not affect cached reads."""
    settings = GitHubAppSettings(
        app_id=1,
        webhook_secret=SecretStr("s"),
        config_file=".github/ghappkit.yml",
    )
    loader = RepoConfigLoader(settings, ttl_seconds=3600.0, clock=lambda: 0.0)

    async def run() -> None:
        ctx = WebhookContext(
            delivery_id="d",
            event="push",
            action=None,
            payload={},
            raw_payload={
                "repository": {
                    "name": "demo",
                    "owner": {"login": "acme"},
                    "default_branch": "main",
                },
            },
            installation_id=1,
            repo=RepositoryRef(owner="acme", name="demo"),
            sender=None,
            github=_stub_github(["enabled: true\n"]),
            log=BoundLogger(logging.getLogger("ghappkit.tests.repo_cfg_ttl"), {}),
            request=None,
            _config_loader=loader,
        )
        cfg1 = await loader.load(ctx, model=SampleCfg, file_name=None, default=None)
        assert cfg1 is not None
        cfg1.enabled = False
        cfg2 = await loader.load(ctx, model=SampleCfg, file_name=None, default=None)
        assert cfg2 is not None
        assert cfg2.enabled is True

    asyncio.run(run())
