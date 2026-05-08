# Event card: `qualified-event-name`

> Fill one card per qualified event in scope. Every line below MUST be either filled with a fact citing an official URL OR marked `n/a` with a reason. Empty bullets are not allowed in a finalized report.

## Identity

- `X-GitHub-Event` value: `event-name`
- `payload.action` value (or "absent" for `push`-style events): `action` or `absent`
- Qualified name: `event[.action]`
- Source URL (per-event docs anchor): `https://docs.github.com/en/webhooks/webhook-events-and-payloads#event-name`

## Action enum (full set documented today)

- `<action-1>`
- `<action-2>`
- `<...>`

(Source must be the per-event anchor on the master event index page. Treat the list captured here as a snapshot; flag drift via the [`drift-detection.md`](../../references/drift-detection.md) checklist.)

## Payload top-level keys

- `<key-1>`
- `<key-2>`
- `<...>`
- Notes: any subkeys the receiver reads, for example `pull_request.head.sha`

## Common payload slots

- `installation` present: `yes|no|sometimes` -> source: `URL`
- `repository` present: `yes|no|sometimes` -> source: `URL`
- `sender` present: `yes|no|sometimes` -> source: `URL`

## `WebhookContext` mapping

- `delivery_id`: `X-GitHub-Delivery`
- `event`: `X-GitHub-Event`
- `action`: `payload.action` (or `None` for `push`)
- `installation_id`: `payload.installation.id` if present
- `repo`: `RepositoryRef.from(payload.repository)` if present
- `sender`: `SenderRef.from(payload.sender)` if present
- `payload`: `typed-model-name` if typed, else parsed `dict[str, Any]`
- `raw_payload`: parsed JSON dict (always populated)

## Helper-vs-raw decision

- Decision: `typed | raw | both`
- Rationale: explain why and cite missing fields, fast-changing payload, or upstream gaps
- v1 typed coverage: `yes|no` per [`typed-context-mapping.md`](../../references/typed-context-mapping.md).

## Errors and edge cases

- Special handling notes: for example, `pull_request.synchronize` fires on every head push and `check_run` actions can fire many times per suite
- Known payload variants: for example, `action='edited'` includes a `changes` object

## Verification (audit mode only)

- Existing handler exists: `yes|no|path`
- Handler signature uses typed model: `yes|no`
- Registry registration string: exactly the qualified name above
