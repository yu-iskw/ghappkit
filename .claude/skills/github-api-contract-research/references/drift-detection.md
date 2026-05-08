# Drift Detection

Run this checklist before finalizing output:

- Confirm each operation URL still resolves to official docs.
- Confirm request parameters and required fields still match docs.
- Confirm permission requirements are unchanged.
- Confirm pagination/rate-limit guidance is still current.
- Confirm deprecation or versioning notices do not alter behavior.

Re-validation triggers:

- Adding a new helper in `rest.*` or new GraphQL wrapper.
- Docs indicate deprecation, preview-to-stable changes, or API version changes.
- New auth model or permission boundary appears in official docs.
- Repeated runtime failures suggest contract mismatch.

Reporting:

- Emit either `no triggers` or a concrete re-validation task list.
