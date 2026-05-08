## Test vector: `<vector-name>`

> Emit at least the five canonical scenarios per report (success, invalid-signature, missing-header, unknown-action, push-no-action). Use this template for each.

### Scenario

- Name: `<vector-name>`
- Category: `success | invalid-signature | missing-header | unknown-action | push-no-action | malformed-json | <other>`
- Goal: `<what the receiver behavior under test is>`

### Inputs

#### Headers

- `X-GitHub-Event`: `<event-name | absent>`
- `X-GitHub-Delivery`: `<UUID, or absent for missing-header tests>`
- `X-Hub-Signature-256`: `<sha256=... | invalid | absent>`
- `X-GitHub-Hook-ID`: `<integer | absent>`
- `X-GitHub-Hook-Installation-Target-Type`: `<repository | organization | integration | absent>`
- `X-GitHub-Hook-Installation-Target-ID`: `<integer | absent>`
- `User-Agent`: `GitHub-Hookshot/<...> | absent`
- `Content-Type`: `application/json`

#### Body

- Source: `<inline | path to fixture | "fabricated minimal payload">`
- Raw body bytes (UTF-8 representation):

  ```text
  <exact bytes used for HMAC computation>
  ```

#### Secret

- Secret used to compute the signature: `<value or test fixture name>`
- For `success` vectors, the published GitHub test secret may be used: `It's a Secret to Everybody` -> expected signature `sha256=757107ea0eb2509fc211221cce984b8a37570b6d7586c22c46f4379c8b043e17` for body `Hello, World!`. Source: [Validating webhook deliveries](https://docs.github.com/en/webhooks/using-webhooks/validating-webhook-deliveries#testing-the-webhook-payload-validation).

### Expected behavior

- HTTP status: `202 | 401 | 400 | 500`
- Octoflow exception (if any): `None | WebhookSignatureError | WebhookHeaderError | PayloadParseError | HandlerExecutionError`
- Handler invoked: `<qualified-event-name | none>`
- Log fields written: `event`, `qualified_event`, `delivery_id`, `<other>`
- Side effects asserted: `<list>`

### Notes

- Why this vector exists: `<failure mode it guards against>`
- Source for the canonical scenario:
  - success / invalid-signature: <https://docs.github.com/en/webhooks/using-webhooks/validating-webhook-deliveries>
  - missing-header / push-no-action: <https://docs.github.com/en/webhooks/webhook-events-and-payloads#delivery-headers>
  - unknown-action: [`event-naming.md`](../../references/event-naming.md) edge cases.

### Five canonical scenarios (mandatory)

When emitting a report, include ALL of the following test vectors at minimum:

| Vector name             | Category          | Why required                                                                                              |
| ----------------------- | ----------------- | --------------------------------------------------------------------------------------------------------- |
| `success-issues-opened` | success           | Verifies signature, parsing, registry routing, and `202` response on the happy path.                      |
| `bad-signature`         | invalid-signature | Verifies `WebhookSignatureError -> 401` and that no handler runs.                                         |
| `missing-event-header`  | missing-header    | Verifies `WebhookHeaderError -> 400` when `X-GitHub-Event` is absent.                                     |
| `unknown-action`        | unknown-action    | Verifies that an unknown `pull_request` action still resolves a qualified name and returns `202`.         |
| `push-no-action`        | push-no-action    | Verifies the bare `push` qualified name (no trailing dot) and that handlers registered for `push.*` miss. |
