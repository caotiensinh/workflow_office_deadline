"""W33 isolated OS worker-process admission for unattended synthetic proposal loop.

The 3 child processes call only local Ollama, never run LLM-created code.
A synthetic mode proves process isolation/timeout behavior without Ollama.
Neither mode has Git or production write authority. Real is opt-in only.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import urllib.error

from .autopilot_probe_w28a import available_memory_bytes
from .autopilot_three_w29a import admit, select_three_models
from .autopilot_worker_w27 import local_ollama, proposed_task, safe_tasks

SYNTHETIC_MODELS = [("w33-test-a", 1), ("w33-test-b", 1), ("w33-test-c", 1)]
MAX_CHILD_OUTPUT = 65536
MAX_WORKER_SECONDS = 165
WORKER_KEYS = frozenset({
    "task_id", "role", "model", "status", "human_review_required",
    "execution_performed", "git_push_performed", "production_accepted",
    "proposal", "validation", "risks", "worker_pid",
})


def fake_ollama(route, payload):
    task_id = payload["prompt"].split("TASK_ID: ", 1)[1].split("\n", 1)[0]
    return {"response": json.dumps({
        "task_id": task_id,
        "proposal": "Synthetic-only independent process smoke, no real coding performed.",
        "validation": "Verify proposal metadata only",
        "risks": ["Synthetic fixture, NOT real Ollama inference"],
        "requires_human_review": True,
    })}


def cpu_transport(route, payload):
    if route != "/api/generate" or not isinstance(payload, dict):
        raise ValueError("Only local bounded generation is permitted")
    safe = dict(payload)
    safe["options"] = {"temperature": 0.1, "num_predict": 650,
                       "num_ctx": 1024, "num_thread": 2, "num_gpu": 0}
    safe["stream"] = False
    safe["keep_alive"] = 0
    return local_ollama(route, safe)


def worker(stdin, stdout, *, synthetic=False):
    """One child handles exactly one task; does not receive GitHub credentials."""
    data = json.loads(stdin.read(MAX_CHILD_OUTPUT + 1))
    if not isinstance(data, dict) or set(data) != {"task", "model"}:
        raise ValueError("Bad trusted worker envelope")
    task, model = data["task"], data["model"]
    if (not isinstance(task, dict) or task.get("kind") != "AUTO_PROPOSAL" or
        task.get("approval_required") is not False or
        not isinstance(model, str) or
        re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]{1,100}", model) is None):
        raise ValueError("Unsafe worker dispatch")
    transport = fake_ollama if synthetic else cpu_transport
    report = proposed_task(task, model, transport)
    report["worker_pid"] = os.getpid()
    stdout.write(json.dumps(report, sort_keys=True) + "\n")


def _collect(proc, payload):
    try:
        out, _ = proc.communicate(json.dumps(payload), timeout=MAX_WORKER_SECONDS)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.communicate()
        raise ValueError("Child worker timed out")
    if proc.returncode != 0 or len(out) > MAX_CHILD_OUTPUT:
        raise ValueError("Child worker failed or output too large")
    result = json.loads(out)
    if not isinstance(result, dict) or set(result) != WORKER_KEYS:
        raise ValueError("Untrusted worker result shape")
    return result


def launch(tasks, models, *, synthetic=False, python=None):
    """Spawn all three OS subprocesses BEFORE waiting for results.

    No shell, no Git token propagation, no arbitrary model-authored process.
    Child stderr and model text are never echoed to the public CI log.
    """
    if (len(tasks) != 3 or len(models) != 3 or
            len({t["id"] for t in tasks}) != 3 or
            len(set(models)) != 3):
        raise ValueError("Three distinct authorized tasks/models required")
    processes = []
    try:
        for task, model in zip(tasks, models):
            if task["kind"] != "AUTO_PROPOSAL" or task["approval_required"] is not False:
                raise ValueError("Blocked external task")
            command = [python or sys.executable, "-m",
                       "edu_workflow.autopilot_process_w33", "--worker"]
            if synthetic:
                command.append("--synthetic")
            # Minimize environment; never pass GH_TOKEN/GITHUB_TOKEN/secrets
            env = {k: v for k, v in os.environ.items()
                   if k in {"PATH", "PYTHONPATH", "HOME", "LANG", "LC_ALL",
                            "SYSTEMROOT", "WINDIR", "VIRTUAL_ENV"}}
            if synthetic:
                env["EDU_W33_SYNTHETIC"] = "1"
            proc = subprocess.Popen(
                command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL, text=True, env=env
            )
            processes.append((proc, {"task": task, "model": model}))
        with ThreadPoolExecutor(max_workers=3) as pool:
            futures = [pool.submit(_collect, proc, payload) for proc, payload in processes]
            results = [f.result() for f in futures]
        for item, task, model, (proc, _) in zip(results, tasks, models, processes):
            if (item["task_id"] != task["id"] or item["model"] != model or
                item["human_review_required"] is not True or
                item["execution_performed"] is not False or
                item["git_push_performed"] is not False or
                item["production_accepted"] is not False or
                type(item["worker_pid"]) is not int or
                item["worker_pid"] != proc.pid or
                not isinstance(item["proposal"], str) or
                not 20 <= len(item["proposal"]) <= 4000):
                raise ValueError("Child identity or review violation")
        if len({r["worker_pid"] for r in results}) != 3:
            raise ValueError("Not three distinct OS processes")
        return results
    finally:
        for proc, _ in processes:
            if proc.poll() is None:
                proc.kill()
            proc.wait()


def run(backlog, *, synthetic=False, transport=local_ollama, meminfo=None,
        load=None, cores=None):
    tasks = [t for t in safe_tasks(backlog) if t["kind"] == "AUTO_PROPOSAL"][:3]
    if len(tasks) != 3:
        raise ValueError("Exactly three safe backlog tasks required")
    if synthetic:
        models = SYNTHETIC_MODELS
        # Synthetic admission is intentionally fake; do NOT label as real.
        admit(models, 16 * 1024**3, 0, 8)
    else:
        models = select_three_models(transport("/api/tags"))
        admit(models, available_memory_bytes(meminfo),
              load, cores)
    reports = launch(tasks, [m for m, _ in models], synthetic=synthetic)
    return {
        "phase": "W33", "status": (
            "THREE_SYNTHETIC_OS_PROCESSES_NOT_REAL_OLLAMA"
            if synthetic else "THREE_REAL_OS_OLLAMA_PROCESSES_VERIFIED"),
        "independent_os_processes": len({x["worker_pid"] for x in reports}),
        "actual_ollama_calls": 0 if synthetic else 3,
        "proposal_hashes": [
            hashlib.sha256(x["proposal"].encode("utf-8")).hexdigest()
            for x in reports
        ],
        "model_authored_code_executed": False, "git_writes": False,
        "human_review_required": True, "auto_merge": False,
        "production_accepted": False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="Bounded unattended W33 worker-process lane")
    parser.add_argument("--backlog", default="autopilot/w27_backlog.json")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--synthetic", action="store_true")
    parser.add_argument("--worker", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.worker:
            if args.synthetic and os.environ.get("EDU_W33_SYNTHETIC") != "1":
                raise ValueError("Unapproved synthetic worker")
            worker(sys.stdin, sys.stdout, synthetic=args.synthetic)
            return 0
        if not args.execute:
            print(json.dumps({"phase": "W33", "status": "DRY_RUN_ZERO_WORKERS",
                              "actual_ollama_calls": 0, "production_accepted": False}))
            return 0
        if args.synthetic:
            if os.environ.get("EDU_W33_SYNTHETIC") != "1":
                raise ValueError("Synthetic smoke not authorized")
            receipt = run(args.backlog, synthetic=True)
        else:
            if (os.environ.get("EDU_AUTOPILOT_ENABLE") != "1" or
                os.environ.get("EDU_AUTOPILOT_THREE_CPU_PROPOSALS") != "1" or
                os.environ.get("EDU_W33_SYNTHETIC") == "1"):
                raise ValueError("Real model execution requires distinct live opt-ins")
            with open("/proc/meminfo", encoding="ascii") as stream:
                meminfo = stream.read(16385)
            receipt = run(args.backlog, meminfo=meminfo,
                          load=os.getloadavg()[0], cores=os.cpu_count() or 0)
        print(json.dumps(receipt, sort_keys=True))
        return 0
    except (OSError, ValueError, TypeError, KeyError, UnicodeError,
            urllib.error.URLError, subprocess.SubprocessError):
        print("W33_WORKER_LOOP_FAIL_CLOSED", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
