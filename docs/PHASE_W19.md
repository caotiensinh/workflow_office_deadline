# W19 — Active-console guard for signed-in Windows GUI UAT

## Original project goal (unchanged)
Automate email, deadlines, document checks, notifications, audit and human decision routing with Python + Rust. Human decisions stay human-authorized. Read `docs/PROJECT_REQUIREMENTS.md` and `docs/IMPLEMENTATION_CHECKLIST.md` before a new engineering session.

## Root cause from W16–W18
MRCAO GitHub Actions service runs in **Session 0**; the console previously observed was **Session 1**. W8 protected the one-click launcher with a coarse `session_id != 0` check, but a nonzero ID **does not imply that the running process belongs to the currently active signed-in console**. A disconnected or different user session could incorrectly proceed. W17/W18 securely hand off and hash-check the ZIP but cannot themselves observe human GUI use.

## W19 implementation
- `python/edu_workflow/interactive_session_w19.py`: read-only Win32 `ProcessIdToSessionId(GetCurrentProcessId())` and `WTSGetActiveConsoleSessionId()` classification. Reject Session 0, missing/invalid active console and other-session mismatches.
- A matching, nonzero active console session is only `W19_ACTIVE_CONSOLE_CANDIDATE_NOT_GUI_UAT`: **never** actual GUI visibility, human input, IT approval or Windows login persistence.
- `field_uat_launcher.one_click()` checks the active console **before consent** and again **after consent**, before allocating a synthetic report/fixture.
- `field_uat.run_manual()` checks again **before launching the fictional GUI** and **just before writing a new UAT JSON** after the operator closes the GUI. If the session changes, fail closed without claiming a complete signed-in report.
- `EDUFieldUAT.exe --session-check-file <new local file>` returns only numeric process/console session IDs and explicit negative approval fields, without touching Outlook, desktop, mail, Tasks, Windows policy or the actual GUI. Refuses overwriting evidence.
- Hosted Windows build **executes the bundled EXE in numeric-diagnostic mode**, waits for the new JSON, validates that no human/IT/production success was claimed, and still validates the existing W17/W18 ZIP.
- 18 synthetic regression tests; Linux CI Python safety floor increased from **272 to 290**; Rust and existing Windows E2E remain mandatory.

## Limitation
An active console match is **not** proof that a person saw the window, heard the notification or clicked ACK/Snooze. Self-attested UAT JSON remains **not independently verified**, and the executable is still unsigned. Only an IT-authorized, signed-in operator can complete GUI/audible acceptance and separately approved logout/login Startup. A remote RDP session that is not the active console is deliberately refused rather than silently treated as approved. This is a safety decision, not an RDP feature guarantee.

No new network access, credentials, actual school/HR cases, SMTP, Outlook, Task Scheduler installation, deployment permissions or PowerShell ExecutionPolicy bypass.

## Acceptance checklist
1. 18 new negative/positive W19 tests PASS; full Python **290/290** and Rust PASS.
2. Hosted Windows executable's `--session-check-file` produces read-only numeric report with **all production/human flags false**.
3. W17/W18 final ZIP verifier still PASS with tamper negatives.
4. Exact-head PR CI 4/4 PASS, merge only then, verify 4/4 exact postmerge main and persist evidence.
5. **External PENDING:** approved real human GUI interaction on Session 1, Japanese font/audio/ACK/Snooze, login Startup, scheduled 15-minute cycles, Outlook, approved recipient, privacy/SSO, signing and three pilots.

Original rollout remains **2/6 technical CI gates**, **0/8 production workflow sign-offs**.
