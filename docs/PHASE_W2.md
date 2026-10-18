# Phase W2 — Safe email intake → Rust deadlines → durable alerts

## Outcome
Offline-first, read-only automatic import from an approved EML folder or explicitly opted-in Outlook Classic. Python deduplicates, Rust generates deadline signals, SQLite sends to local file outbox. Human confirms deadlines and decisions; routine polling is automated.

## Workflow contracts
- EML: `run_once.ps1 -ImportEmlDir examples/w2_inbox` (synthetic).
- Opt-in Outlook Classic: `run_once.ps1 -ImportOutlookClassic` requires IT approval, interactive Outlook profile and pywin32. New Outlook is not supported by COM; Microsoft Graph delegated authorization is a separate phase.
- Rust binary is required in Windows scheduled runner; never silently fall back to Python.
- No full message, subject or sender stored; restricted alerts are masked.
- Only complete explicit timestamps are candidates: `DUE:YYYY-MM-DDTHH:MM+09:00` or `期限：YYYY年MM月DD日 HH時MM分`.
- Conflicting or incomplete markers yield no date. Every imported deadline remains `due_verified=false` until human confirmation.
- EML identity uses W1-compatible raw SHA256. Outlook uses hashed StoreID+EntryID: moves may change EntryID, so cross-folder deduplication cannot be guaranteed.
- Idempotent alert outbox; revisions obsolete queued alerts.
- Local file notification is not a real push notification. SMTP requires approved credentials/recipients and UNKNOWN recovery.

## Acceptance
- [ ] W2 Python tests PASS in Linux CI.
- [ ] Windows synthetic COM tests and EML → Rust → file notification end-to-end PASS.
- [ ] Repeated import yields no duplicate cases/alerts.
- [ ] PR merged and main CI PASS.
- [ ] Institution-approved Outlook and production alert channel tested (external blocker).

## Limits
Repository is public and contains fictional messages only. No live data, credentials, student or HR records. COM scans at most 5000 inbox items, and requires an interactive approved Windows session for real acceptance.
