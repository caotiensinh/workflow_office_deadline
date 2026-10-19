# Self-hosted Windows W4 E2E acceptance report

Date: 2026-10-20 JST (GitHub logs 2026-10-19 UTC)
Repository: caotiensinh/workflow_office_deadline
Runner: MRCAO, Windows self-hosted, service Session 0
Test commit: cb05d75b30b6f2954d659a7bf0e9d5743fba5d10
Verified successful run: https://github.com/caotiensinh/workflow_office_deadline/actions/runs/39275696459
Evidence artifact: selfhost-w4-e2e-evidence, ID 12196883599 (7-day retention)

## Verified on the actual MRCAO runner

- 93/93 Python W1-W4 regression tests: PASS.
- Rust native engine: compiled and unit tested on Windows hosted CI, exact compiled edu_rules.exe downloaded and executed on MRCAO: PASS.
- Initial synthetic EML import 3/3; second import 0 new; duplicate notifications 0.
- ACK and 30-minute Snooze persisted in SQLite after database reopen: PASS.
- Different local account visibility: PASS.
- Human exact deadline confirmation with token and revision: PASS.
- Rust generated D_MINUS_3 after verified date: PASS.
- Unauthorized automatic personnel/business decisions: 0.
- Real Outlook, SMTP, Task Scheduler, camera/RTSP, or user records accessed: NO.

## Failures found and corrected while testing

1. Workflow job-level runner path reference was invalid and prevented job scheduling. It was moved into the runner step.
2. Python missing from runner service PATH. GitHub setup-python installer failed due HKLM registry access. Official Python 3.12.10 embedded ZIP now runs from temporary directory.
3. Cargo missing from runner service PATH. Rust build and unit tests run in hosted Windows; the exact native executable is transferred to the self-host runner.
4. Windows PowerShell 5.1 stderr stream handling caused false failure on unittest output; the harness was changed to an in-process unittest runner.
5. Two fake Rust output tests depended on POSIX shebang execution. Windows-specific command fixtures now pass while actual Rust runs separately in E2E.

## Not accepted

- GUI live visual acceptance: BLOCKED. The runner is in Windows Session 0, not the signed-in user's interactive desktop.
- Real institutional Outlook, SMTP/push delivery, SSO/MFA, encrypted state, actual Windows Task Scheduler and real business user acceptance: NOT TESTED.

Conclusion: SELF-HOSTED CORE E2E PASS; GUI FIELD ACCEPTANCE BLOCKED; PRODUCTION NOT ACCEPTED.