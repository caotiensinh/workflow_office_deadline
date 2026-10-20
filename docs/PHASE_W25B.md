# W25B — IT-authorized read-only audit of configured 15-minute task

**North star:** Python+Rust automate WF01–WF08; no actual employer endpoint/task/mailbox access without independent IT approval. PUBLIC repo: synthetic tests only.

The operator tool `windows/w25_live_task_readonly_audit.ps1` supports `-PlanOnly` (does not touch Task Scheduler at all) and `-AuditLive -ITAuthorized` (explicit permission gate). The read-only audit queries **only** the fixed task name `EducationAIWorkflow`, inspects its real registered Windows Task Scheduler action, native trigger, XML repetition `PT15M`, limited runlevel, enabled status and file-only command. Prints safe boolean checks; no account/command line/raw task XML/recipient/mail contents. The audit neither creates, starts, modifies nor deletes the target task and never reads Outlook or messages. Configuration status cannot prove that 15-minute runs occurred; returns FALSE for execution evidence, IT or production approval.

Branch-only `.github/workflows/w25b-hosted-task-readonly-audit.yml` is **GitHub-hosted Windows only** and creates a future-scheduled isolated synthetic task named `EducationAIWorkflow` solely within an ephemeral CI VM. It invokes the read-only tool against actual registered configuration and deletes the disposable test task and files in finally; refuses a preexisting task. Missing `-ITAuthorized` must fail closed. It intentionally does **not** start the task.

The live tool should only be used locally on a machine where organizational IT has separately authorized read-only task inspection. Passing the switch is an explicit operator assertion, not independent evidence of IT authorization. Even a matching task does not establish login/startup, **three observed automatic 15-minute runs**, real Outlook read-only or any pilot signoff; rollout remains 2/6 and production 0/8.

Acceptance: real hosted branch workflow SUCCESS plus 4/4 regular CI on exact PR head, no confidential data; postmerge 4/4.