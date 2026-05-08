# Drift detection

Use this checklist at the end of every skill run to decide whether the emitted contract is still aligned with GitHub's live behavior. If any trigger fires, re-run the affected sections of the skill before merging dependent code.

Primary sources:

- [GitHub Changelog](https://github.blog/changelog/)
- [Webhook events and payloads](https://docs.github.com/en/webhooks/webhook-events-and-payloads)
- [Best practices for using webhooks](https://docs.github.com/en/webhooks/using-webhooks/best-practices-for-using-webhooks)

## Triggers (any one fires a re-run)

1. **New event in the master index.** The event index page lists an event the report does not cover. Source: [Webhook events and payloads](https://docs.github.com/en/webhooks/webhook-events-and-payloads).
2. **New action on a covered event.** A new action value appears for an event already in scope (e.g. a new `pull_request` action). Cross-check against [`event-naming.md`](event-naming.md) worked examples and update if the action lands on a v1 typed event.
3. **Action seen in a real delivery is not in the registry.** A logged delivery's `qualified_event` does not match any registered handler. Treat as a soft drift signal: either subscribe and handle, or document the deliberate non-handling.
4. **Header changed or deprecated.** The delivery headers reference adds, renames, or deprecates a header (for example a successor to `X-Hub-Signature-256`). Source: [Delivery headers](https://docs.github.com/en/webhooks/webhook-events-and-payloads#delivery-headers).
5. **Signature scheme changed.** Any change to the algorithm, prefix, or required behavior described on [Validating webhook deliveries](https://docs.github.com/en/webhooks/using-webhooks/validating-webhook-deliveries).
6. **Acknowledgment SLA changed.** The 10-second window or the recommended status code on [Handling webhook deliveries](https://docs.github.com/en/webhooks/using-webhooks/handling-webhook-deliveries) shifts.
7. **Redelivery model changed.** Any change to redelivery semantics or window on [Redelivering webhooks](https://docs.github.com/en/webhooks/testing-and-troubleshooting-webhooks/redelivering-webhooks) or [Handling failed webhook deliveries](https://docs.github.com/en/webhooks/using-webhooks/handling-failed-webhook-deliveries).
8. **New permission required for the inbound subscription.** A new GitHub App permission is required to subscribe to an event already in scope.
9. **Schema-only drift.** [`octokit/webhooks`](https://github.com/octokit/webhooks) ships a major version bump. Treat as a structural cross-check signal, not a contract source; still requires re-walking the typed mapping.
10. **Internal contradiction.** A claim in the report disagrees with the live docs page (e.g. status code, response body shape).

## Re-run scope

Map the trigger to the minimum subset of the skill that needs to re-run.

| Trigger | Sections to re-run                                                                                                  |
| ------- | ------------------------------------------------------------------------------------------------------------------- |
| 1, 2, 3 | Event card(s) for the affected events; mapping table in [`typed-context-mapping.md`](typed-context-mapping.md).     |
| 4       | [`transport-contract.md`](transport-contract.md), event cards, signed test vectors.                                 |
| 5       | [`signature-verification.md`](signature-verification.md), signed test vectors.                                      |
| 6       | [`transport-contract.md`](transport-contract.md), [`redelivery-and-idempotency.md`](redelivery-and-idempotency.md). |
| 7       | [`redelivery-and-idempotency.md`](redelivery-and-idempotency.md), signed test vectors.                              |
| 8       | Event card(s) for the affected events.                                                                              |
| 9       | [`typed-context-mapping.md`](typed-context-mapping.md) and event cards.                                             |
| 10      | The contradicting section, plus a citation review of the whole report.                                              |

## Cadence

- Re-run the full skill when the GitHub Changelog publishes a webhooks-tagged entry the application cares about.
- Re-run the full skill before any release that touches the receiver, registry, signature verifier, or `ghappkit.events` payload models.
- Spot-run individual sections at PR review time when only part of the contract changes.

## Output

If any trigger fires, the report's "Drift Checklist Result" section MUST list:

- The trigger that fired and a link to the source that surfaced it.
- The sections re-run.
- The deltas applied to the artifacts (or "no change required").

If no trigger fires, the section MUST say `No drift triggers detected (date: YYYY-MM-DD).`
