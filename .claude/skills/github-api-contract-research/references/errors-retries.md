# Errors and Retries

For each operation, record:

- Success status/result contract
- Non-retryable errors (validation, auth, permission, not found, etc.)
- Retryable errors (timeouts, transient upstream failures, secondary limits if documented)
- Suggested retry strategy class (none, bounded retry with backoff, caller-managed)

Rules:

- Do not mark retries unless behavior is documented or clearly transient by transport class.
- Keep operation-level failure semantics separate from transport-level exceptions.
- Record idempotency implications for write operations before recommending retries.

Output requirements:

- Each operation must map to at least one success vector and one failure vector.
- Include at least one retryable and one non-retryable example in the final bundle.
