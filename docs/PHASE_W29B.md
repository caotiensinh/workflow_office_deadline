# W29B — First unattended *real* GitHub pull-request attempt, docs only

User explicitly authorized safe autonomous repository coding/PR work while preserving IT approval and sensitive-workplace limits. W28B already creates deterministic repository-owned fictional backlog status, but its actual GitHub PR publisher was disabled behind `EDU_AUTOPILOT_DOC_PR_LIVE`; no unattended PR was observed.

`.github/workflows/w29b-unattended-reviewed-doc-pr.yml` implements a **dedicated GitHub-hosted only main push job** which first checks there is no open PR with the fixed bot title, runs offline W28B regression, stages one specific deterministic document `docs/autopilot-proposals/BACKLOG_STATUS.md`, verifies exact staged pathname, commits to a new `autopilot/w29-backlog-<run_id>` branch, and tries opening a **review-required PR** with `gh`. It serializes attempts and never merges. Branch-scoped preview is read-only. No Ollama content, generated Python/Rust scripts, mail or real workplace data enter this branch.

**Permission caveat:** GitHub may reject bot PR creation if repository Actions settings forbid this; observe actual hosted run after merging and record `BLOCKED_GITHUB_PERMISSION` instead of pretending success. PRs created via `GITHUB_TOKEN` can also lack normal automatic `pull_request` event workflows; human reviewer must explicitly require CI before merge (future CI dispatch automation). Avoid granting broad PAT credentials.

Do not claim autonomous coding agents or auto-merge. All production/IT/pilot gates remain pending; rollout 2/6, production 0/8. Acceptance: 4/4 feature CI and hosted no-write preview. Confirm bot PR creation only via an actual postmerge hosted workflow log and created PR reference.

## W29B actual GitHub Actions result (2026-10-21 JST)

- Default-branch push triggered real hosted workflow run **#39539017495**: preview PASS; PR publisher created a one-file fictional docs commit on bot branch `autopilot/w29-backlog-39539017495` and **successfully pushed it to GitHub**.
- `gh pr create` was DENIED by the GitHub **repository Actions setting**: `GraphQL: GitHub Actions is not permitted to create or approve pull requests`. This is not a GitHub token syntax bug, CI failure in Python, or a signal that Autopilot finished.
- The already-pushed, SHA-bound fictional-only branch was opened for review **through the user-authorized GitHub connector**, not unattended background runner, as **PR #58**. Its existence is **not** evidence of unattended bot PR creation.
- W29B correction: publisher now **requires repository variable `EDU_AUTOPILOT_DOC_PR_LIVE=true`**. Keep unset while GitHub Actions repository policy blocks bot PR creation. When enabled after policy approval, if `gh pr create` fails, delete exactly the newly-created bot branch and mark the job as BLOCKED rather than leave more orphan branches. No merge is automatic.
- Only repository owner/admin can approve changing Actions workflow permissions; do not use PAT tricks or silently bypass GitHub's explicit block. GITHUB_TOKEN-created PRs may not automatically trigger normal PR CI, so review requires verified checks.
