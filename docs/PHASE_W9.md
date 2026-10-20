# W9 — WF-06 offline conflict-free meeting proposals

## Original requirement and actual implementation
WF-06 calls for a scheduling proposal from explicit availability and constraints. Humans must authorize any invitation, calendar insert, reschedule, or external notification.

The W9 CLI proposes time ranges from anonymous structured free/busy windows. It does **not** read live Outlook/Graph calendars, check live participants, store a meeting in SQLite, invite anyone, or claim that available data is current.

## Reproducible example

From project root (Python 3.11+):

```powershell
$env:PYTHONPATH = Join-Path $PWD 'python'
python -m edu_workflow.cli schedule-propose --file examples/wf06_availability.json
```

The CLI accepts a read-only JSON file, with a global ISO offset-aware `window`, meeting `duration_minutes` (15–480), optional `slot_minutes` (5–60), optional `max_proposals` (1–20), and 2–20 `participants` containing *only* `available` and `busy` interval arrays. Intervals use `start`/`end` offset-aware ISO times and half-open [start,end) semantics. Intersections exclude known busy blocks, sort deterministically, round up to JST slot boundaries and return the earliest fitting proposals.

Output includes `requires_human_approval=true`, `calendar_verified=false`, `external_actions_performed=false`, and `writes_database=false`.

### Explicit safety boundaries
- No participant names, email addresses, meeting subjects or freeform personal information are accepted. Unknown fields cause a rejection rather than leaking to logs.
- Bounded input (256 KB, <=32 intervals per availability/busy list, <=31 days). No timezone-naive dates accepted.
- No local workflow DB is opened for proposals; `--db` is ignored by this command. No event is booked or submitted.
- For actual Microsoft Calendar/Google Calendar/Outlook integration, institutional authorization, version/revision checking, and human approval before writes remain outstanding.

## Test acceptance
Run `PYTHONPATH=python python -m unittest discover -s tests -p test_schedule_w9.py -v` to test conflict removal, multiple timezones, boundaries, slot rounding, duplicate windows, no common slot, validation failure, CLI no-DB side effects, and symlink/oversize input rejection.

## Actual W9 acceptance evidence
- PR #17 merged commit: `01701ca12c7a6752bf9c36760989d278c6dd06e0`.
- Windows runner dedicated W9 WF-06 read-only command PASS in #39375465997; Linux 126/126 Python + real Rust PASS #39375466012.
- Full four postmerge main workflows PASS: #39375595466, #39375595438, #39375595478, #39375595406.
- Requirement coverage and remaining production gates: `docs/REQUIREMENTS_GAP_AUDIT_W9.md`.
