# REST Contract Rules

For each requested REST endpoint, extract and record:

- Operation name (stable local alias, e.g. `issues.create_comment`)
- HTTP method
- Path template
- Path/query/body parameters and required/optional flags
- Required headers (including API version header behavior when specified)
- Response status codes and response body shape
- Known error statuses and meaning
- Permission requirements for GitHub App installation tokens

Normalization guidance:

- Preserve official parameter names exactly.
- Record enum-like values exactly as documented.
- Distinguish missing field vs nullable field behavior when docs indicate it.
- Separate "required for call" from "required by business logic".

Client-impact guidance:

- Mark if endpoint should be helper candidate in `rest.<resource>.<operation>`.
- Ensure fallback parity is possible through generic `request(method, path, ...)`.
- Record pagination mechanics and link them to rate-limit implications.
