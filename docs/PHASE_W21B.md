# W21B — Exact 15-minute Task Scheduler PLAN acceptance, not installation

## Objective
Move the Python + Rust office automation product toward **authorized** Windows 15-minute scheduling without changing any runner or organization Task Scheduler policy.

## Independent lane B
- `python/edu_workflow/task_plan_w21b.py` rejects unsafe PlanOnly outputs from `windows/install_task.ps1`. It requires exactly a 15-minute interval, limited user task name EducationAIWorkflow, file channel, no email source, no task replacement and an exact quoted `powershell.exe -NoProfile -File "...\\run_once.ps1" -Channel file` action.
- Returns no source command or private paths; avoids accidentally treating a plan as installation, actual execution or IT acceptance.
- 12 local positive/negative regression cases, including forged schema/duplicate JSON keys, metacharacter injection, wrong cadence, SMTP/Outlook and replace-existing.
- Branch-scoped hosted Windows CI runs the **real** `install_task.ps1 -PlanOnly -IntervalMinutes 15`, validates resulting JSON and runs all W21B regression tests. No `schtasks.exe /Create`, no machine mutation or execution-policy bypass. Hosted machines are not institution endpoints.
- Existing four Linux/Windows workflows on PR must pass at exact HEAD; merge only after validated.

## Unchanged rollout boundary
A plan-only PASS does **not** meet rollout gate 3. A real 15-minute scheduled run requires explicit enterprise IT authorization and independent observation on the approved target. Outlook, recipient, privacy/SSO and three pilots likewise remain pending. Public GitHub repository: fictional-only test data.