# Phase W4 test report — 2026-10-19

**Code/CI verified; field and production acceptance outstanding.**

PR #7: https://github.com/caotiensinh/workflow_office_deadline/pull/7
Merge SHA: `a0647f7b51e080232bb1bb7f35db0238aabc0822`

- Linux 93/93 Python + Rust integration: https://github.com/caotiensinh/workflow_office_deadline/actions/runs/39253715289 — SUCCESS
- Windows W4 18/18 Python, Tkinter import, Rust/EML/SQLite/file-spool integration: https://github.com/caotiensinh/workflow_office_deadline/actions/runs/39253715207 — SUCCESS
- Historical Windows W1-W3 E2E: https://github.com/caotiensinh/workflow_office_deadline/actions/runs/39253715141 — SUCCESS

## What the tests proved
3 fictional emails produce 3 durable alerts. Per-user ACK/SNOOZE survive reopening SQLite. Old case revisions disappear. UNKNOWN delivery cannot be ACK'd as delivered; no business approval/decision is generated. Failed audit writes roll back acknowledgment. Regression suites from W1, W2 and W3 are preserved.

## Root cause and correction
The first W4 branch tree was composed from an older tree and omitted W1/W3 tests. Mandatory regression manifest rejected it. W4 files were re-layered on the current main tree, restoring all critical test suites. Re-run CI passed.

## Not yet tested
Real Tk window and bell/focus on signed-in Windows desktop; authorized Outlook mailbox, enterprise SSO, real SMTP, Task Scheduler, local encryption/ACLs, real school documents and production user acceptance.
