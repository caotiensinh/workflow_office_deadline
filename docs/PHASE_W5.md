# Phase W5 — Desktop visibility, one-click Windows package and opt-in login startup

## Goal and safety boundary
Provide a portable Windows notification-center EXE and explicitly user-opted-in current-user Startup shortcut, with no administrator privileges, global registry writes, new service, scheduled tasks or access to the institution's email. **The existing MRCAO self-hosted runner is Session 0, so actual visible GUI acceptance is still blocked without a signed-in interactive Windows account.**

## W5 code
- \`desktop_app.launch\` refuses to start a fake desktop UI in Windows Session 0; the exception names the limitation.
- Notification bells now re-trigger **once** when a snoozed alert disappears and later reappears, while ordinary refreshes do not spam.
- \`windows/build_desktop.ps1\` packages \`windows/notification_entry.py\` to \`dist/EDUNotifications.exe\` with PyInstaller on a Windows CI runner. Python and Tkinter are bundled into an unsigned EXE; check antivirus/SmartScreen and organizational policy before deployment.
- \`windows/manage_desktop_startup.ps1\` defaults to **PlanOnly**, returning a JSON description with no mutation.
- The opt-in \`-Install\` action creates a **current-user Startup-folder link**, not an elevated task or service. It refuses production installation from Session 0.
- \`-Remove\` rolls back only the shortcut owned by this project; unknown/conflicting links are not modified.
- A CI-only isolated Startup directory inside GitHub \`RUNNER_TEMP\` proves install/no-overwrite/remove without touching the real user's Startup.

## Operator workflow after institutional review
1. Obtain and independently hash-check the W5 Windows EXE from the successful GitHub Actions artifact. The executable is **unsigned** and not a production release.
2. Run a synthetic sample in a writable user-owned folder, not a shared school database; ensure the EXE and DB are allowed under institutional IT policy.
3. Run \`windows/manage_desktop_startup.ps1 -PlanOnly -Executable <approved-exe-path> -DbPath <user-owned-db-path>\`.
4. From a real **signed-in interactive user account** (not MRCAO Session 0), after IT approval, \`-Install\` can register login startup. Do not allow a service runner to configure the user's Startup.
5. Roll back with the matching \`-Remove\` options; it removes only this project's shortcut and does not alter the background Python/Rust worker.

## CI and field acceptance
- [ ] W5 seven Tk callback/preflight regression tests and W4 model PASS (code committed; hosted CI pending).
- [ ] One-file Windows desktop EXE built and \`--help\` smoke tested.
- [ ] Startup test in **isolated** directory succeeds; no real user Startup changes.
- [ ] On MRCAO, Session ID captured, UI availability truthfully reported.
- [ ] W5 PR merged, main CI PASS.
- [ ] Real desktop visible UI screenshot *of only our app*, bell, keyboard/mouse button clicks, after-login startup, logoff safety confirmed in interactive user session (external blocker).
- [ ] Approved production Outlook, SMTP, SSO and IT data-protection acceptance (external blocker).

## Why real GUI acceptance is still separate
GitHub Actions service-based Windows runners execute in Session 0 and cannot display a Tkinter window in another user's desktop session by design. Running a process from Session 0 cannot prove users saw an alert. Never launch in someone else's login session, inject clicks, read the real desktop, or alter account startup without explicit local consent. This project therefore reports **CI package and model PASS** separately from **interactive visual acceptance pending**.

## Current acceptance checkpoint

- Branch `feat/w5-interactive-desktop-acceptance`, PR #9: OPEN. The GitHub-hosted W5 packaging and regression jobs were still `queued` at the last check; **no verified W5 EXE or GUI acceptance yet**.
- W5 now includes seven controller/preflight tests; total required Python regressions: **100**. The CI guard requires the W1–W5 test suites to remain present.
- Python GUI launcher explicitly refuses Session 0, and hosted CI's sandbox Startup test is separate from production login. No app was installed on MRCAO.
- A real user-visible notification must still be checked within a signed-in interactive Windows session and after an actual logout/login cycle, with organizational authorization.

## W5 isolated regression finding — 2026-10-20
Before GitHub CI runners became available, seven fake-Tk controller tests were reconstructed in an isolated local Python environment against the current W5 desktop controller. Two tests failed due to test-only argument indexing: `mark_notification(conn, alert_id, actor, choice)` was asserted as if `choice` were argument 3 rather than argument 4. A related ACK assertion incorrectly expected no fourth argument. All three assertions were corrected in commit `5494441ba17ff853f15e087f5535cf4840c92280`; rerunning the seven isolated tests yielded 7/7 PASS.

This is **not** a GitHub Actions run, not an EXE package test and not visual acceptance. Required hosted CI checks on PR #9 were still queued with no runner assignment when inspected, including Ubuntu, Windows and self-hosted labels. Subsequent verification of the official GitHub incident API confirmed **degraded GitHub Actions availability** starting 2026-10-19 15:49 UTC (2026-10-20 00:49 JST). GitHub explicitly warned of workflow-processing delays. This is consistent with queued jobs across hosted and self-hosted labels, though the repository's own job assignment root cause was not independently proven. Verify repository Actions permissions, current runner availability and any account budget/storage policy if the queue does not move; do not merge an unverified build.

## W5 Actions incident and queue hygiene — 2026-10-20

- Official status evidence: https://www.githubstatus.com/api/v2/incidents/unresolved.json (incident `8tzbpcnl75jp`, GitHub Actions/Pages/Webhooks degraded, report updated 2026-10-19 15:56 UTC).
- Four CI workflows were changed to run on **pull requests against main and pushes to main only**, rather than triggering duplicate push+PR runs for every feature commit.
- Concurrency now scopes to workflow + PR head branch and cancels obsolete *new-format* runs. Previously queued historical runs may remain queued because their configuration had no concurrency group; no claim of cancellation is made.
- The read-only MRCAO Session 0 preflight moved to a separate feature-branch-only workflow and does not checkout PR code or mutate real Windows Startup/Task Scheduler.
- Last observed W5 PR head: `385f21fdd4c3fed2e5e08e7c2af23615e88732f5`; CI remains queued without assigned hosted/self-hosted runners and **cannot be marked PASS**.
- Continue on the current checklist after GitHub Actions scheduling recovers; do not merge the unverified unsigned EXE release.

## W5 database path validation (2026-10-20)

Static review of `open_store()` confirmed that the SQLite API creates a new file when an invalid GUI path is supplied. W5 now rejects a missing, symbolic-link or non-SQLite database **before creating the Tk window or calling open_store**, preventing a false empty-work queue. Two new negative tests cover nonexistent and invalid database files. Existing fake-Tk controller tests mock the validated database path and remain unchanged in behavior. The local mirrored 40 reference tests + 9 W5 tests passed (49/49), but this is **not** the complete 102-test suite or a Windows EXE acceptance. The full CI guard is now 102 and remains pending Actions scheduling.

## W5 real Tk rendering smoke (Linux/Xvfb)
- [x] Executed actual Tkinter window with a synthetic SQLite header and fake event adapter on an isolated local Xvfb display (2026-10-20): **PASS**. Verified rendered 790x460 window, Japanese labels, Treeview row, ACK click removing the row, and cleanup on WM_DELETE_WINDOW.
- [x] Added `tests/w5_real_tk_smoke.py` and a CI step running it via `xvfb-run -a` on Ubuntu, alongside the existing 102-test unittest suite.
- [ ] GitHub Actions Linux Xvfb job still must PASS on the PR HEAD; actual test of user-visible Windows fonts, mouse, bell and login startup is not replaced by Xvfb.
- The local Xvfb screenshot uses a fictional case ID only and is **not an actual Windows desktop screenshot**.

## Final W5 CI acceptance — 2026-10-20

PR #9 merged to main as `fbe8aaffebdf791a9c040d05e550bc599cfd1ee1` after green branch CI. Post-merge GitHub Actions all SUCCESS: Linux 102/102 + real Tk Xvfb smoke #39327397812, Windows legacy #39327397881, Windows W4 #39327397739, Windows W5 build + standalone GUI preflight + sandbox Startup install/rollback #39327397726.

The earlier W5 Startup job failure was a test-driver bug: a stale native `$LASTEXITCODE` was inspected after invoking a PowerShell script which had actually created the shortcut. Replaced with direct output-artifact verification and repeated the full workflow to PASS (branch #39327099946 and post-merge #39327397726). W5 EXE is unsigned and must not be presented as production-ready. The only self-hosted W5 check was **read-only Session 0 probe** on MRCAO; the Windows W5 executable/Startup E2E was executed on `windows-latest`, not MRCAO. Actual signed-in Windows GUI remains unverified.

See [W5 acceptance report](W5_TEST_REPORT.md) for the complete evidence table and remaining approval gates.
