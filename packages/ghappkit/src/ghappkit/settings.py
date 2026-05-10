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
    webhook_ack_before_dispatch: bool = Field(
        default=False,
        description=(
            "If True and handlers run via FastAPIBackgroundExecutor, respond with 202 "
            "immediately after signature verification; JSON parsing and handler execution "
            "run in a background task. Invalid JSON is logged with delivery metadata but "
            "GitHub receives 202 (no HTTP 400). Ignored with InlineExecutor / NoopExecutor. "
            "When handler setup fails after 202, logs include failure_phase and error_type. "
            "Contrast: with InlineExecutor (or ack disabled), invalid JSON is rejected with "
            "HTTP 400 before any 202 is sent."
        ),
    )
    config_file: str = Field(
        default=".github/ghappkit.yml",
        description="Default repository-relative configuration path",
    )

    @classmethod
    def from_env(cls, **overrides: Any) -> GitHubAppSettings:
        """Load settings from environment (and optional overrides)."""
        return cls(**overrides)
