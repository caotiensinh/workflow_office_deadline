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

## Phase W4-S — Real Windows self-hosted E2E (2026-10-19)
- [x] GitHub Actions assigned job to `MRCAO` (runner ID 2, Windows self-hosted).
- [x] 93/93 Python tests PASS on MRCAO (run #39275696459).
- [x] Rust source compiled/tested on hosted Windows and exact-commit native binary executed on MRCAO.
- [x] EML x3, second import 0, alerts x3, no duplicates, ACK/SNOOZE, human confirmation, Rust D-3 reminder, audit, 0 automated approvals.
- [x] Public PR #8 merged after hosted CI and MRCAO E2E success.
- [x] Log documents Windows locale and POSIX fixture portability bugs and their fixes.
- [ ] Interactive Tk GUI test on signed-in Windows desktop; service runner Session 0 is NOT a GUI acceptance.
- [ ] IT-approved Outlook mailbox, actual push/email, SSO, scheduler and privacy production gates.

## Phase W5 — Interactive Windows desktop delivery (CI completed; desktop field acceptance pending)

- [x] **W5 PR #9 MERGED** as `fbe8aaffebdf791a9c040d05e550bc599cfd1ee1`.
- [x] Python regression suite **102/102 PASS**, including live Tk/Xvfb smoke (post-merge Linux [#39327397812](https://github.com/caotiensinh/workflow_office_deadline/actions/runs/39327397812)).
- [x] Native Windows W1–W3 E2E [#39327397881](https://github.com/caotiensinh/workflow_office_deadline/actions/runs/39327397881) PASS.
- [x] Native Windows W4 E2E [#39327397739](https://github.com/caotiensinh/workflow_office_deadline/actions/runs/39327397739) PASS.
- [x] Windows one-file `EDUNotifications.exe` built with Python/Tkinter, self-check JSON PASS. CI SHA256 was logged and unsigned EXE artifact retained by workflow (post-merge [#39327397726](https://github.com/caotiensinh/workflow_office_deadline/actions/runs/39327397726)).
- [x] Windows Startup E2E in **RUNNER_TEMP-only** sandbox: PlanOnly → install → no-overwrite → remove PASS; no system Startup changed.
- [x] Self-hosted **MRCAO** Session ID = **0** verified in [#39327093198](https://github.com/caotiensinh/workflow_office_deadline/actions/runs/39327093198), preflight did not change the machine.
- [x] Fixed false CI failure: inherited `$LASTEXITCODE` after a PowerShell script; test now asserts shortcut existence, target and removal.
- [x] Desktop refuses missing/corrupt DB (prevents silently creating empty workflow database).
- [x] UI model ACK/Snooze, re-alert after snooze expiry and read-only masked notification behaviors exercised in CI.
- [ ] **Real interactive Windows UI acceptance**: visible window and Japanese font, focus, bell, buttons, Snooze expiry, session logout/login, current-user Startup persistence, signed-in user evidence. **Not testable in MRCAO service Session 0.**
- [ ] Institution-approved deployment: real Outlook/Graph, verified SSO/MFA/RBAC, policy-approved SMTP or alert push, SQLite ACL/encryption/retention, and production pilot acceptance.
- [ ] Release signing/distribution and installer verification for end-user deployment. CI EXE is **unsigned, synthetic-tested**, not a production installation.

Next: Run W5 visual E2E on a separately authorized *interactive* Windows session; do not assume that runner service E2E proves window visibility. Historical checkpoint failures were fixed, but prior automated CI status entries below this W5 section are superseded by this verified section.

## Phase W5B — Windows real-widget E2E (code/CI accepted; actual user UAT pending)
- [x] Windows test harness creates fictional SQLite alert data, opens actual Tk window, performs Snooze/ACK through actual widgets and confirms audit/receipts.
- [x] Session 0 protection: refuse to claim visible GUI success in service session.
- [x] Added hosted Windows workflow gate and synthetic-only JSON proof.
- [x] Windows GitHub Actions real Tk E2E PASS in hosted Session 2, 2 synthetic alerts, mapped window, Snooze+ACK, 2 audit events and 0 approvals (#39340376029).
- [x] PR #10 MERGED; all four postmerge Linux and Windows CI workflows PASS (#39340624948, #39340624907, #39340624895, #39340624887).
- [ ] Real signed-in Windows workstation user acceptance, Startup after login and audible notice — not covered by hosted CI.

## Phase W6 — Real Windows Snooze re-alert reliability (2026-10-20)

- [x] PR #11 merged at `a4c55825bff0a6e76c15c3eb059d504679774efe`.
- [x] Tk bell/focus exceptions cannot suppress valid notification rows or masquerade as SQLite read failures; synthetic no-audio regression PASS.
- [x] Hosted real Windows Tk Session 2: initial bell once, actual Snooze/ACK widget actions, synthetic snooze expiry then re-alert once, zero repeat bells on unchanged refresh and zero approvals.
- [x] Reproduced and fixed `WinError 32` temporary SQLite file lock from an unclosed test writer; subsequent Windows cleanup PASS.
- [x] PR CI: Linux Python/Rust #39364014697 (103/103 Python PASS), Windows legacy #39364014660, Windows W4 #39364014574, Windows Tk/EXE/Startup sandbox #39364014825 all SUCCESS.
- [x] Postmerge `main` CI: Linux #39364174940, Windows legacy #39364174967, Windows W4 #39364175029, Windows Tk package #39364174898 all SUCCESS.
- [ ] Actual institutional *signed-in Windows user* UAT of Japanese fonts, focus behavior, physical sound, keyboard/mouse and logoff/login Startup persistence.
- [ ] IT-approved Outlook/Graph, SMTP/push, SSO/MFA/RBAC, data-retention/encryption, release signing and production workflow pilot.

W6 CI demonstrates synthetic Windows GUI behavior, not a real school workstation sign-off. See `docs/W6_TEST_REPORT.md`.

## Phase W7 — Startup integrity & reproducible signed-in user UAT kit (2026-10-20)

- [x] Read-only `-Verify` reports Startup shortcut identity, executable and DB arguments, and **never** claims login autorun acceptance.
- [x] Startup removal refuses an owned-looking shortcut with unexpected executable or DB arguments; explicit repair and rollback covered in Windows sandbox CI.
- [x] Fictional two-alert Windows field-UAT fixture, ACK/Snooze receipt audit, no approvals and non-overwriting JSON evidence **tooling** implemented; this does not imply a person completed UAT.
- [x] W7 PR CI at `617d4828768b3363b2cf04e8b4bfdd99e6a330af` all SUCCESS: Linux Python/Rust #39366926773 (**107/107 Python**), Windows W4 #39366926695, Windows legacy #39366926670, Windows real Tk/EXE/sandbox Startup integrity #39366926660.
- [x] Postmerge `main` CI at `2872db09bd9460fada49619c8436062f4c141e3a` all SUCCESS: Linux Python/Rust #39367276876, Windows synthetic #39367276821, Windows W4 #39367276676, Windows Tk/EXE/sandbox Startup #39367276621.
- [ ] Actual signed-in user physically verifies Japanese font/sound/focus and separately approved logout/login Startup.
- [ ] IT authorization for Outlook/Graph, SMTP, SSO and production acceptance.

See `docs/PHASE_W7.md`. UAT tooling is **not** equivalent to actual field or production acceptance.
