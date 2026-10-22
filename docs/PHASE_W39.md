# W39 — Model-authored Python source candidate → isolated tests → bounded repair → reviewed PR

## Purpose

Autopilot must **author actual source code**, not merely summarize tasks or instantiate a fixed trusted test template. W39 introduces a narrowly scoped first real code-change target in the PUBLIC fictional-data office project: `python/edu_workflow/deadline_priority_w39.py`, containing one `deadline_priority(minutes_remaining: int, has_blocker: bool) -> str` function. An eligible installed **local Ollama model authors the entire function body** as a JSON source envelope. The fixed independent acceptance suite covers BLOCKED, OVERDUE, DUE_SOON, TODAY and SCHEDULED classifications at the exact boundaries. No production or employee data is supplied.

The distinction between evidence levels is mandatory:

- A **human-authored, labelled fixture** under `autopilot/w39_handwritten_test_fixture.json` drives GitHub-hosted sandbox acceptance. It is **not** AI-generated code evidence and produces `origin=SYNTHETIC_FIXTURE_NOT_AI`, `model_calls=0`.
- The **actual model path** invokes only `http://127.0.0.1:11434/api/tags` and streaming `/api/generate`, requires an installed named model <=4 GiB and CPU/RAM admission, and generates source with `origin=LIVE_OLLAMA_INFERENCE`. This path **has not executed** as of this checkpoint: the available Linux self-hosted acceptance run W31A #39546648473 was later CANCELLED without verified inference.
- A receipt claiming real source is **not sufficient** for independent approval. The publisher must check exact artifact SHA256, source AST and all independent tests in another no-network Docker container. Even then, human review and exact-head CI remain required for merge.

## Runtime boundaries and fail-closed policy

1. `autopilot_code_candidate_w39.py` enforces one exact target path and function signature, fixed task ID, true `requires_human_review`, no imports, calls, attributes, reassignment, arbitrary identifiers, decorators, loops, extra functions or hidden side effects. Unlike a fixed-template compiler, its returned source bytes are the **model-authored candidate**, not a trusted template. Unsafe envelopes or JSON duplicate keys fail.
2. The model has at most **two attempts**. It can receive only the names of failed **trusted test cases** or a generic AST/JSON policy error. Raw model text and shell exception traces are not fed back or logged. The model never receives a GitHub write token.
3. Untrusted source is not imported by host Python. It is staged in a temporary directory, then evaluated by `python:3.12-alpine` Docker with `--network=none`, `--read-only`, nonroot UID/GID 65534, no Linux capabilities, no-new-privileges, bounded PID/CPU/RAM, and only a read-only bind mount. Docker image is explicitly pre-pulled on GitHub-hosted CI; self-hosted approval requires it already installed. Staging directory is temporarily traversable by the nonroot container, then permissions restored. Test runner itself is fixed trusted source with eleven independent boundary cases. There is **no fallback** to executing AI code outside Docker.
4. After PASS only, stage `deadline_priority_w39.py` plus `receipt.json` under an empty owner-controlled `RUNNER_TEMP` subdirectory. No source is committed to the repository by the model process.
5. A separately gated GitHub-hosted publisher with isolated `contents:write` and `pull-requests:write` permissions independently re-runs Docker acceptance from the artifact. If the exact current-main-derived branch does not already exist, it writes exactly one allowed source path and opens a fixed-title **review-required PR**. **No auto-approve, no merge, no production deployment**. Repo vars required for real mode are `EDU_W39_AI_CODE_ENABLED=true`, `EDU_W39_SANDBOX_APPROVED=true`, `EDU_W39_MODEL_NAME=<installed local model>`; PR publishing additionally requires `EDU_W39_PR_PUBLISH_ENABLED=true`. With missing values, jobs SKIP.

## Evidence and current blockers

- GitHub-hosted run [#39739075173](https://github.com/caotiensinh/workflow_office_deadline/actions/runs/39739075173) PASS: 26/26 Python policy tests and actual no-network Docker execution of the hand-written **non-AI fixture**, followed by independent retest; a fixture could **not** pass the real-source publisher gate.
- GitHub-hosted run [#39739386204](https://github.com/caotiensinh/workflow_office_deadline/actions/runs/39739386204) PASS: 28/28 Python policy tests, actual Docker PASS for correct fixed fixture, actual Docker **FAIL** on a deliberately incorrect function with trusted test identifiers `test_zero_due_soon` and `test_overdue_negative_one`, and the independent publisher revalidation succeeded. **Zero actual Ollama inference calls** in hosted tests.
- [ ] Final exact-feature-head W39 hosted CI and full-repository regression acceptance pending.
- [ ] Authorized self-hosted Linux runner for this repo, actual Ollama model streaming source, resource-admitted Docker sandbox PASS, and generated artifact uploaded to trusted hosted publisher **not yet verified**.
- [ ] First **real model-authored source PR**, independent review, exact SHA standard CI, safe merge, and unattended next work cycle **not yet proven**. W39 is a bounded architectural step, not full 24/7 autonomous product engineering.
- [ ] W38 persistent task lease still resides in unmerged PR #70; this new W39 code-proposal flow is a distinct opt-in lane, **not** yet integrated with that lease backlog. Never count it as proof of repeated autonomous task selection.
