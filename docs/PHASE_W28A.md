# W28A — Real local-model acceptance gate (single inference first)

Mission: automate Python+Rust educational office software development while preserving IT/human authority over real systems and data.

W27B code can send three model proposals concurrently, but hosted CI covered only mocks. W28A introduces a **separate, smaller first gate**: a single nonce-bound local Ollama inference with no real data, no shell execution from model response, no downloads, no git operations, and explicit `EDU_AUTOPILOT_ENABLE=1`.

The proof code reads Ollama inventory at **127.0.0.1:11434 only**, chooses the smallest already-installed model of at most 6 GiB, checks `/proc/meminfo MemAvailable` is at least twice the model size and 6 GiB, and rejects elevated CPU load (above 75% of logical CPUs). Response must echo a random nonce in strict JSON. Inference limits: `num_predict=48`, `num_ctx=512`, `num_thread=4`, `keep_alive=0`. No GPU/VRAM admission guarantee is claimed. A successful probe certifies **one real model call**, not independent AI agents, 3-worker throughput, code generation, PR, or merge.

`.github/workflows/w28a-ollama-real-proof.yml` runs safe hosted synthetic tests on the branch; **the Linux self-hosted real inference job is skipped unless explicit repo variable `EDU_AUTOPILOT_LIVE=true` AND a main-branch workflow_dispatch/schedule are both true.** It never installs or downloads model files, and never writes to work equipment apart from normal authorized model inference.

Never call skipped/hosted mock proof a real Ollama pass. Next external step is separate opt-in, runner resource inspection and resulting 1-model proof, then three independent model proofs. Project rollout remains 2/6, production acceptance 0/8.