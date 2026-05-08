# Typed context mapping

Use this reference to map a webhook delivery onto the ghappkit `WebhookContext` shape (`docs/rfcs/0001-octoflow-fastapi-github-app-framework.md`, §"Typed context") and to decide whether each event uses a typed payload model or the raw-dict fallback.

## RFC v1 typed event coverage

The RFC §"v1 typed event coverage" table is the source of truth for which events MUST ship a typed payload model in v1. Mirror that decision here. Any event NOT in this list MUST go through the raw-dict context.

| Qualified event                      | Typed model required (v1) | Raw-dict fallback OK | Per-event source                                                                                                       |
| ------------------------------------ | ------------------------- | -------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| `issues.opened`                      | yes                       | no                   | [issues](https://docs.github.com/en/webhooks/webhook-events-and-payloads#issues)                                       |
| `issues.edited`                      | yes                       | no                   | [issues](https://docs.github.com/en/webhooks/webhook-events-and-payloads#issues)                                       |
| `issues.closed`                      | yes                       | no                   | [issues](https://docs.github.com/en/webhooks/webhook-events-and-payloads#issues)                                       |
| `issue_comment.created`              | yes                       | no                   | [issue_comment](https://docs.github.com/en/webhooks/webhook-events-and-payloads#issue_comment)                         |
| `pull_request.opened`                | yes                       | no                   | [pull_request](https://docs.github.com/en/webhooks/webhook-events-and-payloads#pull_request)                           |
| `pull_request.synchronize`           | yes                       | no                   | [pull_request](https://docs.github.com/en/webhooks/webhook-events-and-payloads#pull_request)                           |
| `pull_request.closed`                | yes                       | no                   | [pull_request](https://docs.github.com/en/webhooks/webhook-events-and-payloads#pull_request)                           |
| `push`                               | yes                       | no                   | [push](https://docs.github.com/en/webhooks/webhook-events-and-payloads#push)                                           |
| `check_suite.completed`              | yes                       | no                   | [check_suite](https://docs.github.com/en/webhooks/webhook-events-and-payloads#check_suite)                             |
| `check_run.completed`                | yes                       | no                   | [check_run](https://docs.github.com/en/webhooks/webhook-events-and-payloads#check_run)                                 |
| `workflow_run.completed`             | yes                       | no                   | [workflow_run](https://docs.github.com/en/webhooks/webhook-events-and-payloads#workflow_run)                           |
| `installation.created`               | yes                       | no                   | [installation](https://docs.github.com/en/webhooks/webhook-events-and-payloads#installation)                           |
| `installation.deleted`               | yes                       | no                   | [installation](https://docs.github.com/en/webhooks/webhook-events-and-payloads#installation)                           |
| `installation_repositories.added`    | yes                       | no                   | [installation_repositories](https://docs.github.com/en/webhooks/webhook-events-and-payloads#installation_repositories) |
| **anything else (incl. new events)** | no                        | yes (raw `dict`)     | [Webhook events and payloads](https://docs.github.com/en/webhooks/webhook-events-and-payloads)                         |

The "anything else" row matters: ghappkit MUST keep raw delivery handling working for events GitHub ships that are not yet in this table. See the RFC `WebhookContext[dict[str, Any]]` example.

## `WebhookContext` field mapping

For every event card emitted, fill in the table below. The left column is the dataclass field; the right column is its source on the wire.

| `WebhookContext` field | Source                                                                                                            |
| ---------------------- | ----------------------------------------------------------------------------------------------------------------- |
| `delivery_id`          | `X-GitHub-Delivery` header.                                                                                       |
| `event`                | `X-GitHub-Event` header.                                                                                          |
| `action`               | `payload.get("action")`. `None` for `push` and any other event without an action.                                 |
| `payload`              | Pydantic-parsed payload model when typed, else the parsed `dict[str, Any]`.                                       |
| `raw_payload`          | The parsed JSON dict (always populated, even when `payload` is a typed model).                                    |
| `installation_id`      | `payload["installation"]["id"]` when present; absent for non-app deliveries (rare for ghappkit).                  |
| `repo`                 | `RepositoryRef.from(payload["repository"])` when present; absent for `installation*` events without repo context. |
| `sender`               | `SenderRef.from(payload["sender"])` when present; absent for `push` is rare but possible on system events.        |
| `github`               | Installation-scoped `GitHubClient` from the auth/token manager (RFC §"Authentication and token management").      |
| `log`                  | `BoundLogger` already bound to `delivery_id` and `qualified_event`.                                               |
| `request`              | The raw FastAPI `Request` (or `None` when invoked via `receive(...)` in tests).                                   |

## Helper-vs-raw decision rubric

For each requested event in the report, choose ONE of the three outcomes.

1. **Typed.** The event is in the v1 typed coverage table AND a Pydantic model exists (or will exist) in `ghappkit.events`. Emit the event card with the typed model name.
2. **Raw.** The event is NOT in the v1 typed coverage table. Use `WebhookContext[dict[str, Any]]`. The handler signature MUST take a raw dict; do not invent a partial typed shim.
3. **Both.** The event has a typed model but the implementation also wants raw access (for example to read fields not yet covered by the model). Use the typed `payload` and reach into `raw_payload` for the rest.

Record the choice and the rationale on every event card. "It feels right" is not a rationale; cite a missing field, an unmaintained section of GitHub docs, or a known fast-changing payload.

## Mapping verification

When auditing existing receiver/registry code with this skill:

- For every typed event in the table, confirm `ghappkit.events` exposes a model and the registry uses it.
- For events NOT in the table that the project subscribes to, confirm they dispatch to a `WebhookContext[dict[str, Any]]` handler.
- For each WebhookContext field, confirm the source matches the table above. Discrepancies (e.g. `installation_id` derived from a header instead of `payload["installation"]["id"]`) are routing bugs.
