# W15 Requirements Gap Audit

Project requirements: `docs/PROJECT_REQUIREMENTS.md`. W15 narrows the gap between CI-only synthetic code and physically executing the core app on a self-hosted Windows runner. It does not substitute for institution security and operator UAT.

| Requirement | Implementation evidence | Still unverified |
|---|---|---|
| WF01 intake | Offline fictional import and EML parser | Employer-authorized Outlook/Graph mailbox |
| WF02 deadline | Rust rules, SQLite idempotent alert lifecycle; W15 physical selfhost CMD E2E if job PASS | Approved Task Scheduler 15-minute runs on allowed endpoint |
| WF03 DOCX | Structural validation | Real document accuracy and signoff |
| WF04 regulations | Versioned integrity checks and human-only approval | Official authority, legal applicability |
| WF05 HR | Anonymous, sourced fact draft, human-only approval | Real de-identification and manager acceptance |
| WF06 scheduling | Conflict-free offline proposals | Authorized calendar and invitations |
| WF07 human gates | Stale revision rejection and atomic audit | Real SSO/MFA/RBAC, human identity controls |
| WF08 monitoring | UNKNOWN quarantine, local health and offline dashboard | Continuous approved services and real SMTP reconciliation |

Before W15, verified actual selfhost capability was only **CMD transport** on DESKTOP-14SCTF4 (W14), not Rust/Python/SQLite. W15 is explicitly a **synthetic core-engine E2E** using portable binaries, confined to RUNNER_TEMP. No actual institution resources or security controls are modified.

**Original 6 rollout gates:** 2/6 technical CI success, four institution field approvals missing; 0/8 signed-off production workflows. The breadth of code remains 8/8 (not 100% product completion). The repository visibility is reported PUBLIC; never put real confidential documents in code, artifacts or logs.

The gate count must only change upon verified authorized IT/real-user evidence; a synthetic runner E2E is still engineering acceptance, not an approved production pilot.


## Actual W15 selfhost and CI acceptance — 2026-10-20

- **GitHub branch run:** [#39417321087](https://github.com/caotiensinh/workflow_office_deadline/actions/runs/39417321087), head `9679eedd13cb9521a3156db1706d763e0a0bf1ed`.
- **Builder:** Windows-hosted job `118609386374` compiled and tested real Rust, assembled official CPython embedded + Python source and six-alert test fixture, hashed **56 bundle members**, ran exactly this E2E script with `W15_HOSTED_TESTED_PORTABLE_BUNDLE_PASS`, SUCCESS.
- **Actual selfhost:** job `118609720587` ran on named runner **MRCAO** (GitHub log proves identity), Windows `cmd.exe`, SUCCESS. Markers `W15_REAL_SELFHOST_CMD_E2E_PASS` and `W15_CMD_PYTHON_RUST_SQLITE_FILE_AUDIT_PASS`.
- **Persisted counters:** `cases=5, alerts=6, sent=6, unknown=0, decisions=0, audit_imported=5`; six JSON files persisted in unique runner TEMP directory; second cycle did not change output files or duplicate alerts. Published only counters/source SHA as [safe artifact #12261674508](https://github.com/caotiensinh/workflow_office_deadline/actions/runs/39417321087/artifacts/12261674508), not internal SQLite or case content.
- **Important identity distinction:** W14 CMD-transport-only run was on `DESKTOP-14SCTF4`, while W15 Python/Rust/SQLite E2E ran on **MRCAO**. They are not proven to be the same device.
- **PR #29:** MERGED at `6fe9dd9bde3e1aaf42a9e5065992f49f898af70f`, exact PR CI four SUCCESS: Linux Python **227/227 tests** + Rust #39417326145; Windows synthetic E2E #39417326177; W4 #39417326121; W5 #39417326176.
- **Exact merged `main` 4/4 CI:** Linux #39417931869, Windows #39417931783, W4 #39417931623, W5 #39417931810, all SUCCESS.
- **Supply-chain note:** SHA-256 manifest provides integrity against accidental/unauthorized mismatches **relative to the hosted-created manifest**, but is **not a cryptographic signature or externally verified official Python release digest**. Production trust, signing and IT source validation remain pending.
- **Not tested:** end-user signed-in GUI, real Windows Task Scheduler/PowerShell policy on organization workstation, real Outlook/SMTP, employee/student data, or actual authorized production business decision.

**Original rollout gate classification remains 2/6 CI-verified, 4/6 awaiting institution approval, 0/8 production workflow signoffs.**
