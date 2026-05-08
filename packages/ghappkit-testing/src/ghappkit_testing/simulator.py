"""High-level webhook simulation helpers."""

from __future__ import annotations

import json
import uuid
from typing import Any

from ghappkit.app import GitHubApp
from ghappkit.parsing import split_qualified_event
from starlette.responses import Response


class GhappkitTestClient:
    """Utility wrapper around :class:`ghappkit.app.GitHubApp` for tests."""

    def __init__(self, app: GitHubApp) -> None:
        self._app = app

    async def deliver(
        self,
        qualified_event: str,
        payload: dict[str, Any],
        *,
        delivery_id: str | None = None,
    ) -> Response:
        """Dispatch a synthetic webhook through the app without signature checks."""
        event, _remainder = split_qualified_event(qualified_event)
        headers = {
            "X-GitHub-Event": event,
            "X-GitHub-Delivery": delivery_id or str(uuid.uuid4()),
            "X-GitHub-Hook-ID": "12345",
            "User-Agent": "GitHub-Hookshot/tests",
        }
        body = json.dumps(payload).encode("utf-8")
        return await self._app.dispatch_for_tests(headers=headers, body=body)


OctoflowTestClient = GhappkitTestClient
