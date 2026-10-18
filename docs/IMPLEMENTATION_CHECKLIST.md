# Engineering acceptance checklist (2026-10-19)

## Verified locally
- [x] 46 Python tests pass on synthetic data (40 original + 6 W1 regressions).
- [x] JSON intake and idempotent local alert outbox.
- [x] Deadline checks, evidence check and interactive human approval.
- [x] Synthetic Outlook .eml and DOCX checker tests.
- [x] Editable specifications and project requirements written.
- [x] Atomic approval updates and stale alert prevention on local SQLite.
- [x] Recover known durable file notices, quarantine ambiguous SMTP results.

## Hosted CI
- [x] Native Rust compile, tests and CLI integration PASS on Linux (prior main).
- [x] W1 CI Python + Rust integration PASS (Actions #39147471023).
- [x] W1 Windows hosted PowerShell + Rust synthetic end-to-end PASS (Actions #39147470982).
- [x] W1 PR #2 merged and main commit verified (4c1a7fb3a413488a270f87c7e696a9f939de9865).

## External/production acceptance — not yet completed
- [ ] Windows Task Scheduler registration and 15-minute cycles on approved endpoint.
- [ ] Real Outlook Classic COM read-only integration authorized and tested.
- [ ] New Outlook Graph delegated consent and connector if needed.
- [ ] SMTP notifications delivered to an approved synthetic recipient; UNKNOWN reconciliation.
- [ ] Institutional identity, encryption, audit retention and privacy authorization.
- [ ] Semantic review of HR regulations and institutional documents.
- [ ] Three end-user workflows piloted and formally signed off.

**The hosted Windows runner does not replace real institutional Windows/Outlook acceptance.**

## Session W1 checkpoint

- Code merge: PR #2, main 4c1a7fb3a413488a270f87c7e696a9f939de9865.
- Hosted test evidence: Linux CI https://github.com/caotiensinh/workflow_office_deadline/actions/runs/39147471023 and Windows E2E https://github.com/caotiensinh/workflow_office_deadline/actions/runs/39147470982.
- Windows E2E covers synthetic 5-case import, native Rust decision cycle, 6 durable notifications and zero new duplicates on rerun.
- This is **not** live Microsoft Outlook/SMTP/Task Scheduler acceptance. Avoid entering any real confidential school data before authorization.

## Phase W2 — Email intake (verified on hosted CI)
- [x] Multi-marker deadline parser; conflict and incomplete marker fails closed.
- [x] EML backward-compatible hash, opaque Outlook source IDs.
- [x] Skip existing unread mail during COM intake to avoid fixed-batch starvation.
- [x] Opt-in EML source added to Windows entrypoint, with synthetic inbox.
- [x] W2 Python tests PASS: 57 total on Linux, 17 W2-specific on Windows (runs 39149185749, 39149185769).
- [x] Windows native Rust EML intake and alert idempotency PASS: 3 EML, 3 alerts, 0 duplicates on rerun.
- [x] W2 PR #3 merged (740df08842737afbbb73f737a04e5f5553efde5f); main CI must be rechecked on final HEAD.
- [ ] Live Outlook and push notice authorized and verified.

## Session W2 checkpoint
- PR #3 merged; real Outlook and SMTP remain explicitly untested.
- W2 tests: Linux full Python suite 57 PASS, Windows W2 suite 17 PASS, Windows PowerShell+Rust synthetic E2E passed, zero duplicates on second run.
- Next W3 priority: approval-safe deadline confirmation, actual approved notification channel, scheduled Windows acceptance. IT permission remains a blocker for real Outlook/SMTP.

## Phase W2b — Safe recurring task registration
- [x] Added opt-in EML or Outlook Classic source to Windows Task Scheduler registration.
- [x] Rejected dual-source selection; PlanOnly performs no mutation.
- [x] Existing task overwrite needs explicit ReplaceExisting.
- [x] Windows hosted plan-only and validation checks PASS (run 39149550506).
- [ ] IT-authorized real Windows Task Scheduler registration with user-session monitoring PASS.
- [ ] Actual recipient notification (approved SMTP or desktop notifier) E2E PASS.
