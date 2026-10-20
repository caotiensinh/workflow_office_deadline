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


## Phase W8 — One-click synthetic Windows UAT packaging (2026-10-20)
- [x] Consent-first unsigned EDUFieldUAT.exe built on Windows CI; artifact #12242388665, SHA256 7C468CD4E9FBFE4ED3D64AADF692D741361CB8DFDF943FF41D362DE60E086329.
- [x] Packaged EXE preflight PASS: synthetic-only, no Outlook/SMTP/Startup mutation or false production/login claims (#39373594044).
- [x] W8 launcher 7/7 tests, full Linux 114/114 Python regressions + Rust integration, Windows legacy/W4/Tk/EXE CI all PASS.
- [ ] MRCAO read-only diagnostic #39373569883 still queued at latest check; current runner online status and Session ID are UNKNOWN, not field UAT.
- [x] PR #15 merged as f47c5d85acba0e78fa131973ef1214b8acb847ef; all 4 postmerge CI PASS (#39373759396, #39373759417, #39373759454, #39373759473).
- [ ] Actual signed-in Windows workstation user sees Japanese labels, hears notification, clicks ACK/Snooze, produces field JSON with human observation.
- [ ] IT-authorized login/logout Startup acceptance and approved Outlook/SMTP/SSO/privacy controls.

**No Windows automated GUI result is a substitute for an observed, signed-in institutional desktop or approved production pilot.**

## Phase W9 — WF-06 offline schedule conflict proposals + original-requirements audit (2026-10-20)

- [x] Add bounded anonymous-only WF-06 `schedule-propose` CLI: available/busy intersections, timezone-aware JST, earliest candidate slots; no calendar writes or local database creation.
- [x] Verify timezone/conflict, half-open interval, round-up, duplicate, malformed/PII and symlink/oversize negative test cases.
- [x] PR #17 merged as `01701ca12c7a6752bf9c36760989d278c6dd06e0`; exact PR CI 4/4 SUCCESS (#39375466012 Linux/Rust 126/126 Python, #39375465997 Windows including native WF-06 E2E, #39375466020 W4, #39375466005 Tk/EXE); postmerge `main` 4/4 SUCCESS (#39375595466, #39375595438, #39375595478, #39375595406).
- [x] Trace original eight workflow requirements with engineering capability vs outstanding integrations and institutional sign-off in `docs/REQUIREMENTS_GAP_AUDIT_W9.md`.
- [ ] Complete real WF-06 calendar and invitation workflow after explicit institution approval.
- [ ] Institution end-user UAT, approved 15-minute Task Scheduler, real Outlook/SMTP/SSO and production pilot.

## Phase W10 — WF-04 versioned regulation-source gate (2026-10-20)

- [x] Implement offline bounded versioned reference registry with opaque IDs, citations and SHA-256 document integrity.
- [x] Block missing, tampered, superseded, unreviewed or outside-declared-window sources without legal interpretation.
- [x] Integrate REGULATION approval checks and pinned proof into revision-aware, atomic human decision/audit transaction; preserve manual rejection.
- [x] Add masked `VERIFY_REGULATION_SOURCE` review queue and safe read-only CLI with nonpassing exit code.
- [x] Add W10 negative/positive tests, plus Linux suite guard and native Windows WF-04 E2E gate.
- [x] W10 PR #19 MERGED at `be46a35c654135d6b60324f87c4c6a7af8890a32`. PR CI 4/4 SUCCESS: #39380003277 (144/144 Python + Rust), #39380003283 (Windows W10 native E2E), #39380003282 (W4), #39380003303 (Windows Tk/EXE). Postmerge `main` 4/4 SUCCESS: #39380147525, #39380147494, #39380147659, #39380147487.
- [ ] Institutional sourcing/official validity, managed source identity/signatures, SSO/MFA/RBAC and real legal/HR reviewer sign-off.

**Hash and a human_reviewed flag do NOT prove an official regulation is legally valid.** See `docs/PHASE_W10.md`.

## Phase W11 — WF-05 anonymous, source-cited HR reviewer draft (2026-10-20)

- [x] Strict anonymous-only, enum-based structured fact packet; rejects free-text, names, ratings and invalid/duplicate fields.
- [x] Automatically group backed observations into Japanese reviewer draft sections; identify missing, changed, unreviewed and future-dated evidence, with opaque citation IDs.
- [x] HR approval fails closed unless source packet digest and anonymous case ID match, there are no evidence gaps and the existing authorized human typed approval succeeds; pin proof to atomic SQLite audit. Manual rejection remains supported.
- [x] Read-only `hr-draft` CLI never creates workflow SQLite or touches external mail/calendar/HR systems.
- [x] Add W11 Python regression suite, Windows native CLI E2E, protected Linux test count, synthetic demo and documentation.
- [x] PR #21 merged at `cccdd9f13d8cd8ee2902060b97d99fce2b90798f`. Exact PR 4/4 CI SUCCESS: Linux 165/165 Python + Rust #39384141262; Windows HR native E2E #39384141293; W4 GUI #39384142204; W5 Tk/EXE #39384141221. Exact postmerge main 4/4 SUCCESS: Linux/Rust #39384328877, Windows HR/E2E #39384328977, W4 #39384328924, W5 Tk/EXE #39384328968. Windows cp1252 JSON round-trip regression PASS.
- [ ] Approved anonymous institutional data, source signatures/SSO/RBAC, user acceptance, real HR policy and manager sign-off.

**W11 summaries are fact inventories and drafting aids — NEVER HR assessments, performance ratings, rankings, or personnel decisions.**


## Phase W12 — WF-08 read-only monitoring and recovery dashboard (2026-10-20)

- [x] Read existing SQLite states with mode=ro; report missing/corrupt database without creating or modifying it.
- [x] Detect UNKNOWN, SENDING, old QUEUED, invalid dates and schema/integrity problems without automatic resend or repair.
- [x] Privacy-safe aggregate-only JSON and static Japanese HTML dashboard, explicit no-overwrite export.
- [x] Add 20 W12 regression tests, protected 185-test CI floor and native Windows synthetic incident E2E.
- [x] Recheck original WF-01..08 scope and six institution rollout gates in docs/REQUIREMENTS_GAP_AUDIT_W12.md.
- [x] PR #23 MERGED at `6534d14bcbc0afafd547b7b2355d996ffe00dbee`; exact PR head `82f43e977a79e41d308328263955d9f94d1f9610` 4/4 CI SUCCESS (#39386732165 Linux 185/185 Python+Rust, #39386732199 Windows monitoring E2E, #39386732167 W4, #39386732201 Tk/EXE). Postmerge `main` 4/4 CI SUCCESS (#39386978272, #39386977929, #39386978083, #39386978059).
- [ ] Institution-approved continuous monitoring, actual SMTP/DB incident reconciliation and approved 3-workflow pilot.

No W12 monitor operation sends messages, changes cases, restarts services or performs production recovery.


## Phase W13 — IT staging readiness, plan-only and explicit production gates (2026-10-20)

- [x] Read requirements and W12 state before modifying; confirm main HEAD and four green CI.
- [x] Add plan-only static project checks without Task Scheduler, Outlook, SMTP or database access.
- [x] Add optional IT-authorized *read-only* Windows Session ID/PowerShell policy/task existence observation; never bypass restrictions and never assert human GUI UAT.
- [x] Validate fail-closed readiness and immutable evidence in 16 synthetic W13 tests; add Windows hosted 15-minute Task Scheduler plan-only E2E and protect full regression count.
- [x] Record six original institution rollout gates and remaining privacy/security/UAT blockers in docs/REQUIREMENTS_GAP_AUDIT_W13.md.
- [x] W13 PR #25 MERGED as `9c8552cd44dabac9590333c7b86bfdee8b986802`; PR HEAD `e679b28053b7d8840ba8da7904764004e86a0cd7`: four CI SUCCESS (#39389145184 Linux 201/201 Python+Rust, #39389145248 Windows W13 16/16 + Task Scheduler 15-minute PlanOnly, #39389145003 W4, #39389144999 W5/Tk/EXE). Postmerge exact `main` 4/4 CI SUCCESS: #39389357539, #39389357526, #39389357533, #39389357534.
- [ ] Obtain real IT permission and human operator observation on a signed-in Windows endpoint, approved schedule, Outlook, test delivery, SSO/privacy and 3 signed pilots.

W13 is a readiness inspector, **not** authority to bypass managed PowerShell ExecutionPolicy or launch production.

## Phase W14 — Self-hosted CMD runner transport and offline Task Scheduler XML audit (2026-10-20)

- [x] Read latest HEAD, original requirements, W13 checklist, prior self-hosted job failure logs and Task Scheduler installer before code.
- [x] Add strictly bounded self-hosted Windows `cmd` transport probe, branch-scoped, no checkout/policy changes/host inspection; never count as machine UAT.
- [x] Add offline fail-closed Task Scheduler XML audit for one enabled 15-minute low-rights, file-only action; no secrets or task execution.
- [x] Add 17 W14 regression tests and hosted Windows XML audit E2E, protect 218-test CI minimum and preserve Rust regression.
- [x] Record updated six rollout gates and risk/authority limits in `docs/REQUIREMENTS_GAP_AUDIT_W14.md`.
- [x] Self-hosted CMD-only run #39392711809 on runner `DESKTOP-14SCTF4` PASS (job #118527846747); repeat run #39392955500 PASS on the same runner. Both used `cmd.exe`, no checkout/PowerShell policy change, host inspection, real app or Outlook.
- [x] W14 PR #27 MERGED as `bd0b6fc249035f6df37dfd42b60b08776e2ebdb5` after exact PR head `80d7c3861b8ce70bd13e67572f9edc55ac899763` 4/4 hosted CI SUCCESS: Linux Python 218/218 + Rust #39392964104, Windows W14 17/17 synthetic XML E2E #39392963977, W4 #39392964000, W5 GUI/EXE #39392963994. Exact postmerge main 4/4 CI SUCCESS: #39393256363, #39393256349, #39393256321, #39393256319.
- [ ] Institution IT authorization, observed 15-minute scheduled execution, live read-only Outlook, approved notification and three human pilots.

**A valid exported XML or a self-hosted runner CMD echo is not institutional acceptance.**

## Phase W15 — Real self-hosted Windows core E2E, portable CMD (2026-10-20)

- [x] Confirm original 8-workflow requirements, W14 final HEAD, selfhost CMD connectivity and previous PowerShell ExecutionPolicy limitations.
- [x] Implement real selfhost-only branch workflow: hosted native Rust + portable Python bundle, fully hash-pinned to exact commit, transferred by GitHub Actions artifact.
- [x] Implement isolated Windows CMD E2E from fictional fixture: import → Rust tick → SQLite → file dispatch → repeat idempotency and audit; no Outlook, SMTP, Task Scheduler or GUI access.
- [x] Add 9 manifest/runtime boundary regressions to bring Python floor to 227; document safety constraints and original rollout gates.
- [x] W15 actual selfhost run #39417321087 PASS on GitHub runner `MRCAO` (job #118609720587), using `cmd.exe` and host-tested portable Python/Rust from exact branch SHA `9679eedd13cb9521a3156db1706d763e0a0bf1ed`. Verified 5 cases, 6 SENT alerts, 6 file JSON notices, 5 import audits, 0 decisions, 0 UNKNOWN and second-cycle idempotency; safe evidence artifact #12261674508. This is **MRCAO**, not W14's `DESKTOP-14SCTF4`.
- [x] W15 PR #29 MERGED at `6fe9dd9bde3e1aaf42a9e5065992f49f898af70f`; exact PR HEAD `9679eedd13cb9521a3156db1706d763e0a0bf1ed` 4/4 CI SUCCESS: Linux 227/227 Python+Rust #39417326145, Windows Synthetic E2E #39417326177, W4 #39417326121, W5/EXE #39417326176. Exact main postmerge CI 4/4 SUCCESS: #39417931869, #39417931783, #39417931623, #39417931810. W15 portable hosted-build job #118609386374 also PASS.
- [ ] IT-approved signed-in desktop, actual scheduler, real authorized read-only Outlook, approved recipient and three human pilots.

**W15 self-hosted core E2E is not a Task Scheduler, Outlook, SMTP, GUI, or institutional production acceptance.**

## Phase W16 — Windows session readiness for signed-in GUI and scheduler UAT (2026-10-20)

- [x] Confirm requirements, current main HEAD, W15 selfhost Python/Rust E2E, previous GUI Session 0/PowerShell restrictions.
- [x] Add read-only native Windows process+active-console Session ID probe with fail-closed GUI UAT classification; no names, GUI, policy changes or task inspection.
- [x] Run same hosted-tested portable Python/Rust E2E and numeric session probe via CMD on selfhost; bundle SHA manifest and short-retention sanitized reports.
- [x] Add 12 fail-closed tests, Windows native inspection E2E and raise Python safety regression floor to 239.
- [x] Reconcile original 8 workflows and 6 rollout gates without claiming GUI or production acceptance.
- [x] **Actual W16 on MRCAO PASS**: run #39426407245, hosted bundle job #118639977685 PASS, CMD selfhost job #118640312265 PASS. Windows API observed process **Session 0**, active console **Session 1**, `SESSION_0_GUI_UAT_BLOCKED`; real W15 core E2E also PASS with 5 cases, 6 SENT alerts, 0 UNKNOWN, 0 decisions. Sanitized artifact #12266146908. **No interactive GUI was launched or accepted.**
- [x] PR #31 MERGED at `690f05b728c13c1373c82ce9d718d468b671e4b3`. Final PR head `21b75c5b373dd51f1bc137fd4097535d6eaf3a3e`: 4/4 CI SUCCESS (Linux **239/239 Python** + Rust #39426415370, Windows W16 E2E #39426415332, W4 #39426415331, W5 package #39426415403). Exact merged main 4/4 SUCCESS: #39426789284, #39426789332, #39426789314, #39426789280.
- [ ] Authorized *interactive* GUI ACK/Snooze/JP text/audio/login test and IT-approved scheduled execution, Outlook/recipient pilot; institution sign-off.

**Session ID observed != signed-in user GUI UAT; Session 0 explicitly blocks GUI.**

## Phase W17 — One-click signed-in GUI handoff and report verification (2026-10-20)

- [x] Read current W16 HEAD/checklist, W8 GUI UAT EXE code and packaging workflow; retain Python+Rust/human-gate project goal.
- [x] Reuse consent-first synthetic-only `EDUFieldUAT.exe` rather than duplicating UI; design an operator-friendly ZIP with Japanese README and CMD launcher that verifies SHA-256 before launching.
- [x] Add privacy-safe offline UAT report reviewer that refuses forged production/login claims, invalid/duplicate keys and impossible ACK/Snooze/audit counts.
- [x] Add 16 W17 evidence/safety regressions (Python minimum 255), hosted Windows ZIP hash/tamper verification without launching GUI.
- [x] Reconcile eight workflows/six rollout gates; explicitly distinguish a self-attested report from independent/IT acceptance.
- [x] PR #33 MERGED at `8c2e504e61eb02707b9e7d1353539e180633711e` (PR head `fc541797c139f5b823f3763580635a76e4163908`), with exact PR 4/4 SUCCESS: Linux 255/255 Python + Rust #39432415536, Windows Synthetic E2E #39432415566, W4 #39432415515, W5 EXE/ZIP #39432415668. Exact postmerge `main` CI 4/4 SUCCESS: Linux #39432792196, Windows E2E #39432792279, W4 #39432792355, W5 GUI/EXE kit #39432792696. W17 kit artifact #12269820035, ZIP SHA-256 `A67836396A1C66EAC93C1E583AEF65E5708068F126A2D85B9BF0900323A24EC7`, tested hash match + tampered EXE rejection; **not signed**.
- [ ] IT-authorized real signed-in Session 1 user GUI interaction, Japanese/audio/ACK/Snooze, Windows login behavior, real scheduler, authorized Outlook/recipient and 3 pilots.

**W17 package and hash verification != signed executable, human observation or production approval.**


## Phase W18 — Final-artifact ZIP integrity (2026-10-20)

- [x] Reconfirm 8 workflow requirements and W17 main HEAD `9bbf3dff23f7a2ecbd0f405676ba00bb928ac347`, original 2/6 technical rollout and 0/8 production sign-offs.
- [x] Create read-only archive verifier with three-entry allowlist, EXE SHA-256, full trusted CMD-template comparison and anti-tamper ZIP constraints. No GUI, startup, Outlook, SMTP or ExecutionPolicy changes.
- [x] Develop 17 local fictional-only positive/negative regressions: valid, mismatch, both-file tamper, extra/duplicate/path traversal/symlink, compression bomb and checksum failures.
- [x] Wire final packaged ZIP validation and three disposable ZIP negative cases into hosted Windows W5 workflow; protect Linux regression floor at 272 tests.
- [x] **W18 PR #35 MERGED** as `e0d4559eb824742ac4638adecc22253191b9e108` after exact PR head `0b2c4389c023f70435986b2b2e6dc26f957b9855` **4/4 CI SUCCESS**: Linux Python **272/272** + native Rust #39438094518, Windows E2E #39438096939, W4 #39438094329, W5 final ZIP #39438094750. Exact **postmerge main 4/4 CI SUCCESS**: Linux #39438376212, Windows E2E #39438375627, W4 #39438375591, W5 ZIP #39438375606. Hosted Windows validated **17/17 W18 tests** plus real final ZIP and three disposable tamper ZIPs. Postmerge artifact #12271558616; ZIP SHA-256 `C477130F5AD7E29179E543805CD1120258D60FA08DA7BC7E4B3284F8163D806A`. This is unsigned, not Session 1 GUI evidence.
- [ ] IT-authorized signed-in Session 1 human GUI acceptance, real scheduler, read-only Outlook, approved alert recipient, SSO/privacy, release signing and three operator pilots.

**W18 ZIP content validation is NOT code signing, trusted publishing, interactive physical GUI UAT or production approval.** See `docs/PHASE_W18.md`.


## Phase W19 — Active Windows console guard for real signed-in GUI UAT (2026-10-20)

- [x] Recheck latest W18 `main` HEAD `eab47b71597f338bc6786b3768b1d871dea9e9c1`, original 8 Python/Rust workflows, Session 0/Session 1 evidence and unresolved 2/6 rollout gates.
- [x] Replace weak `session != 0` one-click rule with read-only process-versus-active-console Win32 guard; no GUI action on a different/disconnected/session-zero desktop.
- [x] Recheck active console before consent, after consent and before writing final self-attested GUI report; no automatic business approval.
- [x] Add `--session-check-file` numeric-only packaged EXE diagnostic; no Outlook/SMTP/Task Scheduler, desktop capture, policy bypass or private account identifiers.
- [x] Add 18 W19 synthetic safety regressions, raise Python CI floor to 290; keep Rust and W17/W18 Windows ZIP tests.
- [x] **PR #36 MERGED** to `main` as `e637008f6955a6404e32b7fd4b83cf3c91bf1fc9` after exact PR head `fb2d6ef0a29dd3ffd83f1bb02112009d247c6230`, **4/4 PR CI SUCCESS**: Linux Python **290/290** + Rust #39441684432, W4 Windows #39441684454, Windows synthetic E2E #39441684467, W5 packaged EXE/session/ZIP #39441684381. Exact **postmerge 4/4 CI SUCCESS**: Linux #39441983385, Windows E2E #39441983272, W4 #39441983553, W5 #39441983384. Windows packaged numeric Win32 session inspection PASS without launching GUI, W18 final ZIP + 3 anti-tamper negatives PASS. Postmerge artifact #12274321978, ZIP SHA-256 `4B7715E89EC64FB310A0B8812B632FE6553D7267686BC0BFDF141B39696991A1`. No real human GUI/IT acceptance, no production signing.
- [ ] IT-approved real signed-in Session 1 *human* GUI Japanese/audio/ACK/Snooze and login Startup; scheduler/Outlook/recipient/SSO/privacy/three pilots remain external.

**Matching an active console session is only a prerequisite, not independent physical GUI or production acceptance.** See `docs/PHASE_W19.md`.


## Phase W20 — Parallel development lanes A + B (2026-10-20)

**Original goal unchanged:** Python+Rust automate WF01–WF08 email, deadlines, documents, alerts, records and audit; human decisions and external changes stay under explicit human approval. Repository PUBLIC; use fictional data only.

- [x] **Lane A (GUI UAT):** isolated branch `feat/w20a-gui-uat-self-verification`, PR #37. Root cause: one-click GUI previously showed success from the returned in-memory status without checking the immutable-new written report. Added immediate strict read-only W17 JSON review, fail-closed on missing/forged/contradictory reports, nine new Python tests. Final PR head `1fa53cb9692b0242cfb42fdc60e5b2fffe50d0b5`: **4/4 CI SUCCESS**, Linux **299/299** Python plus Rust #39445360362, Windows E2E #39445360572, W4 #39445360570, W5 GUI ZIP #39445360470. PR merged at `8b44c8c1771b4e9463e45d7e55db3c64a174a04d`, followed by exact main **4/4 CI SUCCESS** (#39445658466, #39445658536, #39445658779, #39445658566).
- [x] **Lane B (native selfhost Rust):** isolated branch `feat/w20b-native-selfhost-session-probe`, PR #38, independent files from Lane A. Added standalone Rust numerical Win32 console probe with **9/9 Rust safety tests**, branch-scoped hosted build and CMD-only self-hosted inspection, SHA256-check before execution. Exact PR head `08b5e0c66e28173a28238efebe2892730d77f88a`: **4/4 CI SUCCESS** (#39445369285, #39445369283, #39445369270, #39445369453) and self-hosted run **#39445216471 SUCCESS**, actual runner **DESKTOP-14SCTF4** (not MRCAO). No GUI, Task Scheduler, Outlook, SMTP, policy changes or private data. PR merged after no-overlap check at `80579cc3677c52721c73d78117a6ac8b64f76761`.
- [x] **Integration verification:** exact merged main commit `80579cc3677c52721c73d78117a6ac8b64f76761` **4/4 CI SUCCESS**: Linux Python **299/299** and native Rust including new W20B tests #39445969154; Windows Synthetic E2E #39445969134; W4 #39445969136; W5 packed GUI/session/ZIP #39445969180. Actual final ZIP and W18 tamper checks PASS, artifact **#12275936758**, inner ZIP SHA256 `782D0110F10500B85DAA7AC1F8312492CECBE71914AC62187E9BF847E46846C8`. This is not code signing.
- [ ] **External true blockers:** real IT-authorized signed-in Session 1 operator needs to observe Japanese text/audio/focus/ACK/Snooze, authorized login Startup and 15-minute scheduled operation, approved Outlook read-only, approved recipient and 3 institution pilots. Neither independent agent-lane CI nor Session ID measurements proves a human action.

**Original rollout: 2/6 technical CI gates verified; 0/8 production workflow signoffs.** A PR and passing CI are not equivalent to workplace deployment approval. See `docs/PHASE_W20A.md` and `docs/PHASE_W20B.md`.


## Phase W21 — Independent concurrent GitHub lanes A + B (2026-10-21 JST)

**Original purpose unchanged:** Python + Rust automate WF01–WF08; human authorization for critical decisions. Public repository: fictional-only test data.

- [x] **Lane A — Offline GUI handoff evidence:** PR #39, branch `feat/w21a-offline-uat-evidence-packet`. Added read-only `python/edu_workflow/uat_packet_w21a.py` to review a final ZIP with W18 plus fictional GUI self-report with W17; optional expected ZIP SHA, explicit false flags for binary/report cryptographic binding, independent physical GUI, code signature, IT, schedule, Outlook, SMTP and production. Added **11 tests** including corrupt ZIP rejection; final PR head `a0dd773d9380088b12488d57f3ac5d1dc8448ed6` exact **4/4 PR CI SUCCESS**: Linux #39448509638 Python **310/310** and Rust, Windows E2E #39448509634, W4 #39448509623, W5 #39448509674. Merged as `306e95cfc295690aae601a5f506aa90dc5fbdaa2`.
- [x] **Lane B — Scheduler operator safety plan:** PR #40, branch `feat/w21b-scheduler-plan-acceptance`. Added read-only `task_plan_w21b.py`, 12 positive/negative tests, and branch-scoped hosted Windows workflow invoking the **actual `install_task.ps1 -PlanOnly -IntervalMinutes 15`**; requires file channel, no Outlook/SMTP, no task replacement and exact safe action. Windows hosted run **#39448264819 SUCCESS**: **12/12 tests**, no scheduled task installed. Final PR head `7d2c81809ddefee3057c5c51bef363a2d54139f4` **5/5 CI SUCCESS** including hosted plan run plus four standard workflows: #39448320940 Linux **311/311** Python + Rust, #39448321121 Windows E2E, #39448320930 W4, #39448320966 W5. Merged as `5aa0774eae611496bb277603d01fd55dff9588a4`; exact merged main **4/4 CI SUCCESS** (#39448563216, #39448563206, #39448563197, #39448563180).
- [x] **Both lanes integrated:** exact main merge `306e95cfc295690aae601a5f506aa90dc5fbdaa2`, **4/4 GitHub CI SUCCESS**, Linux **322/322 Python** and native Rust #39448895075; Windows synthetic E2E #39448895210; W4 #39448895139; W5 #39448895292. Signed-in unsigned synthetic Windows kit artifact **#12278480329**, inner ZIP SHA256 `9BC1E0320666397DDFD945FC3037BDD0B5F4CCE1FB072F574561DB6F0C44C9C6`; W18 ZIP tamper checks and Session ID read-only gate PASS. No artificial GUI pass. 
- [x] Raise critical Python CI regression floor to **322** and pin the independent W20A, W21A, W21B test suites.
- [ ] **Only real external gates:** institution IT approval and signed-in Session 1 human GUI Japanese text/audio/focus/ACK/Snooze; logout/login Startup; genuine approved 15-minute Task Scheduler observed; approved Outlook read-only test; approved synthetic recipient; privacy/security/SSO, publisher signature and three pilots. Original rollout **2/6 CI technical gates**, **0/8 workflow production signoffs**.

**Agent execution honesty:** independent GitHub branches/workflows and Windows runners ran concurrently; no independent autonomous AI-model agents were launched. Notion Custom Agent spawn attempt was blocked by workspace entitlement (Business required). Never count agents merely from CI job number.



## Phase W22 — Three independent GitHub lanes A/B/C (2026-10-21 JST)

**Goal stays fixed:** Python+Rust workflow automation WF01–WF08, critical decisions/external changes remain human approved. Repository PUBLIC: synthetic data only.

- [x] **Lane A — Packaged GUI evidence reviewer**, PR #41, branch `feat/w22a-packaged-uat-review-cli`. The real Windows `EDUFieldUAT.exe` now supports opt-in `--review-report-file` + `--review-output-file`, validates a fictional *saved* UAT report offline via W17, writes new privacy-safe summary and cannot overwrite it. No Tk/Win32 session/UI/mail/Startup operations in review mode; all IT/physical GUI/production flags remain false. Latest PR HEAD `a3c2157c67afea2840271ffab2a29887c32d8ee3`: **4/4 CI SUCCESS** (Linux Python/Rust #39451921931, W4 #39451921501, Windows E2E #39451921643, W5 #39451921527). Hosted W5 logs `W22A_PACKAGED_REVIEW_EXE_PASS_SELF_ATTESTED_NOT_PHYSICAL_UAT`. Merged at `550514314416b1000ab1e8198ada1f1aad820d5e`.
- [x] **Lane B — sanitized 15-minute Scheduler timing evidence**, PR #42, branch `feat/w22b-scheduler-cadence-evidence`. Bounded locally-supplied 3–8 numeric event timestamps, UTC seconds, zero exit code and 900±60-second intervals. Source is self-supplied and unauthenticated; no Task Scheduler API, installation or IT acceptance. PR HEAD `45d3fc1c4d56cecc9d9516d1c78bcfd154a82e3d`: **4/4 CI PASS** (Linux #39451196674, W4 #39451195335, Windows E2E #39451196179, W5 #39451195306). Merged at `028b4f0ff6c6795ebea6c47e3b681c87b6a15e21`; exact postmerge **4/4 CI PASS** (#39451466738, #39451467382, #39451466783, #39451466935).
- [x] **Lane C — least-privilege Outlook Classic plan**, PR #43, branch `feat/w22c-outlook-readonly-readiness`. Strict plan requires unread-inbox-only, manual opt-in, max 1–50, no send, read-state change, real data or forged IT sign-off. This does not connect COM/Graph or touch a mailbox. PR HEAD `e306b60ca46b051b297284c6160ac9ab8d646984`: **4/4 CI PASS** (#39451236636, #39451236633, #39451236570, #39451236602). Merged at `2869f448e3c401f9ccedbd016384d8cfcc2fac60`, exact postmerge **4/4 CI PASS** (#39451767037, #39451766936, #39451766974, #39451767073).
- [x] **A+B+C integrated exact merge HEAD** `550514314416b1000ab1e8198ada1f1aad820d5e`: **4/4 CI SUCCESS** — Python **357/357** + Rust #39452369143, Windows E2E #39452369440, W4 #39452368657, W5 #39452368618. Real packaged no-GUI reviewer PASS, W18 ZIP tamper defense PASS. Synthetic unsigned GUI kit artifact **#12278217936**, inner ZIP SHA256 `5D98718E28BB8E6E7D6E8B2F5B8DC9475AD4F46CEF0BFFD1A9122F9768EBB806`. Hash is integrity evidence, **not code signing**.
- [x] Critical CI suite protectors updated and Python regression floor raised to **357** including all W22A/B/C tests.
- [ ] **External real gates:** IT-approved signed-in Windows Session 1 Japanese GUI/audio/ACK/Snooze, genuine login/Startup, actually approved 15-minute Scheduler execution, real read-only Outlook smoke under approval, approved synthetic alert recipient, SSO/MFA/privacy/signature reviews, and 3 real pilot signoffs. Still **2/6 rollout gates and 0/8 production workflows**.

**No autonomous model agents were spawned:** 3 independent GitHub branches, workflow suites and CI runners ran concurrently; the connected Custom Agent function remains unavailable without a Business workspace entitlement. Never conflate parallel CI with independent AI-model workers.


## Phase W23 — Two independent GitHub lanes, real disposable Windows Scheduler smoke (2026-10-21 JST)

**Original objective unchanged:** Python+Rust automate WF01–WF08. Real email, task registration on institutional endpoints, approvals, production/private data remain human/IT gated. PUBLIC repository: synthetic CI only.

- [x] **Lane B / PR #45 — Japanese one-click GUI UAT summary.** Branch `feat/w23b-operator-handoff-summary`, PR head `ff520a9ae1db3ce53fca05f50f2af7f2b5ac12b7`. After consent-first active-console fictional GUI ACK/Snooze and three self-report questions, the app automatically creates a **second immutable-new privacy-safe** `EDU_W23_Operator_Review_*.json` with original report SHA-256, receipt counters, self-reported Japanese readability/audio/window. No Outlook/SMTP, automatic upload, publisher signature or IT approval. Nine added negative/positive tests plus Japanese operator README inside kit. Exact PR head 4/4 PASS (#39454912967 Linux Python **366/366** and Rust, #39454912773 W4, #39454912759 Windows Synthetic E2E, #39454912792 W5). Merged `53ac8f4153689fbe0d57dfb1691d89139cbd4ad7`; exact main postmerge **4/4 CI PASS** (#39455344089, #39455344292, #39455345489, #39455344443).
- [x] **Lane A / PR #44 — REAL disposable hosted Windows Scheduler.** Branch `feat/w23a-hosted-scheduler-live-smoke`, final head `df04e46b75e3ffe462f474a3a6079e460d51b26b`. Windows-hosted-only opt-in creates a *uniquely named synthetic* Task Scheduler task with actual `PT15M` repetition config and registered `RunLevel=Limited`, manually invokes a CMD action **once**, verifies marker then deletes task and all temporary files. No corporate/self-hosted host mutations, real mail/DB, administrator escalation or policy bypass. Actual branch GitHub-hosted E2E **#39456105609 SUCCESS**, marks `W23A_REAL_HOSTED_TASK_REGISTERED_AND_ONDEMAND_EXECUTED_NOT_15MIN_CADENCE` and `W23A_HOSTED_TASK_CLEANUP_PASS_NO_INSTITUTIONAL_ACCEPTANCE`. Early red CI identified real PowerShell `RunLevel` enum and shell array-generation defects; fixed them rather than suppressing checks. Exact final PR head **5/5 CI PASS**: Linux Python/Rust #39456114852, Windows E2E #39456114848, W4 #39456114836, W5 #39456114851 plus Scheduler #39456105609. Merged `f841fe41022e2ddfe67aa85c81255eb933990671`.
- [x] **W23 A+B merged: 4/4 CI SUCCESS** on exact `f841fe41022e2ddfe67aa85c81255eb933990671`: Linux Python **366/366** + native Rust #39456415864, Windows Synthetic E2E #39456416034, W4 #39456416219, W5 #39456416004. Latest unsigned synthetic GUI kit artifact **#12280542310** (run #39456416004), inner ZIP SHA-256 **`DCBF4FF30D30220FFFDAFF791AF037C5E1701FB313D1990263A0B965C35515D6`**, matched W18 ZIP and W17 bundle logs. No signing or real human acceptance.
- [x] Pin W23A script/CI workflow and W23B safety test suite and raise Python minimum to **366**.
- [ ] **Real external acceptance remains:** Windows Session 1 actual IT-authorized human Japanese/audio/ACK/Snooze, observed login Startup, **naturally recurring** 15-minute scheduling on an IT-approved real endpoint, approved Outlook read-only, synthetic recipient delivery, privacy/SSO/signing and 3 human pilot signoffs. An on-demand task is NOT an observed 15-minute recurrence; rollout remains **2/6**, production workflow signoffs **0/8**.

**Autonomous-agent status:** Attempted direct GitHub Copilot issue delegation; GitHub API rejected with HTTP 422 “assignees copilot cannot be assigned to this issue”. Therefore **zero independently spawned AI coding agents**; two GitHub branches and CI lanes executed independently under assistant orchestration. User/repository Copilot cloud agent enablement is required before genuine agent assignment.
