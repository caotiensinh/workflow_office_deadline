# W24A — Real clock-triggered repetition on disposable Windows

Objective: advance Python + Rust institutional office workflow toward a human/IT-approved 15-minute rollout. W23 established only *manual on-demand* Scheduler invocation. W24A tests actual **time-based automatic triggering** on **ephemeral GitHub-hosted Windows** using synthetic marker-only CMD action, without Outlook, SMTP, production case database, organization or self-hosted machines.

- `windows/w24_hosted_automatic_cadence.ps1 -PlanOnly`: no Task Scheduler inspection or modification.
- `-AutomaticHosted`: hard refuses all non-GitHub-hosted Windows workers or missing opt-in; creates a unique limited-rights test task, asserts actual XML has `PT1M` and correct command; **never invokes Start-ScheduledTask**; watches for **two naturally triggered markers** in a bounded period; always removes only its own task and temporary files; validates cleanup.
- `.github/workflows/w24a-real-automatic-hosted.yml`: branch-scoped, hosted Windows only, timeout 6 minutes. Synthetic marker has no real institutional contents. No leaked usernames/paths.
- A pass proves *1-minute automatic repetition on an ephemeral hosted VM only*; it is NOT evidence that a real 15-minute schedule fired, or that a Windows organizational desktop, IT, or human approved it. Never update rollout gate 3 or business WF signoffs from this smoke alone.

Require specialized automatic-run CI success and four standard PR-head workflow SUCCESS before merge. If hosted Windows cannot trigger naturally, record the actual blocker rather than weakening the evidence gate.