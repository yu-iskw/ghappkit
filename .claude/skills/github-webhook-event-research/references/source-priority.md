# Source priority

When this skill emits a claim about webhook delivery, headers, signatures, event payloads, or actions, the citation MUST come from the highest-priority source available. Never silently fall back to memory; if a source cannot be found, mark the claim as unverified and stop.

## Priority order (no exceptions)

1. **Official GitHub Docs (English)** — `https://docs.github.com/en/...`. The webhook section under [`/en/webhooks`](https://docs.github.com/en/webhooks) is the canonical contract for transport, signing, headers, redelivery, and per-event payload schemas.
2. **Official GitHub REST reference** — `https://docs.github.com/en/rest/webhooks/...` for delivery-management endpoints (listing deliveries, redelivering an attempt). Use only when documenting endpoints we call back into GitHub for delivery management.
3. **`octokit/webhooks` JSON Schemas** — `https://github.com/octokit/webhooks` (`payload-schemas/api.github.com/`). Use as a structural cross-check for payload field shapes only when docs.github.com is silent. Never cite as the primary source.
4. **GitHub changelog** — `https://github.blog/changelog/label/webhooks/`. Use only to flag drift (new event, deprecation) and to drive a re-validation cycle.

## Sources that are NEVER authoritative

- Stack Overflow, Reddit, Hacker News, vendor blog posts, third-party tutorials.
- Older repository copies of the docs (e.g. `github/docs` source files at a pinned commit that does not match the live page).
- AI memory or "I recall reading" claims.

## Anchor URLs to cite

Use these exact URLs (English) as the default citations. Pin a deeper anchor only when the page has a stable `id`.

| Topic                                              | URL                                                                                                      |
| -------------------------------------------------- | -------------------------------------------------------------------------------------------------------- |
| About webhooks                                     | <https://docs.github.com/en/webhooks/about-webhooks>                                                     |
| Master event index + payloads                      | <https://docs.github.com/en/webhooks/webhook-events-and-payloads>                                        |
| Delivery headers (anchor)                          | <https://docs.github.com/en/webhooks/webhook-events-and-payloads#delivery-headers>                       |
| Validating deliveries (HMAC, signature)            | <https://docs.github.com/en/webhooks/using-webhooks/validating-webhook-deliveries>                       |
| Handling deliveries (acknowledge fast, async work) | <https://docs.github.com/en/webhooks/using-webhooks/handling-webhook-deliveries>                         |
| Best practices (idempotency, replay, queueing)     | <https://docs.github.com/en/webhooks/using-webhooks/best-practices-for-using-webhooks>                   |
| Redelivering webhooks (UI + API)                   | <https://docs.github.com/en/webhooks/testing-and-troubleshooting-webhooks/redelivering-webhooks>         |
| Handling failed deliveries                         | <https://docs.github.com/en/webhooks/using-webhooks/handling-failed-webhook-deliveries>                  |
| Repo webhook redeliver API                         | <https://docs.github.com/en/rest/webhooks/repo-deliveries#redeliver-a-delivery-for-a-repository-webhook> |
| App webhook redeliver API                          | <https://docs.github.com/en/rest/apps/webhooks#redeliver-a-delivery-for-an-app-webhook>                  |
| Org webhook redeliver API                          | <https://docs.github.com/en/rest/orgs/webhooks#redeliver-a-delivery-for-an-organization-webhook>         |

Per-event payload anchors live on the master event index page; cite the `#<event>` fragment (for example `#pull_request`).

## Citation format

Inline markdown link with the official URL. One canonical example:

```markdown
- `X-Hub-Signature-256` is HMAC-SHA256 of the raw request body using the configured webhook secret. Source: [Validating webhook deliveries](https://docs.github.com/en/webhooks/using-webhooks/validating-webhook-deliveries).
```

When a single section has multiple sources, list them as bullets under "Source URLs".

## Verification rule

Before emitting any artifact, reread each claim and confirm:

- The link resolves to docs.github.com (or one of the explicitly allowed alternatives above).
- The cited section is the **most specific** available (prefer the deep anchor on the master event index page over a generic top-level page).
- The cited content has not been overruled by a later paragraph on the same page.

If any check fails, fix the citation or remove the claim.
