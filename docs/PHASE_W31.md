# Phase W31 — Real local Ollama gate and autonomous PR review safety

**Mission:** Progress from unattended GitHub-bot docs PR generation to a verifiable, resource-bounded Autopilot. This phase must NOT claim autonomous coding, automatic repair or production acceptance without the corresponding real run.

## Verified on 2026-10-21 (JST)

- W30 main-push run **39541564616 SUCCESS**, generated actual GitHub Actions bot PR **#61** (author `github-actions[bot]`; SHA `8be674d832220985a228d85ac75b944fca4af5c3`). PR #61 is review-required and unmerged. Its four ordinary `pull_request` workflows ended `action_required`, NOT green.
- Current main immediately before W31B was `86bf863c9366a4072e4d549a10efc4928d643e3e`, ahead of the prior W30 merge `f2cecfcaed9c920553eb3d850f9655f1a80cbb1e`.
- **Lane W31B PR #63 merged**, exact feature HEAD `acbfc9d09ff4c724c391118684e1e6110d236fd8` and merge commit `ca1ecea1af01b1aa723321f26fc0e114eeb21dfe`. Hosted audit **39546933717 SUCCESS** and 4/4 exact-feature-head standard CI SUCCESS. Read-only actual GitHub API inspection reports bot PR #61 as `HOLD_EXACT_SHA_CI_NOT_PROVEN`, never auto-merge. Python regression floor now **457** (444 previously + 13 W31B cases), confirmed by main Linux CI job `119048015530`.
- **Lane W31A PR #62 OPEN** (feature HEAD `5cba2bebacc6130307f2e043c27dd63675e74d99`). All **4/4 standard feature-head CI PASS**. Specialized workflow **39546648473** has `hosted-contract` PASS but its real `linux-real-ollama-acceptance` self-hosted Linux job is **QUEUED**, no 3 real calls proven. This dedicated branch triggers a CPU-only 3-model admission-gated acceptance attempt (no model downloads, no GPU, no Git writes, no model prose publication). Merge requires real-run evidence, not hosted mocks.

## Next real acceptance gates

1. Attach an authorized **online self-hosted Linux runner to this exact repository** with label `self-hosted` + `Linux`, local Ollama loopback on port 11434, three independently installed models each <=4 GiB, >=8 logical cores, <=50% 1-minute load, and sufficient RAM as enforced by W29A. The queued job must complete and emit `W31A_REAL_THREE_CPU_OLLAMA_CALLS_VERIFIED_NOT_INDEPENDENT_AGENT_PROCESSES`. If capacity is insufficient, report the reason; do not download more models or weaken limits without approval.
2. Three simultaneous inference **requests** are not independent OS-level coding agents. Implement sandboxed independent processes with patch generation/test/CI repair only after real model proof, bounded budgets and fail-closed permission controls. No model output may directly execute arbitrary shell or alter trusted paths.
3. A bot-created PR is not proof of CI. Require trusted exact-HEAD 4/4 CI and independent human review before even documentation-only merge. Keep PR #58 and PR #61 OPEN until their independent review and checks.
4. Institutional rollout is still **2/6**, production workflow signoffs **0/8**. Real Outlook/recipients, signed-in Windows Session 1, actual endpoint scheduling and HR/personnel approval require institution IT/human authorization.

## Autonomy truth table

| Capability | Verified |
| --- | --- |
| Unattended deterministic backlog/docs branch/PR (GitHub Actions bot) | YES — #61 |
| Bot PR read-only policy & CI-gap audit | YES — W31B |
| Three CPU-only local Ollama inference calls on owned Linux runner | NO — W31A queued |
| Three independent model-driven coding-agent OS processes | NO |
| Model-authored safe patch + genuine tests + auto-repair PR | NO |
| CI-verified reviewed safety-gated merge and repeated autonomous coding cycle | NO |
| Live institution use / signed approvals | NO |

All claims apply only to the named evidence, not a broader production guarantee.


## W31D verified follow-up (2026-10-21 JST)

The previously missing GitHub-bot PR → exact-head CI dispatch link is now verified by actual GitHub Actions: main run #39548563982 created reviewed PR #66 as `github-actions[bot]`; the bot PR head `b8e154bde4c786bec52c38c819208963409d697a` ran **four successful independent workflow_dispatch workflows** #39548578633, #39548580887, #39548582931, #39548585338. Main merge `02d5174e2108fc03cfe90a77866ffa902fd2c1c7` itself passed 4/4 standard CI, **465/465 Python tests** and Rust. PR #66 remains OPEN pending review. This is CI autonomy for a deterministic fictional docs PR, not AI-generated code or a repaired failing test. W31A Linux Ollama proof still QUEUED. Details: `docs/PHASE_W31D.md`.
