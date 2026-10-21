# W30 — GitHub Actions GITHUB_TOKEN PR permission acceptance

**Fixed objective:** Advance workflow_office_deadline Autopilot toward safe unattended GitHub PR creation without misrepresenting code autonomy, real Ollama calls, workplace approval or deployment.

## Why a new test?

User screenshots show the GitHub Actions **Allow GitHub Actions to create and approve pull requests** checkbox selected and repository variable `EDU_AUTOPILOT_DOC_PR_LIVE=true` saved. Repository-level permission endpoints are not available from the connected GitHub read API. The previous unattended branch `autopilot/w29-backlog-39539017495` was pushed successfully but PR creation failed due to repository Actions policy. PR #58 has the existing W29B fixed title and is still open, so W29B deliberately skips creating a duplicate: a new push would provide no definitive proof that the permission is now fixed.

## One-time, review-only E2E

`.github/workflows/w30-actions-pr-permission-acceptance.yml` has a harmless read-only preview on the feature branch. Only after independently reviewed merge to `main`, and only if the existing opt-in repository variable is exactly `true`, the GitHub-hosted write job does the following:

1. Confirms exact repository, main ref, no existing fixed file, and no prior PR of its one-time unique title (including closed PRs).
2. Writes **only** `docs/autopilot-proposals/ACTIONS_PR_PERMISSION_E2E.md`, containing fictional, immutable explanatory documentation without email, employer or model output.
3. Stages exactly that one path, commits and pushes a distinct `autopilot/w30-actions-permission-<run_id>` branch, attempts `gh pr create` as GitHub Actions `GITHUB_TOKEN` with explicit `contents: write` and `pull-requests: write`.
4. On denial, fails loudly and attempts to delete only its newly pushed branch. Never merges.
5. On success, prints `W30_GITHUB_ACTIONS_BOT_CREATED_REAL_REVIEW_PR_NO_AUTO_MERGE` and leaves that PR **open for human review**. GitHub-token-created PRs may not automatically trigger ordinary pull_request CI, so reviewers must explicitly verify CI before merging.

**Pass condition:** the real main-push W30 job succeeds with the exact success marker **and** an actual PR exists with an `autopilot/w30-actions-permission-` head and expected one-file diff. Branch preview green alone does not prove permission.

**No real AI workers claimed:** this tests GitHub-controlled automation, not actual Ollama inference or three autonomous coding agents. External institutional approval gates remain 2/6 rollout and 0/8 production workflow sign-offs.
