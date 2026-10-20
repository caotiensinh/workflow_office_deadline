# W17 — Requirements and real-world acceptance gap

Read `docs/PROJECT_REQUIREMENTS.md` before each session. Fixed outcome: automate WF01–08 with Python/Rust and human authorization on decisions and outbound changes.

| Dimension | Latest engineering proof | Unverified before real institution deployment |
|---|---|---|
| WF01 email | Offline synthetic intake/dedupe, optional Outlook COM read-only code | Institution-approved real mailbox and privacy |
| WF02 deadlines | Rust deterministic rules, actual MRCAO Python/Rust/SQLite/file spool E2E | Approved 15-minute Task Scheduler under actual endpoint policy |
| WF03 document | DOCX structure checks | Correctness review using approved material |
| WF04 regulations | Versioned source/evidence proposals and human gate | Official provenance and applicability |
| WF05 HR | Anonymous fact inventory, evidence hashes | Real de-identification and manager signoff |
| WF06 schedule | Synthetic conflict-free proposals | Approved calendar integration and invitation decision |
| WF07 approvals | Authenticated-actor-shaped records, stale-revision and audit guards | Real enterprise SSO/MFA/RBAC and approver provenance |
| WF08 monitoring | SQLite read-only unknown quarantine and Japanese local dashboard | Continuous authorized operational telemetry / restore drills |

W16 established GitHub Actions runner **MRCAO Session 0** versus active console **Session 1**. W17 makes the already-built GUI UAT executable easier to hand off and verifies binary consistency/reports, but does **not** teleport a GUI from Session 0 into Session 1.

A human's GUI ACK/Snooze is a notification receipt, **not** a personnel/official approval. A self-attested report is neither independent observation nor evidence of IT authorization; its fields are untrusted until IT reviews how and where it was produced.

**Engineering breadth:** 8/8 workflows have offline/synthetic code. **Institution rollout:** 2/6 CI technical gates, four institution-controlled gates PENDING. **Production sign-offs:** 0/8 workflows.

Repo visibility is reported PUBLIC; no real school/student/employee data, credentials, screenshots of private desktops or real email artifacts are uploaded to GitHub.
