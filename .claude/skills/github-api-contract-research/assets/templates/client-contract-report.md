# GitHub API Client Contract Report

## Scope

- Requested operations:
- Target package/surface:
- RFC linkage:

## Source Ledger

- Official URLs used:
- Ambiguities found:

## REST Contract Cards

<!-- Paste one or more completed rest-endpoint-card.md sections -->

## GraphQL Contract Cards

<!-- Paste one or more completed graphql-operation-card.md sections -->

## Client Mapping Table

| Operation | Surface | Decision | Rationale                  | Fallback Parity Requirement          |
| --------- | ------- | -------- | -------------------------- | ------------------------------------ |
| example   | rest    | helper   | frequently used and stable | `request(...)` equivalent documented |

## Error and Retry Matrix

| Operation | Success Contract   | Non-Retryable Failures | Retryable Failures | Retry Strategy  |
| --------- | ------------------ | ---------------------- | ------------------ | --------------- |
| example   | 2xx with JSON body | 4xx validation/auth    | timeout/5xx        | bounded backoff |

## Test Vectors

<!-- Paste completed test-vector.md entries -->

## Drift Checklist Result

- [ ] URLs verified
- [ ] Parameter and response shapes re-verified
- [ ] Permission requirements re-verified
- [ ] Pagination and rate-limit notes re-verified
- [ ] Deprecation/versioning notes checked

Re-validation triggers:

- none | list trigger + action
