# W33 — Unattended bounded independent-OS-process AI lane

**Product objective:** Backlog → real local AI coding-agent work → bounded test/repair → PR → exact-head CI → independent review → safe merge → repeat. W33 implements the prerequisite **three real OS child worker processes** boundary, rather than three threads.

## Implemented architecture

- Python parent selects exactly three distinct fictional `AUTO_PROPOSAL` backlog tasks; blocked institution/Outlook/endpoint tasks are never dispatched.
- Parent checks installed localhost Ollama models, admitting three distinct models of at most 4 GiB each, at least 8 cores, at most 50% CPU load1 and sufficient available memory. No automatic model downloads; CPU-only `num_gpu=0`, `num_thread=2` and `num_ctx=1024`.
- Parent starts three child Python **OS processes** each assigned one model and task through JSON-only stdin; subprocess list with no shell and GitHub credentials omitted from child env. It launches all children before concurrent waits, kills unfinished children after failure and limits duration. Trusted child can only invoke localhost Ollama. Model text is review-only proposal, not source to execute, not approval, and never printed into public CI logs. Parent returns only hashed proposal identities and count metadata.
- Hosted GitHub Actions uses real OS processes with **synthetic model response fixture**; status `THREE_SYNTHETIC_OS_PROCESSES_NOT_REAL_OLLAMA`, actual calls 0.
- Live GitHub Actions lane on `[self-hosted, Linux]` runs only from **main** hourly cron `17 * * * *` or manual dispatch, and only if BOTH `EDU_AUTOPILOT_LIVE=true` and `EDU_AUTOPILOT_THREE_CPU_PROPOSALS_LIVE=true`. Read-only GitHub token; no model-authored code execution/PR/merge. An unavailable runner yields QUEUED (not PASS).

## Acceptance

- [ ] Hosted regression and actual 3 OS subprocesses using synthetic Ollama fixture PASS.
- [ ] Standard project 4/4 CI SUCCESS on same exact W33 PR HEAD.
- [ ] Real 3 Ollama calls from 3 OS processes on Linux self-hosted **PENDING authorized runner**.
- [ ] Real AI-authored code patch, sandboxed test and repair, authenticated PR publication, independent reviewed merge: **NOT IMPLEMENTED** by W33.
- [ ] Repeated autonomous lifecycle with durable work lease/backlog: **NOT PROVEN** merely by a cron schedule.

Only public synthetic data. Institution rollout 2/6, signoffs 0/8. Three OS processes are not three independent product coding agents.

## Hosted real-OS-process checkpoint (2026-10-21 JST)

- [x] Hosted run **#39568106515**, feature HEAD `65e45723981d505db44c70b4025a90d6e470df11`: **18/18 W33 regression tests PASS**; real three separate OS Python subprocesses executed a synthetic Ollama *fixture*; receipt `W33_HOSTED_THREE_REAL_OS_PROCESSES_FAKE_INFERENCE_NO_MODEL_CALLS`. This proves process isolation and control flow, **zero real inference calls**.
- [ ] Real self-hosted job for #39568106515 was correctly **SKIPPED** because branch is not main and live vars are not authorized in this feature run. Earlier PR #62 live Linux job #119046212555 in run #39546648473 remains QUEUED; do not claim Linux Ollama success.
- [ ] PR exact-HEAD standard 4/4 CI, independent review and real three-model receipt remain outstanding.

## W36 — Real Ollama streaming heartbeat + supervisor (2026-10-22 JST)

**Specific blocker addressed:** GitHub `in_progress` step status does not reveal model-token progress, and W33 formerly called `/api/generate` with `stream=false`. That prevented distinguishing slow useful inference from a worker no longer delivering output. W36 changes the *live worker transport* to local, redirect-disabled Ollama NDJSON `stream=true` and measures **actual non-empty Ollama response fragments**. A clock tick, status-only NDJSON message or synthetic fixture is **not** counted as inference progress.

- `autopilot_ollama_heartbeat_w36.py`: local POST only, bounded NDJSON line/total/text/chunk sizes, exact `done=true` required, duplicate JSON keys refused, CPU `num_gpu=0`, keep-alive 0. Numeric-only heartbeat in each child-specific private OS temp file: PID, increasing fragment count, state; never prompt, text, credentials or model output. Atomic replace; symlinks/overwrites rejected.
- `autopilot_process_w33.py`: three child processes inherit no GitHub token; parent monitors their numeric heartbeat while collecting child output. A real model is budget-stopped if it emits **zero fragments within 165 seconds**, emits no additional fragments for **90 seconds after first progress**, or exceeds a **600-second absolute cap** even if tokens continue. These are **resource/time budget limits**, not scientific proof of a deadlocked model. If a token count increases, parent does not classify the worker as no-progress. Synthetic workers retain original fixture path and hard timeout, and **never** claim Ollama receipt.
- Successful live receipts now require a matching child PID and at least one observed streamed response fragment. The only public receipt addition is `ollama_stream_progress_verified: true` on real successful inference, never its text. The W33 hosted CI tests include strict mocked Ollama NDJSON/parser tests, actual numeric-only heartbeat file tests, deadline/kill simulation and a real three-OS-child synthetic smoke.
- CI checkpoint: GitHub Actions specialized run **#39704981153** at code HEAD `98241aa8dc9d7698834c5802617a728d4cbb9fa5` succeeded with **18 W33 + 25 W36 regressions PASS**. The self-hosted **real** Ollama job was correctly SKIPPED on the PR feature branch, so actual inference remains **UNVERIFIED**.

**Release conditions:** 4/4 standard Linux/Rust and Windows workflows plus specialized W33/W36 acceptance on exact final PR #70 head, independent review, and a new `main` exact-head CI after authorized merge. Live three Ollama workers and 24/7 product coding/repair/automerge are separate gates. No production model run or host-process kill was done in this phase.
