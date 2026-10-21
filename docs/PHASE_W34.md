# W34 — Runner queue diagnosis and guarded obsolete-run cancellation

## Product objective

Keep the 24/7 Autopilot pipeline moving without killing legitimate long-running AI work or masking absent hardware. Differentiate a **job waiting without a runner**, a **runner-assigned queued job**, and a **task actually executing**. A job remaining QUEUED without assigned runner does not consume the Ollama server CPU. Do not call it a hung process.

## Actual live input (2026-10-21 JST)

GitHub run `39546648473` on W31A feature branch was created `2026-10-21T04:55:07Z` and remained `queued` with `conclusion=null`. Its `hosted-contract` job succeeded, while `linux-real-ollama-acceptance` job `119046212555` remained `queued`. The available job records show no assigned runner. Repository runner inventory endpoint was not exposed to the GitHub connector, so whether an authorized runner is offline, busy elsewhere, or absent is **unknown**. Do NOT cancel a hypothetical running Linux process based on this queue.

## Implemented runtime

- The `autopilot_runner_watch_w34.py` monitor obtains real run/job state via authenticated, read-only `gh api`; distinguishes assigned vs unassigned vs running and reports without GitHub writes.
- Attempts an optional runner inventory check. Lack of runner-settings permission is **INVENTORY_UNAVAILABLE**, never interpreted as zero registered runners.
- A carefully scoped cancel can only target a run which is already **obsolete**: older than 30 minutes, wholly unassigned/no active tasks, older than another SUCCESS from **the same workflow and branch** on the currently verified branch HEAD. It must re-fetch all evidence a second time immediately before cancelling; it cannot cancel the live-HEAD W31A queued run, or an actual running task.
- The dedicated workflow runs hosted synthetic unit tests plus **actual GitHub API read-only queue diagnosis**. It will execute hourly after merging to main, and on feature push/PR for premerge validation.
- Repository variable `EDU_W34_ALLOW_OBSOLETE_RUN_CANCEL=true` is required for the narrow `actions:write` reconciliation job on main; absent it, reconciliation is skipped. This variable must not be turned on before branch review. Cancellation of obsolete runs is not an alternative to registering an online matching Linux runner.

## Acceptance

- [ ] Focused regression suite PASS, including old-queued-safe candidate, double check, lost-race becomes in_progress, no cancellation of live work.
- [ ] Actual read-only GitHub API audit classifies W31A correctly and does not cancel it.
- [ ] Four standard project Linux/Windows CI workflows SUCCESS on exact PR head.
- [ ] Independent reviewer approves merge; verify main exact-head CI afterwards.
- [ ] Authenticated Linux runner online and available to **this repository**; real three Ollama models with bounded CPU/RAM; actual local receipts PASS. This is a separate operational blocker.
- [ ] Future watchdog observes heartbeat/actual work progress before ever considering stuck active-job termination; no process-level termination is implemented here.

**No employee/Outlook/endpoint production data or IT control.** Scheduled diagnosis is autonomous but does not itself provide AI-generated-code/repair/PR/merge lifecycle.

## Live GitHub-hosted acceptance — 2026-10-21 JST

- Hosted workflow **#39570350653** PASS on source HEAD `056038a4fc27efa2ce6d1518c990702ee361c8cc`, **25/25 focused tests PASS** and real authenticated GitHub API queue query PASS.
- Observed W31A workflow run **#39546648473**, Linux job **#119046212555**: `run_status=queued`, `active_jobs=0`, `queued_jobs=1`, **`queued_assigned_jobs=0`**, and current feature branch HEAD still matches `5cba2bebacc6130307f2e043c27dd63675e74d99`. Therefore `cancel_safe_obsolete=false`; no cancellation and no new inference claim.
- The completed GitHub-hosted sibling carries its own historical runner assignment (`assigned_jobs=1`); that assignment does **not** prove that the waiting Linux Ollama job occupies a runner. A regression was found and fixed to distinguish these; both the API audit and tests confirm the correction.
- GitHub's runner inventory API is inaccessible with this workflow's low-privilege token: `RUNNER_INVENTORY_PERMISSION_OR_API_UNAVAILABLE`. Whether a suitable runner is offline, busy in another repo, unavailable to this repository or absent is still UNVERIFIED; do not guess.
- The restricted reconciliation job was **skipped** (feature branch, no main opt-in). No `actions:write` operation was attempted, no live process was killed, and current task must not be canceled until an independent safety condition is proven.

**Operational next action:** check runner registration/assignment for repository `caotiensinh/workflow_office_deadline` in GitHub Settings → Actions → Runners, and ensure the authorized Linux server is online with local Ollama and enough RAM/CPU. Merely cancelling and re-queuing the same unassigned job cannot fix unavailable runner capacity.

## W35 — Guarded recovery for active work and superseded queues (2026-10-22 JST)

**Implementation:** `python/edu_workflow/autopilot_runner_recovery_w35.py` and `tests/test_autopilot_runner_recovery_w35.py`; dedicated W34 workflow now invokes both W34/W35 regressions, real queued inventory scan and bounded live active-run sampling.

**1. Actual in-progress job versus suspected overrun:** sample job/step state at three distinct points, at least 20 seconds per interval. A step transition counts as progress: KEEP. If step details are missing/ambiguous, job is unknown or within its budget, or another active/queued job is present, KEEP. An allowlisted job (`linux-real-ollama-acceptance` 15-minute workflow timeout; `selfhost-real-ollama-three-processes` 17-minute timeout) can only request GitHub run cancellation after exceeding that declared timeout **plus 15-minute grace** with no step transition through every fresh sample, and only with explicit main-only variable `EDU_W35_ALLOW_OVERBUDGET_CANCEL=true`. This is an **over-budget policy**, not proof of zero internal model progress; unrecognized long-running jobs are always preserved. No operating-system process kill is implemented.

**2. Superseded queued run:** the prior W34 rule checked newer run-level SUCCESS only. W35 additionally fetches the entire newer job list and demands all queued job names from the older run individually finished **completed/success**, with no skipped/failed/pending successor job. A hosted-only mock SUCCESS cannot substitute for missing Linux Ollama acceptance. Require same workflow/branch, exact current branch SHA, no active or assigned queued job, 30-minute stale threshold and two fresh complete API reads immediately before the cancel request. Explicit main-only `EDU_W34_ALLOW_OBSOLETE_RUN_CANCEL=true` remains the separate opt-in. No unconditional GitHub job kill, restart or automatic retry.

**Real hosted evidence (initial):** GitHub run `39691756162` finished SUCCESS, 26/26 W34 and 30/30 W35 regressions PASS, and authenticated read-only GitHub API calls succeeded. W31A #39546648473 still had one queued, unassigned Linux Ollama job and `safe_cancel=false` on its exact current HEAD. Dynamic queued scanning identified the same run and did not cancel it. Read-only active scanning sampled three actual GitHub runs and returned `cancel_requested=false` for all: one was not an allowlisted worker and two had no confirmed overrun. This demonstrates **the live diagnostic**; it does not prove a real overrun has been cancelled in production.

**Release and limitations:** safe-reconcile jobs are SKIPPED on the feature branch; **neither cancellation path has been executed against a live run**. They only become main-scheduled after review/merge and their distinct repo variable is explicitly enabled. Public GitHub job API does not establish internal Ollama token progress or local process CPU use, so unchanged steps by themselves never imply a proven deadlock. Runner inventory remains inaccessible to the read-only token; Linux runner availability is unknown.

- [x] W35 positive/negative tests and real read-only queue/active audits PASS on initial code SHA.
- [ ] Exact **final PR HEAD** standard 4/4 Linux/Windows CI and W34/W35 audit PASS, then independent review.
- [ ] Real runner + local installed 3 Ollama models proven, model patch/repair/PR lifecycle proven; not supplied by this watchdog.
