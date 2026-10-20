# W6 — Windows interactive Tk re-alert and sound failure resilience

Date: 2026-10-20 (JST)

## Scope and objective
Python/Rust automatic deadline intake, detection, notification and audit. ACK/Snooze is **visibility only** and must never become a workflow approval. No real HR/institutional data, Outlook mailbox, SMTP destination, production Startup folder or machine-global screenshots were used.

## Code and evidence
- PR #11 MERGED: https://github.com/caotiensinh/workflow_office_deadline/pull/11
- Merge SHA: `a4c55825bff0a6e76c15c3eb059d504679774efe`
- PR Linux Python and Rust CI #39364014697: SUCCESS, **103/103 Python regressions** and Rust integration PASS.
- PR Windows legacy synthetic E2E #39364014660: SUCCESS.
- PR Windows W4 desktop model #39364014574: SUCCESS.
- PR Windows W5/W6 actual Tk + packaged EXE + Startup sandbox #39364014825: SUCCESS.
- Postmerge main Linux #39364174940, legacy Windows #39364174967, W4 Windows #39364175029, desktop package #39364174898: all SUCCESS.

## Confirmed new W6 behavior
- A missing OS audio or Tk bell/focus failure no longer turns a valid notification list into a false SQLite error.
- Real Tk widgets on GitHub-hosted Windows **Session 2**, with an isolated two-case SQLite fixture: window mapped and Japanese title, 2 initially visible notices, initial bell invoked exactly once, Snooze hides the first notice, ACK hides the second.
- The test advances only the **synthetic** snooze receipt expiration and invokes the real Refresh button: notice reappears and bell invocation count advances to exactly two, then stays unchanged on the next refresh. A failed or stale approval is never invented; **0 approvals**, 2 desktop audit events.
- No raw synthetic "private" content is rendered to Treeview/labels. This is a safe software-level display check, **not proof of font readability or physically audible sound**.

## Failure reproduced, root cause fixed
The first W6 CI showed functional GUI PASS but job FAILED with `PermissionError: [WinError 32]` during removal of the synthetic SQLite fixture. Python's `with sqlite3.connect(...)` commits but does not close the connection. Explicit `writer.close()` in a `finally` fixed the Windows handle leak. Rerun and postmerge CI completed successfully.

## Not accepted / field gates
- No UAT proof of real signed-in user's Windows desktop, local Japanese font legibility, focus under live interaction, actual audible alerts, keyboard/mouse interactions, or logout/login autorun.
- MRCAO was previously observed in **service Session 0**, which cannot certify interactive GUI. Online status was not established via runner administration API during W6.
- No approved Outlook/Graph/SMTP/SSO, enterprise policy controls, production deployment or release signing.

**Acceptance disposition:** code + hosted synthetic Windows E2E PASS; actual institutional Windows user and production acceptance **PENDING**.
