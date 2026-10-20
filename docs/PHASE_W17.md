# W17 — Signed-in Windows GUI UAT handoff and evidence review

## Goal and security boundary
The core Python + Rust workflow is already proven on the MRCAO Windows self-hosted runner, but MRCAO's GitHub Actions service is in **Session 0**, while its active console is **Session 1** (W16 run #39426407245). A service must not launch, click or impersonate an interactive UI. Human approval remains mandatory for business and institution decisions.

W8 already built a one-click fictional UAT executable; W17 **does not rewrite that interface**. It packages that existing tested binary for an **IT-permitted, logged-in operator** and adds a strict read-only validator for the report.

## Deliverable
The Windows W5/W8 packaging GitHub Actions job produces an additional artifact:
`W17-Windows-SignedIn-Unsigned-Synthetic-GUI-UAT-Kit` containing:
- `EDUFieldUAT.exe`: existing consent-first Windows Tk GUI test (unsigned).
- `00_START_UAT.cmd`: Windows CMD launcher, static SHA-256 of the matching EXE embedded at CI build time. Rejects a mismatched EXE. `--verify-only` verifies the hash but does not start GUI.
- `W17_README_JP.txt`: operator instructions in Japanese.

Hash checking catches changed executables relative to the bundled launcher, **not proof of the publisher**. An attacker could alter both. No Authenticode signature, software installation, security-policy bypass, service registration or SSO is provided. A separate IT release-security review and signed deployment remain mandatory.

## Operator acceptance sequence (only after IT approval)
1. IT reviews the GitHub workflow source, commit, artifact and integrity check. User downloads/extracts the ZIP into an approved test folder on a Windows machine signed into an **interactive test account**.
2. The operator double-clicks `00_START_UAT.cmd`. It verifies the local EXE against the SHA baked into the launcher, then starts the consent-first one-click UAT EXE. **Never launch from the Session 0 runner service.**
3. The EXE asks consent. Cancel produces no fictional database. Consent creates two **fictional** local notifications. Click one `確認済み` (ACK) and the other `30分後に再表示` (Snooze), close the window, and answer the Japanese visibility / audible bell / interactive window questions based on real observations.
4. The app creates an immutable-new `EDU_W8_Synthetic_UAT_*.json` under the signed-in **user's** temporary folder. It contains only receipt counts, audit counts and the user's yes/no answers. It never copies actual school email/HR cases into the fixture and never changes Task Scheduler or Startup.
5. IT can inspect the original report **locally**, without uploading it to the public GitHub repository:
   `PYTHONPATH=python python -m edu_workflow.uat_review --report <approved-test-JSON>`
   The validator rejects duplicate keys, private extra fields, impossible receipts/audits, forged login autorun/production claims, and status contradictions. Even a consistent report produces `CONSISTENT_SELF_ATTESTATION_NOT_INDEPENDENTLY_VERIFIED`, NOT an independently confirmed GUI/IT or production PASS.

## What CI can prove
- W17 synthetic report-review test suite rejects inconsistent/forged evidence, and can parse the actual shape that W8 generates.
- The Windows GitHub-hosted packaging lane builds the same W8 PyInstaller EXE, performs the existing `--preflight-file` **without opening GUI**, creates the ZIP, verifies SHA via the CMD `--verify-only` path and deliberately tampers a disposable copy to prove mismatch rejection.
- GitHub-hosted tests and bundle validation do NOT establish actual signed-in-user consent, Japanese readability, sound output, Windows login Startup behavior or an IT-approved workstation pilot.

## Original rollout gates unchanged
1. Synthetic Python CI — PASS.
2. Native Rust integration CI — PASS.
3. Approved Task Scheduler 15-minute execution on a real endpoint — PENDING.
4. Authorized Outlook real mailbox read-only test — PENDING.
5. Authorized recipient alert test — PENDING.
6. Three signed-off operator pilots — PENDING.

Production sign-offs remain **0/8 workflows** until organizational approval, regardless of the W17 artifact results. Repository is reported **PUBLIC**, so use fictional data only.


## Verified W17 engineering acceptance — 2026-10-20

- **PR #33** MERGED: `8c2e504e61eb02707b9e7d1353539e180633711e`, final PR head `fc541797c139f5b823f3763580635a76e4163908`.
- Four exact-head PR CI SUCCESS: Linux **255/255 Python** + native Rust [#39432415536](https://github.com/caotiensinh/workflow_office_deadline/actions/runs/39432415536); Windows E2E #39432415566; W4 #39432415515; W5 UAT packaging #39432415668.
- Four exact postmerge main CI SUCCESS: [Linux/Rust #39432792196](https://github.com/caotiensinh/workflow_office_deadline/actions/runs/39432792196), Windows E2E #39432792279, W4 #39432792355, W5 #39432792696.
- **Operator ZIP artifact**: [W17 GitHub run #39432792696 artifact #12269820035](https://github.com/caotiensinh/workflow_office_deadline/actions/runs/39432792696/artifacts/12269820035). `W17_SignedIn_GUI_UAT_Kit.zip` SHA-256 `A67836396A1C66EAC93C1E583AEF65E5708068F126A2D85B9BF0900323A24EC7`. GitHub artifact retention seven days.
- Hosted Windows build checked the **EXE's** SHA against the value injected into `00_START_UAT.cmd`, then modified a disposable EXE and confirmed refusal. It did NOT open an interactive GUI. The UAT executable is unsigned and has no enterprise release authorization.
- W17 review tool rejects inconsistent ACK/Snooze/audit, unexpected fields, fake production/login approvals; a logically consistent report explicitly remains `CONSISTENT_SELF_ATTESTATION_NOT_INDEPENDENTLY_VERIFIED`.
- An initial corrupted GitHub workflow YAML and a leftover native exit code from a purposely negative tamper test were repaired; only final green CI is counted.

**Field/production acceptance remains PENDING:** approved interactive Windows Session 1 operator must personally observe Japanese labels, sound, ACK/Snooze; real login Startup, approved 15-minute Task Scheduler, Outlook/Graph, authorized test recipient, institutional privacy/identity and 3 pilots require separate approval. **Rollout gates 2/6 CI-only; production sign-offs 0/8.**
