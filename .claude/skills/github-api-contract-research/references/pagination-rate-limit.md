# Pagination and Rate Limits

Capture pagination and quota behavior as part of each contract.

REST:

- Identify whether endpoint is paginated.
- Record pagination parameters (`page`, `per_page`, cursor variants) exactly as documented.
- Record response headers or links required for iteration.

GraphQL:

- Record connection pagination requirements (`first`/`last`, cursors) when applicable.
- Note rate-limit and cost considerations for the operation shape.

Rules:

- Include page-size defaults and maximums if documented.
- Record safe client defaults to avoid accidental quota spikes.
- Distinguish retry/backoff behavior from pagination iteration logic.
