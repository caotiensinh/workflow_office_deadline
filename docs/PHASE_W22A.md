# W22A — Operator handoff: no-GUI report review by packaged EXE

## Fixed objective
Automate educational office workflows with Python + Rust; IT-approved human actions only for real data and consequential decisions.

## Operator friction removed
The Windows packaged `EDUFieldUAT.exe` previously supported only launching a consent-first fictional GUI, or numeric session/preflight diagnostics. Operators needed Python to independently run the W17 saved self-report reviewer. W22A adds `--review-report-file FILE --review-output-file NEWFILE`, a review-only route to the same EXE. It consumes only the pre-existing synthetic UAT JSON and returns a redacted, exclusive-new JSON summary. It never launches GUI, queries Win32 session/Task Scheduler, or touches mail/Startup. Complete results remain **self-attested**, not independent operator/IT/production approval.

Unit tests cover successful/incomplete reviews, tampered approvals, mismatched receipt counters, CLI argument safety, exclusive-write/no-overwrite and no GUI. The Windows W5 build job **runs the actual packaged EXE** using a synthetic fixture, validates that its output has all important approval flags false, and confirms original fixture bytes unchanged.

This workflow is deliberately synthetic and does not grant access to real institution devices. True human GUI Session 1 observation still pending.