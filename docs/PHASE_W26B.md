# W26B — Current Windows user Startup + running-desktop candidate read-only verification

## Fixed product objective
Python+Rust automation for approved institutional office email/deadline/alerts/audit; humans approve important actions. PUBLIC repo tests fictional data only.

## Implementation
`windows/manage_desktop_startup.ps1 -Verify` already validates the real expected `EDU_Workflow_Notifications.lnk` owner description, exact `EDUNotifications.exe` target and `--db` arguments; no write is made by `-Verify`. W26B adds a narrowly scoped read-only **current-session candidate snapshot**: if the exact expected shortcut exists and matches, find any `EDUNotifications` process in the current process session whose executable path exactly matches the installed target. Report **only a boolean**, never username, PID, process command line, private path or endpoint identity.

Always return FALSE for `process_was_started_by_startup_verified`, `actual_login_autorun_verified`, `independent_human_gui_observation_verified`, `it_approved` and `production_accepted`. Neither a link nor a running process proves the app was automatically started at Windows login or that a human saw its alert window.

Branch-only `.github/workflows/w26b-startup-readonly-evidence.yml` tests the native script using a temporary synthetic EXE placeholder, SQLite filename and Startup folder under `RUNNER_TEMP` on GitHub-hosted Windows, verifies valid link and zero unauthorized success claims, then removes precisely the synthetic shortcut and files. **#39519142449 PASS**, marker `W26B_HOSTED_STARTUP_LINK_READONLY_PROCESS_NEGATIVE_PASS_NOT_LOGIN_UAT` and cleanup marker. Hosted task never logs out/in or changes actual organizational Startup.

Institution IT must approve any real signed-in local verification. Rollout remains 2/6, workflows 0/8 until proper human evidence. Require 4/4 standard exact PR-head CI and postmerge main verification.