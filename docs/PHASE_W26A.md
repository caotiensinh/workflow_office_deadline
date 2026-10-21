# W26A — Real Windows schtasks MINUTE 15 compatibility

## Fixed product objective
Python+Rust automate educational-office WF01–WF08, with human approval for consequential decisions. PUBLIC repository uses only fictional, non-personal CI inputs.

## Previously uncovered compatibility risk
The real `windows/install_task.ps1` registers with `schtasks.exe /Create /SC MINUTE /MO 15`, whereas the W25B read-only audit assumed an XML `TimeTrigger`. Windows may represent scheduled minute repetition with a `CalendarTrigger`; never assume a prior PowerShell-created fixture matches the actual installer.

## Implementation
- The existing read-only audit now demands **exactly one** native registered trigger, **exactly one** supported XML `TimeTrigger` or `CalendarTrigger`, and exactly `PT15M`. It still checks enabled trigger, limited rights, executable/arguments restricted to file-only workflow, and returns no identity/path information.
- A new branch-only `.github/workflows/w26a-schtasks-minute-compat.yml` invokes genuine **`schtasks.exe /Create /SC MINUTE /MO 15` on disposable GitHub-hosted Windows only**, inspects its actual configuration with the read-only W25B auditor, and removes the exact task. The synthetic script is inert, never reads real messages or sends mail.
- Proven hosted test run **#39519010716 PASS**, marker `W26A_REAL_SCHTASKS_MINUTE_15_CONFIG_COMPAT_PASS_NOT_EXECUTION`, all six boolean checks true, exact task cleanup PASS.

**No claim of actual automatic 15-minute executions**, real enterprise IT approval, SSO, publisher signature, production or pilot acceptance. Rollout remains 2/6, workflows 0/8.

Accept after hosted smoke and 4/4 standard exact PR HEAD CI, then 4/4 postmerge main CI. No self-hosted host changes.