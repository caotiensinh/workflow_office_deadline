# W13 — Readiness and original requirements gap audit

Original source: docs/PROJECT_REQUIREMENTS.md.

Eight workflows already have offline/synthetic code (WF-01 email, 02 deadlines, 03 DOCX, 04 rule reference, 05 anonymous HR inventory, 06 schedule proposal, 07 human approvals, 08 outbox health). This means **8/8 engineering breadth**, not product completion or actual institutional rollout.

## Original rollout gates and evidence
| Gate | Evidence as of W13 code phase | Status |
|---|---|---|
| 1 Synthetic Python regression | 185 W12 baseline, new W13 plan safety regression | CI verified only |
| 2 Native Rust/Python integration | GitHub Linux and Windows builds | CI verified only |
| 3 Approved 15-minute Windows Scheduler | \`install_task.ps1 -PlanOnly\` + W13 explicit readiness checks, no approved endpoint run | PENDING |
| 4 Authorized Outlook mailbox read-only smoke | No employer IT-approved mailbox verification | PENDING |
| 5 Approved test alert to synthetic recipient | Synthetic file outbox E2E, no approved real SMTP/local delivery field acceptance | PENDING |
| 6 Three pilots with operator sign-off | No approval, no signed-off end-user pilots | PENDING |

Counts remain **2/6 CI technical gates, 4/6 real rollout gates pending, 0/8 institution-approved production workflows**.

## Identified blockers
- Repository GitHub API visibility is public, so confidential content is forbidden.
- The prior self-hosted Windows probe (#39373569883) failed when Windows PowerShell ExecutionPolicy blocked a temporary script on runner DESKTOP-14SCTF4. There is no reliable GUI Session ID or real field UAT; machine command probes cannot bypass managed policy.
- An existing Task Scheduler entry does not prove frequency, actual user rights, correct Rust binary, successful delivery or that the organization authorizes it.
- Missing institutional real Outlook/Graph permissions, SSO/MFA, signed installer, privacy impact and retention, approved test SMTP endpoint and human pilots.

## W13 scope
The W13 preflight provides read-only **source/endpoint facts only**. It never installs tasks, changes ExecutionPolicy, starts the desktop GUI, connects to Outlook, touches a production SQLite DB, sends mail, modifies cases or performs approvals. Machine probes are optional and gated by explicit prior IT permission; tests use fabricated Windows observations.

Next: get IT permission for reviewed/signed execution methods, real Windows field tests with a signed-in operator, approved 15-minute schedule proof, read-only mailbox and recipient checks, and institution privacy/identity sign-off. Do not treat green GitHub CI as enterprise UAT.
