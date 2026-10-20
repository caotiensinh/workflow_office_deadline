# W14 — Windows Runner CMD Transport + Offline 15-Minute Task Audit

## Fixed project objective
Automate education-office inbox intake, evidence checks, deadlines, alerts, planning and audit with Python + Rust. All regulation, HR, external communications and other consequential decisions remain **human-authorized**.

## Read the evidence boundaries first
W8 real self-hosted runner DESKTOP-14SCTF4 accepted GitHub job #39373569883 on October 20, 2026, but the Windows PowerShell host refused GitHub's temporary `.ps1` because script execution was disabled. The intended Session ID check never ran. This is not proof that GUI works or that the organization allows scripts.

W14 introduces a **different, strictly bounded CMD shell connectivity test**. It tests whether a self-hosted Windows agent can execute GitHub Actions' own temporary CMD batch step, and nothing beyond printing three fixed markers. It does **not** switch ExecutionPolicy, bypass a PowerShell restriction, checkout source, inspect machine configuration, run Python, access work files or send mail. Any successful marker only proves CMD job transport, **not IT approval**, login session or Task Scheduler operation.

- Workflow: `.github/workflows/w14-cmd-selfhost-probe.yml`
- Trigger: a single push to `feat/w14-safe-cmd-runner-probe`; no main push/PR schedule, no new persistent background job.
- Runner selector: `[self-hosted, Windows]`. It may select **any matching Windows runner**. Verify GitHub's actual job runner before making any named-machine claim. If queued, offline or blocked, report that status plainly.
- GitHub agent itself may create normal temporary job scripts/logs; the script performs no additional project or system mutation.

## Offline IT Task Scheduler evidence auditor
`python/edu_workflow/task_xml_audit.py` strictly analyzes only an explicitly supplied local exported XML snapshot. It rejects oversized files, symlinks, DTD/entity declarations and incompatible task XML. A task snapshot qualifies as `CONFIG_MATCH_UNVERIFIED` only when:
- One enabled TimeTrigger/CalendarTrigger has exact `PT15M` repetition.
- Task settings are enabled and a single principal has `LeastPrivilege`.
- Exactly one Exec action uses a fixed PowerShell executable and `-NoProfile -File "C:\...\run_once.ps1" -Channel file`, with **no** Outlook, SMTP or extra shell commands.
- There are no extra actions or working directory overrides.

Sample fixture `examples/w14_task_synthetic.xml` is entirely fictional. From project root:

```powershell
$env:PYTHONPATH = Join-Path $PWD 'python'
python -m edu_workflow.task_xml_audit --xml examples/w14_task_synthetic.xml
```

The expected result is `CONFIG_MATCH_UNVERIFIED` (exit code 0), all eight structural checks true, but `task_existence_verified=false`, `task_executed_verified=false`, `fifteen_minute_runs_observed=false` and `production_accepted=false`. A mismatch returns code 3, and malformed input code 2.

### Why offline XML is insufficient for production
An exported XML can be fictional, stale or modified. It does not prove the task exists on a real workstation, runs at the expected interval, can access Rust, reads an approved mailbox, creates actual approved alerts or is authorized by IT. **Never export actual XML or private computer/account paths to public GitHub CI.** Instead use test fixtures here, retain true evidence only in an authorized institution-controlled location, and have IT verify timing/logs separately.

## Original six rollout gates
The original requirements remain **2/6 CI gates verified**, with actual approved Windows Task Scheduler run, Outlook read-only, approved alert and three user pilots pending. Enterprise SSO/MFA, approved privacy handling and signed releases are also outstanding. Green CMD or XML tests do not advance any of these rollout gates.

## Engineering test and release criteria
- 17 W14 Python safety tests (total at least 218), Linux native Rust and Python integration.
- Windows-hosted synthetic W14 XML audit E2E, W4 GUI and W5 EXE must remain green.
- GitHub self-hosted CMD transport test is **separate** from the four hosted engineering CI gates and can be queued/offline or run on a different Windows runner. Do not claim the target runner was tested unless GitHub job metadata identifies it.
- Merge W14 only after 4/4 hosted CI pass, then verify exact postmerge `main` checks. No production UAT claim.

## Next real-world evidence step
Only after organizational authorization, review task XML **locally**, verify 15-minute scheduler execution logs and Rust on an approved endpoint, perform approved read-only Outlook intake and local/synthetic-recipient notification, then collect signed-in operator attestations. Do not defeat PowerShell ExecutionPolicy or access real HR/email records without permission.
