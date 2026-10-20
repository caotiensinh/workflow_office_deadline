# W11 — Original eight workflows vs actual execution evidence

Date: 2026-10-20 (JST). Source of truth: docs/PROJECT_REQUIREMENTS.md and W1–W11 testable code, not old completion percentages.

## Engineering scope classification (NOT production readiness)
| Workflow | Executable offline/synthetic capability | Missing before actual operation | State |
|---|---|---|---|
| WF-01 Email | EML ingestion, dedupe, tentative deadlines, optional Outlook Classic COM adapter | Institution-approved real Outlook/Graph account smoke/polling | PARTIAL |
| WF-02 Deadline | Rust/Python deterministic D-3/D-1/due/overdue, SQLite revision-based alert delivery | Approved 15-minute recurring Task Scheduler and field alert acceptance | PARTIAL |
| WF-03 Documents | DOCX phrase/heading checks and missing evidence | Reliable semantic quality/source validation and document reviewer sign-off | PARTIAL |
| WF-04 Regulation | W10 versioned source registry, SHA256, supersession, citation pinning, human approval gate | Authentic official authority/currency, legal applicability and signed source chain | PARTIAL |
| WF-05 HR observations | **W11 anonymous-only** strict fact packets, source hash checks, structured Japanese reviewer draft, missing-evidence reasons and HR approval packet-integrity gate | Real authorized source records and validity, de-identification assurance, local policy, human reviewer acceptance | PARTIAL |
| WF-06 Schedule | W9 bounded anonymous conflict-free proposals | Approved live calendar read and human-confirmed invitations | PARTIAL |
| WF-07 Decision | Typed human confirmation, revision guard, atomic audit, W10/W11 source-integrity gates | Enterprise SSO/MFA/RBAC and verified human identity | PARTIAL |
| WF-08 Operations | Durable alert outbox, SMTP unknown quarantine, GUI ACK/Snooze receipts | Full service health/repair dashboard, incident SOP, real production monitoring | PARTIAL |

**All 8/8 workflows now have meaningful offline/synthetic code**, with significant gaps inside each. This is *breadth*, not 100% product completion. **Zero workflows have institutional production sign-off**.

## Rollout gates from original requirements
| Original gate | Evidence | Status |
|---|---|---|
| 1 Synthetic Python/sample data | W11 Python suite + fictional EML/HR packets | PASS (CI) |
| 2 Native Rust and Python/Rust E2E | Actual Linux/Windows GitHub CI | PASS (CI) |
| 3 Approved Windows scheduled operation | Plan-only/sandbox; no observed institutional endpoint | PENDING |
| 4 Authorized Outlook read-only real account smoke | No recorded institution account acceptance | PENDING |
| 5 Approved SMTP/push to test recipient | File spool and synthetic GUI, no approved live external test | PENDING |
| 6 Three signed-off institutional pilots | No recorded approved pilots | PENDING |

**Total original rollout acceptance: 2/6 synthetic CI gates PASS, 4/6 pending. 0/8 institutional sign-offs.**

## Safety and implementation boundaries
- Human decision remains mandatory: W11 generates template-based evidence inventory, **not HR appraisal**, ranking or employment action. Hash/metadata cannot prove a fact or identity. Real data requires institutional privacy review and authorization.
- GitHub API reports this repo as PUBLIC despite private description, so all W11 fixtures are completely fictional.
- Runner W8 diagnostic #39373569883 was actually accepted by DESKTOP-14SCTF4 but failed before test logic because Windows PowerShell ExecutionPolicy blocked the temporary `.ps1`. There is **no Session ID evidence** and no actual GUI acceptance. Do not bypass an institution security policy without explicit approval.
- Signed release, secure retention, encrypted real data, SSO/MFA, policy traceability and three approved human workflow pilots remain unmet.

## Priority after W11
1. W12: WF-08 monitoring dashboard, local outbox/UNKNOWN incident surfacing and privacy-safe admin audit (no automatic ambiguous resend).
2. Institution-approved operational staging: Windows Task Scheduler, Outlook/Graph read-only pilot, approved notifications, SSO/MFA, official source validation, signed release.
3. Three tracked, low-risk end-user pilots; human acceptance and corrections. Do not interpret CI success as production success.

## Verified W11 engineering result
- PR #21 MERGED at `cccdd9f13d8cd8ee2902060b97d99fce2b90798f`.
- **165/165 Python tests** plus native Rust PASS; Windows HR draft/approval, W4 notifications and Tk/EXE E2E PASS on both PR and postmerge.
- Final `main` CI proofs: Linux/Rust #39384328877, Windows synthetic HR E2E #39384328977, Windows W4 #39384328924, GUI/EXE #39384328968 — **4/4 SUCCESS**.
- The 8/8 engineering coverage classification is about offline/synthetic executable breadth; the original institution rollout remains **2/6 CI gates, 0/8 signed-off production workflows**. Do not confuse counts with 100% product completion.
