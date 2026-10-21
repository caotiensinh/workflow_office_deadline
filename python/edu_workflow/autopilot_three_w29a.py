"""W29A: real three-way CPU-only local Ollama proposal inference admission.

All three independent inference requests must succeed; fail closed otherwise.
No shell from LLM, repo writes, arbitrary network, model downloads, or
publication of model-generated text into public GitHub logs.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import urllib.error

from .autopilot_probe_w28a import GIB, available_memory_bytes
from .autopilot_worker_w27 import dispatch, local_ollama, safe_tasks

MAX_EACH_MODEL_BYTES = 4 * GIB
MAX_CPU_LOAD_RATIO = .50


def select_three_models(tags):
    if not isinstance(tags, dict) or not isinstance(tags.get("models"), list):
        raise ValueError("Missing Ollama inventory")
    found = {}
    for item in tags["models"]:
        if not isinstance(item, dict):
            continue
        name, size = item.get("name"), item.get("size")
        if (isinstance(name, str) and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]{1,100}", name)
                and type(size) is int and 0 < size <= MAX_EACH_MODEL_BYTES):
            found[name] = size
    if len(found) < 3:
        raise ValueError("Three distinct installed CPU-budgeted models required")
    ordered = sorted(found.items(), key=lambda entry: (entry[1], entry[0]))[:3]
    return ordered


def admit(models, mem_available, cpu_load, cores):
    if (not isinstance(models, list) or len(models) != 3 or
            len({name for name, _ in models}) != 3 or
            not all(type(sz) is int and 0 < sz <= MAX_EACH_MODEL_BYTES for _, sz in models)):
        raise ValueError("Unsafe three-model inventory")
    if (type(mem_available) is not int or type(cores) is not int or cores < 8 or
            not isinstance(cpu_load, (int, float)) or cpu_load < 0 or
            cpu_load > cores * MAX_CPU_LOAD_RATIO):
        raise ValueError("Insufficient CPU admission")
    if mem_available < max(12 * GIB, 2 * sum(sz for _, sz in models) + 4 * GIB):
        raise ValueError("Insufficient RAM for concurrent model residency")


def run(backlog, transport, meminfo, load, cpus):
    tasks = safe_tasks(backlog)
    selected = [task for task in tasks if task["kind"] == "AUTO_PROPOSAL"][:3]
    if len(selected) != 3 or len({t["id"] for t in selected}) != 3:
        raise ValueError("Exactly three distinct authorized proposal jobs required")
    models = select_three_models(transport("/api/tags"))
    admit(models, available_memory_bytes(meminfo), load, cpus)

    allowed = {name for name, _ in models}
    def cpu_only(route, payload=None):
        if route != "/api/generate" or not isinstance(payload, dict):
            raise ValueError("Only bounded local inference allowed")
        name = payload.get("model")
        if name not in allowed:
            raise ValueError("Unexpected model selection")
        safe = dict(payload)
        safe["options"] = {"temperature": 0.1, "num_predict": 650,
                           "num_ctx": 1024, "num_thread": 2, "num_gpu": 0}
        safe["keep_alive"] = 0
        safe["stream"] = False
        return transport(route, safe)

    results = dispatch(selected, [name for name, _ in models], cpu_only)
    if len(results) != 3 or {r["task_id"] for r in results} != {t["id"] for t in selected}:
        raise ValueError("Model responses missing or duplicated")
    if (len({r["model"] for r in results}) != 3 or
            any(r["human_review_required"] is not True or
                r["execution_performed"] is not False or
                r["git_push_performed"] is not False or
                r["production_accepted"] is not False for r in results)):
        raise ValueError("Unsafe proposal results")
    # Hash result identity, never log model text, path, username or prompts.
    return {
        "phase": "W29A",
        "status": "THREE_REAL_CPU_OLLAMA_PROPOSAL_CALLS_VERIFIED",
        "actual_model_calls": 3, "distinct_models_used": 3,
        "proposal_hashes": [hashlib.sha256(r["proposal"].encode("utf-8")).hexdigest()
                            for r in results],
        "independent_processes_proven": False, "parallel_inference_requests": True,
        "human_review_required": True, "code_executed": False,
        "github_write": False, "production_accepted": False
    }


def main(argv=None, transport=local_ollama):
    parser = argparse.ArgumentParser(description="W29A three CPU-only local Ollama proposal requests")
    parser.add_argument("--backlog", required=True)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)
    if not args.execute:
        print(json.dumps({"phase": "W29A", "status": "DRY_RUN_NO_AI",
                          "actual_model_calls": 0, "production_accepted": False}))
        return 0
    if (os.environ.get("EDU_AUTOPILOT_ENABLE") != "1" or
            os.environ.get("EDU_AUTOPILOT_THREE_CPU_PROPOSALS") != "1"):
        print("W29A_THREE_MODEL_EXPLICIT_OPTIN_REQUIRED", file=sys.stderr)
        return 2
    try:
        with open("/proc/meminfo", encoding="ascii") as fd:
            meminfo = fd.read(16385)
        result = run(args.backlog, transport, meminfo,
                     os.getloadavg()[0], os.cpu_count() or 0)
        print(json.dumps(result, sort_keys=True))
        return 0
    except (OSError, ValueError, TypeError, KeyError, urllib.error.URLError):
        print("W29A_THREE_MODEL_RUN_BLOCKED_OR_UNVERIFIED", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
