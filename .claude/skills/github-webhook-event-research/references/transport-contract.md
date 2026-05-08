# Transport contract

Use this reference to fill the **Transport Contract Sheet** section of [`assets/templates/webhook-contract-report.md`](../assets/templates/webhook-contract-report.md). Every claim below has a citation that MUST be reproduced in the emitted report.

## Required delivery headers

The headers below arrive on every GitHub webhook POST. Source: [Delivery headers](https://docs.github.com/en/webhooks/webhook-events-and-payloads#delivery-headers).

| Header                                   | Meaning                                                                                             | Notes                                                                                                                                        |
| ---------------------------------------- | --------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------- |
| `X-GitHub-Event`                         | Name of the event that triggered the delivery (e.g. `issues`, `pull_request`, `push`).              | Used as the first half of the qualified event name; see [`event-naming.md`](event-naming.md).                                                |
| `X-GitHub-Delivery`                      | Globally unique GUID for this delivery.                                                             | Canonical replay/idempotency key; see [`redelivery-and-idempotency.md`](redelivery-and-idempotency.md). Redelivery preserves the same value. |
| `X-GitHub-Hook-ID`                       | Identifier of the webhook configuration that produced the delivery.                                 | Useful for binding logs to a specific subscription.                                                                                          |
| `X-GitHub-Hook-Installation-Target-Type` | Resource type the webhook is attached to (for example `repository`, `organization`, `integration`). | Required for correctly disambiguating GitHub App, repo, and org webhooks in audit logs.                                                      |
| `X-GitHub-Hook-Installation-Target-ID`   | Identifier of the resource above.                                                                   |                                                                                                                                              |
| `X-Hub-Signature-256`                    | `sha256=` followed by the HMAC-SHA256 hex digest of the raw request body using the webhook secret.  | See [`signature-verification.md`](signature-verification.md). Reject deliveries when the secret is configured and the header is missing.     |
| `X-Hub-Signature`                        | Legacy SHA-1 signature.                                                                             | Do NOT verify against this in new code; SHA-1 is deprecated. Recorded for awareness only.                                                    |
| `User-Agent`                             | Always begins with `GitHub-Hookshot/`.                                                              | Useful for log filtering; do NOT use as an authentication signal.                                                                            |
| `Content-Type`                           | `application/json` (default) or `application/x-www-form-urlencoded` (legacy form-encoded option).   | Ghappkit MUST configure JSON; form-encoded mode breaks the raw-body signature contract.                                                      |

## Body and content type

Source: [Webhook events and payloads](https://docs.github.com/en/webhooks/webhook-events-and-payloads).

- Default `Content-Type` is `application/json`. The body is the JSON payload as-sent.
- Payloads are **capped at 25 MB**. Larger events are dropped by GitHub and never delivered. The receiver MUST NOT assume retries occur for size-rejected events.
- The body is the exact byte sequence used to compute `X-Hub-Signature-256`. Any re-encoding before verification breaks the signature.

## Raw-body rule (security-critical)

The receiver MUST capture the raw request bytes BEFORE any framework parses or transforms them. In FastAPI/Starlette this is `await request.body()`.

```python
from fastapi import Request
import json

async def handle(request: Request) -> Response:
    raw = await request.body()  # MUST come first
    sig_ok = verify_signature(secret, raw, request.headers.get("X-Hub-Signature-256"))
    if not sig_ok:
        raise WebhookSignatureError()  # -> HTTP 401
    payload = json.loads(raw)  # parse only AFTER verification
    ...
```

Failure modes if the rule is violated:

- Re-serializing JSON (e.g. via Pydantic) and hashing the re-serialized bytes will produce a different digest than GitHub's, so legitimate deliveries fail signature verification.
- Hashing only the parsed dict (after key reordering) likewise mismatches.
- Decoding to `str` and re-encoding via `.encode("utf-8")` succeeds for ASCII payloads but silently breaks for non-ASCII characters in actor logins, branch names, or commit messages.

## Acknowledgment timing

Source: [Handling webhook deliveries](https://docs.github.com/en/webhooks/using-webhooks/handling-webhook-deliveries) and [Best practices for using webhooks](https://docs.github.com/en/webhooks/using-webhooks/best-practices-for-using-webhooks).

- The receiver SHOULD respond with a 2XX status within **10 seconds**. GitHub treats slower responses as failures.
- The recommended response is **`202 Accepted`** when the handler is enqueued for asynchronous processing. Synchronous work must finish within the 10-second window.
- `200 OK` is also accepted. `204 No Content` is fine when no body is returned.

## Headers to record in logs

For every accepted delivery, ghappkit logs MUST bind:

- `event` (from `X-GitHub-Event`).
- `qualified_event` (derived per [`event-naming.md`](event-naming.md)).
- `delivery_id` (from `X-GitHub-Delivery`).
- `hook_id` (from `X-GitHub-Hook-ID`).
- `installation_target_type` and `installation_target_id` (from the `X-GitHub-Hook-Installation-Target-*` headers).

Do not log the request body, signature header, or webhook secret. Source: ghappkit RFC redaction policy ([`docs/rfcs/0001-octoflow-fastapi-github-app-framework.md`](../../../../docs/rfcs/0001-octoflow-fastapi-github-app-framework.md)).
