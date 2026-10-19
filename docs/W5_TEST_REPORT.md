# Phase W5 — Test and field acceptance report
Date: 2026-10-20 (JST)

## Final status
**Code and hosted CI: PASS. Interactive desktop/production: NOT ACCEPTED.**

### GitHub facts
- [PR #9 merged](https://github.com/caotiensinh/workflow_office_deadline/pull/9)
- Merge SHA: `fbe8aaffebdf791a9c040d05e550bc599cfd1ee1`
- [Postmerge Linux CI #39327397812](https://github.com/caotiensinh/workflow_office_deadline/actions/runs/39327397812): SUCCESS, 102/102 Python tests, Rust integration, real Tk/Xvfb smoke
- [Postmerge Windows legacy CI #39327397881](https://github.com/caotiensinh/workflow_office_deadline/actions/runs/39327397881): SUCCESS
- [Postmerge Windows W4 CI #39327397739](https://github.com/caotiensinh/workflow_office_deadline/actions/runs/39327397739): SUCCESS
- [Postmerge Windows W5 CI #39327397726](https://github.com/caotiensinh/workflow_office_deadline/actions/runs/39327397726): SUCCESS, PyInstaller one-file EXE, bundled Tk smoke JSON, sandbox Startup link install/overwrite refusal/rollback
- [MRCAO self-hosted Session probe #39327093198](https://github.com/caotiensinh/workflow_office_deadline/actions/runs/39327093198): SUCCESS **only as a diagnostic**, Session ID 0, cannot display interactive Tk GUI
- The PyInstaller binary is **unsigned**, available as a GitHub Actions artifact for a limited retention period; its SHA256 was logged in W5 CI. IT approval and signing required before end-user deployment.

### Root cause and fix
Earlier W5 Startup E2E incorrectly checked `$LASTEXITCODE` immediately after calling a PowerShell script; `$LASTEXITCODE` retained the previous native process' status although the script had successfully created the shortcut. Commit `55a07c66b71bb8740bc48df4c6c37b1e2bf47138` removed that false check and directly verified shortcut existence, the target path, arguments, overwrite refusal and removal. Full green CI verified the fix.

### What the CI proves
- Python unit/regression suite 102/102, Rust integration.
- Real Tk/Xvfb synthetic window can display a notification and ACK through actual widgets on virtual Linux display.
- Windows self-contained executable loads bundled Tk and writes a file-based preflight report without a visible desktop interaction.
- Windows isolated startup shortcut can be previewed, created, validated, protected from unintended overwrite and removed.
- No real user Startup entry, Windows Task Scheduler, registry, Outlook account, SMTP, camera or production SQLite was changed during these tests.

### What it does NOT prove
- The Tk window appears on a real logged-in Windows user's desktop; sound, Japanese font, focus, mouse/keyboard, Win32 window handles, logoff/login and autorun.
- Enterprise auth, data protection or actual human-in-the-loop permissions.
- Real mail ingestion or production alert delivery.

Next hard acceptance gate: run a consented interactive Windows E2E on an IT-approved test user session with synthetic DB, capture app-only evidence and confirm login startup/rollback. Do not launch GUI from MRCAO Session 0 or mistake Linux/Xvfb for visible Windows behavior.
