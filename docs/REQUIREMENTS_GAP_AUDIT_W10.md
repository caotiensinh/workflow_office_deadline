# W10 — Current requirements traceability after WF-04 implementation

Date: 2026-10-20 JST. This updates, but does not erase, the historical W9 audit.
Sources: `docs/PROJECT_REQUIREMENTS.md`, `docs/ARCHITECTURE.md`, W1–W10 code/CI.

## Workflow coverage (NOT production readiness)
| WF | Verified substantive offline/CI capability | Outstanding requirements | Status |
|---|---|---|---|
| 01 Email intake | EML parser, tentative dates, dedupe and optional Outlook Classic COM code | Authorized live Outlook or delegated Graph adapter and signed-in acceptance | PARTIAL |
| 02 Deadline watch | Deterministic Rust/Python D-3/D-1/today/overdue, durable idempotent alerts | Approved Windows 15-minute scheduler and real delivery | PARTIAL |
| 03 Document check | DOCX phrase/structure and missing-reference report | Semantic accuracy, authentic citations, end-user document acceptance | PARTIAL |
| 04 Regulation source check | **W10:** versioned local registry, document SHA-256, citation/authority opaque codes, declared effective windows, supersession/review flags; atomic REGULATION human approval source pinning | Official source authenticity, legal interpretation/currency, signed trusted registry, authorized compliance review | PARTIAL (new substantive offline control) |
| 05 HR observations | Case/audit and evidence hold | Structured anonymous fact synthesis, source-based draft for reviewer, approved HR pilot | MINIMAL |
| 06 Schedule | W9 conflict-free anonymous free/busy proposals | Authorized live calendar integration, invitation after human approval | PARTIAL |
| 07 Decision gates | Case revision, typed confirmation, atomic audit; W10 stricter for REGULATION | Enterprise SSO/MFA/RBAC, multi-user identity and policy governance | PARTIAL |
| 08 Operations/recovery | Durable SQLite alerts, unknown SMTP quarantine, GUI receipts | Health monitoring dashboard, remediation controls, secure production SOP | PARTIAL |

Engineering tally: **7/8** workflows have meaningful offline/synthetic code; **1/8** has a narrow technical foundation (WF-05). **0/8** signed off for institution production. This 7/8 count means breadth of implementation only; it is not an 87.5% completion measure.

## Six original rollout gates
1. Synthetic Python sample/tests: PASS at CI level.
2. Native Rust compiler + Python/Rust integration: PASS at CI level.
3. Approved recurring Windows scheduler on institution endpoint: PENDING.
4. Authorized read-only Outlook smoke: PENDING.
5. Approved SMTP/push delivery to test recipient: PENDING.
6. Three signed-off institution workflow pilots: PENDING.

**Result: 2/6 verified at synthetic CI, 4/6 awaiting external authorization or real environment.**

## W10 security boundary
Versioned hash validation demonstrates that a file matches an *untrusted locally declared registry*. It **never** establishes official issuer identity, legal effect, exact applicability or a human's identity. A paired manifest+document can be maliciously changed without digital signatures or trusted metadata governance. The control prevents **unverified REGULATION approvals** but cannot replace lawyer/school administrator review.

The repository API still reports visibility `public`. MRCAO's read-only W8 Session probe job #39373569883 remains queued at the latest check; no claim of current interactive desktop acceptance.

## Next substantive work
W11: WF-05 source-cited, anonymous-only HR observations and missing-evidence summaries. Then WF-08 operational dashboard, plus separate IT-approved live connectors, trust policy, signed release, security review and three-personnel-safe pilots.
