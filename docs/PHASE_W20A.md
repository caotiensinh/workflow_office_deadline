# W20A — Verify persisted signed-in GUI UAT report before success dialog

## Original goal
Python + Rust automate institutional email, deadlines, records, alerts and audit, with explicit human authorization for consequential decisions. See `docs/PROJECT_REQUIREMENTS.md`.

## Root cause and implementation
The W8/W19 one-click launcher previously trusted `run_manual()`'s **in-memory** success status when displaying a Japanese success dialog. Although W17 implemented strict read-only JSON review, the one-click UAT did not invoke that reviewer before telling the operator that fictional GUI actions were complete.

W20A changes `field_uat_launcher.one_click()` to read **the immutable-new JSON file that was written** and call `edu_workflow.uat_review.review()` before showing the result. It fails visibly when:
- report is missing, malformed or contains duplicate keys;
- ACK/Snooze/audit receipts are inconsistent;
- a production/IT/login autorun/independent physical observation flag is forged;
- the in-memory completion disagrees with the persisted document.

Only the privacy-safe review status appears in the dialog, which explicitly says that a structurally consistent report is **self-attestation and not independently observed physical GUI, signed IT approval or production acceptance**. A partial report is shown as incomplete, not PASS. Existing consent-first behavior, fictional SQLite data, Session 0/active-console protection, startup and outbound safety remain unchanged. The UAT report is read-only after creation.

## Acceptance
- 9 new fictional-only persisted-file positive/negative regressions, plus original W7/W8/W17/W19 and Rust tests.
- Hosted Windows packaging must continue to PASS preflight, numerical session checks, W18 ZIP hash and three negative tamper ZIPs.
- Exact-head PR 4/4 CI, merge only after PASS, exact postmerge 4/4 CI and persisted checklist.

## Unchanged external blockers
No Session 0 service can observe the real Session 1 operator's Japanese text, audio, focus, ACK/Snooze, or logout/login Startup. No real Outlook, SMTP, approved recipient, Task Scheduler installation, IT authorization, code signing or production pilot performed. Original institutional rollout remains **2/6 technical gates** and **0/8 signoffs**.
