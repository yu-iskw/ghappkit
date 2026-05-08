# GraphQL Contract Rules

For each requested GraphQL operation, extract and record:

- Operation name and type (`query` or `mutation`)
- Variable names, types, and required/optional status
- Expected response shape (top-level fields and critical nested fields)
- Documented auth/permission requirements relevant to data access or mutation
- Known error classes and documented failure conditions

Normalization guidance:

- Keep GraphQL variable and field names exactly as official docs show.
- Separate schema-required constraints from application-required constraints.
- Record nullable response branches that client code must handle.

Client-impact guidance:

- Primary path is `graphql(query, variables=...)`.
- Optional typed wrapper candidates may be added when usage frequency is high.
- Wrapper naming must not hide required variables or side effects.
