# W27A — Safe Autopilot Queue (deterministic)

## Mission
Python+Rust institutional office automation WF01–WF08. Important decisions, real data and production access always require actual institutional authorization and human approval. PUBLIC GitHub repository contains fictional only.

## Runtime
`python/edu_workflow/autopilot_plan_w27.py` validates strict `autopilot/w27_backlog.json` with explicit AUTO_PROPOSAL and BLOCKED_EXTERNAL types, refuses forged human permission, duplicate tasks, control characters and malformed JSON. A hosted-**Ubuntu** read-only GitHub Actions workflow `.github/workflows/w27a-autopilot-plan.yml` runs on default branch twice daily when merged, or via workflow_dispatch. It emits a short-lived CI artifact reporting queue and blockers, without changing repository, GitHub privileges, data sources, other machines or approval status.

Unit suite `tests/test_autopilot_plan_w27a.py` tests safe queue splitting, required human gates and a deterministic docs-only merge eligibility policy that requires **the same exact Git SHA on all four normal CI workflow names**. Even eligible docs-only work is ONLY recommended for policy review; no merge is executed. All source code, workflows, secret paths, binaries and Windows scripts are outside the eligible auto-merge scope.

## Proof and limits
`PLANNED_ONLY_NOT_RUNNING_AGENTS` means precisely zero autonomous model workers running. Do not confuse GitHub scheduling with real local model inference or actual workplace/GUI acceptance. The schedule is not a session of ChatGPT running forever. Never auto-escalate `BLOCKED_EXTERNAL`, and never auto-mark 2/6 rollout or 0/8 production workflow gates PASS.

## Acceptance
Exact PR-head 4/4 CI plus W27A hosted workflow marker `W27A_DETERMINISTIC_UNATTENDED_PLAN_PASS_NOT_AI_AGENTS`; on merge verify an unattended scheduled/default-branch plan if possible, and 4/4 postmerge. The plan is a safe foundation for an actual agent worker layer, not the entire end-to-end automated developer.