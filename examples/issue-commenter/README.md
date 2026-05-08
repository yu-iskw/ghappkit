# Issue commenter example

Demonstrates mounting `GitHubApp`, handling `issues.opened`, loading optional `.github/ghappkit.yml`, and posting issue comments via `ctx.github`.

## Environment

Set standard `GITHUB_APP_*` variables (see `GitHubAppSettings`). At minimum you need `GITHUB_APP_APP_ID`, `GITHUB_APP_WEBHOOK_SECRET`, and a PEM via `GITHUB_APP_PRIVATE_KEY` or `GITHUB_APP_PRIVATE_KEY_PATH`.

## Run locally

```bash
uvicorn issue_commenter.app:app --reload --port 8000
```

Expose the `/github/webhooks` route to GitHub using smee.io or another tunnel.
