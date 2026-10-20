# W14 — Original Requirements and Field-Evidence Gap Audit

Reference: `docs/PROJECT_REQUIREMENTS.md`, eight workflows and six original rollout gates.

The W13 and W14 code does not change the fundamental production classification:

| Requirement | Verified engineering capability | Missing actual field evidence |
|---|---|---|
| WF-01 Email | EML parser, dedupe, optional Outlook Classic code | Authorized actual mailbox/Graph read-only smoke |
| WF-02 Deadline | Rust rules, revision-aware idempotent outbox, W13 task plan, W14 strict exported XML audit | 15-minute real scheduled runs on approved host |
| WF-03 Documents | Offline DOCX structure/phrase audit | Authentic documents and reviewer validation |
| WF-04 Regulations | Versioned declared source integrity and human approval gate | Official current source and interpretation |
| WF-05 HR | Anonymous structured evidence inventory and human-only approval | Actual privacy-compliant de-identification, HR reviewer UAT |
| WF-06 Schedule | Offline conflict proposals | Approved calendar integration and human-confirmed invitations |
| WF-07 Decisions | Revision checks, typed confirmation, transactional audit | Managed SSO/MFA/RBAC |
| WF-08 Recovery | Read-only status dashboard, UNKNOWN quarantine and audit | Continuous approved service monitoring and incident runbooks |

**Engineering breadth:** 8/8 workflows have meaningful synthetic/offline code. **Production institutional sign-offs:** 0/8. This is not a measure of percentage product completion.

## Rollout gates
1. Synthetic Python/local acceptance — VERIFIED IN CI (W14 adds 17 tests).
2. Real Rust compile and Python/Rust CI — VERIFIED IN CI.
3. Authorized Windows 15-minute task execution observed — PENDING (W14 exported XML audit cannot prove execution).
4. Approved read-only Outlook actual user smoke — PENDING.
5. Approved local/SMTP test alert with synthetic recipient — PENDING.
6. Three documented operator pilots signed off — PENDING.

**Result remains 2/6 technical CI gates, 4/6 pending field gates.**

## W14 specific outcome types
- GitHub-hosted Windows W14 XML audit PASS means a fictional configuration satisfies exactly defined restrictions.
- Self-hosted CMD transport PASS means a Windows runner executed only three hardcoded `echo` statements; it says nothing about signed-in GUI, ability to run PowerShell or Rust, IT authorization, installed task or mailbox access.
- Self-hosted CMD job QUEUED means no observed machine test; job blocked/failure also cannot establish GUI or user acceptance.
- Test runner machine identity must be obtained from GitHub job metadata, never assumed from `runs-on` label.

Repository GitHub API still reports PUBLIC. All examples and test data must remain fictional. Use no actual corporate SMTP, HR or student records. Do not modify company PowerShell policy, service configuration, Task Scheduler or security software as part of W14.


## Verified W14 real runner transport and synthetic CI checkpoint — 2026-10-20

**Separate self-hosted transport evidence:**
- GitHub run #39392711809, job #118527846747: Windows runner **DESKTOP-14SCTF4**, actual `cmd.exe` invocation, `W14_CMD_RUNNER_TRANSPORT_PASS`, SUCCESS.
- Repeat run #39392955500: exact same runner and CMD marker, SUCCESS. No checkout/PowerShell, no machine/OS data collection and no task installation.
- **NOT proven:** interactive Session ID, signed-in GUI, PowerShell ability, actual 15-minute Task Scheduler executions, live Rust, real Outlook, SMTP or IT authorization.

**Engineering PR #27 and main evidence:**
- PR #27 merged `bd0b6fc249035f6df37dfd42b60b08776e2ebdb5`; final PR head `80d7c3861b8ce70bd13e67572f9edc55ac899763`.
- Exact PR 4/4: Linux **218/218 Python tests** + Rust #39392964104; Windows W14 XML/17 tests #39392963977; W4 #39392964000; W5 #39392963994.
- Exact postmerge main 4/4: Linux/Rust #39393256363, Windows native #39393256349, W4 #39393256321, W5 #39393256319. All SUCCESS.
- An intermediate safety test expected only structured mismatch for XML metacharacters; fixed it to count XML parser rejection as fail-closed. No failed run counted as accepted.

**Rollout classification unchanged:** 2/6 technical CI gates; 4/6 genuine institution rollout gates pending; 0/8 institution production approvals.
