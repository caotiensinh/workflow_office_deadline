# W21A — Offline local GUI UAT evidence packet review

## Objective
Retain the original Python + Rust institution workflow goal (WF01–WF08), with all consequential approvals human-gated. This lane does **not** enable real Outlook, Task Scheduler or institution data.

## Gap
Previously operators had to reconcile the unsigned Windows ZIP (W18) and their fictional GUI self-attestation JSON (W17/W20A) as **separate** evidence types. A verified ZIP hash never proves a person ran its EXE, and a syntactically consistent self-report never proves the report originated from that specific ZIP.

## Independent lane A
- `python/edu_workflow/uat_packet_w21a.py` reads a *local* final ZIP through the W18 strict integrity verifier and a *local* self-attested report through W17; optional expected SHA-256 of complete ZIP.
- Returns a redacted, evidence-only combined summary of two independent facts, with explicit negatives for GUI independently observed, report cryptographically bound to binary, publisher signature, IT authorization, scheduler, login autorun, Outlook, SMTP and production.
- Refuses mismatched hashes, extra archive member, forged approvals, missing report and duplicate/invalid fields. No EXE execution, extraction, host inspection or source mutations.
- 10 additional fictional-only safety tests in `tests/test_uat_packet_w21a.py`.

## Evidence acceptance
Linux Python/Rust CI, hosted Windows synthetic E2E and signed-in UAT packaging with W18 tamper negatives must all remain green, first at exact PR HEAD, then at exact merged main SHA.

## Remaining physical sign-offs
Neither checker nor CI performs Session 1 GUI review. IT-approved operator must confirm Japanese text, audio, ACK/Snooze and actual startup; IT must approve 15-minute scheduled execution, Outlook read-only, approved recipient and pilots. Original rollout still 2/6 CI gates and 0/8 production workflow sign-offs.