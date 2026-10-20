# W8 — one-click, synthetic Windows field UAT and MRCAO preflight

## Fixed objective
Python + Rust automatic email/deadline/workflow/notification/audit operations, with humans only for source confirmation or material approval. GUI ACK/Snooze is never business approval.

## New deliverables
- Portable, **unsigned** EDUFieldUAT.exe, built on GitHub-hosted Windows with Python and Tk bundled.
- Starting EDUFieldUAT.exe with no arguments in an **interactive Windows user session** first asks explicit permission. If denied, it creates **no test database or report**.
- On acceptance, it creates exactly two fictional local notifications in a disposable SQLite DB, opens the *real* local Tk desktop center, and lets the user click ACK and Snooze.
- It asks for Japanese text readability, audible notification and window interaction, then creates a **new** JSON report in the user's temporary directory. Report never asserts production acceptance or login Startup verification.
- Packaging CI only executes the EXE in --preflight-file mode; it never clicks consent or touches the real desktop Startup folder.
- A separate MRCAO self-hosted workflow runs **read-only Session ID** diagnostics. Session 0 does NOT count as actual desktop acceptance.

## Signed-in field check (requires explicit local/IT authorization)
1. Obtain the Windows EXE from the GitHub Actions W8 artifact for the reviewed commit; verify the SHA256 from the CI log. The executable is unsigned and not approved for institutional rollout.
2. Use an approved **test Windows account in a signed-in desktop**, not a GitHub runner service. Double-click EDUFieldUAT.exe. This is explicit opt-in; click Cancel to exit without testing.
3. In the fictional notification center, select one alert and choose 確認済み. Select the other and choose 30分後に再表示. Close the window.
4. Answer the three local questions based on what the operator physically read, heard and interacted with. Locate the new EDU_W8_Synthetic_UAT_*.json report in the current user's TEMP. Only masked counts and booleans are retained, not real emails or staff data.

**Not accepted by W8 CI:** physical sound, institution workstation readability, actual login/logout Startup, private data access authorization, Outlook/SMTP/SSO, executable signing or a production pilot.

No real inbox, SMTP recipient, institutional record, Windows registry, current-user Startup entry or service is modified by this workflow.

## Engineering CI gates
- 7+ W8 launcher tests, positive/negative/boundary cases; Linux suite and Rust integration.
- Windows PyInstaller one-file UAT build, noninteractive smoke report, SHA256, seven-day artifact retention.
- W5B Windows actual Tk widget E2E and W7 Startup sandbox must remain green.
- Self-hosted runner diagnostic is strictly read-only; a run stuck in queue is *not* evidence the runner is online.

## W8 validated checkpoint
- PR #15 MERGED as f47c5d85acba0e78fa131973ef1214b8acb847ef. Four PR and four main postmerge CI workflows SUCCESS; 114/114 Python regression tests PASS.
- The one-click UAT artifact is unsigned and has limited retention. Packaging preflight did not launch GUI or simulate a human attestation.
- MRCAO probe #39373569883 queued; current Session ID and online status unknown.
- Details: docs/W8_TEST_REPORT.md. Engineering acceptance only, not institutional desktop sign-off.
