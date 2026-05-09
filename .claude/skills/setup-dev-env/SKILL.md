---
name: setup-dev-env
description: Set up the development environment for the project. Use when starting work on the project, when dependencies are out of sync, or to fix environment setup failures.
---

# Setup Development Environment

Ensure Python, `uv`, and `Trunk` match this template, then install dependencies.

## Workflow

1. **Validate tooling** — Read `.python-version` in the repo root; the active interpreter should match. Prefer **`uv`** and **`trunk`** on `PATH` (on macOS: `brew install trunk-io uv` if missing). If **`uv` is missing** and `dev/setup.sh` installs it via `pip install --user`, ensure **`$HOME/.local/bin`** is on **`PATH`** before the next step (otherwise `make setup` can fail with `uv: command not found`). If **`trunk`** is missing globally, use **`npx --yes @trunkio/launcher`** for `install` / `check` / `fmt` (see **`lint-and-fix`**).
2. **Install dependencies** — From the repo root, run `make setup` (see [CLAUDE.md](../../../CLAUDE.md) for `uv` / `make` conventions). This runs `dev/setup.sh`, which creates the venv and syncs dependencies.
3. **Trunk artifacts** — Run **`trunk install`**, or **`npx --yes @trunkio/launcher install`** when `trunk` is not on `PATH`, so managed linters and formatters are present. On a **fresh** environment, this step can take a long time (downloads); run it **before** assuming `check` failed for code reasons.
4. **Optional verification** — Invoke the `verifier` subagent ([../../agents/verifier.md](../../agents/verifier.md)) if you need a full build, lint, and test pass after a broken or fresh environment.

## Success criteria

- Dependencies install without errors into the project virtual environment.
- `uv` is available (and on `PATH` after user-site install when applicable); **`trunk`** is available **or** you can run it via **`npx --yes @trunkio/launcher`**. Python matches `.python-version` after `uv sync` / venv creation.
