# W10 — WF-04 versioned local reference evidence and approval safety

## Fixed purpose
The office workflow automatically flags missing/stale references and prepares an auditable provenance record. It **never** interprets school regulations, verifies their legal authenticity, or autonomously approves HR/administrative decisions.

## Changes
- Strict bounded JSON manifest with `schema_version=1` and at most 128 distinct `reference_id@version` records; duplicate fields or IDs are invalid.
- Each record includes an opaque `authority_code`, `citation_id`, source document basename and SHA-256, a human-declared review boolean, declared effective-from/until dates, and `superseded_by`.
- Reject symlink sources, absolute/traversal names, oversized files, changed content, superseded/unknown/out-of-window versions, non-reviewed references and malformed/duplicate registry records.
- `check-regulations` CLI checks a reference **without creating a workflow database**, connecting to Microsoft services or disclosing raw document content. Nonpassing source checks exit code 3.
- A REGULATION case cannot pass human `APPROVED` in the SQLite store without a matching source registry. Check executes inside revision-checked `BEGIN IMMEDIATE`; the approval's audit event stores the opaque citation/version and both SHA-256 digests atomically with the decision.
- `review-queue` flags `VERIFY_REGULATION_SOURCE` when reference metadata is not verified. This is a reminder to an authorized human, **not evidence of a valid law**.
- A REGULATION `REJECTED` decision remains available without a registry, so reviewers can reject an unsupported case rather than become blocked.

## Synthetic example
All bundled artifacts in `examples/wf04_*` are completely fictional; do **not** use them for real institutional decisions. From the repository root:

```powershell
$env:PYTHONPATH = Join-Path $PWD 'python'
python -m edu_workflow.cli check-regulations --registry-file examples/wf04_regulation_registry.json --reference SYN-REG-001@V1 --as-of 2026-10-20
```

Expected `SOURCE_SNAPSHOT_PASS`, `official_authenticity_verified=false`, `legal_applicability_verified=false`, `human_decision_required=true`.

Checking `SYN-REG-001@V0` gives `SUPERSEDED_REFERENCE` and exits 3. Missing or unconfigured registry always blocks REGULATION approval.

To approve a REGULATION case, an authorized user must first have an explicitly prepared case whose `evidence_ref` equals its source `reference_id@version`, and then manually use `decide --registry-file ...` with the existing exact typed confirmation. No CLI command automatically promotes cases into approval-ready status.

## Security/acceptance limits
- File hashes can detect a changed document **relative to the registry**. They do not authenticate who created/edited either file, validate law, prove a source is official, or establish human identity.
- The current manifest is not cryptographically signed or secured by institution-managed permissions. The `human_reviewed` flag is only *declared metadata*.
- Before handling real sources, obtain institutional authorization for official document acquisition, version authority, data retention, signatures/ACLs, revocation, managed SSO/RBAC and audit review.
- Do not ingest personal data while GitHub reports this repository PUBLIC.
- W10 is offline engineering acceptance, not Outlook/Graph, live law interpretation or school deployment.

## CI acceptance
- Tests: `PYTHONPATH=python python -m unittest discover -s tests -p test_regulation_w10.py -v`.
- Full Python/Rust and native Windows workflows must PASS on the exact PR and postmerge commits.
- Review code/test/merge evidence in GitHub Actions; never claim MRCAO physical desktop UAT from GitHub-hosted CI.
