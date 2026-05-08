# Webhook Contract Report

> Output template for `github-webhook-event-research`. Fill every section. Every claim MUST cite an official URL per [`references/source-priority.md`](../../references/source-priority.md). Leave no placeholder bullets in a finalized report.

## Scope

- Events in scope: `<list of qualified event names>`
- Implementation target: `<file or module under review, or "new design">`
- Date: `<YYYY-MM-DD>`

## 1. Transport Contract Sheet

- Headers covered: `X-GitHub-Event`, `X-GitHub-Delivery`, `X-GitHub-Hook-ID`, `X-GitHub-Hook-Installation-Target-Type`, `X-GitHub-Hook-Installation-Target-ID`, `X-Hub-Signature-256`, `X-Hub-Signature` (legacy, advisory), `User-Agent`, `Content-Type`.
- Raw-body rule confirmed: `<yes|no>` (capture body bytes BEFORE any parser).
- Acknowledgment SLA: respond `2XX` within 10 seconds; preferred status `202 Accepted`.
- Logged fields: `event`, `qualified_event`, `delivery_id`, `hook_id`, `installation_target_type`, `installation_target_id`.
- Source URLs:
  - <https://docs.github.com/en/webhooks/webhook-events-and-payloads#delivery-headers>
  - <https://docs.github.com/en/webhooks/using-webhooks/handling-webhook-deliveries>
  - <https://docs.github.com/en/webhooks/using-webhooks/best-practices-for-using-webhooks>

## 2. Signature Verification Procedure

- Algorithm: HMAC-SHA256 of the raw request body using the configured webhook secret.
- Header format: `sha256=<hex digest>`. Reject any other prefix.
- Constant-time compare: `<yes|no>` (use `hmac.compare_digest`).
- Rotation policy: accept old AND new secret during one redelivery window; drop the old secret only after the window.
- Pitfall checklist passed: `<count> / 10` (see [`references/signature-verification.md`](../../references/signature-verification.md)).
- HTTP response mapping:
  - Missing/invalid signature -> `WebhookSignatureError` -> `401`
  - Missing `X-GitHub-Event` -> `WebhookHeaderError` -> `400`
  - Body not valid JSON -> `PayloadParseError` -> `400`
  - Verified delivery -> `202`
- Source URLs:
  - <https://docs.github.com/en/webhooks/using-webhooks/validating-webhook-deliveries>
  - <https://docs.github.com/en/webhooks/using-webhooks/validating-webhook-deliveries#testing-the-webhook-payload-validation>

## 3. Event Card(s)

> One filled instance of [`event-card.md`](event-card.md) per qualified event in scope.

`<insert event cards here>`

## 4. Redelivery & Idempotency Notes

- Replay key: `X-GitHub-Delivery` (preserved across redeliveries).
- Idempotency boundary: `(delivery_id, qualified_event)`.
- Persistence window: at least one GitHub redelivery window (default seven days unless the docs page declares a shorter value).
- Acknowledgment-vs-retry split: receiver returns `2XX` within 10s; handler-level retries are executor-internal and never trigger GitHub redelivery.
- Recovery API: `POST .../deliveries/{delivery_id}/attempts` (repo, org, or app subscription scope).
- Source URLs:
  - <https://docs.github.com/en/webhooks/using-webhooks/best-practices-for-using-webhooks>
  - <https://docs.github.com/en/webhooks/using-webhooks/handling-failed-webhook-deliveries>
  - <https://docs.github.com/en/webhooks/testing-and-troubleshooting-webhooks/redelivering-webhooks>
  - <https://docs.github.com/en/rest/webhooks/repo-deliveries#redeliver-a-delivery-for-a-repository-webhook>

## 5. Signed Test Vectors

> One filled instance of [`signed-test-vector.md`](signed-test-vector.md) per scenario. The five canonical scenarios are required; add more when the implementation needs them.

- success
- invalid-signature
- missing-header
- unknown-action
- push-no-action

`<insert signed test vectors here>`

## 6. Drift Checklist Result

- Date checked: `<YYYY-MM-DD>`
- Triggers fired: `<none | list>` (see [`references/drift-detection.md`](../../references/drift-detection.md)).
- Sections re-run: `<list or "n/a">`
- Deltas applied: `<list or "no change required">`

## 7. Open Questions / Followups

- `<list any unresolved items, e.g. an event GitHub documents inconsistently>`
