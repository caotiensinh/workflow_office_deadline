# Phase W3 — Human deadline confirmation and approval audit

## Process
1. Read-only Outlook/EML intake creates a case with unverified deadline candidate, never a confirmed commitment.
2. Scheduled Python → Rust rule evaluation creates VERIFY_DEADLINE exceptions.
3. The masked review-queue command shows only cases requiring human intervention: unverified deadline, missing evidence, pending approval.
4. The allowlisted operator reviews the original source and explicitly types the case ID and full ISO deadline to confirm. The action is transactionally revision-checked and recorded in audit without raw message text.
5. Earlier queued alerts are marked STALE; newly verified due date enables deterministic Rust D-3, D-1 and overdue reminders.
6. An allowlisted human can separately APPROVE or REJECT a ready case. The status, decision record and audit event must commit in one database transaction.
7. Actual SMTP remains opt-in with recipient allowlist; ambiguous remote delivery is UNKNOWN and requires reconciliation.

## Operator demo
```powershell
$env:PYTHONPATH = "$PWD\python"
python -m edu_workflow.cli --db .\data\w2.sqlite3 review-queue
$env:EDU_VERIFIER_USERS = $env:USERNAME
# Replace DEMO_CASE with a case ID from review-queue and use its actual candidate.
python -m edu_workflow.cli --db .\data\w2.sqlite3 confirm-deadline --case-id DEMO_CASE --revision 1 --due "2026-10-22T17:00:00+09:00" --method source-reviewed
$env:EDU_APPROVER_USERS = $env:USERNAME
python -m edu_workflow.cli --db .\data\demo.sqlite decide --case-id EDU-002 --revision 1 --decision approve
python -m edu_workflow.cli --db .\data\demo.sqlite audit
```

`confirm-deadline` now requires an interactive token exactly matching both the case ID and ISO deadline. Revision conflicts, closed/approved cases, missing verifier permission or wrong tokens block all changes.

## Root cause and regression gates
The W2 migration used an old tree to stage changes, inadvertently reverting previously verified W1 safety in store.py and deliver.py, while losing tests/test_delivery_integrity.py. W3 restores those three exact W1 Git blobs before adding new functionality. This prevents silent loss of transactional approval and stale-alert delivery protections.

Acceptance:
- [ ] Linux Python full regression suite PASS including recovered W1 tests and W3 tests.
- [ ] Rust native build and bridge PASS.
- [ ] Windows PowerShell synthetic EML → confirmation → Rust D-3 → decision → audit E2E PASS.
- [ ] PR merged with verified main CI.
- [ ] Actual Outlook, organization identity, Task Scheduler and push notices require external authorization and independent acceptance.

## Security limits
Current local-account allowlists and typed confirmations are **not** institutional SSO/MFA. The audit can establish that an operator made a declared confirmation, but cannot prove the referenced regulation was correct. Public repository hosts synthetic examples only; no real personnel or student information or institutional email content is allowed.
