# W22B — Evidence intake for three or more 15-minute Task Scheduler runs

## Purpose
The W21B -PlanOnly safeguard validates configuration but cannot prove cadence. W22B takes **operator-provided, sanitized metadata** about 3–8 claimed executions of EducationAIWorkflow, reads it offline, requires strict UTC timestamps, zero exit codes and 900 ± 60 second differences. It returns privacy-safe counters only. The file schema is exact; unknown keys, subject identifiers, absent/extra events, bad timezone, duplicate JSON keys and failed runs are rejected. No Windows Task Scheduler API calls, no installation, no Outlook, no machine policy changes.

## Evidence limits
These entries are not signed; even fully consistent timestamps only establish local internal consistency. `real_task_execution_independently_verified`, `it_approved`, and `production_accepted` are always false. Institution rollout gate 3 stays PENDING until IT explicitly approves and independently observes actual 15-minute execution.

Python test suite uses invented timestamps only; run through Linux and Windows CI on exact branch head before PR merge.