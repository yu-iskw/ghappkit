# Auth and Permissions

Auth model for this skill output:

- GitHub App installation token for repository-scoped operations.
- Record when operation instead depends on app-level or user-level context.

For each operation, record:

- Token type expected by GitHub docs
- Required repository or organization permission scope
- Minimum permission level (read/write/admin if specified)
- Any repository selection constraints

Rules:

- Map permissions to least-privilege defaults for client examples.
- If docs provide multiple auth paths, note the preferred installation-token path and alternatives.
- Flag operations that cannot be satisfied by installation token alone.
- Never infer broader scopes than documented.
