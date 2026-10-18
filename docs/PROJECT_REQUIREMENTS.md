# Education Office Deadline & Approval Workflow — Project Requirements

## Outcome
Automate intake, risk classification, task/due-date tracking, document checklist checks, evidence references, decision routing, alerts and audit. Only human-authorized decisions or external changes may be committed.

## Roles
- Operator: prepares, checks and triages synthetic or institution-approved data.
- Approver: verifies evidence and issues an explicit approval or rejection.
- IT/security administrator: approves data handling, identity, Outlook/Graph integration and notification destinations.

## Workflows (WF-01–WF-08)
| ID | Input | Automatic steps | Mandatory human gate | Output |
|---|---|---|---|---|
| WF-01 Email intake | Outlook Classic read-only / approved `.eml` | Redact, fingerprint, deduplicate, create tentative case | Confirm extracted deadline; external email replies | Task |
| WF-02 Deadline watch | Verified case due date | D-3/D-1/due/overdue; idempotent outbox | Resolve ambiguous deadlines | Local alert or approved SMTP |
| WF-03 Document check | Local DOCX + rules | Check required headings/phrases and missing evidence | Final correctness and official submission | Validation report |
| WF-04 Regulation check | Versioned official references | Check evidence pointer and flag missing information | Interpret applicable rules; approve action | Review-needed signal |
| WF-05 HR observations | Fictional/approved anonymous records | Organize facts and missing references | All appraisal and personnel decisions | Draft evidence summary |
| WF-06 Schedule | Explicit availability and constraints | Detect conflict/propose schedule (future adapter) | Invite/send/reschedule | Proposal |
| WF-07 Decision gate | Revision, authenticated actor, evidence | Reject invalid/stale transitions; audit | Explicit approve/reject confirmation | Decision log |
| WF-08 Health/recovery | Process health, outbox, state | Retry safe local steps, quarantine unknown sends | Resolve ambiguous SMTP delivery; unlock incidents | Auditable recovery |

## Functional acceptance gates
- No guessed extracted dates are treated as verified.
- A completed or canceled case produces no new deadline events.
- Same daily deadline event is emitted no more than once per case revision.
- Approval fails for missing evidence or unverified deadlines.
- External mail sending is disabled by default and uses an explicit allowlist.
- A connection timeout after sending results in UNKNOWN, not blind retry.
- Raw email content and employee identifiers are not copied into public logs.
- Every workflow decision has an audit event and a human-readable state.

## Technical boundaries
- Python 3.11+ controls state, adapters, local document checks and SQLite.
- Rust handles deterministic rule evaluation over a strict tab-delimited protocol.
- Windows Task Scheduler triggers polling; task must be permitted by endpoint policy.
- Outlook Classic COM is an explicitly optional read-only adapter; New Outlook requires Microsoft Graph delegated authorization.
- Local rule evaluation is **not** document/legal semantic accuracy or an AI model integration.
- Real personnel/student data is forbidden until institutional authorization and security review.

## Rollout gates
1. Synthetic local sample and Python test PASS.
2. Rust compiled tests and Python↔Rust end-to-end PASS in GitHub CI.
3. Windows scheduled run approved and observed.
4. Read-only Outlook smoke with organization approval.
5. Approved local/SMTP alert to synthetic recipient.
6. Three workflow pilots, documented outcomes, operator sign-off.
