"""Installation token provider tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import httpx
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from ghappkit_client.token_provider import InstallationTokenProvider


def _pem_pair() -> tuple[str, object]:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")
    return pem, key.public_key()


def test_token_cache_hit() -> None:
    pem, _pub = _pem_pair()
    expires = datetime.now(UTC) + timedelta(hours=1)
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        assert "/access_tokens" in str(request.url)
        body = {"token": "abc123", "expires_at": expires.replace(microsecond=0).isoformat()}
        return httpx.Response(201, json=body)

    transport = httpx.MockTransport(handler)
    client = httpx.AsyncClient(transport=transport)
    provider = InstallationTokenProvider(
        app_id=7,
        private_key_pem=pem,
        api_base_url="https://api.github.com",
        http_client=client,
        skew_seconds=120,
    )

    async def run() -> None:
        first = await provider.get_token(99)
        second = await provider.get_token(99)
        assert first.token == second.token
        assert calls["n"] == 1

    import asyncio

    asyncio.run(run())


def test_permission_specific_cache_keys() -> None:
    pem, _pub = _pem_pair()
    expires = datetime.now(UTC) + timedelta(hours=1)

    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        body = {"token": f"tok{calls['n']}", "expires_at": expires.isoformat()}
        return httpx.Response(201, json=body)

    transport = httpx.MockTransport(handler)
    client = httpx.AsyncClient(transport=transport)
    provider = InstallationTokenProvider(
        app_id=7,
        private_key_pem=pem,
        api_base_url="https://api.github.com",
        http_client=client,
    )

    async def run() -> None:
        a = await provider.get_token(5, permissions={"issues": "write"})
        b = await provider.get_token(5, permissions={"metadata": "read"})
        assert a.token != b.token
        assert calls["n"] == 2

    import asyncio

    asyncio.run(run())
