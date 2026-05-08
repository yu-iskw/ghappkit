"""Tests for ``ghappkit_client.errors``."""

from __future__ import annotations

from ghappkit_client.errors import redact_secrets


def test_redact_secrets_removes_bearer_value_without_prefix_leak() -> None:
    raw = "Authorization: Bearer extremely_sensitive_material_here"
    out = redact_secrets(raw)
    assert "extremely_sensitive" not in out
    assert "Bearer extr" not in out
    assert out.count("[REDACTED]") >= 1


def test_redact_secrets_removes_github_pat_substrings() -> None:
    raw = "log ghp_abcdefghijklmnopqrst"
    out = redact_secrets(raw)
    assert "ghp_" not in out


def test_redact_secrets_removes_json_token_values() -> None:
    raw = '{"token":"secret_value_xyz","ok":true}'
    out = redact_secrets(raw)
    assert "secret_value" not in out
