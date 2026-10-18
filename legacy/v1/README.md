# Education AI Workflow Automation — executable rule-engine reference

**Scope**: a locally runnable, offline acceptance harness for automated deadline alerts,
missing-evidence checks, privacy masking, approval holds, and persistent idempotent outbox.
It **does not** connect to Outlook, Microsoft 365 or ChatGPT. Production orchestration is
specified in the accompanying project design DOCX and requires an authorized tenant.

## Requirements
Python 3.10+ with `zoneinfo` and IANA timezone data for Asia/Tokyo (on Windows, install
an approved tzdata package only if your Python environment lacks the timezone database).
No third-party application/library is needed on a typical Linux development machine.

## Quickstart
Use a COPY of `sample_cases.json` for approval tests, as approval changes the file.

```shell
python -m unittest -v test_workflow_engine.py
python workflow_engine.py run --cases sample_cases.json --db workflow_state.sqlite3 --at 2026-10-19T09:00:00+09:00
python workflow_engine.py outbox --db workflow_state.sqlite3
python workflow_engine.py dispatch --db workflow_state.sqlite3 --channel stdout
```

Run `run` with the same date twice: second run must create 0 additional alerts. Reminder
policies are D−3, D−1, D0, and daily overdue. Missing deadline and approval requests
are surfaced daily until resolved. Completed cases do not trigger alerts.

To test an approval, **copy** the fixture and run:

```shell
python workflow_engine.py approve --cases sample_copy.json --case-id EDU-002 --decision approve --approver demo_manager --at 2026-10-19T10:00:00+09:00
```

The `EDU-003` HR example is blocked from approval due to missing evidence.
The `EDU-005` completed case will never be reminded.

## Explicit SMTP opt-in (not configured)
`dispatch --channel smtp` requires `WORKFLOW_SMTP_HOST`, `WORKFLOW_SMTP_PORT`,
`WORKFLOW_SMTP_FROM`, `WORKFLOW_SMTP_ALLOWLIST` and optionally username/password.
Only send to authorized addresses on the allowlist. No actual email is sent by default.
SMTP has an acknowledgement ambiguity on timeout: reconcile provider delivery logs
before retry to avoid duplicate sends. Production should use Outlook connector and
transactional outbox in an organization-approved tenant.

## Security / functional limitations
- Demo data is fictional, addresses use `.invalid` domain.
- Sensitive cases are anonymized in the notification body.
- External actions do not execute automatically; a human approval API is not included.
- This offline model does not parse Japanese natural-language deadlines or validate
  regulations, personnel evaluation, or source documents.
- Local SQLite is only for **single-machine demonstration**, not a multi-user system.
- Scheduling a CLI via Task Scheduler is not a replacement for a tenant-approved cloud flow.
