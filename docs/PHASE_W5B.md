# W5B — Real Tk widget E2E on Windows CI

## Goal
Raise W5 GUI confidence beyond Linux Xvfb and pure mocks, using a real **Windows Tkinter window on GitHub-hosted `windows-latest`**. This is still **not acceptance on the actual signed-in school user's PC**.

## Controlled, non-invasive test
- Windows session ID must be nonzero; Session 0 must FAIL CLOSED without faking visibility.
- Create an isolated SQLite database under a temporary directory with two fictional, locally delivered reminders.
- Launch actual `desktop_app.launch` and use the genuine Tk event loop, widgets and application database calls. Do not hook `list_notifications` or `mark_notification`.
- Locate own Treeview and button widgets (no global desktop automation or screenshot); assert the Japanese title and mapped window.
- Select first alert → invoke Snooze → verify removed. Select second alert → invoke ACK → verify removed. Persist `desktop_receipts` and audit; verify no `decisions`, and other local account still sees both.
- Close the test window via its own WM_DELETE_WINDOW callback; save synthetic-only JSON evidence with session ID, safe test status and counts.
- Never access Outlook, SMTP, actual employee documents, Windows Startup/Task Scheduler, other windows, or company network.

## Verification
- [ ] Hosted Windows Tk widget E2E PASS with a mapped window.
- [ ] All W1–W5 regression suites PASS on new branch.
- [ ] After merge, post-merge main CI green.
- [ ] Separately authorize an actual Windows logged-in-user UAT using a nonproduction test account and data.

A hosted Windows VM's visible widget mapping is an automated Windows GUI test, **not** verification that a human saw, heard or clicked an alert on the deployment PC. A runner installed as service in Session 0 cannot be used for this interactive gate.
