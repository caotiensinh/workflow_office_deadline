# Engineering acceptance checklist (2026-10-19)

## Verified locally
- [x] 40 Python tests pass on synthetic data.
- [x] JSON intake and idempotent local alert outbox.
- [x] Deadline checks, evidence check and interactive human approval.
- [x] Synthetic Outlook `.eml` and DOCX checker tests.
- [x] Editable specifications and project requirements written.

## Pending external verification
- [x] Rust native unit tests, release build and Python↔Rust CLI integration on hosted Ubuntu CI (run #39145381931).
- [ ] Rust and Python behavior parity verified on approved Windows host.
- [ ] Windows/PowerShell scheduled task tested on permitted endpoint.
- [ ] Real Outlook Classic COM read-only integration approved and tested.
- [ ] New Outlook OAuth delegated consent and Graph connector, if necessary.
- [ ] SMTP alert delivery accepted to approved recipient; UNKNOWN recovery checked.
- [ ] Production identity, local encryption, retention and institutional privacy authorization.
- [ ] Full semantic review of regulations, HR evidence and scheduling proposal.
- [ ] Three end-user workflow pilots with operator signoff.

**Do not equate reference rule testing with production automation acceptance.**
