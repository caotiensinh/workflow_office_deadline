# W9 — Original requirements vs implementation audit

**Date:** 2026-10-20 (JST)  
**Source of truth:** `docs/PROJECT_REQUIREMENTS.md` (WF-01..WF-08; six rollout gates), `docs/ARCHITECTURE.md`, implementation, and GitHub Actions evidence.

## Interpret progress honestly
- **6/8 workflows have substantive executable offline/synthetic implementations** (WF-01, 02, 03, 06, 07, 08). This is **not** a 75% production-ready estimate; each still has specific missing real-world capabilities.
- **2/8 workflows have only narrow safety primitives** (WF-04 regulation references and WF-05 HR observations). Neither is a complete workflow.
- **0/8 have final institutional production sign-off.** Multiple are tested synthetically, but not approved for real personal data.
- **2/6 rollout gates are verified at the CI/synthetic level**, while four require IT authorization, live endpoint/integration evidence, or human pilot sign-off.

## Traceability matrix

| Requirement | Verified engineering | Critical missing requirement | Disposition |
|---|---|---|---|
| WF-01: Email intake | EML parser/dedupe, redaction, unverified deadline preservation and optional Classic Outlook COM adapter code; Windows synthetic E2E | Real authorized Outlook mailbox; Graph for New Outlook; real read-only user acceptance and approved continuous polling | PARTIAL |
| WF-02: Deadline monitoring | Python→real Rust deterministic D-3/D-1/due/overdue, revision-aware idempotent alerts, file delivery; Windows CI E2E | Approved actual scheduled 15-minute cycles on institution endpoint, real alert delivery | PARTIAL |
| WF-03: Document checks | Offline DOCX required-heading/phrase checks and missing-reference gate | Contextual accuracy, regulation citations, actual end-user document acceptance and official submission | PARTIAL |
| WF-04: Regulation references | Only detects absent `evidence_ref` and blocks unsupported approval | Versioned official rule/document registry, currency checks, precise citations, reviewer traceability, substantive regulation workflow | MINIMAL |
| WF-05: HR observations | Local case/audit and evidence hold; no autonomous HR approval | Anonymous fact aggregation, missing-evidence structured summaries, usable management draft, approved human pilot; no auto HR appraisal | MINIMAL |
| WF-06: Schedule proposals | **New in W9:** anonymous free/busy intersection, conflict exclusions, JST time rounding, deterministic proposals, read-only CLI and tests | Real approved calendar availability adapter, permissioned scheduling integration, human-confirmed invites/rescheduling | PARTIAL |
| WF-07: Human decision gate | Optimistic case revision, typed approve/reject/confirm-deadline, local user allowlist, audit and transaction rollback tests | Institutional SSO/MFA/RBAC, managed authorization and production policy | PARTIAL |
| WF-08: Health and recovery | Durable SQLite file outbox, no duplicate deliveries, ambiguous SMTP state UNKNOWN quarantine, audit; GUI alert receipts | Continuous service health metrics, admin diagnostics dashboard, approved notification destination, incident resolution SOP and long-running endpoint acceptance | PARTIAL |

**WF-06 does not write or read a real calendar, database or external service. Its suggestions are based only on supplied fictional/approved snapshots.**

## Original six rollout gates

| Gate | Evidence | Status |
|---|---|---|
| 1. Synthetic Python/local sample | 126 regression tests after W9, sample EML/DOCX/deadlines | PASS (CI) |
| 2. Real Rust build and Python→Rust integration | Linux/Windows GitHub-hosted Rust native CI | PASS (CI) |
| 3. Approved 15-minute Windows scheduled run | PlanOnly and sandbox tests; *no authorized institution endpoint acceptance* | PENDING |
| 4. Authorized Outlook read-only smoke | COM adapter exists, no institution mailbox test | PENDING |
| 5. Approved alert to synthetic recipient | File spool & Tk smoke; no approved SMTP/push recipient E2E | PENDING |
| 6. Three end-user pilots and sign-off | No institutional sign-off | PENDING |

## Additional operational constraints
- The previous Windows self-hosted MRCAO was identified as **service Session 0**; W8 session diagnostic job #39373569883 remains QUEUED as inspected and does not establish the runner's present status or interactive UI.
- GUI/Tk and unsigned PyInstaller EXE acceptance is confined to synthetic CI, not human-observed signed-in operator UAT or actual logout/login Startup acceptance.
- GitHub repository API reports `visibility=public` even though the brief calls the repository private. No actual HR/student/email content should be committed or ingested before access review.
- SQLite local credentials / per-user allowlists are **not** tenant-grade identity or enterprise security; release is not signed.
- The system is deterministic automation, **not yet AI-powered semantic review, policy interpretation, or HR assessment**.

## Next engineering priorities (while production approval is unavailable)
1. **W10 WF-04 versioned regulation-reference registry** with content hashes, supersession flags and citation provenance; fail closed on stale or missing references, no invented legal conclusions.
2. **W11 WF-05 anonymous HR evidence summary generator** with source references and human-only approval.
3. **W12 WF-08 operational health & recovery dashboard**, including actionable alerts for UNKNOWN sends and file/DB health without exposing private data.
4. Institution-gated integration acceptance: task scheduling, Outlook/Graph, approved notifications, SSO/MFA, signed deployment, three documented pilots.

Do not convert PASS synthetic test counts into arbitrary percent of business requirements. The precise coverage indicator is **6 substantive + 2 skeletal of 8 workflows; production 0/8; rollout 2/6**.

## Verified release checkpoint
- W9 code merged via PR #17 at `01701ca12c7a6752bf9c36760989d278c6dd06e0`.
- Linux CI 126/126 Python plus native Rust PASS; Windows executed the new WF-06 schedule-propose command and confirmed exactly two candidates, no SQLite creation and no external actions.
- Postmerge main four workflows SUCCESS: Linux/Rust #39375595466, Windows legacy/WF-06 #39375595438, W4 #39375595478, Windows Tk/EXE #39375595406.
- These proofs remain **synthetic/offline CI** and do not change the six rollout-gate disposition (2/6 PASS at synthetic/CI level; 4 pending institutional acceptance).
