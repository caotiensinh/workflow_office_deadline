# CI Verification Evidence — 2026-10-19

## GitHub-hosted acceptance

- Repository: https://github.com/caotiensinh/workflow_office_deadline
- Source commit: `5914534b703f6edfeec2636bfd35032c0e5a3cf2`
- Push run: https://github.com/caotiensinh/workflow_office_deadline/actions/runs/39145381931 — **SUCCESS**
- PR run: https://github.com/caotiensinh/workflow_office_deadline/actions/runs/39145396201 — python-reference and rust-and-integration jobs **SUCCESS**
- Rust CI includes `cargo test --manifest-path rust-core/Cargo.toml`, release build and compiled Rust CLI processing fictional cases.
- Local authoring Python reference: 40/40 unittest PASS.
- Uploaded Git blob integrity: SHA of all 42 files matched original staged files before Git tree creation.

## Explicit exclusions

These tests do NOT validate real Outlook accounts, Microsoft Graph permissions, Windows Task Scheduler, school data, SMTP notifications, organization SSO, real personnel appraisal or official regulatory correctness. See `docs/IMPLEMENTATION_CHECKLIST.md`.
