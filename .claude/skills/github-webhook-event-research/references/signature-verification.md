# Signature verification

Use this reference to fill the **Signature Verification Procedure** section of [`assets/templates/webhook-contract-report.md`](../assets/templates/webhook-contract-report.md). Every claim has a citation that MUST be reproduced in the emitted report.

Primary source: [Validating webhook deliveries](https://docs.github.com/en/webhooks/using-webhooks/validating-webhook-deliveries).

## Algorithm

GitHub computes `X-Hub-Signature-256` as:

```text
"sha256=" + HMAC_SHA256(key=webhook_secret, msg=raw_request_body).hex()
```

- The hash is over **raw request bytes**, including any whitespace.
- The header value always begins with the literal prefix `sha256=`.
- The webhook secret is the value configured on the webhook (per repo, per org, or per GitHub App).

Source: [Validating webhook deliveries](https://docs.github.com/en/webhooks/using-webhooks/validating-webhook-deliveries) ("The hash signature always starts with `sha256=`.").

## Reference Python procedure

```python
import hmac
import hashlib

class WebhookSignatureError(Exception):
    """Raised on missing or invalid X-Hub-Signature-256."""


def verify_signature(secret: bytes, body: bytes, header: str | None) -> bool:
    """Return True iff `header` is a valid sha256 HMAC of `body` under `secret`.

    `secret` and `body` MUST be bytes that were not transformed in any way
    after arrival on the wire.
    """
    if not header or not header.startswith("sha256="):
        return False
    expected = "sha256=" + hmac.new(secret, body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, header)
```

Source for `compare_digest` (constant-time comparison): GitHub explicitly requires it; see [Validating webhook deliveries](https://docs.github.com/en/webhooks/using-webhooks/validating-webhook-deliveries) ("Never use a plain `==` operator… use … 'constant time' string comparison…").

## Pitfall checklist

The receiver implementation MUST be checked against every item below. A failure on any item is a security defect.

1. **Verify before parsing.** Do not call `json.loads(...)` or any model parser before the signature check; the parsed dict cannot be re-serialized identically.
2. **Use raw bytes.** Capture the body via the framework's raw-body API (e.g. `await request.body()` in FastAPI/Starlette). Never hash a decoded `str`.
3. **Constant-time compare.** Use `hmac.compare_digest` (Python) or its language equivalent. A plain `==` leaks signature prefixes through timing.
4. **Reject missing headers.** When a webhook secret is configured but `X-Hub-Signature-256` is absent or empty, raise `WebhookSignatureError` -> HTTP 401.
5. **Reject the legacy `X-Hub-Signature` (SHA-1) header.** Do not accept it as a fallback; SHA-1 is deprecated and using it weakens the contract.
6. **Validate the `sha256=` prefix.** A header like `md5=...` or a bare hex digest MUST fail.
7. **Use bytes for the secret.** Pass `secret.encode("utf-8")` once when loading the secret; do not re-encode per request.
8. **Rotate without downtime.** During rotation, accept either the old or new secret. Drop the old one only after one redelivery window has elapsed (see [`redelivery-and-idempotency.md`](redelivery-and-idempotency.md)).
9. **Do not log the signature header or the secret.** Both are sensitive. The signature header is enough for offline forgery attempts when paired with a captured body.
10. **Fail closed on errors.** Any unexpected exception during verification MUST be treated as a verification failure (HTTP 401), not a 500.

## Test vector

GitHub publishes a deterministic test vector. Source: [Validating webhook deliveries](https://docs.github.com/en/webhooks/using-webhooks/validating-webhook-deliveries#testing-the-webhook-payload-validation).

```text
secret  = "It's a Secret to Everybody"
payload = "Hello, World!"
expected X-Hub-Signature-256
        = sha256=757107ea0eb2509fc211221cce984b8a37570b6d7586c22c46f4379c8b043e17
```

The receiver MUST be exercised against this vector during unit tests; if the vector is missing or fails, the implementation is broken.

## HTTP response mapping

These values mirror the RFC error taxonomy ([`docs/rfcs/0001-octoflow-fastapi-github-app-framework.md`](../../../../docs/rfcs/0001-octoflow-fastapi-github-app-framework.md), §"Error handling"):

| Failure                                  | Ghappkit exception      | HTTP response |
| ---------------------------------------- | ----------------------- | ------------- |
| Missing `X-Hub-Signature-256`            | `WebhookSignatureError` | `401`         |
| Invalid signature                        | `WebhookSignatureError` | `401`         |
| Missing `X-GitHub-Event`                 | `WebhookHeaderError`    | `400`         |
| Body is not valid JSON                   | `PayloadParseError`     | `400`         |
| Verified, no handler                     | (none)                  | `202`         |
| Verified, handler scheduled              | (none)                  | `202`         |
| Internal scheduling failure after verify | `HandlerExecutionError` | `500`         |

## Verification mode

When auditing existing receiver code with this skill, walk it from raw-body capture to handler dispatch and check each pitfall above explicitly. Record one yes/no per pitfall in the emitted contract report.
