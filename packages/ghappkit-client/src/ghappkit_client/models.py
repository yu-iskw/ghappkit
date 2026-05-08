"""Transport and auth response models."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class InstallationToken:
    """Installation access token from GitHub."""

    token: str
    expires_at: datetime


@dataclass(frozen=True)
class GitHubResponse:
    """Normalized HTTP response from GitHub."""

    status_code: int
    headers: Mapping[str, str]
    json_data: Any | None
    text: str

    @property
    def ok(self) -> bool:
        return 200 <= self.status_code < 300
