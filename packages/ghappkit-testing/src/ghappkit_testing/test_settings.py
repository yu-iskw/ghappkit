"""Settings helpers for tests."""

from __future__ import annotations

from typing import Any

from ghappkit.settings import GitHubAppSettings
from pydantic import SecretStr


def make_test_settings(**kwargs: Any) -> GitHubAppSettings:
    """Defaults suitable for unit tests (signatures disabled)."""
    defaults: dict[str, Any] = {
        "app_id": 1,
        "webhook_secret": SecretStr("unit-test-secret"),
        "require_signature": False,
    }
    defaults.update(kwargs)
    return GitHubAppSettings(**defaults)
