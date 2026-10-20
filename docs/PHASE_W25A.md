# W25A — Verify *both* offline signed-in GUI UAT handoff files

**North star:** Python + Rust school-office workflow automation, all consequential approval by authorized humans. PUBLIC repo with fictional data only.

W23 produces immutable local self-reported UAT JSON plus independent operator handoff summary. Previously the reviewer could read them separately, but did not automatically compare the handoff's original SHA-256, receipt counters, Japanese readability, audible alert and window interaction back to the original saved report.

W25A `edu_workflow.uat_pair_w25a` performs a **read-only cross-file consistency audit**; enforces exact schema, duplicate field rejection, size bounds, symlink denial, strict expected false authority flags and SHA-256 match. It rejects modified receipts, mismatched source bytes and forged approvals. A consistent *incomplete* original report is explicitly flagged as incomplete, never PASS for GUI acceptance. The UAT EXE gains a no-GUI three-argument mode `--pair-report-file FILE --pair-summary-file FILE --pair-output-file NEW_FILE`, exits 2 safely for invalid pairs and never overwrites existing evidence. Windows W5 packaged EXE smoke now runs this real binary with a fictional report and W23 summary pair, checking that inputs never change. Thirteen safety tests in `tests/test_uat_pair_w25a.py`.

**Important:** SHA-256 is an unkeyed content fingerprint. These two files can both be forged. Even a matching pair is **not** cryptographically authenticated operator identity, independent physical Session 1 GUI observation, IT authorization, genuine logon Startup, signed release or production acceptance. No mail, real schools or Windows Task Scheduler touched. Real rollout remains 2/6 and production 0/8.

Acceptance: exact PR head 4/4 CI and Windows packaged EXE pair smoke; exact postmerge 4/4 PASS.