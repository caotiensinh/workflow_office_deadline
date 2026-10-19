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

## Phase W3 — Atomic human gate and W1 regression restoration (verified in CI)
- [x] Recover verified W1 transactional store, crash-safe dispatch and 6 missing W1 regression tests.
- [x] Deadline confirmation writes verification method, audit and optimistic revision in one transaction.
- [x] CLI requires verifier allowlist and exact ISO deadline confirmation token.
- [x] Exception-only masked review queue and negative boundary tests added.
- [x] Hosted Windows synthetic confirmation → Rust D−3 → approval → audit test prepared.
- [x] W3 full Linux Python/Rust CI PASS (75/75 Python; Actions #39250582011).
- [x] W3 native Windows E2E PASS: confirmed deadline, Rust D−3, atomic approval and audit (Actions #39250581975).
- [x] W3 PR #5 merged to main at ca3ffdafb17be6a2220c98ba64d14952ba391786.
- [x] PR #6 merged and post-merge main CI PASS on commit 56c272d6d06a758e4972c0d155f7003098f3e919 (Linux #39251244897, Windows #39251244750).
- [ ] Real school SSO, Outlook, SMTP and Windows endpoint acceptance (requires external authorization).

## Root-cause prevention
- [x] Explicit CI guard requires W1/W2/W3 regression files and a 75-test minimum.
- [x] CI regression guard verified on PR (#39251101968) and main (#39251244897).
- [ ] Real school Windows endpoint, Outlook, SSO and push notices still require institutional permission.

## Phase W4 — Interactive local desktop notifications (CI verified; field validation pending)
- [x] Added SQLite alert reader; status and case-revision checks hide stale/closed notifications.
- [x] Per-user ACK/SNOOZE receipts persisted with audit, never as workflow approvals.
- [x] UNKNOWN delivery incidents are CRITICAL and cannot be acknowledged as delivered.
- [x] Added Japanese Tkinter center and Windows foreground launcher (no network, no service).
- [x] Added 18 W4 regression tests, Windows Rust→notification E2E and 93-test minimum CI guard.
- [x] Full W1–W4 Python tests 93/93, Rust build, Windows W4 tests 18/18 and Windows legacy E2E PASS.
- [x] W4 PR #7 merged as a0647f7b51e080232bb1bb7f35db0238aabc0822; all post-merge CI green (#39253715289, #39253715207, #39253715141).
- [ ] Visual test with signed-in Windows desktop user (Tk bell/focus and buttons).
- [ ] Institution-approved real Outlook/SMTP/SSO and endpoint security acceptance.

## W4 root-cause & field status
- [x] Initial old-tree commit unintentionally dropped W1/W3 tests; CI guard caught it and tree was rebuilt from live main, then 93 tests passed.
- [x] Windows hosted Python Tkinter import and synthetic Rust→SQLite→ACK/SNOOZE passed (18/18 W4 tests, 3 notices, 0 business decisions).
- [ ] Actual Tk GUI, Windows bell/focus and signed-in workstation behavior still require manual or authorized interactive UI acceptance.


## MRCAO self-hosted Windows acceptance (2026-10-20 JST)
- [x] MRCAO job #39275696459 SUCCESS on actual self-hosted Windows.
- [x] Python W1-W4 regression: 93/93 PASS on MRCAO.
- [x] Rust compiled executable executed on MRCAO with synthetic EML, SQLite, ACK/Snooze, human confirmation and D_MINUS_3.
- [x] Imported 3 synthetic emails, rerun imported 0, duplicate alerts 0, unintended approvals 0.
- [x] No real Outlook, SMTP, camera/RTSP or Task Scheduler mutations.
- [ ] GUI visual acceptance requires signed-in interactive Windows session; MRCAO runner uses Session 0.
- [ ] Real institutional security, identity, Outlook and production notification acceptance remain blocked.
