"""W28A: real, bounded Ollama inference proof on a permitted Linux runner.

No repo writes, external API calls, model downloads, commands from LLM,
or claims that more than one model has run. Fail closed on host pressure.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import secrets
import sys

from .autopilot_worker_w27 import local_ollama, no_duplicates

GIB = 1024 ** 3
MAX_MODEL_BYTES = 6 * GIB
MAX_LOAD_RATIO = 0.75


def candidate_model(tags):
    if not isinstance(tags, dict) or not isinstance(tags.get("models"), list):
        raise ValueError("No local Ollama inventory")
    models = []
    for entry in tags["models"]:
        if not isinstance(entry, dict):
            continue
        name, size = entry.get("name"), entry.get("size")
        if (isinstance(name, str) and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]{1,100}", name)
                and type(size) is int and 0 < size <= MAX_MODEL_BYTES):
            models.append((size, name))
    if not models:
        raise ValueError("No bounded installed model; download forbidden")
    return min(models)[1], min(models)[0]


def available_memory_bytes(meminfo):
    if not isinstance(meminfo, str) or len(meminfo) > 16384:
        raise ValueError("Malformed Linux memory accounting")
    found = re.search(r"^MemAvailable:\s+(\d+) kB$", meminfo, re.MULTILINE)
    if found is None:
        raise ValueError("MemAvailable unavailable")
    return int(found.group(1)) * 1024


def host_budget(model_size, available_bytes, load, cpus):
    if (type(model_size) is not int or type(available_bytes) is not int or
            type(cpus) is not int or cpus < 1 or not isinstance(load, (float, int))):
        raise ValueError("Invalid host telemetry")
    if (model_size <= 0 or model_size > MAX_MODEL_BYTES or
            available_bytes < max(6 * GIB, 2 * model_size) or
            load < 0 or load > cpus * MAX_LOAD_RATIO):
        raise ValueError("Unsafe host resource budget")
    return True


def prove(transport, meminfo, load, cpus, nonce):
    name, size = candidate_model(transport("/api/tags"))
    host_budget(size, available_memory_bytes(meminfo), load, cpus)
    if not isinstance(nonce, str) or re.fullmatch("[0-9a-f]{24}", nonce) is None:
        raise ValueError("Probe nonce must be generated locally")
    token = "W28A_" + nonce
    result = transport("/api/generate", {
        "model": name,
        "prompt": ("Fictional synthetic health-check, no personal data. "
                   "Respond with a JSON object with exactly one key named token, "
                   "whose value is exactly this literal identifier: " + token),
        "stream": False, "format": "json",
        "options": {"temperature": 0, "num_predict": 48, "num_ctx": 512,
                    "num_thread": 4},
        "keep_alive": 0,
    })
    if not isinstance(result, dict) or not isinstance(result.get("response"), str):
        raise ValueError("No generated model content")
    parsed = json.loads(result["response"], object_pairs_hook=no_duplicates)
    if not isinstance(parsed, dict) or set(parsed) != {"token"} or parsed["token"] != token:
        raise ValueError("Model token proof did not match")
    return {
        "phase": "W28A", "status": "ONE_REAL_OLLAMA_INFERENCE_VERIFIED",
        "model_name_sha256": hashlib.sha256(name.encode()).hexdigest().upper(),
        "model_calls_proven": 1, "independent_agents_proven": 0,
        "three_parallel_workers_proven": False, "output_proposal_created": False,
        "download_performed": False, "git_write_performed": False,
        "production_accepted": False,
    }


def main(argv=None, transport=local_ollama):
    parser = argparse.ArgumentParser(description="W28A single bounded local-model proof")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)
    if not args.execute:
        print(json.dumps({"phase": "W28A", "status": "DRY_RUN_NO_OLLAMA_REQUEST",
                          "model_calls_proven": 0, "production_accepted": False}))
        return 0
    if os.environ.get("EDU_AUTOPILOT_ENABLE") != "1":
        print("W28A_EXPLICIT_ENABLE_REQUIRED", file=sys.stderr)
        return 2
    try:
        with open("/proc/meminfo", encoding="ascii") as fd:
            meminfo = fd.read(16385)
        result = prove(transport, meminfo, os.getloadavg()[0],
                       os.cpu_count() or 0, secrets.token_hex(12))
        print(json.dumps(result, sort_keys=True))
        return 0
    except (ValueError, TypeError, KeyError, OSError, json.JSONDecodeError):
        print("W28A_LOCAL_PROOF_BLOCKED_OR_UNVERIFIED", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
