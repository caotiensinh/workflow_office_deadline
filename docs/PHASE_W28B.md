# W28B — Deterministic docs-only autopilot pull request lane

Original goal: software should pick authorized engineering work, continue after CI, and request human/IT approval only when necessary. GitHub is PUBLIC: fictional data only.

`autopilot_pr_w28b.py` computes a strict SHA-256-bound Markdown snapshot from repo-controlled `autopilot/w27_backlog.json` using the W27 safe backlog validator. The target is **only** `docs/autopilot-proposals/BACKLOG_STATUS.md`. Default is zero-write dryrun; `--write` requires `EDU_AUTOPILOT_DOC_PR_ENABLE=1`, pre-existing project-owned directory, and refuses symlinks/unowned files. Output contains never-completed AUTO_PROPOSAL vs BLOCKED_EXTERNAL, no real messages and no raw LLM proposal text. It reports correctly that writing docs to local workspace is not pushing GitHub or opening a PR.

The branch-hosted workflow defaults to read-only preview. Only when repo variable `EDU_AUTOPILOT_DOC_PR_LIVE=true` is explicitly configured on **main scheduled/manual runs**, the second **GitHub-hosted** job receives narrowly scoped contents/pull-requests write permission. It refuses a duplicate open PR, stages only the one fixed `docs/...` file, creates a distinct review-required branch and uses `gh pr create`. No auto-merge, no arbitrary executable change, no model-generated code, no real endpoints or organizational IT authority. Actions permission restrictions can block bot PR creation; until an actual run succeeds do not claim PR automation is working.

The W28B workflow and Python regressions must PASS on branch and exact main after merge. W28B docs PR creation is **not an AI agent**. Additional W29 engineering is required for branch-isolated AI-generated code edits and fail-closed CI repair loop.

Rollout 2/6, workflows 0/8 until separately authorized institutional acceptance.