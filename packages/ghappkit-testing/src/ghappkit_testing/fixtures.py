"""Synthetic webhook payloads for fixtures."""

from __future__ import annotations

import copy
from typing import Any


def _repo(owner: str = "acme", name: str = "demo") -> dict[str, Any]:
    return {
        "id": 1,
        "name": name,
        "full_name": f"{owner}/{name}",
        "owner": {"login": owner},
        "default_branch": "main",
    }


def _installation(inst_id: int = 12345) -> dict[str, Any]:
    return {"id": inst_id}


def _sender(login: str = "octocat") -> dict[str, Any]:
    return {"login": login}


def issues_opened() -> dict[str, Any]:
    return {
        "action": "opened",
        "issue": {"number": 1},
        "repository": _repo(),
        "installation": _installation(),
        "sender": _sender(),
    }


def issues_edited() -> dict[str, Any]:
    data = issues_opened()
    data["action"] = "edited"
    return data


def issues_closed() -> dict[str, Any]:
    data = issues_opened()
    data["action"] = "closed"
    return data


def issue_comment_created() -> dict[str, Any]:
    return {
        "action": "created",
        "issue": {"number": 1},
        "comment": {"id": 42},
        "repository": _repo(),
        "installation": _installation(),
        "sender": _sender(),
    }


def pull_request_opened() -> dict[str, Any]:
    return {
        "action": "opened",
        "pull_request": {"number": 2},
        "repository": _repo(),
        "installation": _installation(),
        "sender": _sender(),
    }


def pull_request_synchronize() -> dict[str, Any]:
    data = pull_request_opened()
    data["action"] = "synchronize"
    return data


def pull_request_closed() -> dict[str, Any]:
    data = pull_request_opened()
    data["action"] = "closed"
    return data


def push_event() -> dict[str, Any]:
    return {
        "ref": "refs/heads/main",
        "repository": _repo(),
        "installation": _installation(),
        "sender": _sender(),
    }


def check_suite_completed() -> dict[str, Any]:
    return {
        "action": "completed",
        "check_suite": {"id": 99},
        "repository": _repo(),
        "installation": _installation(),
        "sender": _sender(),
    }


def check_run_completed() -> dict[str, Any]:
    return {
        "action": "completed",
        "check_run": {"id": 101},
        "repository": _repo(),
        "installation": _installation(),
        "sender": _sender(),
    }


def workflow_run_completed() -> dict[str, Any]:
    return {
        "action": "completed",
        "workflow_run": {"id": 555},
        "repository": _repo(),
        "installation": _installation(),
        "sender": _sender(),
    }


def installation_created() -> dict[str, Any]:
    return {
        "action": "created",
        "installation": _installation(),
        "sender": _sender(),
    }


def installation_deleted() -> dict[str, Any]:
    data = installation_created()
    data["action"] = "deleted"
    return data


def installation_repositories_added() -> dict[str, Any]:
    return {
        "action": "added",
        "installation": _installation(),
        "repository_selection": "selected",
        "sender": _sender(),
    }


FIXTURES: dict[str, dict[str, Any]] = {
    "issues.opened": issues_opened(),
    "issues.edited": issues_edited(),
    "issues.closed": issues_closed(),
    "issue_comment.created": issue_comment_created(),
    "pull_request.opened": pull_request_opened(),
    "pull_request.synchronize": pull_request_synchronize(),
    "pull_request.closed": pull_request_closed(),
    "push": push_event(),
    "check_suite.completed": check_suite_completed(),
    "check_run.completed": check_run_completed(),
    "workflow_run.completed": workflow_run_completed(),
    "installation.created": installation_created(),
    "installation.deleted": installation_deleted(),
    "installation_repositories.added": installation_repositories_added(),
}


def payload_fixture(qualified_event: str) -> dict[str, Any]:
    """Return a deep copy of the synthetic payload for a qualified event."""
    base = FIXTURES.get(qualified_event)
    if base is None:
        raise KeyError(f"unknown fixture for {qualified_event}")
    return copy.deepcopy(base)
