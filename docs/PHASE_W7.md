# Phase W7 — startup integrity and signed-in Windows field UAT kit

## Objective
Verify a real logged-in-user's Tk notification interface with **fictional** local SQLite and keep the Windows per-user login Startup shortcut safe. No Outlook, SMTP, school files, worker scheduling, real credentials or production database are used.

## CI / safety boundary
- `windows/manage_desktop_startup.ps1 -Verify` is read-only and returns JSON showing whether the shortcut is owned by this project and references the **expected** EXE and database. `actual_login_autorun_verified` is **always false**: reading a shortcut cannot prove a real Windows login occurred.
- The installer refuses removal if a link with our description points to a different EXE or DB, even if the description matches. `-ReplaceExisting` requires an explicit action to repair a project-owned link.
- GitHub-hosted Windows CI installs, deliberately tampers, repairs and removes **only a RUNNER_TEMP sandbox shortcut**. It never registers the real user's Startup folder.
- A self-hosted Windows runner in Session 0 is not the signed-in desktop and must not claim GUI UAT.

## Read-only Startup check
From PowerShell in project root, use approved test paths:

```powershell
.\windows\manage_desktop_startup.ps1 -Verify -Executable 'C:\ApprovedApp\EDUNotifications.exe' -DbPath 'C:\ApprovedData\workflow.sqlite3'
```

Check `valid_link` and `is_interactive_session`. This is not evidence that Windows *actually launched* the shortcut after login. Logout/login startup verification requires an independently authorized test account and observed app launch.

## Interactive synthetic GUI UAT (opt-in)
In an approved **signed-in Windows test session**, install an approved Python 3.11+ (with Tkinter) for test execution. From repository root:

```powershell
$env:PYTHONPATH = Join-Path $PWD 'python'
python -m edu_workflow.field_uat --plan-only
python -m edu_workflow.field_uat --run-synthetic --report (Join-Path $env:TEMP 'edu-w7-manual-uat.json')
```

The second command is **explicit**, never triggered by CI or Session 0. It creates exactly two fictional reminders inside a disposable temporary SQLite database and launches the real Tk application. In the window, choose one reminder and click `確認済み` (ACK), then choose the other and click `30分後に再表示` (Snooze). Close the window. Three prompts ask the signed-in operator to attest Japanese legibility, audible sound and actual window interactivity. The tool writes only booleans, synthetic action counts, Session>0 and the explicit `production_accepted=false` flag to the new JSON report. No screenshots of other windows or usernames are collected.

If the report file already exists, the command refuses overwriting it. Choose a fresh filename for a new attempt. If any human answer is “No”, actions are missing, or service Session 0 is detected, **do not treat the UAT as passed**. Self-reports do not replace IT sign-off.

## Still outside W7
- Actual logout/login with opt-in Startup shortcut on an approved endpoint and physical observation; no automated claim.
- Production Outlook/Graph/SMTP/SSO, institutional privacy requirements, signed EXE and formal pilot sign-off.

## Verified synthetic CI checkpoint
- PR #13 W7 functional CI on `617d4828768b3363b2cf04e8b4bfdd99e6a330af`: Linux Python/Rust #39366926773, Windows W4 #39366926695, Windows legacy #39366926670, Windows GUI/EXE/Startup sandbox #39366926660 — all SUCCESS.
- 107/107 Python regression tests PASS. Windows log emits `W7_STARTUP_INTEGRITY_E2E_PASS` and verifies tamper refusal, explicit repair and removal.
- These results certify safe synthetic tooling, **not** physical sound, real workstation startup, IT authorization or production operation.
