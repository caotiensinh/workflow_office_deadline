# W12 — Requirements gap after offline Monitoring & Recovery

Reference: docs/PROJECT_REQUIREMENTS.md. All 8 workflows have substantive offline/synthetic executable code. That is breadth, not 100% feature or production completion.

| Workflow | Offline engineering proof | Still missing before real institutional operation |
|---|---|---|
| WF-01 Email | EML parser/dedupe, tentative deadlines; optional Classic Outlook COM | Approved real Outlook/Graph mailbox, read-only smoke and regular polling |
| WF-02 Deadline | Rust/Python D-3/D-1/due/overdue, durable idempotent alerts | Approved 15-min Task Scheduler and live endpoint confirmation |
| WF-03 Documents | DOCX structure/phrase evidence checks | Semantic validity and human document acceptance |
| WF-04 Regulations | Local version/date/hash checks and atomic human decision audit | Authoritative official source provenance and legal review |
| WF-05 HR | Anonymous fact packets, Japanese reviewer drafts and source integrity gate | Genuine de-identification, factual verification, manager sign-off |
| WF-06 Schedule | Conflict-free anonymous free/busy proposals | Approved live calendar + invitations only after human confirmation |
| WF-07 Approvals | Typed human confirmation, revision and transactional audit | Managed organizational SSO/MFA/RBAC |
| WF-08 Health/recovery | W12 read-only aggregate monitoring, UNKNOWN/SENDING incidents, overdue QUEUED, SQLite check, offline JP HTML | Continuous on-site monitoring, operator runbooks, backup/restore drills and real SMTP reconciliation |

Engineering breadth: 8/8. Institutional production approvals: 0/8.

Original rollout gates:
1. Synthetic Python/data CI — PASS.
2. Native Rust and Python/Rust integration CI — PASS.
3. Institution-approved Windows scheduled operation — PENDING.
4. Authorized Outlook read-only smoke — PENDING.
5. Authorized local/SMTP alert to a test recipient — PENDING.
6. Three signed-off workflow pilots — PENDING.

Total 2/6 rollout gates verified at CI level. No actual institutional production sign-off.

Security: GitHub API reports this repository PUBLIC, and the W8 self-hosted Windows diagnostic failed under Windows PowerShell ExecutionPolicy on DESKTOP-14SCTF4. No interactive Session ID and no field GUI sign-off can be inferred. Do not bypass managed machine policies without IT authorization.

Next focus: security and privacy approvals, signed release, approved connected systems, field desktop and Task Scheduler, human-approved alert destination, and three measured pilots. UNKNOWN must not be blindly retried.
