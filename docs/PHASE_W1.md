# Phase W1 — Windows native workflow reliability

## Scope
- Prevent stale case revisions from creating or delivering alerts.
- Make human approval case update + decision record + audit one SQLite transaction.
- Recover durable file-spool sends after process crashes without duplicate notifications.
- Quarantine ambiguous SMTP sends as `UNKNOWN`; do not retry automatically.
- Run synthetic native Windows E2E in GitHub Actions using compiled Rust + PowerShell.

## Decision matrix
| State | Automated action | Human involvement |
|---|---|---|
| `QUEUED`, current revision, active | File-spool/send if explicitly configured | No |
| `QUEUED`, obsolete revision or completed case | Mark `STALE` | No |
| `SENDING`, file exists and content matches | Mark `SENT` without re-sending | No |
| `SENDING`, missing/corrupted file | Mark `UNKNOWN` | Operator investigates |
| `SENDING`, SMTP outcome unknown | Mark `UNKNOWN` | Operator checks recipient before replay |
| `READY_FOR_APPROVAL`, evidence present | Prompt authorized approver | Yes |
| No evidence / unverified due | Block approval and flag | Yes |

## Acceptance and limitations
- 46+ Python regression tests locally must pass.
- CI on `ubuntu-latest` and `windows-latest` must pass before marking this phase complete.
- Real Outlook Classic COM, New Outlook Graph, SMTP credentials, and institutional Windows scheduled-task registration are **not** tested by this CI; explicit authorization is required.
- No claim of exactly-once delivery across SQLite and remote SMTP. `UNKNOWN` is quarantined.
- Public repository must contain only synthetic data; no tokens, institutional emails or private records.
