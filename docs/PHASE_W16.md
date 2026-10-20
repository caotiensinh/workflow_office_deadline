# W16 — Actual Windows runner session readiness, not a fake GUI UAT

## Fixed objective
Automate office email intake, rule evaluation, deadline alerts, local document/evidence checks, scheduling proposals, and audit using Python and Rust. Human review is mandatory for extracted deadlines, HR appraisal, regulatory interpretations and external decisions.

## Why W16
The previous W15 performed a **real** core E2E on self-hosted runner MRCAO: native Rust, portable Python, SQLite, six JSON notifications, audit and idempotency; but did not prove that the GitHub runner was launched under the same interactive desktop as the logged-in user. Before testing Tk GUI or Windows login Startup, measure that distinction.

## W16 implementation
- `tests/w16_session_probe.py`: a **minimal read-only** Windows API observer using `GetCurrentProcessId`, `ProcessIdToSessionId` and `WTSGetActiveConsoleSessionId`. No usernames, credentials, window titles, screenshots, browser, mail, task XML, registry, Explorer or services are read.
- Defaults to `PLAN_ONLY_NO_HOST_INSPECTION` without `--inspect`. The explicit inspection produces only numeric process/active-console session IDs and negative flags indicating that human GUI acceptance and Task Scheduler execution **have not been demonstrated**.
- Session 0 is `SESSION_0_GUI_UAT_BLOCKED`. Matching nonzero process and console session becomes only `CONSOLE_SESSION_CANDIDATE_NOT_UAT`, never a human validation. A mismatched session becomes `NOT_ACTIVE_CONSOLE_NO_GUI_UAT`.
- `--output` is only permitted in an already-existing subdirectory of GitHub `RUNNER_TEMP`, and refuses overwriting existing evidence.
- `.github/workflows/w16-selfhost-session-probe.yml`: hosted Windows builds/tests the actual Rust + portable CPython bundle and adds the W16 probe before sealing all files with SHA-256; self-hosted Windows runs W15 core E2E, then W16 numerical session probe using **CMD only**, placing only sanitized JSON evidence in its temporary directory.
- **Not** an interactive GUI launch, an IT-approved task installer, an attempt to change PowerShell ExecutionPolicy, or an email/SMTP smoke test.
- 12 synthetic safety tests protect fail-closed Session 0/no-console semantics. GitHub-hosted Windows E2E invokes the Windows API; Linux/Rust suites must also pass.

## Execution constraints
- W16 self-hosted workflow triggers **only** on push to `feat/w16-session-readonly-e2e`. No periodic checks, no main-target runner actions.
- Runner selector is `[self-hosted, Windows]`, so GitHub may select **MRCAO** or **DESKTOP-14SCTF4**; only completed GitHub job log identifies the actual machine.
- No non-temporary installation, Task Scheduler registration, PowerShell script execution, Outlook, SMTP, institution data or changing Windows security policies.
- The GitHub-hosted build fetches Python from python.org, and transfers the bundle as a short-retention GitHub artifact. The bundle SHA-256 manifest is an integrity check relative to CI, not an enterprise release signature.
- If the runner is Session 0 or otherwise not the logged-in console, do NOT spawn GUI. It must be tested later with an approved signed-in Windows test user and physical operator interaction.

## Rollout and human acceptance
The original six rollout gates remain: (1) Python fake-data CI PASS, (2) native Rust integration CI PASS, (3) actual IT-approved 15-minute Windows scheduled run PENDING, (4) approved real Outlook read-only PENDING, (5) approved test recipient notification PENDING and (6) three pilots with operator sign-off PENDING.

**W16 session evidence cannot move gates 3–6 to PASS.** Production sign-off is still 0/8 workflows. Public repository: never use confidential employee/student/email records.

## Required acceptance records
- Self-hosted W16 job runner name, job ID and marker from exact log; no assumption from labels.
- On-machine Session ID result and any GUI-blocked/candidate classification; no human pass claim.
- PR 4/4 CI on exact HEAD, then exact postmerge 4/4; all results recorded in checklist.
