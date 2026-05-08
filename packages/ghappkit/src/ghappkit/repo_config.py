"""Repository YAML configuration loading."""

from __future__ import annotations

import copy
import time
from collections.abc import Callable
from typing import Any

import yaml
from pydantic import BaseModel, ValidationError

from ghappkit.context import WebhookContext
from ghappkit.exceptions import RepoConfigError
from ghappkit.settings import GitHubAppSettings


def _snapshot_repo_config(value: Any) -> Any:
    """Detach cached config from callers so mutations cannot leak across deliveries."""
    if value is None:
        return None
    if isinstance(value, BaseModel):
        return value.model_copy(deep=True)
    return copy.deepcopy(value)


class RepoConfigLoader:
    """Load ``.github/ghappkit.yml`` via the GitHub Contents API."""

    def __init__(
        self,
        settings: GitHubAppSettings,
        *,
        ttl_seconds: float = 0,
        clock: Callable[[], float] | None = None,
    ) -> None:
        self._settings = settings
        self._ttl = ttl_seconds
        self._clock = clock or time.monotonic
        self._cache: dict[tuple[Any, ...], tuple[float, Any]] = {}

    async def load(
        self,
        ctx: WebhookContext[Any, Any],
        *,
        model: type[BaseModel] | None,
        file_name: str | None,
        default: Any | None,
    ) -> Any | None:
        """Fetch YAML from the repository and validate."""
        path = file_name or self._settings.config_file
        repo = ctx.repo
        if repo is None:
            return self._finalize_default(model, default)

        ref = self._default_branch(ctx.raw_payload)
        cache_key = (ctx.installation_id, repo.owner, repo.name, path, ref)
        now = self._clock()
        cached = self._cache.get(cache_key)
        if cached and self._ttl > 0:
            ts, value = cached
            if now - ts < self._ttl:
                return _snapshot_repo_config(value)

        text = await ctx.github.rest.issues.fetch_repo_text_file(
            owner=repo.owner,
            repo=repo.name,
            path=path,
            ref=ref,
        )
        if text is None:
            result = self._finalize_default(model, default)
            self._maybe_store(cache_key, now, result)
            return _snapshot_repo_config(result)

        try:
            loaded = yaml.safe_load(text)
        except yaml.YAMLError as exc:
            raise RepoConfigError("repository configuration YAML is invalid") from exc

        parsed = self._validate(model, loaded)
        self._maybe_store(cache_key, now, parsed)
        return _snapshot_repo_config(parsed)

    def _maybe_store(self, key: tuple[Any, ...], now: float, value: Any) -> None:
        if self._ttl > 0:
            self._cache[key] = (now, _snapshot_repo_config(value))

    def _finalize_default(
        self,
        model: type[BaseModel] | None,
        default: Any | None,
    ) -> Any | None:
        if default is None:
            return None
        if model is None:
            return default
        if isinstance(default, dict):
            return model.model_validate(default)
        return default

    def _validate(self, model: type[BaseModel] | None, loaded: Any) -> Any:
        if model is None:
            if isinstance(loaded, dict):
                return loaded
            return {"value": loaded}
        try:
            return model.model_validate(loaded)
        except ValidationError as exc:
            raise RepoConfigError("repository configuration validation failed") from exc

    def _default_branch(self, raw_payload: dict[str, Any]) -> str | None:
        repo = raw_payload.get("repository")
        if not isinstance(repo, dict):
            return None
        branch = repo.get("default_branch")
        return branch if isinstance(branch, str) else None
