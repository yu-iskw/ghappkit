# Redelivery and idempotency

Use this reference to fill the **Redelivery & Idempotency Notes** section of [`assets/templates/webhook-contract-report.md`](../assets/templates/webhook-contract-report.md). Every claim has a citation that MUST be reproduced in the emitted report.

Primary sources:

- [Best practices for using webhooks](https://docs.github.com/en/webhooks/using-webhooks/best-practices-for-using-webhooks)
- [Handling failed webhook deliveries](https://docs.github.com/en/webhooks/using-webhooks/handling-failed-webhook-deliveries)
- [Redelivering webhooks](https://docs.github.com/en/webhooks/testing-and-troubleshooting-webhooks/redelivering-webhooks)

## Redelivery model (what GitHub actually does)

- **GitHub does NOT automatically redeliver failed webhook deliveries.** A non-2XX response or a slow response is recorded as failed and stays failed unless someone (a human via the UI, or your service via the redeliver API) explicitly requests redelivery. Source: [Handling failed webhook deliveries](https://docs.github.com/en/webhooks/using-webhooks/handling-failed-webhook-deliveries).
- Redelivery preserves the original `X-GitHub-Delivery` GUID. Source: [Best practices for using webhooks](https://docs.github.com/en/webhooks/using-webhooks/best-practices-for-using-webhooks) ("If you request a redelivery, the `X-GitHub-Delivery` header will be the same as in the original delivery.").
- Past deliveries are inspectable through the UI and APIs for a limited window (the docs index uses 7 days in some places and 3 days in body copy; treat the **shorter** value as the contractual minimum and confirm against the live page when planning operational tooling). Source: [Redelivering webhooks](https://docs.github.com/en/webhooks/testing-and-troubleshooting-webhooks/redelivering-webhooks).

## Idempotency model (what the receiver must do)

- The canonical replay key is `X-GitHub-Delivery`. Persist it to recognize redeliveries.
- The idempotency boundary is the tuple `(delivery_id, qualified_event)`. Two deliveries can share `delivery_id` only across redelivery; never across distinct events.
- Handlers MUST be safe under at-least-once semantics: a redelivery of an already-processed `delivery_id` MUST NOT cause double side effects. Implement either:
  - A "seen deliveries" store that short-circuits handlers on a hit; or
  - Functionally idempotent operations (e.g. `PUT`-style state mutation, dedupe-keyed downstream writes).
- Persist seen deliveries for **at least one redelivery window** (use the conservative bound from the source above; if unsure, default to seven days).

## Acknowledgment vs handler retries

- The receiver MUST respond `2XX` within the GitHub deadline (10 seconds; see [`transport-contract.md`](transport-contract.md)). Retries the receiver performs internally are an _executor_ concern, NOT GitHub's redelivery.
- Failing inside a handler AFTER the receiver has already returned `202` does NOT cause GitHub to redeliver. The executor must surface failures to the application's `on_error` hook (per the RFC error taxonomy) and decide whether to retry, dead-letter, or escalate.
- Returning `5xx` because a handler scheduling failed is the only signal GitHub sees that retry might help; even then, only a human-triggered or API-triggered redelivery will actually re-send the payload.

## Redeliver API endpoints (for reactive recovery)

When the application detects a missed or failed delivery, it can request redelivery through the GitHub REST API. Cite these endpoints whenever the report touches recovery automation.

| Subscription scope | Endpoint                                                                       | Source                                                                                                                               |
| ------------------ | ------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------ |
| Repository webhook | `POST /repos/{owner}/{repo}/hooks/{hook_id}/deliveries/{delivery_id}/attempts` | [Repo deliveries: redeliver](https://docs.github.com/en/rest/webhooks/repo-deliveries#redeliver-a-delivery-for-a-repository-webhook) |
| Organization hook  | `POST /orgs/{org}/hooks/{hook_id}/deliveries/{delivery_id}/attempts`           | [Org webhooks: redeliver](https://docs.github.com/en/rest/orgs/webhooks#redeliver-a-delivery-for-an-organization-webhook)            |
| GitHub App         | `POST /app/hook/deliveries/{delivery_id}/attempts`                             | [App webhooks: redeliver](https://docs.github.com/en/rest/apps/webhooks#redeliver-a-delivery-for-an-app-webhook)                     |

All three return `202 Accepted` and produce a fresh delivery attempt with the same `delivery_id`.

## Replay protection

- Treat any second appearance of a `delivery_id` within the persistence window as a redelivery (intended or accidental).
- Treat a `delivery_id` reuse with a different payload signature as a forgery attempt and refuse it.
- Never rely on payload equality alone: an attacker that captured a real delivery cannot regenerate `X-Hub-Signature-256` without the secret, but the secret-less replay attack succeeds if the receiver does not verify the signature on every delivery (including redeliveries).

## Verification rule

When auditing receiver code with this skill, confirm the code:

- Persists `X-GitHub-Delivery` for at least the redelivery window.
- Short-circuits handlers when a delivery has already been processed.
- Distinguishes redelivery from replay-attack reuse via signature verification.
- Does NOT use `5xx` responses as a generic retry signal (GitHub does not auto-retry).
- Routes handler-time failures to `on_error`, not to a HTTP-level error.
