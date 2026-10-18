# Verification checkpoint — 2026-10-19

## PASS — persisted and validated

- Python `unittest`: 40/40 green.
- JSON intake: 5 synthetic cases imported.
- Python reference tick: 6 alerts added, next identical tick 0 alerts.
- File spool: 6 JSON notifications written and marked SENT; second dispatch zero.
- Human approval gate: rejects missing references, rejects unverified due dates, records actor/revision/audit, requires interactive confirmation.
- Mail import is conservative, stores only non-PII hash/source and generic RESTRICTED label.
- DOCX structural checker: positive, negative, invalid checklist tests pass.
- SMTP exception: UNKNOWN state, no blind repeat send.
- Python-to-compiled-process protocol bridge: tests with a simulated executable (NOT Rust compiler).

## NOT PASS — engineering work remains

- `cargo`/`rustc` not installed on this sandbox; Rust source and its native unit tests are **NOT compiled or run**. GitHub Actions workflow present but not executed/pushed.
- No real Microsoft 365/Outlook To Do/SharePoint/Graph credentials or explicit integration permission.
- Classic Outlook COM adapter untested (requires user Windows workstation and approved pywin32).
- Windows task registration untested (authoring host is Linux).
- No production delivery path tested; file spool only. Actual SMTP configuration and authorized destinations required.
- No production user identity provider/RBAC or encryption-at-rest enforcement in application. OS ACL/BitLocker must be configured externally.
- No semantic legal verification or AI appraisal. `evidence_ref` is a pointer presence check only.
- No organizational records have been processed; no cloud side effects were attempted.

## Next valid acceptance sequence

1. Compile `cargo test`, format lint and Rust binary on Windows runner.
2. Run Python CLI E2E using compiled Rust and assert 6/0 alert totals.
3. Check institution's endpoint security and scheduled-task permission; test a 15-minute run with local synthetic cases.
4. Choose Outlook Classic COM vs Graph after verifying the user's Outlook version and IT permissions.
5. Enable and verify authorized email notifications with non-sensitive test recipient; resolve failure/unknown deliveries by inspection.
6. Pilot the three highest-impact workflows, with audit log, human sign-off and rollback plan.
