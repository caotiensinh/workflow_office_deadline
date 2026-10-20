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


## Verified W16 Session 0 finding (October 20, 2026)

**Evidence (do not promote to GUI UAT):** [GitHub run #39426407245](https://github.com/caotiensinh/workflow_office_deadline/actions/runs/39426407245), exact source HEAD `21b75c5b373dd51f1bc137fd4097535d6eaf3a3e`.
- Hosted build job `118639977685`: portable Python + native Rust smoke E2E and Windows session API PASS.
- Real Windows self-hosted **MRCAO** job `118640312265`: CMD `W15_REAL_SELFHOST_CMD_E2E_PASS` and `W16_SELFHOST_SESSION_PROBE_PASS`, SUCCESS.
- Actual Windows API fields: `process_session_id=0`, `active_console_session_id=1`, `console_match=false`, `status=SESSION_0_GUI_UAT_BLOCKED`. **The GitHub runner runs in Session 0, not the active user's Session 1**. Thus automatic GitHub-runner Tk GUI tests cannot validate signed-in user interaction.
- The same job reverified the actual offline core with fictional data: 5 cases, 6 alerts SENT as six JSON files, 0 UNKNOWN and 0 business decisions, second-run idempotency. Sanitized [evidence artifact #12266146908](https://github.com/caotiensinh/workflow_office_deadline/actions/runs/39426407245/artifacts/12266146908).
- No account names, corporate files, calendar/mail data, screenshots, Outlook, SMTP, Task Scheduler or PowerShell policy were accessed/modified during this numerical session probe.
- Prior selfhost W14 CMD transport ran on `DESKTOP-14SCTF4`, W15 and W16 core/session ran on `MRCAO`: they are distinct runner identities.

**Engineering acceptance:**
- W16 PR #31 merged at `690f05b728c13c1373c82ce9d718d468b671e4b3`; exact PR head `21b75c5b373dd51f1bc137fd4097535d6eaf3a3e`.
- Final PR 4/4 SUCCESS: Linux 239/239 Python tests + real Rust #39426415370; Windows Session API + synthetic E2E #39426415332; Windows W4 #39426415331; Windows W5 Tk/EXE #39426415403.
- Exact postmerge main 4/4 SUCCESS: Linux #39426789284, Windows E2E #39426789332, W4 #39426789314, W5 #39426789280.
- First run failed on inconsistent artifact upload/download names, and another on test output outside the required runner TEMP subdirectory. Both fixed, rerun and accepted only on the final green commit.

**Institution rollout acceptance unchanged:** 2/6 synthetic technical rollout gates, four missing authorized Windows Scheduler/Outlook/notification/three-pilot gates; 0/8 production approvals. Session 0 cannot be fixed by forcibly displaying windows from the service. The next GUI acceptance requires a **separately authorized** interactive signed-in Windows test session and a real human physically reviewing Japanese font, notification audio and ACK/Snooze.
