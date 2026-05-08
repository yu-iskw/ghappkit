"""Application settings for ghappkit."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import AnyHttpUrl, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class GitHubAppSettings(BaseSettings):
    """Environment-driven configuration for GitHub Apps."""

    model_config = SettingsConfigDict(
        env_prefix="GITHUB_APP_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_id: int = Field(description="GitHub App ID")
    webhook_secret: SecretStr = Field(description="Webhook secret for HMAC verification")
    private_key: SecretStr | None = Field(
        default=None,
        description="PEM-encoded RSA private key",
    )
    private_key_path: Path | None = Field(
        default=None,
        description="Filesystem path to PEM-encoded RSA private key",
    )
    github_api_url: AnyHttpUrl = Field(default=AnyHttpUrl("https://api.github.com"))
    github_web_url: AnyHttpUrl = Field(default=AnyHttpUrl("https://github.com"))
    webhook_path: str = Field(default="/webhooks")
    require_signature: bool = Field(default=True)
    config_file: str = Field(
        default=".github/ghappkit.yml",
        description="Default repository-relative configuration path",
    )

    @classmethod
    def from_env(cls, **overrides: Any) -> GitHubAppSettings:
        """Load settings from environment (and optional overrides)."""
        return cls(**overrides)
