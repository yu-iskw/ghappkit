# Client Surface Mapping

Map every researched operation to one of these RFC-aligned surfaces:

1. REST helper: `rest.<resource>.<operation>(...)`
2. GraphQL raw path: `graphql(query, variables=...)`
3. Generic fallback: `request(method, path, params=..., json=..., headers=...)`

Decision rules:

- Choose helper when operation is common, stable, and benefits from typed ergonomics.
- Keep fallback available for all helper-backed operations to preserve protocol completeness.
- Use GraphQL raw path by default; add typed wrapper only for frequent and stable operations.
- Record why helper was chosen or rejected.

Parity requirements:

- Helper behavior must be reproducible through generic fallback inputs/outputs.
- Auth, headers, pagination, and error semantics must match between helper and fallback.
- Mapping must specify where the implementation should live (`client.py`, `rest.py`, `graphql.py`).

v1 prioritization guidance:

- Prefer high-frequency operations first (e.g., issue comments, label mutations, checks).
- Avoid broad generated surfaces in v1; keep incremental helper growth.
- Always include one fallback example for unsupported or low-frequency operations.
