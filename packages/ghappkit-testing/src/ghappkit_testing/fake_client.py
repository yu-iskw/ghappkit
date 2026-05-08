"""Lightweight fake GitHub client for behavioral tests."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any

from ghappkit_client.models import GitHubResponse


@dataclass
class ExpectedCall:
    method: str
    path: str
    json: Any | None = None


class FakeIssuesApi:
    """Records REST calls aimed at issue endpoints."""

    def __init__(self, owner: FakeGitHubClient) -> None:
        self._owner = owner

    async def create_comment(
        self,
        *,
        owner: str,
        repo: str,
        issue_number: int,
        body: str,
    ) -> dict[str, Any]:
        self._owner.record(
            "POST",
            f"/repos/{owner}/{repo}/issues/{issue_number}/comments",
            json={"body": body},
        )
        return {"id": 1}

    async def add_labels(
        self,
        *,
        owner: str,
        repo: str,
        issue_number: int,
        labels: list[str],
    ) -> list[dict[str, Any]]:
        self._owner.record(
            "POST",
            f"/repos/{owner}/{repo}/issues/{issue_number}/labels",
            json=labels,
        )
        return [{"name": label} for label in labels]

    async def fetch_repo_text_file(
        self,
        *,
        owner: str,
        repo: str,
        path: str,
        ref: str | None = None,
    ) -> str | None:
        self._owner.record("GET", f"/repos/{owner}/{repo}/contents/{path}", json={"ref": ref})
        response = self._owner.next_response()
        if isinstance(response, str):
            return response
        return None


class FakeGraphQL:
    def __init__(self, owner: FakeGitHubClient) -> None:
        self._owner = owner

    async def execute(
        self, query: str, *, variables: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        self._owner.record("POST", "/graphql", json={"query": query, "variables": variables})
        return {}


class FakeGitHubClient:
    """State-based fake that avoids monkeypatching."""

    def __init__(self) -> None:
        self.rest = SimpleNamespace(issues=FakeIssuesApi(self))
        self.graphql = FakeGraphQL(self)
        self.calls: list[ExpectedCall] = []
        self._responses: deque[Any] = deque()

    def record(self, method: str, path: str, json: Any | None) -> None:
        self.calls.append(ExpectedCall(method=method, path=path, json=json))

    def queue_response(self, value: Any) -> None:
        """Provide the next response for simple helpers like config downloads."""
        self._responses.append(value)

    def next_response(self) -> Any:
        if not self._responses:
            return None
        return self._responses.popleft()

    async def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: Any | None = None,
        headers: dict[str, str] | None = None,
    ) -> GitHubResponse:
        self.record(method.upper(), path, json=json)
        return GitHubResponse(status_code=200, headers={}, json_data={"ok": True}, text="{}")

    def assert_called(self) -> None:
        if not self.calls:
            raise AssertionError("expected at least one GitHub call")

    def assert_no_calls(self) -> None:
        if self.calls:
            raise AssertionError(f"expected no calls, got {self.calls}")
