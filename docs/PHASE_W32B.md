# W32B — Controlled declarative QA proposal → real trusted test code

**Objective:** Close one actual coding-loop boundary without pretending that the unavailable Linux Ollama worker ran. The user/model may provide a *schema-1 list of allowlisted scenario names* from a synthetic QA backlog task, never executable Python, shell, paths, assertions or arbitrary files. The repository's trusted renderer creates executable Python regression tests with only fixed, audited templates.

## Implementation contract

- `python/edu_workflow/autopilot_candidate_w32b.py` accepts only the repo-owned `autopilot/w32b_qa_candidate.json`, validates W27-QA is an authorized `AUTO_PROPOSAL` task (not `BLOCKED_EXTERNAL`), and rejects duplicate schema fields, unrecognized text, linked inputs and missing/linked directories.
- Fixed output: `tests/test_autopilot_generated_w32b.py`; no other location, no trust in model output as code. `--write` requires local `EDU_AUTOPILOT_TEST_STAGE=1`; `--verify` compares byte-for-byte deterministic rendering. Existing human/tampered files are never overwritten.
- Default `--repo-root .` is read-only and performs **zero model calls / zero GitHub API writes**. Generated tests use only `unittest`, `tempfile`, `json` and the repository's existing `load_backlog` policy; no OS/network/process/employee access.
- GitHub-hosted `w32b-trusted-candidate.yml` runs offline negative+positive safety tests; stages a trusted candidate **only in ephemeral checkout**, executes its six real generated tests, proves only one added file and never pushes or creates a PR itself. Normal four project CI workflows must pass on the code PR.
- Code changes from future autonomous LLM agents must **still require independent review**, and must never directly execute arbitrary model-supplied source, commands or CI definitions.

## Acceptance

- [ ] `test_autopilot_candidate_w32b.py` safety regression suite PASS.
- [ ] Six generated **real** Python unit tests PASS on GitHub-hosted runner after allowlisted rendering.
- [ ] Main Python/Rust + three Windows CI (4/4) PASS at one exact W32B PR head.
- [ ] PR reviewed independently; no auto-merge and no institution/production approval implied.
- [ ] Linux W31A three-Ollama real calls and independent OS coding agents still **unverified**.

This demonstrates **controlled test-code generation and actual execution by a trusted renderer**. It is not proof that an AI model independently authored or repaired the source code, and does not count toward the autonomous three-agent milestone.
