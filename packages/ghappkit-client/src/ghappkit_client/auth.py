"""GitHub App JWT creation."""

from __future__ import annotations

import time
from pathlib import Path

import jwt


def load_private_key_pem(*, secret_pem: str | None, path: Path | None) -> str:
    """Load PEM-encoded RSA private key from inline secret or file."""
    if secret_pem is not None and secret_pem.strip():
        return secret_pem
    if path is not None:
        return path.read_text(encoding="utf-8")
    raise ValueError("private_key or private_key_path is required for JWT auth")


def create_app_jwt(
    app_id: int,
    private_key_pem: str,
    *,
    ttl_seconds: int = 600,
    clock_skew_seconds: int = 60,
) -> str:
    """Create a GitHub App JWT (RS256).

    GitHub recommends keeping TTL short; default is 10 minutes.
    """
    now = int(time.time())
    payload = {
        "iat": now - clock_skew_seconds,
        "exp": now + ttl_seconds,
        "iss": str(app_id),
    }
    return jwt.encode(payload, private_key_pem, algorithm="RS256")
