---
name: lint-and-fix
description: Run linters and fix violations using Trunk, run Vulture (`make vulture`), fall back to `npx --yes @trunkio/launcher` when `trunk` is missing, and use a Python-first Trunk scope when networks or sandboxes block full `check -a`. Use when code quality checks fail, before PRs, or to repair broken linting states.
---

# Lint and Fix Loop: Trunk

## Purpose

An autonomous loop for the agent to identify, fix, and verify linting and formatting violations using [Trunk](https://trunk.io), plus unused-code signals from [Vulture](https://github.com/jendrikseipp/vulture) via `make vulture`.

## Trunk CLI on PATH

`make lint` and `make format` invoke `trunk` directly. If `trunk` is missing from `PATH` (for example `command -v trunk` fails), use the same commands through the npm-published launcher so Trunk still downloads the project-pinned CLI from `.trunk/trunk.yaml`:

- **Check**: `npx --yes @trunkio/launcher check -a`
- **Format**: `npx --yes @trunkio/launcher fmt -a`
- **Pre-install tools** (offline prep or “tool not found” from Trunk): `npx --yes @trunkio/launcher install`

See [Trunk: Install](https://github.com/trunk-io/docs/blob/main/code-quality/overview/cli/getting-started/install.md) (NPM / `@trunkio/launcher`).

### Cold environments and captured logs (CI, sandboxes, agents)

On a **first** run, Trunk may spend a long time downloading its CLI and hermetic linter tools with little or no stdout—**do not** treat a silent, in-progress process as a failed check. Prefer:

1. **`npx --yes @trunkio/launcher install`** once before `check` / `fmt` when the environment is fresh or Trunk complains about missing tools.
2. **Non-interactive flags** on checks: add **`--ci --no-progress`** (still use **`-a`** when you need the whole repo). Example: `npx --yes @trunkio/launcher check -a --ci --no-progress`.

If an orchestration timeout is unavoidable, say explicitly that **full Trunk verification did not finish** rather than assuming the tree is clean.

### Network, TLS, and sandbox limits

Some Trunk linters **reach the public internet** (for example **Semgrep** fetching rules from `semgrep.dev`, **markdown-link-check** hitting URLs in docs, or **hermetic tool downloads** such as Go). If errors are clearly **TLS handshake failures**, **connection resets**, **timeouts**, or **HTTP errors to third-party hosts**, treat that as **environment or network policy**, not as a defect in your Python code—**do not** “fix” the repository by editing unrelated markdown links or disabling linters unless the user explicitly asked for that.

When outbound access is uncertain or **`check -a` is too slow or too noisy**:

1. Run a **Python-first** slice first, for example: `npx --yes @trunkio/launcher check --ci --no-progress --filter ruff,pyright packages/` (narrow paths further if you only touched one package).
2. Still run **`make vulture`** and **`make test`** when behavior or types changed.
3. Widen to **`check -a`** (full CI parity) only when the environment is trusted to reach all external endpoints and you have enough wall time.

### `uv` / Vulture side effects

**`make vulture`** runs **`uv run vulture`**. `uv` may **recreate `.venv`** or switch the interpreter when it reconciles the version in `.python-version` with what is installed—treat that as normal after dependency or Python changes, not as a Vulture bug.

## Loop Logic

1. **Identify**: Run `make lint` (which executes `trunk check -a`) to list current violations. If `trunk` is unavailable, use **`npx --yes @trunkio/launcher`** (after **`install`** on a cold machine). In **sandboxes, agents, or flaky networks**, prefer a **Python-first** check (see **Network, TLS, and sandbox limits**) before relying on **`check -a`**. In non-interactive shells, always add **`--ci --no-progress`** to `check`.
2. **Analyze**: Examine the output from Trunk, focusing on the file path, line number, and error message.
3. **Fix**:
   - For formatting issues, run `make format` (which executes `trunk fmt -a`), or **`npx --yes @trunkio/launcher fmt -a`** when `trunk` is not on `PATH`.
   - For linting violations, apply the minimum necessary change to the source code to resolve the error.
   - Resolve findings by changing code, types, imports, or structure—not with suppressions (see **Constraints**).
4. **Verify**:
   - Re-run `make lint`, or the same **npx** command with **`check -a --ci --no-progress`** if `trunk` is missing **and** full CI parity is appropriate. Otherwise re-run the **narrow** `check` you used in **Identify** (for example **`--filter ruff,pyright`** on **`packages/`**).
   - Run **`make vulture`** (`uv run vulture`; configuration under `pyproject.toml` `[tool.vulture]`). Treat unused-code findings like other fixable issues: remove dead code or refactor so symbols are used; if a hit is a false positive (dynamic use, framework magic), adjust `[tool.vulture]` **only** when the user asked for that policy change—otherwise stop and ask a human.
   - For type-only triage, `uv run pyright` also reads `pyproject.toml` `[tool.pyright]`; prefer Trunk for CI parity.
   - When the change affects **executable code** (behavior, types, imports beyond formatting), run **`make test`** after lint passes (pytest-cov; see **Resources**). Same entrypoint as CI: `dev/test_python.sh`. Formatting- or comment-only edits may stop after `make lint` and `make vulture`.
   - If passed: Move to the next issue or finish if all are resolved.
   - If failed: Analyze the new failure and repeat the loop.

## Constraints

- Do not silence Trunk/Ruff/Pyright/Pylint/Bandit/Semgrep findings with inline suppressions (for example `# noqa`, `# type: ignore`, `# pylint: disable`, `ruff: noqa`, file-level `# ruff: noqa`, or Trunk inline disable comments).
- Do not broaden project configuration to hide violations (for example new `[tool.ruff.lint]` ignores, Pyright `report*` toggles, or Pylint disables) unless the user explicitly asked for that policy change.
- Prefer `make format` for auto-fixable style; otherwise fix the underlying issue the linter reports.
- If fixes fail after genuine attempts, stop and surface the finding for a human to decide—do not add suppressions to make CI green.

## Termination Criteria

- No more errors from the **Trunk scope you chose** (`make lint` / full **`check -a`**, or the **narrow** **`ruff`/`pyright`** path once Trunk has finished)—and if you intentionally used a narrow check because of the environment, say so explicitly instead of claiming full CI parity.
- No unresolved issues from **`make vulture`** that the agent can fix without policy changes or guesswork.
- When fixes touched executable code: **`make test`** passes.
- Reached max iteration limit (default: 5).

## Examples

### Scenario: Fixing a formatting violation

1. `make lint` reports formatting issues in `src/your_package/main.py`.
2. Agent runs `make format`.
3. `make lint` now passes.

### Scenario: `trunk` not installed globally

1. `make lint` fails with `trunk: command not found` (or the shell cannot resolve `trunk`).
2. Agent runs `npx --yes @trunkio/launcher install`, then `npx --yes @trunkio/launcher check -a --ci --no-progress` and `npx --yes @trunkio/launcher fmt -a` as needed.
3. Agent runs `make vulture` and addresses or escalates unused-code output.
4. When behavior changed: `make test` passes.

### Scenario: Dead code after lint is clean

1. `make lint` passes.
2. `make vulture` reports an unused function; agent removes it or wires it into used code paths.
3. `make vulture` is clean (or remaining items are escalated).

### Scenario: Sandbox or flaky network (Semgrep, link check, or tool download errors)

1. `npx --yes @trunkio/launcher install` succeeds, but **`check -a`** fails or stalls on **Semgrep**, **markdown-link-check**, or **downloading a hermetic compiler**—errors mention **HTTPS**, **SSL**, or **timeouts** to hosts outside the repo.
2. Agent runs **`npx --yes @trunkio/launcher check --ci --no-progress --filter ruff,pyright packages/`** (or paths touched), then **`make vulture`** and **`make test`** as needed.
3. Agent reports **environment limits** for full `check -a` rather than changing unrelated docs or suppressing linters to “go green.”

## Resources

- [Trunk Documentation](https://docs.trunk.io/): Official documentation for the Trunk CLI.
- [Trunk install (NPM launcher)](https://github.com/trunk-io/docs/blob/main/code-quality/overview/cli/getting-started/install.md): `@trunkio/launcher` and `npx` usage.
- [Vulture](https://github.com/jendrikseipp/vulture): Dead-code detection; this repo runs it via `make vulture` / `uv run vulture`.
- [pytest-cov](https://pytest-cov.readthedocs.io/) / [Coverage.py](https://coverage.readthedocs.io/): Test coverage used by `make test` / `make coverage`.
