# W15 — Real Self-hosted Windows Portable E2E (CMD, fictional data)

## Objective
Verify the actual Python + compiled native Rust + SQLite + file notification + audit workflow on a real Windows self-hosted GitHub Actions runner. The fixed business goal remains fully automated office intake, task tracking, reminders and audit, with human decisions and institutional approvals explicitly separated.

## Engineering execution design
- `.github/workflows/w15-portable-selfhost-e2e.yml` runs only on pushes to `feat/w15-selfhost-portable-cmd-e2e` to avoid touching selfhost on unrelated PRs/main.
- The **GitHub-hosted Windows builder** checks out the exact SHA with `persist-credentials:false`, compiles/tests the real native Rust engine, downloads **official CPython 3.12.10 embeddable** from python.org only on the hosted runner, copies the current repository's Python package and `examples/cases.json`, and writes SHA-256 hashes for all bundle files. The bundle is tested on that hosted runner first.
- The **self-hosted Windows job** receives the pre-tested bundle through GitHub artifacts and runs it via `cmd.exe`. No PowerShell commands, bypass flags, package installer, tools setup, live Outlook, SMTP, Task Scheduler, persistent services, system registry, or employer documents are used on the selfhost node.
- Input is five **fictional cases** from `examples/cases.json`; all database and file-spool outputs are under a unique job-specific path within `RUNNER_TEMP`.
- The script rejects a missing/invalid signed-by-CI source SHA or bundle member digest, refuses pre-existing test output directories, and requires Windows and the exact bundled Python executable.
- Two complete rounds of `import-json → Rust tick → file dispatch` must produce exactly **5 cases, 6 distinct SENT alerts, 6 matching JSON notice files, 5 import audit events and 0 business decisions**, with all second-run operations idempotent.
- Sanitized JSON evidence includes counts, source SHA, no Outlook/SMTP or Task Scheduler actions, and explicit `gui_accepted=false` / `production_accepted=false`. Logs must not print fake case titles or real email/account data.
- Bundle build/hosted smoke and selfhost actual job are separate; **only the GitHub job log's actual runner name** can establish that DESKTOP-14SCTF4 performed the test. If job fails/queues, state that explicitly.

## Acceptance boundaries
- This tests the core engine **on the self-hosted Windows machine** if and only if the job actually runs there and its E2E assertions pass. It does not prove that Windows Task Scheduler, PowerShell, GUI, Outlook, SMTP or an actual institutional user account works.
- The previous W8 PowerShell ExecutionPolicy restriction remains unresolved and must not be overridden. Running a portable Python executable through CMD without invoking scripts does not change that policy.
- Real email, employee/student data, passwords and secrets must never be placed in public repo CI artifacts. GitHub reports repository as public.
- No routine cleanup is installed; artifact retention is short, and sandbox output is scoped only to job-specific RUNNER_TEMP. All external operational changes still require organizational approval.

## Reproducibility and evidence
- Engineering regression suite: at least 227 Python tests (including 9 W15 safety tests) plus native Rust/Windows GUI regressions.
- W15 hosted bundle must pass the same E2E script before it is shipped to selfhost.
- Separate W15 selfhost job must PASS and print `W15_REAL_SELFHOST_CMD_E2E_PASS` plus `W15_CMD_PYTHON_RUST_SQLITE_FILE_AUDIT_PASS`; verify actual runner identity via GitHub job logs.
- PR 4/4 hosted checks must succeed at exact HEAD, followed by exact main 4/4 postmerge. Do not fabricate live operational sign-off from either.

## Original rollout gates
1. Synthetic Python CI: verified.
2. Native Rust integration CI: verified.
3. IT-approved 15-minute Windows Task Scheduler: pending.
4. Authorized real Outlook read-only: pending.
5. IT-approved test delivery to a recipient: pending.
6. Three institution operator sign-offs: pending.

Even if W15 selfhost E2E passes, there are still **2/6 rollout gates verified**, **4/6 pending**, and **0/8 institution-approved production workflows**.


## Actual W15 selfhost and CI acceptance — 2026-10-20

- **GitHub branch run:** [#39417321087](https://github.com/caotiensinh/workflow_office_deadline/actions/runs/39417321087), head `9679eedd13cb9521a3156db1706d763e0a0bf1ed`.
- **Builder:** Windows-hosted job `118609386374` compiled and tested real Rust, assembled official CPython embedded + Python source and six-alert test fixture, hashed **56 bundle members**, ran exactly this E2E script with `W15_HOSTED_TESTED_PORTABLE_BUNDLE_PASS`, SUCCESS.
- **Actual selfhost:** job `118609720587` ran on named runner **MRCAO** (GitHub log proves identity), Windows `cmd.exe`, SUCCESS. Markers `W15_REAL_SELFHOST_CMD_E2E_PASS` and `W15_CMD_PYTHON_RUST_SQLITE_FILE_AUDIT_PASS`.
- **Persisted counters:** `cases=5, alerts=6, sent=6, unknown=0, decisions=0, audit_imported=5`; six JSON files persisted in unique runner TEMP directory; second cycle did not change output files or duplicate alerts. Published only counters/source SHA as [safe artifact #12261674508](https://github.com/caotiensinh/workflow_office_deadline/actions/runs/39417321087/artifacts/12261674508), not internal SQLite or case content.
- **Important identity distinction:** W14 CMD-transport-only run was on `DESKTOP-14SCTF4`, while W15 Python/Rust/SQLite E2E ran on **MRCAO**. They are not proven to be the same device.
- **PR #29:** MERGED at `6fe9dd9bde3e1aaf42a9e5065992f49f898af70f`, exact PR CI four SUCCESS: Linux Python **227/227 tests** + Rust #39417326145; Windows synthetic E2E #39417326177; W4 #39417326121; W5 #39417326176.
- **Exact merged `main` 4/4 CI:** Linux #39417931869, Windows #39417931783, W4 #39417931623, W5 #39417931810, all SUCCESS.
- **Supply-chain note:** SHA-256 manifest provides integrity against accidental/unauthorized mismatches **relative to the hosted-created manifest**, but is **not a cryptographic signature or externally verified official Python release digest**. Production trust, signing and IT source validation remain pending.
- **Not tested:** end-user signed-in GUI, real Windows Task Scheduler/PowerShell policy on organization workstation, real Outlook/SMTP, employee/student data, or actual authorized production business decision.

**Original rollout gate classification remains 2/6 CI-verified, 4/6 awaiting institution approval, 0/8 production workflow signoffs.**
