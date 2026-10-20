# W20B — Native Rust probe on actual Windows self-hosted runner

## Fixed product objective
Python + Rust automate office email, deadlines, documentation, alerts and audit. Consequential decisions require explicit human authorization. Source: `docs/PROJECT_REQUIREMENTS.md`.

## Purpose and ownership
Independent W20B engineering lane owns only `rust-core/src/bin/w20_session_probe.rs`, `.github/workflows/w20b-native-selfhost-session.yml` and this document. It does not change W20A GUI code or the existing four main CI workflows.

W16 measured a Windows service Session 0 and active console Session 1 on **MRCAO**, so Session 0 cannot establish interactive GUI UAT. W20B supplies a minimal standalone native Rust read-only probe and exercises it on a **real self-hosted Windows GitHub runner**. It does not launch any GUI, invoke Task Scheduler, inspect an existing account, read Outlook, touch production cases or bypass PowerShell policy.

### Verification boundary
- 9 Rust positive/negative tests protect `Session 0`, different/absent console, invalid session IDs, nonzero matching-console **candidate**, plan-only mode and never-return-production-approved output.
- Hosted Windows builds the Rust binary, tests `--plan-only` and `--inspect`, then stores EXE plus SHA-256 as a short-retention artifact.
- Self-hosted Windows only downloads that exact run's artifact into GitHub `RUNNER_TEMP`, uses CMD and certutil to verify its SHA-256 and invokes the EXE with `--inspect`. No repository checkout or PowerShell commands on the host.
- Only numeric process/console session IDs and negative acceptance flags are permitted. A matching console is **not a human UAT PASS**. The GitHub artifact checksum is an integrity check, not an enterprise signature.
- Workflow is branch-scoped; it does not automatically run on `main` or on arbitrary pull requests.

## Verified implementation evidence (20 October 2026)
- Branch head `617b8dcac89ba3ba89641dab6d4c340c70671f4d`, GitHub Actions <https://github.com/caotiensinh/workflow_office_deadline/actions/runs/39444760875> **SUCCESS**.
- Hosted build job #118703606920: **9/9 Rust tests PASS**, native Windows plan-only and read-only inspection PASS.
- Self-hosted job #118704057291: **SUCCESS**, actual runner **`DESKTOP-14SCTF4`**, not MRCAO; verifies the exact artifact SHA with CMD/certutil then executes read-only EXE. Marker `W20B_SELFHOST_NUMERIC_SESSION_PASS_NOT_HUMAN_GUI_UAT`.
- Does not claim an operator touched the screen or provide proof of actual user Session 1 interactions.
- Before integration, require 4/4 PR main workflows at exact head and postmerge 4/4 main at exact merge SHA.

## Remaining external acceptance
Real signed-in GUI Japanese font/audio/ACK/Snooze, Windows logout/login Startup, authorized 15-minute Task Scheduler execution, Outlook/approved notification/identity/privacy and three pilots remain pending. Original organization rollout still **2/6 CI gates** and **0/8 production signoffs**.
