"""Tests for repository contents helpers."""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

import pytest

from ghappkit_client.errors import RepositoryFileDecodeError
from ghappkit_client.rest import IssuesHelpers


def test_fetch_repo_text_file_raises_on_invalid_base64(monkeypatch: pytest.MonkeyPatch) -> None:
    helper = IssuesHelpers(
        http_client=MagicMock(),
        api_base_url="https://api.github.com",
        auth_header="Bearer x",
    )

    async def fake_get_repo_content_json(
        *,
        owner: str,
        repo: str,
        path: str,
        ref: str | None = None,
    ) -> dict[str, object]:
        del owner, repo, path, ref
        return {"type": "file", "content": "!!!not-valid-base64!!!"}

    monkeypatch.setattr(helper, "get_repo_content_json", fake_get_repo_content_json)

    async def run() -> None:
        with pytest.raises(RepositoryFileDecodeError, match="base64"):
            await helper.fetch_repo_text_file(owner="o", repo="r", path=".github/x.yml")

    asyncio.run(run())
