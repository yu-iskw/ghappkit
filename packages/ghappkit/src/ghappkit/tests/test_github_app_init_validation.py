"""Construction-time validation for :class:`GitHubApp`."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from ghappkit_client.models import InstallationToken
from ghappkit_testing.fake_client import FakeGitHubClient
from pydantic import SecretStr

from ghappkit.app import GitHubApp
from ghappkit.settings import GitHubAppSettings


class _StubInstallationTokenProvider:
    async def get_token(
        self,
        installation_id: int,
        *,
        permissions: dict[str, str] | None = None,
        repository_ids: list[int] | None = None,
    ) -> InstallationToken:
        del installation_id, permissions, repository_ids
        return InstallationToken(
            token="",
            expires_at=datetime.now(timezone.utc),
        )


def _minimal_rsa_pem() -> str:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")


def test_rejects_app_id_zero_when_private_key_configured() -> None:
    settings = GitHubAppSettings(
        app_id=0,
        webhook_secret=SecretStr("secret"),
        private_key=SecretStr(_minimal_rsa_pem()),
    )
    with pytest.raises(ValueError, match="app_id"):
        GitHubApp(settings=settings)


def test_accepts_app_id_zero_for_webhook_only_install() -> None:
    settings = GitHubAppSettings(app_id=0, webhook_secret=SecretStr("secret"))
    gh = GitHubApp(settings=settings)
    assert gh._token_provider is None


def test_accepts_injected_token_provider_when_app_id_zero() -> None:
    settings = GitHubAppSettings(app_id=0, webhook_secret=SecretStr("secret"))
    gh = GitHubApp(
        settings=settings,
        token_provider=_StubInstallationTokenProvider(),  # type: ignore[arg-type]
    )
    assert gh._token_provider is not None


def test_injected_token_provider_skips_private_key_path_loading(
    tmp_path: Path,
) -> None:
    """Injected provider must not call PEM loading (avoids missing-path failures)."""
    missing_pem = tmp_path / "does-not-exist.pem"
    settings = GitHubAppSettings(
        app_id=1,
        webhook_secret=SecretStr("secret"),
        private_key_path=missing_pem,
    )
    gh = GitHubApp(
        settings=settings,
        token_provider=_StubInstallationTokenProvider(),  # type: ignore[arg-type]
    )
    assert gh._token_provider is not None


def test_github_client_factory_skips_app_id_validation_when_pem_configured() -> None:
    """Factory-driven GitHub clients bypass default installation-token flow."""
    settings = GitHubAppSettings(
        app_id=0,
        webhook_secret=SecretStr("secret"),
        private_key=SecretStr(_minimal_rsa_pem()),
    )

    async def factory(_installation_id: int | None) -> FakeGitHubClient:
        return FakeGitHubClient()

    gh = GitHubApp(settings=settings, github_client_factory=factory)
    assert gh._token_provider is not None


def test_warns_when_signature_verification_disabled(caplog: pytest.LogCaptureFixture) -> None:
    settings = GitHubAppSettings(webhook_secret=SecretStr("secret"), require_signature=False)
    with caplog.at_level(logging.WARNING, logger="ghappkit"):
        GitHubApp(settings=settings)
    assert "github_webhook_signature_verification_disabled" in caplog.text
