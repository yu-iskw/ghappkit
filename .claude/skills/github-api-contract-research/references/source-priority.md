# Source Priority

Use this priority order when extracting facts. If sources disagree, cite the higher-priority source and note the conflict.

1. Official GitHub API docs for the exact operation:
   - REST: `https://docs.github.com/en/rest/...`
   - GraphQL: `https://docs.github.com/en/graphql/...`
2. Official endpoint-specific permission and auth notes in those same docs.
3. Official pagination/rate-limit docs:
   - REST pagination
   - GraphQL limits and resource limits
4. Official changelog/deprecation notes when operation behavior has changed.

Rules:

- Every emitted claim must have at least one official URL.
- Do not use unofficial blogs, wrappers, or forum posts as primary evidence.
- If the official docs are ambiguous, record the ambiguity explicitly.
- Include any required API-version header behavior when documented.
