# Phase W4 — Windows local notification center

## Outcome and architecture
The Python + Rust background worker continues to import approved EML, evaluate deterministic deadlines and store durable SQLite alerts. A separate **Tkinter foreground application** running in the signed-in Windows user's desktop displays privacy-masked notification labels, raises its window/bell for newly noticed alerts, and persists viewed/snoozed state.

- \`python/edu_workflow/desktop_center.py\`: headless/testable model, SQLite receipts and audit.
- \`python/edu_workflow/desktop_app.py\`: Japanese UI using built-in Tkinter.
- \`windows/start_desktop.ps1\`: foreground launcher and non-mutating \`-PlanOnly\` mode.
- \`windows/START_NOTIFICATIONS.cmd\`: double-click startup for default DB.
- \`windows/run_once.ps1\`: separate Rust evaluator and file-spool sender. This **must not** launch Tkinter from a noninteractive scheduled task.

## Setup with fictional data
From the repository root on Windows:
\`\`\`powershell
cargo build --release --manifest-path rust-core\Cargo.toml
.\windows\run_once.ps1 -ImportEmlDir .\examples\w2_inbox -DbPath .\data\workflow.sqlite3 -OutDir .\notifications
.\windows\start_desktop.ps1 -PlanOnly
.\windows\start_desktop.ps1
\`\`\`
Requires Python 3.11+ with Tkinter and a signed-in user desktop. Closing the center stops on-screen notifications, **not** the scheduled rule processor. There is no screen notification while signed out or if the UI is not running. This is not a native Windows Action Center toast or phone push.

## State and authorization
- Only current-revision \`SENT\` alerts and \`UNKNOWN\` delivery incidents from active cases are visible.
- No raw email, student details, sender or case safe_title are shown. UI shows static Japanese code labels, severity and opaque case ID.
- \`確認済み\` (ACK) means *seen*, **never** management approval, document submission or deadline confirmation. It creates \`DESKTOP_ACK\` in the audit log and a per-user \`desktop_receipts\` row.
- \`30分後に再表示\` (SNOOZE) hides the notice for 30 minutes, persists after restart and logs \`DESKTOP_SNOOZE\`.
- \`UNKNOWN\` delivery is a critical incident. The notification cannot be ACK'd, only snoozed temporarily; an authorized operator must reconcile any ambiguous SMTP send.
- Stale, replaced, canceled or completed cases cannot be acknowledged or resurface through old alerts.
- User name derives from local OS, **not enterprise SSO**. SQLite is not encrypted; Windows ACL, encryption at rest and institutional security approval are required before any real school data.

## CI and acceptance
- W1–W4 Linux Python suite minimum **93** tests, Rust native/integration CI.
- Windows W4 unit tests, Windows Rust → EML → SQLite → file-spool E2E, then ACK/SNOOZE tested across DB reopen, plus Windows Tk module import.
- Actual Tk window visual appearance, font rendering, window focus/bell and signed-in session behavior **cannot be certified by a headless GitHub CI test**. This remains a separate field acceptance.
- No live Outlook, Microsoft Graph, SSO, SMTP service, Windows Task Scheduler registration, real mail or school/employee/student data is used in CI.

## Rollback / troubleshooting
Close the notification window to stop polling. It does not stop the Rust worker; stop or uninstall the separately configured scheduled task only after checking its current settings. If the window cannot open, verify Tkinter, Python PATH, SQLite path and interactive desktop session. A receipt failure leaves the alert visible because the local DB transaction rolls back. Backup the SQLite database before institutional rollout.
