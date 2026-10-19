# Self-hosted Windows W4 E2E — bounded test protocol

- Trigger: a one-off push to `test/selfhost-w4-e2e` (no pull-request trigger). Uses `runs-on: [self-hosted, Windows]`, **not** `windows-latest`.
- Scope: synthetic EML fixtures only, isolated database and notification files within GitHub Actions `RUNNER_TEMP`. Nothing reads live Outlook, SMTP, browsers, camera/RTSP, documents or user Desktop folders. No Task Scheduler changes.
- Resources: Cargo build restricted to two jobs; GitHub job timeout 18 minutes. No system-wide install, registry changes or reboot.
- Criteria: Python 93/93; Rust tests/build; twice-running Windows PowerShell intake and confirming 0 duplicates; SQLite ACK/SNOOZE restart; operator-typed exact deadline; Rust D-3; 0 automatic business approvals; UI session status.
- GUI: self-host runner executing as a service may be in Session 0, so the Tk window **cannot** be demonstrated to a signed-in desktop. The test marks this `BLOCKED_SESSION_0_NONINTERACTIVE`, not PASS. In an interactive Windows runner session it launches **only our notification center**, verifies a visible owned window by PID and closes it.
- Real Outlook, external notifications, actual institution identity, human visual quality and production signoff remain separate. Never claim user-visible GUI PASS solely because unit tests pass.
- Diagnostics: inspect workflow run, job logs and small synthetic JSON evidence artifact; report runner assigned / queued and exact blockers.
- Safety: this workflow is intentionally scoped to the test branch and does not auto-run on public pull requests.
