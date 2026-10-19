# Self-hosted Windows W4 E2E — bounded test protocol

## Scope
The W4 end-to-end workflow runs a **synthetic-only**, one-off push on `test/selfhost-w4-e2e`. It targets repository runner labels `[self-hosted, Windows]` and was verified on `MRCAO` (runner ID 2). No live Outlook, SMTP, camera/RTSP, production SQLite, system registry or Windows Task Scheduler was accessed.

## Build and runtime separation
- `build-rust-windows` runs native Rust unit tests and builds `edu_rules.exe` on GitHub-hosted Windows from **the same exact commit**.
- The executable is passed through a same-run GitHub Actions artifact, then **executed and verified by SHA256** on the actual Windows self-hosted runner.
- The runner does **not** need a preinstalled Rust compiler or Cargo. This architecture **does not claim** Rust source compilation on MRCAO.
- A standalone official Python.org 3.12.10 embeddable distribution is prepared in runner temporary storage without an MSI/registry installation or a reboot.
- The self-hosted job uses a disposable per-run SQLite database and file notifications within `RUNNER_TEMP`. No organization data is used.
- The workflow trigger is scoped to the fixed test branch; it does not run self-hosted code from arbitrary pull requests. GitHub token permissions are read-only.

## Acceptance matrix
| Gate | Expected | Verified result |
|---|---|---|
| Runner assignment | Windows self-hosted MRCAO | PASS |
| Python W1-W4 regression | 93/93 | PASS on MRCAO |
| Rust binary tested and built | Native Windows | PASS on hosted Windows |
| Rust binary executed | Native on MRCAO | PASS |
| Fictional EML intake | 3 items, two cycles | PASS; second import 0 |
| Duplicate alerts | Zero | PASS |
| Notification ACK / SNOOZE | Persistent across SQLite reopen | PASS |
| Human confirmation | Exact case + deadline token | PASS |
| Deadline reminder | Rust D-3 event | PASS |
| Unauthorized business decisions | Zero | PASS |
| GUI in real logged-in desktop | Visible and interactive Tk window | **BLOCKED**: MRCAO runner in Session 0 |
| Actual Outlook, SMTP, SSO and scheduler | IT-approved institutional environment | NOT TESTED |

## Authoritative GitHub evidence
- **Success on MRCAO**: https://github.com/caotiensinh/workflow_office_deadline/actions/runs/39275696459
- [Run log shows `SELFHOST_PYTHON_TESTS 93 PASS` and `SELFHOST_W4_CORE_E2E_PASS`](https://github.com/caotiensinh/workflow_office_deadline/actions/runs/39275696459)
- Small synthetic-only JSON evidence artifact `selfhost-w4-e2e-evidence` is attached to that run; retention is 7 days.
- PR #8 merged this test harness: https://github.com/caotiensinh/workflow_office_deadline/pull/8

## Errors actually found and addressed
1. GitHub initially did not begin steps on MRCAO; pre-checkout runner diagnostics were added.
2. PowerShell 5.1 interpreted unittest's stderr output as a native command error when piping `2>&1`; test output is now collected inside Python.
3. The runner service account did not have Cargo on PATH; Rust is compiled and tested on hosted Windows and the binary is transferred for **real execution** on MRCAO.
4. Installing Python via Windows MSI/registry exceeded the runner account permissions; the workflow uses a portable embeddable distribution in temporary storage.
5. Windows `cp932` produced an encoding failure during process startup; the runner sets `PYTHONUTF8=1` and `PYTHONIOENCODING=utf-8`.
6. Two old mock-Rust unit tests used POSIX shebang files directly; the Windows variant now uses native `.cmd` files. The corresponding 93/93 suite passed on MRCAO.

## Strictly not accepted
The service-based runner operates in **Windows Session 0**, so the Tkinter GUI was deliberately not launched as though it were visible. A separate signed-in/interactive Windows session test must verify actual appearance, notification bell, focus, controls and user acceptance. Real Outlook, corporate SMTP, institution SSO/MFA, retention and production data must be authorized and checked separately.

**Status: SELF-HOSTED CORE E2E PASS; INTERACTIVE GUI BLOCKED; PRODUCTION WORKFLOWS NOT ACCEPTED.**
