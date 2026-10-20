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
