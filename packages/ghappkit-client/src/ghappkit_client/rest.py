"""REST helpers for common GitHub resources."""

from __future__ import annotations

import base64
from typing import Any
from urllib.parse import quote

import httpx

from ghappkit_client.transport import join_api_url, raise_for_github_status, send_request


class IssuesHelpers:
    """High-value issue helpers."""

    def __init__(
        self,
        *,
        http_client: httpx.AsyncClient,
        api_base_url: str,
        auth_header: str,
    ) -> None:
        self._http = http_client
        self._api_base = api_base_url.rstrip("/")
        self._auth_header = auth_header

    async def create_comment(
        self,
        *,
        owner: str,
        repo: str,
        issue_number: int,
        body: str,
    ) -> dict[str, Any]:
        """POST /repos/{owner}/{repo}/issues/{issue_number}/comments"""
        path = f"/repos/{owner}/{repo}/issues/{issue_number}/comments"
        url = join_api_url(self._api_base, path)
        headers = self._headers()
        resp = await send_request(
            self._http,
            "POST",
            url,
            headers=headers,
            json={"body": body},
        )
        raise_for_github_status(resp, operation="issues.create_comment")
        if not isinstance(resp.json_data, dict):
            raise ValueError("expected object JSON from comments API")
        return resp.json_data

    async def add_labels(
        self,
        *,
        owner: str,
        repo: str,
        issue_number: int,
        labels: list[str],
    ) -> list[dict[str, Any]]:
        """POST /repos/{owner}/{repo}/issues/{issue_number}/labels"""
        path = f"/repos/{owner}/{repo}/issues/{issue_number}/labels"
        url = join_api_url(self._api_base, path)
        headers = self._headers()
        resp = await send_request(
            self._http,
            "POST",
            url,
            headers=headers,
            json=labels,
        )
        raise_for_github_status(resp, operation="issues.add_labels")
        if not isinstance(resp.json_data, list):
            raise ValueError("expected array JSON from labels API")
        return resp.json_data

    async def get_repo_content_json(
        self,
        *,
        owner: str,
        repo: str,
        path: str,
        ref: str | None = None,
    ) -> dict[str, Any]:
        """GET /repos/{owner}/{repo}/contents/{path}"""
        segments = [segment for segment in path.strip("/").split("/") if segment]
        encoded = "/".join(quote(segment, safe="") for segment in segments)
        api_path = f"/repos/{owner}/{repo}/contents/{encoded}"
        url = join_api_url(self._api_base, api_path)
        headers = self._headers()
        params: dict[str, str] = {}
        if ref:
            params["ref"] = ref
        resp = await send_request(self._http, "GET", url, headers=headers, params=params or None)
        if resp.status_code == 404:
            raise FileNotFoundError(path)
        raise_for_github_status(resp, operation="repos.get_content")
        if not isinstance(resp.json_data, dict):
            raise ValueError("expected object JSON from contents API")
        return resp.json_data

    async def fetch_repo_text_file(
        self,
        *,
        owner: str,
        repo: str,
        path: str,
        ref: str | None = None,
    ) -> str | None:
        """Return decoded text for a file or None when missing/not a file."""
        try:
            data = await self.get_repo_content_json(owner=owner, repo=repo, path=path, ref=ref)
        except FileNotFoundError:
            return None
        if data.get("type") != "file":
            return None
        encoded = data.get("content")
        if not isinstance(encoded, str):
            return None
        decoded_bytes = base64.b64decode(encoded.replace("\n", ""))
        return decoded_bytes.decode("utf-8")

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": self._auth_header,
            "Accept": "application/vnd.github+json",
        }


class GitHubRestClient:
    """REST surface grouping."""

    def __init__(
        self,
        *,
        http_client: httpx.AsyncClient,
        api_base_url: str,
        auth_header: str,
    ) -> None:
        self.issues = IssuesHelpers(
            http_client=http_client,
            api_base_url=api_base_url,
            auth_header=auth_header,
        )
