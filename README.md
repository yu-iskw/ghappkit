# ghappkit (GitHub App Kit)

FastAPI-native framework for building production-grade GitHub Apps in Python.

## Workspace packages

| Package                                                   | Purpose                                                      |
| --------------------------------------------------------- | ------------------------------------------------------------ |
| [`packages/ghappkit`](packages/ghappkit/)                 | FastAPI router, webhooks, contexts, repo config, execution   |
| [`packages/ghappkit-client`](packages/ghappkit-client/)   | GitHub App JWT, installation tokens, REST/GraphQL helpers    |
| [`packages/ghappkit-testing`](packages/ghappkit-testing/) | Signed payloads, fixtures, fake client, `GhappkitTestClient` |

Examples live under [`examples/`](examples/). Authoritative design notes: [RFC 0001](docs/rfcs/0001-octoflow-fastapi-github-app-framework.md), [ADR 0001](docs/adr/0001-use-uv-workspace-and-split-github-client.md).

## Webhooks: HTTP responses & security

GitHub posts JSON bodies to the FastAPI route exposed by [`GitHubApp.router`](packages/ghappkit/). Responses use stable `detail` strings (not raw exception messages) so clients can branch without parsing internal wording:

| Scenario                                     | HTTP status | `detail`                                            |
| -------------------------------------------- | ----------- | --------------------------------------------------- |
| Bad or missing `X-Hub-Signature-256`         | 401         | `invalid_webhook_signature`                         |
| Missing or malformed GitHub delivery headers | 400         | `invalid_webhook_headers`                           |
| Body not UTF-8                               | 400         | `invalid_webhook_payload_encoding`                  |
| Body not JSON                                | 400         | `invalid_webhook_payload_json`                      |
| JSON value not an object                     | 400         | `invalid_webhook_payload_not_object`                |
| Other unhandled delivery errors              | 500         | `webhook_delivery_failed` (type logged server-side) |

Several mapped internal failures use dedicated 500 `detail` strings (for example `webhook_handler_failed`); see `packages/ghappkit/src/ghappkit/app.py`.

**Trust model:** GitHub signs the **raw request body** with your webhook secret (`X-Hub-Signature-256`). Header names such as `X-GitHub-Event` are **not** part of that digest—only the shared secret binds authenticity to the payload bytes. Keep `GITHUB_APP_WEBHOOK_SECRET` confidential.

**`GITHUB_APP_REQUIRE_SIGNATURE`:** Defaults to enabled. Turning signature verification off exposes your webhook URL to unauthenticated traffic and should be limited to tests or tightly controlled environments. [`GitHubApp`](packages/ghappkit/) logs a warning at startup when verification is disabled.

**Legacy handler matching:** With `GITHUB_APP_WEBHOOK_MATCH_LEGACY_BASE_EVENT_HANDLERS=true`, handlers registered for both the qualified event (for example `issues.opened`) and the base event (`issues`) are merged; **the same handler object is only invoked once** per delivery.

Python tooling shares the root [`ruff.toml`](ruff.toml); flake8-type-checking `TC001`–`TC003` are ignored there because Pyright already validates imports and PEP 563 annotations keep many imports typing-only at runtime.

## Features

- **Package Management**: [uv](https://github.com/astral-sh/uv)
- **Build System**: [Hatchling](https://hatch.pypa.io/latest/)
- **Linting & Formatting**: [Trunk](https://trunk.io/) (Ruff, Pyright, Pylint, Bandit; Ruff is also the formatter)
- **Testing**: [pytest](https://docs.pytest.org/)
- **CI/CD**: GitHub Actions

## Security & Quality

This template enforces high security and maintainability standards:

- **[GitHub CodeQL](https://codeql.github.com/)**: Deep analysis using the `security-and-quality` suite to track code health and catch vulnerabilities.
- **Complexity Guardrails**: Cyclomatic complexity is capped at **10** per function (enforced via Ruff `C901`).
- **Trunk Linters**: [Bandit](https://github.com/PyCQA/bandit) (security), [Semgrep](https://semgrep.dev/) (patterns), [Trivy](https://github.com/aquasecurity/trivy) (IaC/Secret scanning), and [OSV-Scanner](https://github.com/google/osv-scanner) (dependencies).

## Development

Conventions, build commands, and AI-agent instructions: see [AGENTS.md](AGENTS.md). Claude Code–specific config lives in `CLAUDE.md` (it imports [AGENTS.md](AGENTS.md)) and in [`.claude/`](.claude/).

```bash
make setup      # Install dependencies and set up environment
make lint       # Run all linters via Trunk
make format     # Auto-format code via Trunk
make test       # Run pytest test suite
```
