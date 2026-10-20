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


## Verified W17 engineering acceptance — 2026-10-20

- **PR #33** MERGED: `8c2e504e61eb02707b9e7d1353539e180633711e`, final PR head `fc541797c139f5b823f3763580635a76e4163908`.
- Four exact-head PR CI SUCCESS: Linux **255/255 Python** + native Rust [#39432415536](https://github.com/caotiensinh/workflow_office_deadline/actions/runs/39432415536); Windows E2E #39432415566; W4 #39432415515; W5 UAT packaging #39432415668.
- Four exact postmerge main CI SUCCESS: [Linux/Rust #39432792196](https://github.com/caotiensinh/workflow_office_deadline/actions/runs/39432792196), Windows E2E #39432792279, W4 #39432792355, W5 #39432792696.
- **Operator ZIP artifact**: [W17 GitHub run #39432792696 artifact #12269820035](https://github.com/caotiensinh/workflow_office_deadline/actions/runs/39432792696/artifacts/12269820035). `W17_SignedIn_GUI_UAT_Kit.zip` SHA-256 `A67836396A1C66EAC93C1E583AEF65E5708068F126A2D85B9BF0900323A24EC7`. GitHub artifact retention seven days.
- Hosted Windows build checked the **EXE's** SHA against the value injected into `00_START_UAT.cmd`, then modified a disposable EXE and confirmed refusal. It did NOT open an interactive GUI. The UAT executable is unsigned and has no enterprise release authorization.
- W17 review tool rejects inconsistent ACK/Snooze/audit, unexpected fields, fake production/login approvals; a logically consistent report explicitly remains `CONSISTENT_SELF_ATTESTATION_NOT_INDEPENDENTLY_VERIFIED`.
- An initial corrupted GitHub workflow YAML and a leftover native exit code from a purposely negative tamper test were repaired; only final green CI is counted.

**Field/production acceptance remains PENDING:** approved interactive Windows Session 1 operator must personally observe Japanese labels, sound, ACK/Snooze; real login Startup, approved 15-minute Task Scheduler, Outlook/Graph, authorized test recipient, institutional privacy/identity and 3 pilots require separate approval. **Rollout gates 2/6 CI-only; production sign-offs 0/8.**
