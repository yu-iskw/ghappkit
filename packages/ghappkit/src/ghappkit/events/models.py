"""Pydantic models for typed webhook payloads (v1 coverage)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


class _WebhookModel(BaseModel):
    model_config = ConfigDict(extra="allow")


class Owner(_WebhookModel):
    login: str


class Repository(_WebhookModel):
    name: str
    owner: Owner | dict[str, Any]


class User(_WebhookModel):
    login: str


class Issue(_WebhookModel):
    number: int


class PullRequest(_WebhookModel):
    number: int


class Comment(_WebhookModel):
    id: int


class Installation(_WebhookModel):
    id: int


class CheckSuite(_WebhookModel):
    id: int


class CheckRun(_WebhookModel):
    id: int


class WorkflowRun(_WebhookModel):
    id: int


class IssuesPayload(_WebhookModel):
    issue: Issue
    repository: Repository
    sender: User | None = None


class IssueCommentPayload(_WebhookModel):
    issue: Issue
    comment: Comment
    repository: Repository
    sender: User | None = None


class PullRequestPayload(_WebhookModel):
    pull_request: PullRequest
    repository: Repository
    sender: User | None = None


class PushPayload(_WebhookModel):
    repository: Repository
    sender: User | None = None
    ref: str | None = None


class CheckSuiteEventPayload(_WebhookModel):
    check_suite: CheckSuite
    repository: Repository
    sender: User | None = None


class CheckRunEventPayload(_WebhookModel):
    check_run: CheckRun
    repository: Repository
    sender: User | None = None


class WorkflowRunPayload(_WebhookModel):
    workflow_run: WorkflowRun
    repository: Repository
    sender: User | None = None


class InstallationEventPayload(_WebhookModel):
    installation: Installation
    sender: User | None = None


class InstallationRepositoriesPayload(_WebhookModel):
    installation: Installation
    repository_selection: str | None = None


EVENT_MODEL_BY_NAME: dict[str, type[_WebhookModel]] = {
    "issues.opened": IssuesPayload,
    "issues.edited": IssuesPayload,
    "issues.closed": IssuesPayload,
    "issue_comment.created": IssueCommentPayload,
    "pull_request.opened": PullRequestPayload,
    "pull_request.synchronize": PullRequestPayload,
    "pull_request.closed": PullRequestPayload,
    "push": PushPayload,
    "check_suite.completed": CheckSuiteEventPayload,
    "check_run.completed": CheckRunEventPayload,
    "workflow_run.completed": WorkflowRunPayload,
    "installation.created": InstallationEventPayload,
    "installation.deleted": InstallationEventPayload,
    "installation_repositories.added": InstallationRepositoriesPayload,
}
