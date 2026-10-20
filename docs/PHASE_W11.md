# W11 — WF-05 Anonymous HR Evidence and Reviewer Draft

## Objective and boundaries
The institution's office workflow should organize **already approved/fictional and de-identified** HR observations, flag missing source material and prepare a **draft evidence inventory** for an authorized manager.

**The program never appraises, scores, ranks, recommends, or decides anything about a person.** A report marked `READY_FOR_HUMAN_REVIEW` is *not* evidence of the authenticity or correctness of HR claims, nor approval for any employment or personnel action.

## Implemented
- New offline `hr-draft` CLI reads a strict 128 KB max local UTF-8 packet with only enumerated fact codes, opaque IDs, dates and SHA-256-linked source references. 1–100 observations and at most 64 sources.
- Anonymous case reference must be exactly `ANON-` followed by 16 uppercase hex characters. Claim and evidence IDs are opaque. The input schema rejects names, titles, email addresses, free-text notes, ratings and unexpected fields.
- SHA-256 integrity checks against local bounded (1 MB) evidence documents, checks the supplied `reviewed` flag, excludes future observations, identifies missing/unlisted/changed/symlinked sources and unsupported required categories.
- Output is structured, Japanese template-based reviewer draft sections with claim/source IDs plus specific missing-evidence reasons. It does not reproduce source document contents or personal free text.
- `READY_FOR_HUMAN_REVIEW` means the declared packet is *structurally consistent*, not verified truth. `EVIDENCE_GAPS` means the user must investigate.
- `hr-draft` is read-only and does not open/create SQLite, send email, access institutional systems, or change HR cases.
- Approving an existing `HR` case through the **existing manual** `decide` flow additionally requires a matching `--hr-packet-file`. Its case ID must match the anonymized packet and `evidence_ref` must be `HR-PACKET:<SHA256 of packet bytes>`. No gaps are allowed; the proof digest and counts are stored in the same transaction as the human's approval and audit. A missing/stale/tampered packet blocks the action. REJECT remains possible without a packet.
- The masked `review-queue` adds `VERIFY_HR_EVIDENCE_PACKET` when HR evidence is not ready. This is only a reviewer task, not a judgment.

## Reproduce on fictional data

From project root:

```powershell
$env:PYTHONPATH = Join-Path $PWD 'python'
python -m edu_workflow.cli hr-draft --packet-file examples/wf05_hr_packet.json --as-of 2026-10-20
```

Expected output: `READY_FOR_HUMAN_REVIEW`, two templated Japanese draft sections, source-linked claim IDs and `human_review_required=true`; all HR assessment/decision/external-action flags are false.

An authorized local approver may separately import a synthetic HR case whose `case_id` is equal to the packet's `case_ref` and whose `evidence_ref` is `HR-PACKET:` followed by the SHA-256 digest of the entire JSON packet. Only then, after validating the underlying facts, may they use the CLI's revision-checked `decide --hr-packet-file ...` with explicit typed confirmation. The tool **never automatically approves** and cannot validate personnel data against a real HR system.

## Institutional blockers
- Packet and evidence integrity checks do not authenticate the issuer or prove factual accuracy; a maliciously altered packet and matching document can pass unless records are protected by institution-managed signatures/permissions.
- Pseudonymous IDs and strict enum schemas reduce exposure; they **do not guarantee de-identification** or k-anonymity. Do not insert real employee/student/personnel records.
- The repository is currently reported PUBLIC by GitHub; real confidential organizational data must not be committed, uploaded, logged or used in CI until permission/privacy and source controls are formally approved.
- Full SSO/MFA/RBAC, encrypted storage, legal retention, workplace privacy review, real user UAT and final HR decisions all remain institution-gated.
- No local AI-generated HR appraisal, opinions, job suitability, compensation or ranking is implemented.

## Tests and CI acceptance
- `PYTHONPATH=python python -m unittest discover -s tests -p test_hr_evidence_w11.py -v`: strict field/PII rejection, duplicate keys/IDs, source mismatch and symlinks, missing evidence, future data, stable templating, human approval fail-closed, stale revisions and rollback, CLI no SQLite writes.
- The Linux regression suite minimum becomes **165** with native Rust integration.
- Windows GitHub-hosted CI runs native Python tests and calls the real `hr-draft` CLI against the fictional sample; no institutional desktop/machine acceptance is implied.

## W11 verified checkpoint — 2026-10-20
- PR #21 merged at `cccdd9f13d8cd8ee2902060b97d99fce2b90798f`.
- The exact final PR head `73d4ffa07ef56fbe007866a2be674f246ed1143a` passed four workflows: Linux Python **165/165** + native Rust #39384141262, Windows HR command-line E2E #39384141293, W4 #39384142204, W5 GUI/EXE #39384141221.
- Postmerge four workflows on the exact merge SHA passed: #39384328877, #39384328977, #39384328924, #39384328968.
- During CI an encoding defect was detected on Windows: printing raw Japanese JSON under cp1252 raised UnicodeEncodeError. `hr-draft` now emits ASCII-safe JSON Unicode escapes; regression explicitly uses `PYTHONIOENCODING=cp1252` and checks the decoded Japanese template.
- This is **synthetic CI engineering acceptance**, NOT signed-in user UAT, not real personnel processing, not appraisal accuracy, not institution production approval.
