# Event naming

Use this reference to derive the **qualified event name** that the ghappkit registry dispatches on. The rule below mirrors the RFC (`docs/rfcs/0001-octoflow-fastapi-github-app-framework.md`, §"Event naming") and the live shape of GitHub webhook payloads.

Primary source: [Webhook events and payloads](https://docs.github.com/en/webhooks/webhook-events-and-payloads).

## The rule

```python
def qualified_name(event: str, payload: dict) -> str:
    """Return the ghappkit-qualified event name.

    `event` is the value of the `X-GitHub-Event` header.
    `payload` is the parsed JSON body.
    """
    action = payload.get("action")
    return f"{event}.{action}" if action else event
```

- The event component comes from `X-GitHub-Event`.
- The action component comes from `payload["action"]` when present.
- An absent or `None` `action` yields the bare event name.
- Action values are always lower-case GitHub-defined strings; never normalize them.

## Worked examples

Each row maps a real GitHub delivery to its qualified name.

| `X-GitHub-Event`            | `payload.action` | Qualified name                    | Source                                                                                                                 |
| --------------------------- | ---------------- | --------------------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| `issues`                    | `opened`         | `issues.opened`                   | [issues](https://docs.github.com/en/webhooks/webhook-events-and-payloads#issues)                                       |
| `issues`                    | `closed`         | `issues.closed`                   | [issues](https://docs.github.com/en/webhooks/webhook-events-and-payloads#issues)                                       |
| `issue_comment`             | `created`        | `issue_comment.created`           | [issue_comment](https://docs.github.com/en/webhooks/webhook-events-and-payloads#issue_comment)                         |
| `pull_request`              | `opened`         | `pull_request.opened`             | [pull_request](https://docs.github.com/en/webhooks/webhook-events-and-payloads#pull_request)                           |
| `pull_request`              | `synchronize`    | `pull_request.synchronize`        | [pull_request](https://docs.github.com/en/webhooks/webhook-events-and-payloads#pull_request)                           |
| `pull_request`              | `closed`         | `pull_request.closed`             | [pull_request](https://docs.github.com/en/webhooks/webhook-events-and-payloads#pull_request)                           |
| `push`                      | (absent)         | `push`                            | [push](https://docs.github.com/en/webhooks/webhook-events-and-payloads#push)                                           |
| `check_suite`               | `completed`      | `check_suite.completed`           | [check_suite](https://docs.github.com/en/webhooks/webhook-events-and-payloads#check_suite)                             |
| `check_run`                 | `completed`      | `check_run.completed`             | [check_run](https://docs.github.com/en/webhooks/webhook-events-and-payloads#check_run)                                 |
| `workflow_run`              | `completed`      | `workflow_run.completed`          | [workflow_run](https://docs.github.com/en/webhooks/webhook-events-and-payloads#workflow_run)                           |
| `workflow_run`              | `requested`      | `workflow_run.requested`          | [workflow_run](https://docs.github.com/en/webhooks/webhook-events-and-payloads#workflow_run)                           |
| `installation`              | `created`        | `installation.created`            | [installation](https://docs.github.com/en/webhooks/webhook-events-and-payloads#installation)                           |
| `installation`              | `deleted`        | `installation.deleted`            | [installation](https://docs.github.com/en/webhooks/webhook-events-and-payloads#installation)                           |
| `installation_repositories` | `added`          | `installation_repositories.added` | [installation_repositories](https://docs.github.com/en/webhooks/webhook-events-and-payloads#installation_repositories) |

## Edge cases (must be handled explicitly)

1. **`push` has no `action`.** Qualified name is `push` (no dot, no suffix). Handlers registered as `push.*` MUST never match.
2. **`installation` vs `installation_repositories`.** They are distinct events. `installation.created` fires when the GitHub App is installed on a target; `installation_repositories.added` fires when repositories are added to an existing installation. Do not collapse them.
3. **`workflow_run.completed` vs `workflow_run.requested` vs `workflow_run.in_progress`.** All three actions exist; subscribers MUST register for the specific qualified name(s) they care about.
4. **Unknown actions on a known event.** When GitHub adds a new action (e.g. a new `pull_request` action), `qualified_name` still returns a well-formed string. The registry SHOULD route to a handler if registered, otherwise fall through to `on_any` and respond `202` per the RFC error table.
5. **Empty-string `action`.** Treat as absent. The dispatch table MUST NOT contain an entry like `issues.` (trailing dot).
6. **Casing.** Both event and action are always lower-case in GitHub deliveries. The registry SHOULD compare exactly; do not lower-case input from handler registrations either, to keep typos visible.

## Registration patterns

```python
@github.on("issues.opened")
async def on_issue_opened(ctx): ...

@github.on("push")
async def on_push(ctx): ...

@github.on_any()
async def audit(ctx):
    ctx.log.info("github_webhook_received", qualified_event=ctx.qualified_event)
```

The qualified-name string used at registration MUST equal the value produced by `qualified_name(event, payload)` for that delivery.

## Verification rule

When auditing or extending the registry with this skill:

- For every event listed in the requested scope, confirm the qualified name in the event card matches what `qualified_name` would return for a real payload.
- Confirm there is no implicit fallback that strips the action (e.g. dispatching `issues.opened` to a handler registered as just `issues`). Such fallbacks are a routing bug.
- Confirm `push` is registered without a trailing dot.
