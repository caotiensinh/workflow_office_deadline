# W32A — Trusted exact-head GitHub workflow identity gate

## Objective

Prevent a bot-created, fictional-document-only PR from being marked CI-verified using a workflow run with a familiar display name but an untrusted origin. Preserve human review; never auto-merge.

## Observed real provenance from W31D

PR #66 exact head `b8e154bde4c786bec52c38c819208963409d697a` successfully dispatched these four real GitHub Actions jobs:

| Trusted workflow | Immutable workflow ID | Workflow file | Successful run |
| --- | ---: | --- | ---: |
| Hybrid Workflow CI | 388590017 | `.github/workflows/ci.yml` | 39548578633 |
| Windows Synthetic E2E | 388610038 | `.github/workflows/windows-e2e.yml` | 39548580887 |
| W4 Windows Desktop Alert E2E | 389392239 | `.github/workflows/w4-desktop.yml` | 39548582931 |
| W5 Windows Desktop Package & User-Session Safety | 389574496 | `.github/workflows/w5-desktop.yml` | 39548585338 |

The GitHub run API for each showed exact head SHA, branch, matching workflow ID/path, event `workflow_dispatch`, `actor=github-actions[bot]`, and both repository identities `caotiensinh/workflow_office_deadline`.

## Code change

`autopilot_pr_gate_w31b.py` now requires all workflow name, immutable ID, exact workflow path, exact SHA, exact branch, same repository/head repository, trusted bot actor, completed SUCCESS and dispatch event. For repeated runs at the same exact SHA and workflow, only the newest run ID/attempt counts: a later failure or pending run supersedes an earlier green. No model generated code is executed and no write/merge token is involved.

The existing `tests/test_autopilot_pr_gate_w31b.py` fixtures now include real API metadata. Thirteen new adversarial cases cover incorrect ID/path, repository/branch/actor/event, missing provenance, wrong ID type, and run ordering.

## Acceptance

- [x] Exact feature HEAD `71b9c0d6cf709ab3fc1242cdd9a121c58a0c5063` completed **478/478 Python PASS and Rust success** on Hybrid CI #39557581567; Windows Synthetic #39557581682, W4 #39557581734 and W5 #39557581554 also completed SUCCESS, all at this exact SHA.
- [x] Specialized GitHub-hosted W31B audit #39557575680 SUCCESS at same exact feature HEAD: 26/26 focused tests PASS and direct GitHub API audit of PR #66 prints `W32A_REAL_GITHUB_BOT_PR_66_FOUR_TRUSTED_WORKFLOWS_ID_PATH_ACTOR_SHA_PASS_NO_MERGE`; PR #61 remains HOLD, no merge.
- [ ] After reviewed merge, verify 4/4 CI on the new `main` HEAD and report hashes.
- [ ] External IT/Outlook, actual three Ollama requests on Linux and real 3 coding-agent loop remain separately UNVERIFIED.

No official institutional approvals or production signoffs are inferred from this hardening work.
