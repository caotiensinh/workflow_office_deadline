# W12 — WF-08 Local Monitoring & Recovery

## Purpose
An offline, privacy-safe health dashboard for the Python + Rust education office workflow. It is not a service controller and cannot approve decisions or resend notifications.

## Implemented
- Read-only SQLite URI mode=ro, query_only, schema inspection and optional quick_check. Missing database is reported without creating a file.
- Aggregates QUEUED, SENDING, SENT, UNKNOWN, STALE, case count, decision count and audit count. Individual messages, cases, personnel and email contents are never displayed.
- Alerts UNKNOWN as CRITICAL. A pending SENDING event is likewise escalated for manual reconciliation; no automatic resend. QUEUED older than a configurable interval is WARNING. Invalid timestamps, missing or corrupt databases and incompatible schema are incident codes.
- Ages measure alert creation, not the time of SMTP connection start.
- Japanese offline HTML (no JavaScript, external URLs, forms or action buttons) and ASCII-safe JSON. HTML file is created only with explicit output and never overwrites an existing report.

## How to use on fictional data
From project root in Windows PowerShell:

    $env:PYTHONPATH = Join-Path $PWD 'python'
    python -m edu_workflow.cli --db ./data/fictional.sqlite monitor
    python -m edu_workflow.cli --db ./data/fictional.sqlite monitor --format html --output ./w12-review.html

The monitor will NOT create fictional.sqlite. Use only a separately approved or synthetic existing SQLite file. For CI, the test itself constructs a disposable DB.

Optional --at takes a timezone-aware ISO timestamp for deterministic simulation; --queue-max-minutes takes 1..10080, default 30. Exit code 0 means healthy. Exit 3 means nonhealthy including a missing DB. Exit 2 means invalid args/file output.

## Incident response
1. UNKNOWN: do not resend automatically. Compare approved SMTP logs and notification records, have an authorized person determine actual delivery status.
2. SENDING: ambiguous; reconcile manually. The age reported is from record creation, NOT delivery-start time.
3. Overdue QUEUED: inspect configured scheduler and local delivery path. Do not assume external delivery.
4. Corrupt/missing DB: preserve backups and request system administrator analysis; no automatic migration, repair, restore or WAL reset.

## Limitations and safety
- This is a snapshot, not continuous monitoring, operational readiness, approved notifications, a live desktop UI or a service restart mechanism.
- SQLite quick_check and grouped counts can be expensive on very large datasets; operational acceptance and thresholds are outstanding.
- Never use confidential HR/student data in CI or this PUBLIC repository.
- Institutional Outlook/Graph, SMTP, SSO/MFA/RBAC, privacy/retention, code signing, physical Windows UAT and three approved pilots remain unresolved.


## W12 Verified engineering acceptance — 2026-10-20
- PR #23 MERGED at 6534d14bcbc0afafd547b7b2355d996ffe00dbee.
- PR head 82f43e977a79e41d308328263955d9f94d1f9610: Linux Python 185/185 + native Rust #39386732165 SUCCESS; Windows W12 read-only UNKNOWN/HTML E2E #39386732199 SUCCESS; Windows W4 #39386732167 SUCCESS; W5 Tk and unsigned EXE #39386732201 SUCCESS.
- Exact main postmerge: #39386978272 (Linux/Rust), #39386977929 (Windows W12 E2E), #39386978083 (W4), #39386978059 (W5) — all SUCCESS.
- W12 Windows tests verified UNKNOWN stays UNKNOWN; no case decision or SMTP retry, HTML output excludes invented private fixture text.
- CI found and fixed an initial HTML join syntax error (protected suite refused to load), and a Windows test fixture SQLite handle that needed explicit close. Neither intermediate failure was counted as accepted.
- Offline engineering acceptance only. No real account, signed-in endpoint, live SMTP recipient or production approved monitoring was tested.
