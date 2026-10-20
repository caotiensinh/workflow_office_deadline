# W18 — Final ZIP integrity gate (synthetic Windows UAT handoff)

## Fixed project outcome
See `docs/PROJECT_REQUIREMENTS.md`: Python + Rust automate email intake, deadline checks, documentation, alerting, human-authorized decisions and audit. Never claim field or production acceptance from synthetic tests.

## Root cause addressed
W17 verified the GUI EXE and SHA-pinned CMD launcher **before** creating `W17_SignedIn_GUI_UAT_Kit.zip`. This proves pre-archive consistency but does not independently inspect the final compressed artifact that an operator will receive. W18 adds a read-only integrity gate for that final ZIP. It does not edit the W8 GUI, deploy to MRCAO or launch from runner Session 0.

## Implementation
- `python/edu_workflow/kit_integrity_w18.py` independently reads the **final ZIP** and compares its immutable three-member allowlist to `EDUFieldUAT.exe`, `00_START_UAT.cmd` and `W17_README_JP.txt`.
- Reject duplicate, extra, missing, traversal or nested entries; ZIP symlinks, directories, encrypted members, unexpectedly large files, excessive compression ratios and non-UTF-8 readme.
- Verify EXE SHA-256 against the embedded CMD `EXPECTED` constant. Compare the **entire launcher** against the trusted W17 source template after substituting that exact hash (to catch injected commands, including attacks that change the EXE and launcher together).
- Optional `--expected-zip-sha256` verifies the full ZIP against an expected artifact checksum. CLI failures produce only `W18_ZIP_REJECTED` (no filenames or user data).
- `tests/test_kit_integrity_w18.py` adds **17 fictional-only regressions**; Linux CI must discover **at least 272 Python tests**.
- `tests/w18_kit_zip_smoke.py` checks the actual Windows CI output ZIP and three separate disposable ZIP tamper cases (EXE, launcher, extra member). Originals remain unchanged. SHA of the final ZIP is emitted by the job.
- Windows W5 packaging job performs the archive gate **before uploading the artifact**, with failure blocking the job.

## Acceptance and authority boundary
W18 PASS means only that the final unsigned ZIP content is structurally valid and matches its **checked-out GitHub source launcher template**. This is **not** Authenticode, signed publisher identity, verified provenance against a hostile GitHub repository, human consent, actual Session 1 desktop/audio testing, institution IT authorization, login Startup, Task Scheduler, Outlook, SMTP or production signoff. Do not upload real school or HR data; repository is PUBLIC.

The original six rollout gates remain: 2/6 **synthetic CI technical gates** passed historically. **0/8 institutional production signoffs**. The unresolved signed-in GUI UAT and institution-specific gates require authorization and actual observations.
