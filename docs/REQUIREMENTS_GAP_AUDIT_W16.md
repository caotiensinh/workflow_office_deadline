# W16 — Readiness gap after self-hosted Windows session probe

The original requirements in `docs/PROJECT_REQUIREMENTS.md` cover WF01–WF08 with explicit human gates and six rollout criteria.

| Original requirement | Engineering evidence | Remaining institutional acceptance |
|---|---|---|
| WF01 email | EML import/dedupe and read-only Outlook Classic adapter code | Approved live mailbox/Graph delegated permissions |
| WF02 deadline | Native Rust engine, SQLite and six durable file notices, actual W15 selfhost E2E | Approved Task Scheduler every 15 minutes with logs |
| WF03 documents | DOCX structural checklist | Authentic source and human document correctness |
| WF04 regulations | Offline versioned provenance and human audit | Official legal authority and applicability review |
| WF05 HR | Anonymous fact inventory and source hash gate | Real compliant data authorization, manager approval |
| WF06 schedule | Offline conflict-free proposals | Approved calendar and human invites |
| WF07 decisions | Typed explicit approval, revision and audit | SSO/MFA/RBAC and institution-approved identity |
| WF08 operation | Unknown delivery quarantine, offline local dashboard | Real monitoring SOP and approved incident recovery |

W16 tests whether the self-hosted runner lives in the Windows Session 0 service context or the active console; it cannot prove a user has read Japanese, heard an alert or interacted with Tk. A matching session ID is only a prerequisite, **not sufficient**.

**Original 6 rollout gates: 2/6 CI-verified; 4/6 institution-gated and PENDING. 0/8 workflow production signoffs.** 8/8 workflow engineering breadth is NOT percent of business completion.

W14 CMD transport ran on DESKTOP-14SCTF4 and W15 Python/Rust/SQLite ran on MRCAO. W16 must report its own actual GitHub job runner identity and not conflate them. Neither Session ID nor a synthetic dashboard validates Task Scheduler 15-minute execution.

The GitHub API reports repository PUBLIC. Do not place real user data, credentials or IT infrastructure logs in GitHub artifacts.
