# W22C — Outlook Classic least-privilege request validation

## Purpose
WF01's Outlook Classic adapter requires enterprise authorization and a signed-in Windows user. Before that, W22C validates a strictly local fictitious plan: `adapter=outlook-classic`, `mode=manual-opt-in`, `scope=unread-inbox-only`, max 1..50 items, `send_enabled=false`, `modify_read_state=false`, `it_approval_recorded=false`, `use_real_data=false`. Duplicate/extra/unknown fields or attempted IT sign-off fail closed. Static inspection does not import COM or Graph, access a mailbox, capture credentials or send notifications.

## Unchanged blockers
No actual Outlook read-only smoke has been performed. The adapter still requires explicit institutional IT approval before any real mailbox test. This plan cannot satisfy rollout gate 4 or constitute production acceptance. Use only fictional synthetic JSON in this PUBLIC repository.

Run Linux + Windows Python regression tests and all four mandatory CI workflows before merging.