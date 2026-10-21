# W31D — Trusted GitHub-token workflow_dispatch of exact bot PR SHA

**Goal:** Prove the missing W30→W31 link: GitHub Actions can create a harmless reviewed PR **and separately trigger all four real standard CI workflows at its generated branch HEAD**, without treating action_required checks as success, bypassing a reviewer, or executing model-authored code.

## Why

GitHub Actions-generated PR #61 exists (W30 SUCCESS) but normal `pull_request` runs are `action_required`. PR #61 remains unmerged; the W31B audit correctly rejects this missing CI evidence. `workflow_dispatch` is one of the allowed secondary events of `GITHUB_TOKEN`, so the new one-time acceptance has an independent way to request CI without using a PAT or elevated GitHub app.

## Implementation

1. Four trusted standard CI workflow files add `workflow_dispatch:`; no changes to their core tests, default `contents: read` permission, or production permissions.
2. `.github/workflows/w31d-trusted-ci-dispatch.yml` has read-only feature-branch preview and a write job **only on `main`** of the exact repository with user-enabled `EDU_AUTOPILOT_DOC_PR_LIVE=true`. It never runs write operations from a PR or feature branch.
3. On its first qualifying main push, the job writes **one static fictional documentation file** `docs/autopilot-proposals/W31D_TRUSTED_CI_DISPATCH.md`, stages exactly that file, pushes a unique bot branch, opens one review-required PR, then asks GitHub to dispatch `ci.yml`, `windows-e2e.yml`, `w4-desktop.yml`, and `w5-desktop.yml` against that exact new branch.
4. It emits `W31D_FOUR_REAL_CI_DISPATCHES_REQUESTED_NOT_CI_PASSED_NOT_MERGED`. This marker proves dispatch requests, **not success**. Exact PR-head `head_sha` and 4/4 successful `workflow_dispatch` run conclusions must be inspected independently.
5. Duplicate one-time titles or already-merged documentation are skipped, no blind retries. PR creation failure attempts to remove only the newly created branch; no auto-merge, no IT/mail authorization, no local Ollama calls.

## Acceptance and risk

- First require 4/4 ordinary feature-head CI plus the specialized hosted contract PASS.
- After safely reviewed merge, verify the **main push publisher SUCCESS**, a real new `github-actions[bot]` PR with the expected **one-file diff**, and 4 separate completed SUCCESS dispatch-origin workflow runs **all at the same exact bot PR head**.
- Even if all four checks pass, PR **requires independent human review** before merging. Do not merge code, workflows or human-approval changes autonomously; W31B gate does not perform merges.
- If dispatch fails, inspect actual job output and API error. Do not claim success from a successful PR alone or re-run blindly.
- Does not solve the W31A self-hosted Linux worker queue or prove autonomous code patch/repair; institutional rollout still 2/6 and production signoffs 0/8.
