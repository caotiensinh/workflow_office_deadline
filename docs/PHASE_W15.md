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
