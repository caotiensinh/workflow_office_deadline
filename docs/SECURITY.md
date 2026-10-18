# Data protection and security controls

The repository is PUBLIC. Only synthetic, anonymized demonstration data and generic specifications may be committed. No real employee/student records, institutional mails, tenant tokens, passwords or SMTP credentials.

1. Do not send confidential or restricted records to ChatGPT/other cloud AI by default.
2. `safe_title` for confidential cases is masked before log display; restrict access to SQLite and local notification files using Windows ACL and BitLocker.
3. Approvals use a local-account allowlist and interactive prompt in the reference implementation, **not enterprise SSO**. It must not authorize personnel changes in production.
4. External mail notifications are opt-in with an explicit recipient allowlist. SMTP sends that fail ambiguously remain UNKNOWN pending investigation.
5. Evidence references in the reference engine are *presence checks*, not verification of regulatory accuracy.
6. Incident response: stop scheduled job, preserve logs, revoke any compromised credentials, inspect notifications, fix cause, then selectively resume.
7. Tenant-wide Outlook/Graph integration and any production data require written organizational approval and privacy impact review.
