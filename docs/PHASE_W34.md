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
