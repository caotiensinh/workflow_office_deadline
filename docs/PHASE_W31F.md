# W31F — Exact-head acceptance checkpoint

Verified on 2026-10-21 JST against main `0d202a69ea4814abe435c66c2c60d0a03d4f9f9e`.

- PR #62 head `5cba2bebacc6130307f2e043c27dd63675e74d99` remains open. Workflow run 39546648473: hosted-contract SUCCESS, linux-real-ollama-acceptance QUEUED. No real three-worker inference proof.
- PR #66 head `b8e154bde4c786bec52c38c819208963409d697a` remains open. Four workflow_dispatch runs 39548578633, 39548580887, 39548582931, 39548585338 completed SUCCESS on that exact SHA. No human review; no merge.
- All four workflow run records expose stable workflow IDs 388590017, 388610038, 389392239, 389574496 and paths ci.yml, windows-e2e.yml, w4-desktop.yml, w5-desktop.yml respectively. This is evidence for a future provenance hardening gate; a workflow name alone is insufficient identity proof.

Institution IT approval, actual local model inference, independent coding agents and human review remain pending. No Outlook or endpoint access attempted.
