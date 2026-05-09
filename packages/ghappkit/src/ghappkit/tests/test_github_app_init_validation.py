"""Construction-time validation for :class:`GitHubApp`."""

from __future__ import annotations

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from pydantic import SecretStr

from ghappkit.app import GitHubApp
from ghappkit.settings import GitHubAppSettings


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
