# Education AI Workflow — Python + Rust v0.2

**Runnable reference project** for Japan educational-office workflow automation, with a deterministic Rust rules binary, Python ingestion/orchestrator, SQLite outbox, deadline checks, local DOCX structural checks, decision approval gate, and optional read-only Classic Outlook import. Designed to run locally with no server or admin privileges if Windows security policy permits it.

## What is working vs blocked

- **Verified on hosted CI:** Python, Rust and synthetic Windows workflow tests (75 Python tests on W3, native Rust build and rule evaluation, Windows PowerShell E2E). W3 restores W1 transactional case/decision writes and reliable notification handling, plus adds human deadline confirmation and a masked review queue.
- **Verified via GitHub Actions:** Rust native unit tests, Rust release build, and Python-to-compiled-Rust CLI smoke passed on Ubuntu CI (run #39145381931). The authoring sandbox did not have a Rust compiler; Windows hardware remains unverified.
- **Not connected:** Customer Outlook mailbox, new Outlook Graph, SMTP service, To Do, local LLM, school information systems, Windows scheduler and production RBAC.

## Build Rust (Windows PowerShell)

1. Obtain an **approved Rust toolchain** (including `cargo`) from your organization's permitted source. No elevation should be required if installed for current user and IT permits execution.
2. In this project root:

```powershell
cargo test --manifest-path rust-core\Cargo.toml
cargo build --release --manifest-path rust-core\Cargo.toml
```

This creates `rust-core\target\release\edu_rules.exe`. Linux uses `edu_rules` without `.exe`.

## Quickstart without personal data

From repository root, create/activate a Python 3.11+ virtual environment if desired. Python standard library suffices for core. Set the Python package path:

```powershell
$env:PYTHONPATH = "$PWD\python"
python -m edu_workflow.cli --db .\data\demo.sqlite import-json --file .\examples\cases.json
python -m edu_workflow.cli --db .\data\demo.sqlite tick --backend rust --rust-bin .\rust-core\target\release\edu_rules.exe --at 2026-10-19T09:00:00+09:00
python -m edu_workflow.cli --db .\data\demo.sqlite cases
python -m edu_workflow.cli --db .\data\demo.sqlite alerts
python -m edu_workflow.cli --db .\data\demo.sqlite deliver --channel file --out-dir .\notifications
```

For a **Python-only demonstration** while the Rust compiler is unavailable, replace `--backend rust ...` with `--backend python`. This does **not** test the Rust engine. Rust mode never silently falls back to Python.

Run tests:

```powershell
$env:PYTHONPATH = "$PWD\python"
python -m unittest discover -s tests -v
```

### Real email: explicitly opt-in after IT/privacy clearance

For an approved folder of exported `.eml` files:

```powershell
python -m edu_workflow.cli --db .\data\demo.sqlite import-eml --dir .\approved_eml
```

The intake does not retain raw emails, subjects or sender addresses, and never trusts extracted dates until a user verifies them.

For *Classic Outlook on Windows only*, after IT approval and an installed/authorized `pywin32`:

```powershell
python -m edu_workflow.cli --db .\data\demo.sqlite import-outlook-classic --limit 50
```

No Outlook mail is modified and there is no auto-reply. New Outlook does **not** support this COM method; Graph integration needs a separately approved delegated OAuth app.

### Human approval

Inspect `cases` to obtain `revision`. Set an allowlist for actual local approver accounts:

```powershell
$env:EDU_APPROVER_USERS = $env:USERNAME
python -m edu_workflow.cli --db .\data\demo.sqlite decide --case-id EDU-002 --revision 1 --decision approve
```

The prompt requires manually typing `APPROVE EDU-002`. Missing evidence or an unverified deadline blocks approval. Audit log is queryable with `audit`. Local OS account is not equivalent to school SSO.

### Automatic checks every 15 minutes

After the Rust executable is compiled and your security rules permit scheduled tasks:

```powershell
.\windows\install_task.ps1 -IntervalMinutes 15
```

The scheduled action calls `run_once.ps1`, which runs `tick --backend rust` and saves alerts to a local notification folder. **File spool is not a push alert**. For actual email notifications, run `run_once.ps1 -Channel smtp` and configure an approved TLS SMTP server/allowlist via environment variables. SMTP ambiguity marks the alert UNKNOWN and requires operator reconciliation before any retry.

The task defaults to **no Outlook scanning** and **no outgoing email**, until explicitly enabled.

## Required SMTP environment variables (opt-in only)

`EDU_SMTP_HOST`, `EDU_SMTP_PORT` (465 or 587), `EDU_SMTP_FROM`, `EDU_SMTP_ALLOWLIST` (comma-separated authorized emails); optionally `EDU_SMTP_USER`, `EDU_SMTP_PASSWORD`. Prefer organization-managed secret storage rather than persistent plaintext environment variables.

## Files

- `rust-core/`: pure rule engine, seven Rust unit tests (not executed here)
- `python/edu_workflow/`: Python orchestration, store, adapters and CLI
- `tests/`: 40 Python tests and CLI E2E
- `examples/`: fictional sample cases, fictional sample mail and phrase criteria
- `windows/`: current-user Task Scheduler scripts
- `docs/ARCHITECTURE.md`: technical requirement mapping, workflows, privacy and acceptance
- `docs/STATUS.md`: verified vs unverified truth table
- `.github/workflows/ci.yml`: Python + Rust CI instructions for a future repository

## Safety limits

Do NOT use with real student/personnel records until the institution approves the data handling, retention, privacy classification, deployment policy and login model. `evidence_ref` check is *existence only*, not proof that law or regulations are correct. Office integrations and actual notice delivery are not included in the verified demo. Approval is always explicitly human-initiated.

## W2 synthetic EML intake (automatic offline demo)

After building Rust on Windows:

```powershell
.\windows\run_once.ps1 -ImportEmlDir .\examples\w2_inbox -DbPath .\data\w2.sqlite3 -OutDir .\notifications
```

Running this twice imports three cases and queues three notifications without duplicating them. Extracted deadlines are candidates only and must be verified by a human.

```powershell
$env:PYTHONPATH = "$PWD\python"
python -m unittest discover -s tests -p test_intake_w2.py -v
```

See [Phase W2 workflow and limits](docs/PHASE_W2.md). Live Outlook and real notification delivery require a separate approved acceptance test.

## Phase W3: human exception and approval gate

Use `python -m edu_workflow.cli --db .\data\w2.sqlite3 review-queue` to list only cases requiring a person to verify a deadline, supply missing evidence, or approve a decision. `confirm-deadline` requires `EDU_VERIFIER_USERS`, `--method source-reviewed` (or institution-reviewed), and an exact typed case ID + timestamp. `decide` requires `EDU_APPROVER_USERS` and a typed decision. All are revision-bound and recorded in SQLite audit. See [Phase W3](docs/PHASE_W3.md).

**Environment warning:** Hosted CI uses synthetic records and does not certify Microsoft Outlook mailbox access, institution SSO or production notification delivery.

## Phase W4: local Windows desktop notification center

The local Tkinter window displays only masked, current-revision alerts from SQLite; ACK means viewed, NOT business approval. Snooze hides until expiration. UNKNOWN SMTP results are critical and not dismissible as delivered.

```powershell
# After a synthetic Rust run_once.ps1 has populated .\data\workflow.sqlite3:
.\windows\start_desktop.ps1 -PlanOnly
.\windows\start_desktop.ps1
```

Or double-click `windows/START_NOTIFICATIONS.cmd` on a signed-in Windows desktop. The UI polls every 15 seconds while open; it will **not** show notifications when closed or on a noninteractive Task Scheduler runner. Read [the W4 specification](docs/PHASE_W4.md).
