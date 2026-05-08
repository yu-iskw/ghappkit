"""Webhook handler context objects."""

from __future__ import annotations

import logging
from collections.abc import Mapping, MutableMapping
from dataclasses import dataclass
from typing import Any, Generic, TypeVar

from fastapi import Request
from ghappkit_client.client import GitHubClient
from pydantic import BaseModel

from ghappkit.events.models import EVENT_MODEL_BY_NAME
from ghappkit.exceptions import EventModelError

PayloadT = TypeVar("PayloadT")
ConfigT = TypeVar("ConfigT")


@dataclass(frozen=True)
class RepositoryRef:
    """Normalized repository coordinates."""

    owner: str
    name: str

    def params(self, *, path: str | None = None) -> dict[str, str]:
        """Common kwargs for REST helpers."""
        data: dict[str, str] = {"owner": self.owner, "repo": self.name}
        if path is not None:
            data["path"] = path
        return data


@dataclass(frozen=True)
class SenderRef:
    """GitHub user login."""

    login: str


class BoundLogger(logging.LoggerAdapter):
    """Logger adapter that carries webhook metadata without dumping payloads."""

    def process(
        self,
        msg: str,
        kwargs: MutableMapping[str, Any],
    ) -> tuple[str, MutableMapping[str, Any]]:
        extra = dict(kwargs.get("extra") or {})
        extra.update(self.extra or {})
        kwargs["extra"] = extra
        return msg, kwargs


@dataclass
class WebhookContext(Generic[PayloadT, ConfigT]):
    """Per-delivery context passed to handlers."""

    delivery_id: str
    event: str
    action: str | None
    payload: PayloadT
    raw_payload: dict[str, Any]
    installation_id: int | None
    repo: RepositoryRef | None
    sender: SenderRef | None
    github: GitHubClient
    log: BoundLogger
    request: Request | None
    _config_loader: Any

    async def config(
        self,
        model: type[BaseModel] | None = None,
        *,
        file_name: str | None = None,
        default: ConfigT | dict[str, Any] | None = None,
    ) -> ConfigT | dict[str, Any] | None:
        """Load repository configuration via the GitHub Contents API."""
        return await self._config_loader.load(
            self,
            model=model,
            file_name=file_name,
            default=default,
        )


def extract_repository_ref(payload: Mapping[str, Any]) -> RepositoryRef | None:
    """Best-effort repository extraction."""
    repo = payload.get("repository")
    if not isinstance(repo, dict):
        return None
    name = repo.get("name")
    owner_obj = repo.get("owner")
    owner_login = None
    if isinstance(owner_obj, dict):
        owner_login = owner_obj.get("login")
    if not isinstance(name, str) or not isinstance(owner_login, str):
        return None
    return RepositoryRef(owner=owner_login, name=name)


def extract_sender_ref(payload: Mapping[str, Any]) -> SenderRef | None:
    sender = payload.get("sender")
    if not isinstance(sender, dict):
        return None
    login = sender.get("login")
    if not isinstance(login, str):
        return None
    return SenderRef(login=login)


def extract_installation_id(payload: Mapping[str, Any]) -> int | None:
    inst = payload.get("installation")
    if not isinstance(inst, dict):
        return None
    inst_id = inst.get("id")
    return inst_id if isinstance(inst_id, int) else None


def build_payload_model(qualified_event: str, raw: dict[str, Any]) -> Any:
    """Validate payload when a typed model exists."""
    model_cls = EVENT_MODEL_BY_NAME.get(qualified_event)
    if model_cls is None:
        return raw
    try:
        return model_cls.model_validate(raw)
    except Exception as exc:
        raise EventModelError(f"failed to validate payload for {qualified_event}") from exc
