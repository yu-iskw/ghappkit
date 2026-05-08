---
name: github-api-contract-research
description: Produce source-linked, implementation-ready contracts for GitHub REST and GraphQL operations (endpoint/operation shape, installation auth and permissions, pagination, rate limits, error semantics, helper-vs-fallback mapping, drift detection) to drive ghappkit's outbound client. Use when implementing or validating ghappkit-github REST/GraphQL methods, transport behavior, or client mapping decisions.
compatibility: Internet access for official GitHub docs (docs.github.com/en/rest and docs.github.com/en/graphql). Read-only skill: emits a Markdown bundle in chat. Pairs with `github-webhook-event-research` (use that one for inbound webhook contracts).
---

# GitHub API Contract Research

Use this skill when implementing or validating outbound GitHub API client code in ghappkit:
REST helpers, GraphQL operations, installation-token permission mapping, pagination handling,
retry/error behavior, and helper-vs-fallback placement in `ghappkit-github`.
Every claim must be anchored to official GitHub references so client behavior cannot drift.

## When to use

Trigger this skill on prompts such as:

- "implement `ctx.github.rest.issues.create_comment(...)`"
- "add REST helper for checks / pulls / repos"
- "add GraphQL operation wrapper and variable contract"
- "validate installation-token permissions for endpoint X"
- "decide helper vs generic `request(...)` fallback"
- "audit outgoing GitHub API client behavior against official docs"

## When NOT to use

- Inbound webhook transport/event parsing/signature work -> use `github-webhook-event-research`.
- Generic Python lint, build, or test tasks -> use `lint-and-fix`, `build-and-fix`, `test-and-fix`.
- ADR or architecture-record authoring -> use `manage-adr`.

## Mandatory output bundle (every run)

Every run MUST emit all five sections, even if placeholders are needed while research proceeds.
Compose the final output from [`assets/templates/client-contract-report.md`](assets/templates/client-contract-report.md).

1. **REST contract card(s)** — one card per endpoint with URL, method/path, params/body, response shape, required headers, auth scope, pagination/rate-limit notes.
2. **GraphQL operation card(s)** — one card per query/mutation with operation definition, variable and response contract, auth scope, complexity/rate-limit notes.
3. **Client mapping table** — helper candidate vs generic `request(...)` fallback decision for each operation, with rationale and parity requirements.
4. **Error/retry matrix + test vectors** — status/error taxonomy, retryability, and concrete vectors for success + expected failures.
5. **Drift checklist** — re-validation triggers and what must be re-checked when GitHub references evolve.

## Workflow

Follow these ten steps in order. Each step links to the governing reference or template.

1. Confirm the prompt fits this skill (see "When NOT to use").
2. Read [`references/source-priority.md`](references/source-priority.md). After this point, all emitted claims must cite official URLs.
3. For each REST operation, fill [`assets/templates/rest-endpoint-card.md`](assets/templates/rest-endpoint-card.md) using [`references/rest-contract.md`](references/rest-contract.md).
4. For each GraphQL operation, fill [`assets/templates/graphql-operation-card.md`](assets/templates/graphql-operation-card.md) using [`references/graphql-contract.md`](references/graphql-contract.md).
5. Determine installation-token permissions and auth constraints via [`references/auth-and-permissions.md`](references/auth-and-permissions.md).
6. Apply pagination and rate-limit rules from [`references/pagination-rate-limit.md`](references/pagination-rate-limit.md).
7. Fill error and retry behavior per operation using [`references/errors-retries.md`](references/errors-retries.md), then emit vectors from [`assets/templates/test-vector.md`](assets/templates/test-vector.md).
8. Build helper-vs-fallback decisions and parity rules using [`references/client-surface-mapping.md`](references/client-surface-mapping.md).
9. Run re-validation checks in [`references/drift-detection.md`](references/drift-detection.md) and record triggers.
10. Compose and emit the final bundle using [`assets/templates/client-contract-report.md`](assets/templates/client-contract-report.md).

## Stop conditions

Halt the skill when ALL of the following hold:

- Every `client-contract-report.md` section is filled (no placeholder bullets remain).
- Every claim includes at least one official source URL (per `source-priority.md`).
- Every requested operation has a helper-vs-fallback mapping decision.
- Error/retry matrix includes success plus non-retryable and retryable failure vectors.
- Drift checklist has been run and either reports "no triggers" or lists required re-validation.

## Relationship to the ghappkit RFC

This skill feeds [`docs/rfcs/0001-octoflow-fastapi-github-app-framework.md`](../../../docs/rfcs/0001-octoflow-fastapi-github-app-framework.md):

- RFC "GitHub API client" -> protocol surface (`rest`, `graphql`, generic `request(...)`) and ergonomic helper expectations.
- RFC Phase 4 ("GitHub auth and client") -> default `httpx` transport and installation-scoped auth behaviors.
- RFC Milestone M3 ("auth/client") -> mapping outputs used to implement installation-scoped API calls.
- RFC architectural trade-off "GitHub client: separate package plus protocol" -> helper-vs-fallback decisions preserve stable protocol while allowing incremental helper growth.
