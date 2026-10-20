# W8 — One-click Windows synthetic UAT: engineering acceptance

Date: 2026-10-20 (JST)

## Objective
Python + Rust local mail/workflow/deadline/notification/audit with human confirmation and important decisions. ACK and Snooze do not grant approval.

## Persisted code and CI proof
- PR #15 merged at f47c5d85acba0e78fa131973ef1214b8acb847ef: https://github.com/caotiensinh/workflow_office_deadline/pull/15
- PR Linux + Rust #39373594064 SUCCESS, Windows synthetic #39373594083 SUCCESS, W4 #39373594063 SUCCESS, Windows Tk/EXE/W8 #39373594044 SUCCESS.
- Postmerge Linux + Rust #39373759396 SUCCESS (114/114 Python tests), Windows synthetic #39373759417 SUCCESS, W4 #39373759454 SUCCESS, Windows Tk+EXE #39373759473 SUCCESS.
- W8-only one-click launcher tests 7/7 PASS, including refusal in service Session 0, refusal before consent, and stale report overwrite rejection.
- Windows CI compiled a portable unsigned EDUFieldUAT.exe and ran its safe non-UI preflight. No human confirmation was automatically simulated as genuine field acceptance.
- Source CI artifact https://github.com/caotiensinh/workflow_office_deadline/actions/runs/39373594044/artifacts/12242388665
- Executable SHA256: 7C468CD4E9FBFE4ED3D64AADF692D741361CB8DFDF943FF41D362DE60E086329

## MRCAO
Read-only self-hosted Windows session probe #39373569883 is still queued at latest check. No runner/session result is available; no W8 code was executed on MRCAO as part of the queued job. Do not infer current online status from past Session 0 evidence.

## Gates remaining
- Physical observed GUI, Japanese font, audible bell, keyboard/mouse and ACK/Snooze behavior in an approved logged-in user session.
- Independently approved logout/login current-user Startup acceptance.
- Outlook/Graph, SMTP, institutional SSO/MFA/RBAC, privacy/encryption/retention, code signing and production pilot.
- GitHub currently reports repository visibility public, despite private project description. Do not import real organization data pending review.

Disposition: synthetic Windows engineering CI PASS; MRCAO, field UAT and production PENDING.
