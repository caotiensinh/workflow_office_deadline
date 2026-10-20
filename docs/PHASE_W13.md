# W13 — Field Staging Readiness Gate (read-only)

## Original purpose (do not change)
The Python + Rust office workflow automates source intake, reminders, document/evidence checks, suggested meeting times, and audit. A human confirms extracted deadlines, performs personnel and regulation review, and explicitly approves material actions. External mail/calendar writes must require authorized human approval.

**W13 does not perform rollout**. It produces conservative source/endpoint readiness evidence and prepares the *existing* 15-minute Windows Task Scheduler PLAN only.

## What W13 actually delivers
- \`python/edu_workflow/staging_preflight.py\` reads only a fixed list of essential project files by default. It does not inspect the host, initialize SQLite or run any task.
- Opt-in machine observation (only when IT authorization actually exists) may read **only** current Windows process Session ID, effective PowerShell execution policy and existence of the exactly named \`EducationAIWorkflow\` task. No task XML, credentials, Outlook, registry modification, changes to ExecutionPolicy or personal records.
- There is **no automatic production PASS**: task existence cannot prove a 15-minute cadence, session ID != 0 cannot prove an operator observed the UI, and a permissive ExecutionPolicy cannot prove script integrity.
- The six institutional items (approved endpoint, observed Task Scheduler, approved read-only Outlook, approved test delivery, privacy/SSO/signing, three signed pilots) remain \`PENDING_AUTHORIZED_EVIDENCE\`.
- JSON output is ASCII-safe, limited to fixed labels and statuses. A file is written only with explicit \`--output\` to a new path, exclusive/no overwrite.

## Safe command on any machine — PLAN ONLY

From the repository root, with Python 3.11+:

    $env:PYTHONPATH = Join-Path $PWD 'python'
    python -m edu_workflow.staging_preflight --project .

This command reads project files only and does not access Windows endpoint state. It can be run on GitHub-hosted CI with fictional fixtures.

### IT-approved, read-only endpoint inspection ONLY

The following is **not an instruction to bypass company policy**. After IT separately permits running this diagnostic using the existing approved environment (without changing execution policy), an authorized operator may choose:

    python -m edu_workflow.staging_preflight --project . --mode machine-readonly --ack-it-authorized

This will probe a few Windows OS facts without running a \`.ps1\` or writing system configuration. The flag **is not proof of permission**; IT must approve use beforehand. Do not run on managed corporate endpoints without that authorization.

If the current effective PowerShell policy is \`Restricted\` or \`AllSigned\`, the report says \`BLOCKED_NEEDS_IT\`; it does not use \`-ExecutionPolicy Bypass\`, set policy, disable antivirus, install anything or spawn GUI. Session 0 yields \`BLOCKED_FOR_GUI\`. Nonzero session remains \`OBSERVED_NOT_HUMAN_UAT\`. Even an existing task is only \`EXISTS_NOT_VALIDATED\`.

### Task Scheduler source preview ONLY

On a permitted Windows PowerShell session:

    .\windows\install_task.ps1 -PlanOnly -IntervalMinutes 15

The plan describes a limited-rights local file-only notification task. GitHub-hosted Windows CI tests the plan but does not call installer without \`-PlanOnly\` or modify real Task Scheduler. If the company's policy blocks PS scripts, **do not bypass it**. Ask IT to review the script, signing, and approved deployment method instead.

## Go/no-go decisions after this phase
A human IT/security owner must provide appropriate evidence for: endpoint & script policy approval, installed task execution (including schedule and logs), read-only authorized Outlook smoke, approved test delivery, SSO/MFA/privacy/retention and signed release, and three recorded operator pilots. Until then, this tool always reports \`production_accepted: false\` and does not authorize migration to production.

The original repository is reported PUBLIC by GitHub. No real email, employee/student records or secrets may be committed or uploaded to CI.

## Test evidence required
- W13 deterministic mock Session 0/Restricted, AllSigned, nonzero session, missing task and malformed observations.
- Plan-only never invokes machine inspection unless specifically requested and authorized.
- Windows hosted synthetic CI exercises the real 15-minute \`install_task.ps1 -PlanOnly\`; source code review only, no registered task.
- Merge only with 4/4 exact PR CI and 4/4 postmerge main CI PASS; production gate remains separate.

## Verified W13 CI checkpoint (2026-10-20)
- W13 PR #25 MERGED at `9c8552cd44dabac9590333c7b86bfdee8b986802`.
- Exact PR Linux: 201/201 Python regression tests including 16 W13 tests and native Rust PASS (#39389145184).
- Exact PR Windows W13: 16/16, `install_task.ps1 -PlanOnly -IntervalMinutes 15` returned file channel, no Outlook/SMTP and no ExecutionPolicy bypass (#39389145248). W4 #39389145003, W5 GUI/EXE #39389144999 also SUCCESS.
- Four exact postmerge main CI: Linux/Rust #39389357539, Windows E2E #39389357526, W4 #39389357533, W5 #39389357534 — all SUCCESS.
- CI exercises GitHub-hosted Windows, NOT corporate runner; no Task Scheduler changes, live Outlook/SMTP, machine policy override, signed-in desktop UAT or institutional production approval.
