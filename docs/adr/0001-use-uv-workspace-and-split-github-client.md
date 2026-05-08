# ADR 0001: Use a uv workspace and split the GitHub client from the FastAPI framework

- **Status:** Proposed
- **Date:** 2026-05-08
- **Related RFC:** [RFC 0001: ghappkit — FastAPI-native framework for enterprise-grade GitHub Apps](../rfcs/0001-octoflow-fastapi-github-app-framework.md)

## Context

ghappkit is intended to become a FastAPI-native framework for implementing GitHub Apps in Python.

The framework has at least three distinct responsibility groups:

1. **FastAPI framework layer**
   - Router integration
   - Webhook endpoint
   - Event registration and dispatch
   - Handler contexts
   - Repository config loading
   - Logging and background execution

2. **GitHub API client layer**
   - GitHub App JWT creation
   - Installation token creation and caching
   - REST transport
   - GraphQL transport
   - Pagination helpers
   - Rate-limit and error handling

3. **Testing and simulation layer**
   - Signed webhook payload helpers
   - Payload fixtures
   - Fake GitHub client
   - Local webhook delivery simulation

These concerns evolve at different rates. The GitHub API client may be useful outside FastAPI, while the FastAPI framework should not be forced to expose every GitHub API detail directly.

uv workspaces support multi-package repositories with a shared lockfile and workspace dependencies. This makes them a good fit for developing `ghappkit`, `ghappkit-client`, and `ghappkit-testing` together while keeping their APIs and packaging boundaries explicit.

## Decision

Use a uv workspace for the repository and split the implementation into separate packages:

```text
packages/ghappkit          # FastAPI framework
packages/ghappkit-client   # GitHub App auth and REST/GraphQL client
packages/ghappkit-testing  # testing and simulation utilities
```

The root `pyproject.toml` should define the workspace:

```toml
[tool.uv.workspace]
members = [
  "packages/ghappkit",
  "packages/ghappkit-client",
  "packages/ghappkit-testing",
  "examples/*",
]

[tool.uv.sources]
ghappkit = { workspace = true }
ghappkit-client = { workspace = true }
ghappkit-testing = { workspace = true }
```

## Rationale

### Keep framework and GitHub client concerns separate

The FastAPI framework should focus on webhook delivery, event routing, context creation, background execution, configuration loading, and framework ergonomics.

The GitHub client should focus on authentication, transport, pagination, error mapping, and API helpers.

Separating them prevents the framework package from becoming a monolithic GitHub API wrapper and allows future users to consume the client without FastAPI.

### Support enterprise extensibility

Enterprise users often need custom queues, token stores, observability, policy engines, and tenancy controls. Clear package boundaries make these extension points easier to define and test.

### Improve release discipline

The packages may need different stability promises:

| Package            | API stability expectation                            |
| ------------------ | ---------------------------------------------------- |
| `ghappkit`         | Stable developer-facing framework API                |
| `ghappkit-client`  | Stable client protocol with evolving helper coverage |
| `ghappkit-testing` | Stable test ergonomics, flexible internals           |

### Preserve local development ergonomics

A uv workspace allows contributors to work across package boundaries with one lockfile, one repository, and local workspace dependencies.

## Consequences

### Positive

- Cleaner architecture and dependency graph
- GitHub client can be reused independently
- Testing helpers can evolve without bloating framework runtime dependencies
- Examples can consume workspace packages directly
- Easier future split into optional packages such as queue, persistence, OpenTelemetry, or policy integrations

### Negative

- More initial repository structure to maintain
- Slightly more complex packaging and CI matrix
- Contributors must understand workspace package boundaries
- Cross-package changes require careful versioning once packages are published

## Alternatives considered

### Alternative 1: Single package only

Keep everything under one `ghappkit` package.

**Rejected because:** it is simpler initially but risks creating a large monolith that mixes FastAPI framework logic, GitHub API transport, testing utilities, and future integrations.

### Alternative 2: Split only after v1

Start with one package and extract `ghappkit-client` later.

**Rejected because:** the GitHub client boundary is architectural. Delaying the split would make public API design harder and increase migration cost.

### Alternative 3: Use separate repositories

Create independent repositories for framework, GitHub client, and testing utilities.

**Rejected because:** the project is early, cross-package changes will be frequent, and a monorepo gives faster iteration with shared CI and a shared lockfile.

## Implementation notes

Initial package responsibilities:

```text
ghappkit/
  app.py
  routing.py
  context.py
  security.py
  execution.py
  config.py
  logging.py
  exceptions.py

ghappkit_client/
  auth.py
  client.py
  rest.py
  graphql.py
  pagination.py
  transport.py
  errors.py

ghappkit_testing/
  fixtures.py
  signatures.py
  fake_client.py
  simulator.py
```

The framework package should depend on the GitHub client package:

```toml
[project]
dependencies = [
  "fastapi>=0.115",
  "pydantic>=2",
  "ghappkit-client",
]

[tool.uv.sources]
ghappkit-client = { workspace = true }
```

The testing package should depend on both:

```toml
[project]
dependencies = [
  "ghappkit",
  "ghappkit-client",
  "pytest>=8",
]

[tool.uv.sources]
ghappkit = { workspace = true }
ghappkit-client = { workspace = true }
```

## Follow-ups

1. Convert the current template package to the workspace layout.
2. Add minimal package skeletons for `ghappkit`, `ghappkit-client`, and `ghappkit-testing`.
3. Add CI jobs that run lint, type checks, and tests across all workspace packages.
4. Add an example app that imports packages through workspace dependencies.
