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


## Observed real main-push acceptance (2026-10-21 JST)

- PR **#65** exact feature-head `ec67ec29a8474df4202298779aa53f1fc119f279`: **5/5 SUCCESS** (specialized hosted W31D #39548370983 plus all 4 standard PR CI). MERGED as `02d5174e2108fc03cfe90a77866ffa902fd2c1c7`.
- On this **exact merged main** commit, actual unattended publisher **#39548563982 SUCCESS** (both `hosted-policy-preview` and `one-time-bot-pr-and-dispatch` jobs). Logs show `W31D_REAL_GITHUB_ACTIONS_BOT_PR_CREATED`, four `W31D_DISPATCH_REQUESTED_WORKFLOW` lines and `W31D_FOUR_REAL_CI_DISPATCHES_REQUESTED_NOT_CI_PASSED_NOT_MERGED`.
- Bot itself created **PR #66** https://github.com/caotiensinh/workflow_office_deadline/pull/66 as **`github-actions[bot]`**, head `b8e154bde4c786bec52c38c819208963409d697a`, exactly one added file `docs/autopilot-proposals/W31D_TRUSTED_CI_DISPATCH.md`. Still **OPEN, REVIEW REQUIRED, NOT MERGED**.
- **ACTUAL 4/4 BOT PR HEAD CI PASSED**, all `workflow_dispatch`, same exact PR head `b8e154bde4c786bec52c38c819208963409d697a`:
  - Hybrid Workflow CI Linux Python/Rust **#39548578633 SUCCESS**
  - Windows Synthetic E2E **#39548580887 SUCCESS**
  - W4 Windows Desktop Alert E2E **#39548582931 SUCCESS**
  - W5 Windows Desktop Package & User-Session Safety **#39548585338 SUCCESS**
- The ordinary PR-triggered runs remain `action_required`, but the independently dispatched four exact-head runs genuinely passed. Do not conflate their event types.
- Postmerge main `02d5174e2108fc03cfe90a77866ffa902fd2c1c7`: **4/4 standard CI SUCCESS**, Python **465/465 PASS** and Rust success in #39548563918; Windows E2E #39548563917, W4 #39548563947, W5 #39548563983. W29B and W30 repeat-push jobs correctly idempotent SUCCESS.
- **Remaining:** PR #66 still requires actual review before merge; existing PR #61 has not been upgraded or independently run through the new dispatch route. W31A PR #62's actual `[self-hosted, Linux]` inference remains QUEUED and is not local model evidence. No 3 independent coding processes, safe model patch/auto-repair, or autonomous code lifecycle is claimed. Institution rollout remains 2/6, signoffs 0/8.

**Verdict:** W31D's *bot PR creation → 4/4 exact-SHA CI dispatch* acceptance is **PASS** with real GitHub Actions evidence. Autonomous AI code-writing/repair and unattended production acceptance remain **NOT PROVEN**.
