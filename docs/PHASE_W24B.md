# W24B — Real Windows Startup link roundtrip, without login test

Objective: close installer/readiness gaps toward user-signed-in Windows GUI notifications, subject to enterprise IT permission, without modifying any organization endpoint.

- `windows/w24_hosted_startup_roundtrip.ps1 -PlanOnly`: returns non-mutating JSON, false for startup created, observed logout/login, approval or production.
- `-LiveHosted`: before doing anything requires all environment gates `GITHUB_ACTIONS=true`, `RUNNER_ENVIRONMENT=github-hosted`, `RUNNER_OS=Windows` and opt-in `W24_ALLOW_DISPOSABLE_STARTUP_TEST=yes`.
- On the **ephemeral GitHub-hosted Windows VM only**, create a single uniquely named temporary per-user Startup `.lnk` to benign local `cmd.exe /D /C exit 0`, read it back using native Windows Shell COM, and delete that exact link. On failed checks, cleanup occurs in `finally`.
- Branch-only GitHub Actions hosted Windows workflow tests plan-only + roundtrip. No registry/system Startup, no corporate user or Outlook/SMTP, and no user data logged.

A pass proves Startup link creation/readback/cleanup works on GitHub-hosted Windows, **not** a user login occurred or the GUI launched after login. Real Windows Session 1 and startup after organizational login remain an IT-authorized independent acceptance gate. Do not count this as rollout or production sign-off.