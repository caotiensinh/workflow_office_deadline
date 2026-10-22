# W38 — Persistent lease and restart-safe worker recovery

## Product goal

Keep the approved public/synthetic-only Autopilot task queue moving across worker crashes and orchestrator restarts, without duplicating already-successful tasks or accepting late output from a previous lease owner. W38 builds upon W33's three independent OS workers, W36's real token-fragment heartbeat, and W37's bounded alternate-task dispatch. It **does not** establish model-authored code patch/repair, autonomous GitHub PR publication or reviewed merge.

## Runtime implementation

- `python/edu_workflow/autopilot_task_lease_w38.py` uses SQLite with durable WAL journal, `BEGIN IMMEDIATE` transactions and owner-fenced random lease tokens. Only approved `AUTO_PROPOSAL` task IDs, canonical task fingerprints, owner/token/deadline/attempts, numeric token-chunk count, and SHA256 of accepted output are stored. No model text, prompt, employee data, secret or actual Outlook content enters SQLite.
- States: `PENDING → LEASED → DONE`, `LEASED → PENDING` on recoverable failure, `LEASED → FAILED` after two bounded attempts, and expired `LEASED` eligible for one fenced reclaim while attempts remain. `DONE` tasks never re-run after restart. An expired owner cannot renew/finish an already reclaimed lease. Changed backlog task content for an existing task ID is rejected.
- Lease duration 165 seconds for initial work, extended for 90 seconds **only if observed Ollama response chunk count increases**; still bounded by original start +600 seconds. Synthetic test fixture can complete with no Ollama inference, but its receipt remains `actual_ollama_calls=0`.
- W33/W37 coordinator now operates 1–3 lanes when durable state is enabled, so a restart with only one remaining task will actually process it rather than stall awaiting three tasks. Successful siblings are committed individually after result identity/review validation; even a third-worker failure with no available successor does **not** roll back the other two successes. W37 may replace failed lanes only with distinct still-authorized tasks and at most once per lane.
- Enable persistence only on **an authorized persistent directory outside the Git checkout**: set `EDU_W38_PERSISTENT_LEASES=1` and invoke `python -m edu_workflow.autopilot_process_w33 --execute --state-dir /OWNER_APPROVED_PERSISTENT_DIR`. The existing Linux self-hosted workflow can receive this as repository variables `EDU_W38_PERSISTENT_LEASES=1` and `EDU_W38_STATE_DIR`; it still requires the independent W33 live gates and a matching online runner. If those variables are absent, W33 retains nonpersistent behavior. Hosted GitHub Actions temp directories are ephemeral and **cannot prove durable across real host reboots**.
- Only repository-authorized `AUTO_PROPOSAL` jobs can be seeded. `BLOCKED_EXTERNAL`/IT/Outlook and human-review decisions are never admitted. Model workers do not inherit GitHub credentials, run generated source or automatically approve/merge.

## Evidence and remaining gates

- Real GitHub-hosted W33 workflow [#39713803434](https://github.com/caotiensinh/workflow_office_deadline/actions/runs/39713803434) finished SUCCESS at source checkpoint `3a3316b6f77b142003c9d66b19daaf5d5ae1bf88`, with **18 W33 +25 W36 +13 W37 +25 W38 focused tests passing**.
- On real OS child processes with synthetic inference only, the specialized workflow ran: first execution completes three tasks in SQLite → restart processes remaining one task → another restart returns `IDLE_NO_APPROVED_READY_TASKS` and zero inference/replays. W38 tests also verify owner token fencing, simultaneous multi-owner claims, expired lease reclaim, monotonic progress renewals, max attempt exhaustion, no-result tampering, no-symlink state and preservation of two successful siblings when the third worker fails with no replacement.
- [ ] Four standard GitHub CI workflows plus specialized acceptance must PASS on the **final** PR #70 SHA; independent human review before merge.
- [ ] Actual persistent path on the designated self-hosted Linux runner and recovery after a real worker/host restart must be observed; currently the self-hosted Ollama job in W31A #39546648473 remains **QUEUED** (not verified).
- [ ] Actual bounded three-model local Ollama inference with stream token progress; trusted model-generated source patch, isolated test/repair, reviewed pull request and unattended repeat. **NOT IMPLEMENTED/PROVEN** by W38.
- [ ] Cross-run GitHub queue watchdog W34/W35 remains in separate PR #71 and is not merged. Never kill a queued unassigned job just to reduce wait time; don't cancel a running job without established policy/evidence.

**Safety:** Public synthetic examples only; IT and operational permissions unchanged; no production or personal data access.
