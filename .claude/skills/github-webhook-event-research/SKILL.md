---
name: github-webhook-event-research
description: Produce source-linked, implementation-ready contracts for GitHub webhook deliveries and event payloads (transport headers, X-Hub-Signature-256 verification, qualified event naming, per-event action research, typed-context mapping, redelivery, drift detection) to drive ghappkit's inbound path. Use when implementing or validating webhook receivers, signature verifiers, event registries, typed event models, or signed test fixtures.
compatibility: Internet access for official GitHub docs (docs.github.com/en/webhooks). Read-only skill: emits a Markdown bundle in chat. Pairs with `github-api-contract-research` (use that one for outbound REST/GraphQL).
---

# GitHub Webhook & Event Research

Use this skill when implementing or validating GitHub-webhook-facing code in ghappkit:
webhook receivers, signature verifiers, header parsers, event registries, typed event models, or signed test fixtures. The skill grounds every claim in **official GitHub references** so receiver behavior, signatures, headers, and per-event payload assumptions cannot drift away from the upstream contract.

## When to use

Trigger this skill on prompts such as:

- "implement the webhook receiver / signature verifier / header parser"
- "add a typed context for `<event>.<action>`"
- "verify `X-Hub-Signature-256` / handle redelivery"
- "extend `ghappkit.events` with a new event model"
- "build signed-payload fixtures in `ghappkit-testing`"
- "audit how we validate or dispatch GitHub webhook deliveries"

## When NOT to use

- Outbound REST/GraphQL client work (e.g. `ctx.github.rest.issues.create_comment(...)`) -> use the `github-api-contract-research` skill (sibling, opposite direction).
- Generic Python lint, build, or test tasks -> use the matching repo skill (`lint-and-fix`, `build-and-fix`, `test-and-fix`).
- ADR or design-document authoring -> use `manage-adr`.

## Mandatory output bundle (every run)

Every run MUST emit all five sections, even if empty placeholders are kept until research completes. The final report is composed via [`assets/templates/webhook-contract-report.md`](assets/templates/webhook-contract-report.md).

1. **Transport contract sheet** — required headers and the raw-body rule.
2. **Signature verification procedure** — HMAC-SHA256 of raw bytes, constant-time compare, `sha256=` prefix handling, secret-rotation policy.
3. **Event card(s)** — one card per requested event with: official URL, action enum, payload top-level keys, sender/repo/installation slots, qualified-name examples, RFC typed-context mapping, raw-fallback decision.
4. **Redelivery and idempotency notes** — keyed off `X-GitHub-Delivery`.
5. **Drift checklist + signed test vectors** — at least five vectors covering success, bad signature, missing header, unknown action, and the `push` no-action edge.

## Workflow

Follow these ten steps in order. Each step links to the exact reference or template that governs it.

1. Confirm the trigger fits this skill (see "When NOT to use" above).
2. Read [`references/source-priority.md`](references/source-priority.md). From this point forward, every emitted claim MUST cite an official URL.
3. Fill the transport contract sheet using [`references/transport-contract.md`](references/transport-contract.md).
4. Apply the procedure in [`references/signature-verification.md`](references/signature-verification.md) to the receiver design or code under review.
5. For each requested event, draft an event card from [`assets/templates/event-card.md`](assets/templates/event-card.md), following the rules in [`references/event-naming.md`](references/event-naming.md) for qualified-name derivation.
6. Map each event to the typed `WebhookContext` shape using [`references/typed-context-mapping.md`](references/typed-context-mapping.md). Decide helper-vs-raw fallback per event and record the rationale.
7. Apply [`references/redelivery-and-idempotency.md`](references/redelivery-and-idempotency.md) and capture the dedupe key and idempotency boundary.
8. Emit signed test vectors using [`assets/templates/signed-test-vector.md`](assets/templates/signed-test-vector.md). Cover at least the five canonical scenarios.
9. Run the [`references/drift-detection.md`](references/drift-detection.md) checklist and record any re-validation triggers found.
10. Compose the final output using [`assets/templates/webhook-contract-report.md`](assets/templates/webhook-contract-report.md) and emit it in chat.

## Stop conditions

Halt the skill when ALL of the following hold:

- Every section of `webhook-contract-report.md` is filled (no placeholder bullets).
- Every claim cites an official URL (per `source-priority.md`).
- A raw-fallback decision is recorded for every requested event.
- At least five signed test vectors exist (success / bad-sig / missing-header / unknown-action / `push` no-action edge).
- The drift checklist has been applied and either reports "no triggers" or lists what to re-validate.

## Relationship to the ghappkit RFC

The skill is engineered to feed [`docs/rfcs/0001-octoflow-fastapi-github-app-framework.md`](../../../docs/rfcs/0001-octoflow-fastapi-github-app-framework.md):

- Webhook lifecycle (RFC §"Webhook lifecycle") -> transport + signature references.
- Event-name derivation `{event}.{action}` (RFC §"Event naming") -> [`references/event-naming.md`](references/event-naming.md).
- Typed `WebhookContext` shape (RFC §"Typed context") -> [`references/typed-context-mapping.md`](references/typed-context-mapping.md).
- v1 typed event coverage table (RFC §"v1 typed event coverage") -> mapping table in [`references/typed-context-mapping.md`](references/typed-context-mapping.md).
- Error taxonomy (`WebhookSignatureError`, `WebhookHeaderError`, `PayloadParseError`, `EventModelError`) -> response codes recorded in [`assets/templates/signed-test-vector.md`](assets/templates/signed-test-vector.md).
