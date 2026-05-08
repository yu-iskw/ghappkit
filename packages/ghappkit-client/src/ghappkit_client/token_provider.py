"""Installation access token provider with in-memory caching."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx

from ghappkit_client.auth import create_app_jwt, load_private_key_pem
from ghappkit_client.errors import GitHubApiError, InstallationAuthError, redact_secrets
from ghappkit_client.models import InstallationToken
from ghappkit_client.transport import join_api_url, raise_for_github_status, send_request


def _parse_github_datetime(raw: str) -> datetime:
    """Parse GitHub ISO timestamps."""
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    dt = datetime.fromisoformat(raw)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


@dataclass
class TokenCacheEntry:
    token: InstallationToken
    cache_key: str


class InstallationTokenProvider:
    """Exchange GitHub App JWTs for installation tokens with caching."""

    def __init__(
        self,
        *,
        app_id: int,
        private_key_pem: str,
        api_base_url: str,
        http_client: httpx.AsyncClient,
        skew_seconds: int = 60,
        jwt_ttl_seconds: int = 600,
    ) -> None:
        self._app_id = app_id
        self._private_key_pem = private_key_pem
        self._api_base = api_base_url.rstrip("/")
        self._http = http_client
        self._skew = skew_seconds
        self._jwt_ttl = jwt_ttl_seconds
        self._cache: dict[str, TokenCacheEntry] = {}

    @classmethod
    def from_settings(
        cls,
        *,
        app_id: int,
        private_key_pem: str | None,
        private_key_path: str | None,
        api_base_url: str,
        http_client: httpx.AsyncClient,
    ) -> InstallationTokenProvider:
        pem = load_private_key_pem(
            secret_pem=private_key_pem,
            path=None if private_key_path is None else Path(private_key_path),
        )
        return cls(
            app_id=app_id,
            private_key_pem=pem,
            api_base_url=api_base_url,
            http_client=http_client,
        )

    def cache_key(
        self,
        installation_id: int,
        *,
        permissions: dict[str, str] | None,
        repository_ids: list[int] | None,
    ) -> str:
        payload = {
            "installation_id": installation_id,
            "permissions": permissions or {},
            "repository_ids": sorted(repository_ids or []),
        }
        blob = json.dumps(payload, sort_keys=True).encode()
        return hashlib.sha256(blob).hexdigest()

    async def get_token(
        self,
        installation_id: int,
        *,
        permissions: dict[str, str] | None = None,
        repository_ids: list[int] | None = None,
    ) -> InstallationToken:
        """Return a valid installation token, refreshing when near expiry."""
        key = self.cache_key(
            installation_id,
            permissions=permissions,
            repository_ids=repository_ids,
        )
        now = datetime.now(UTC)
        cached = self._cache.get(key)
        if cached is not None and cached.token.expires_at - timedelta(seconds=self._skew) > now:
            return cached.token

        token = await self._fetch_token(
            installation_id,
            permissions=permissions,
            repository_ids=repository_ids,
        )
        self._cache[key] = TokenCacheEntry(token=token, cache_key=key)
        return token

    async def _fetch_token(
        self,
        installation_id: int,
        *,
        permissions: dict[str, str] | None,
        repository_ids: list[int] | None,
    ) -> InstallationToken:
        jwt_token = create_app_jwt(
            self._app_id,
            self._private_key_pem,
            ttl_seconds=self._jwt_ttl,
        )
        url = join_api_url(self._api_base, f"/app/installations/{installation_id}/access_tokens")
        headers = {
            "Authorization": f"Bearer {jwt_token}",
            "Accept": "application/vnd.github+json",
        }
        body: dict[str, Any] | None = None
        if permissions is not None or repository_ids is not None:
            body = {}
            if permissions is not None:
                body["permissions"] = permissions
            if repository_ids is not None:
                body["repository_ids"] = repository_ids

        resp = await send_request(
            self._http,
            "POST",
            url,
            headers=headers,
            json=body,
        )
        try:
            raise_for_github_status(resp, operation="create_installation_token")
        except GitHubApiError as exc:
            raise InstallationAuthError(redact_secrets(str(exc))) from exc
        data = resp.json_data
        if not isinstance(data, dict):
            raise InstallationAuthError("installation token response malformed")
        raw_token = data.get("token")
        expires_raw = data.get("expires_at")
        if not isinstance(raw_token, str) or not isinstance(expires_raw, str):
            raise InstallationAuthError("installation token response missing fields")
        expires_at = _parse_github_datetime(expires_raw)
        return InstallationToken(token=raw_token, expires_at=expires_at)
