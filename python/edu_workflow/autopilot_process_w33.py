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
import tempfile
import time
import urllib.error

from .autopilot_ollama_heartbeat_w36 import Heartbeat, read_progress, stream_generate
from .autopilot_probe_w28a import available_memory_bytes
from .autopilot_worker_recovery_w37 import execute_lanes
from .autopilot_three_w29a import admit, select_three_models
from .autopilot_worker_w27 import local_ollama, proposed_task, safe_tasks

SYNTHETIC_MODELS = [("w33-test-a", 1), ("w33-test-b", 1), ("w33-test-c", 1)]
MAX_CHILD_OUTPUT = 65536
MAX_WORKER_SECONDS = 165
MAX_REAL_ABSOLUTE_SECONDS = 600
MAX_REAL_NO_TOKEN_SECONDS = 90
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


def cpu_transport(route, payload, *, progress=None):
    if route != "/api/generate" or not isinstance(payload, dict):
        raise ValueError("Only local bounded generation is permitted")
    safe = dict(payload)
    safe["options"] = {"temperature": 0.1, "num_predict": 650,
                       "num_ctx": 1024, "num_thread": 2, "num_gpu": 0}
    safe["stream"] = progress is not None
    safe["keep_alive"] = 0
    # The live worker always supplies a private heartbeat callback; synthetic
    # and legacy direct unit calls keep the old non-streaming test contract.
    return (stream_generate(safe, progress=progress) if progress is not None
            else local_ollama(route, safe))


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
    if synthetic:
        if os.environ.get("EDU_W37_SYNTHETIC_FAIL_ONCE") == "1" and synthetic:
        raise ValueError("Synthetic first-lane failure fixture")
    transport = fake_ollama
        heartbeat = None
    else:
        path = os.environ.get("EDU_W36_HEARTBEAT_PATH")
        if not path:
            raise ValueError("Live worker requires private progress receipt")
        heartbeat = Heartbeat(path)
        transport = lambda route, payload: cpu_transport(
            route, payload, progress=heartbeat.progress)
    report = proposed_task(task, model, transport)
    if heartbeat is not None:
        heartbeat.completed()
    report["worker_pid"] = os.getpid()
    stdout.write(json.dumps(report, sort_keys=True) + "\n")


def _collect(proc, payload, heartbeat_path=None):
    """Observe actual model tokens, never equate clock ticks to progress.

    Live worker: startup grace 165s; after first response fragment allow 90s
    without more tokens, with absolute cap 600s. Synthetic mode retains
    original hard limit. Child stdout is consumed privately.
    """
    started = time.monotonic()
    last_progress, seen_chunks = started, 0
    first_input = json.dumps(payload)
    while True:
        try:
            out, _ = proc.communicate(
                first_input, timeout=5 if heartbeat_path else MAX_WORKER_SECONDS)
            break
        except subprocess.TimeoutExpired:
            first_input = None
            if heartbeat_path is None:
                proc.kill()
                proc.communicate()
                raise ValueError("Synthetic worker hard deadline")
            chunks = read_progress(heartbeat_path, proc.pid)
            now = time.monotonic()
            if chunks > seen_chunks:
                seen_chunks, last_progress = chunks, now
            if (now-started > MAX_REAL_ABSOLUTE_SECONDS or
                    (seen_chunks == 0 and now-started > MAX_WORKER_SECONDS) or
                    (seen_chunks > 0 and now-last_progress > MAX_REAL_NO_TOKEN_SECONDS)):
                proc.kill()
                proc.communicate()
                raise ValueError("Real worker no-token/absolute deadline")
    if proc.returncode != 0 or len(out) > MAX_CHILD_OUTPUT:
        raise ValueError("Child worker failed or output too large")
    result = json.loads(out)
    if not isinstance(result, dict) or set(result) != WORKER_KEYS:
        raise ValueError("Untrusted worker result shape")
    if heartbeat_path and read_progress(heartbeat_path, proc.pid) < 1:
        raise ValueError("No actual Ollama token-progress proof")
    return result


def launch(tasks, models, *, synthetic=False, python=None, alternatives=()):
    """Preserve useful worker successes; replace failures with different tasks.

    All first-round OS children are started and observed independently.
    A stuck worker is killed by _collect's bounded heartbeat deadlines; only
    its failed slot may receive one distinct approved pending AUTO_PROPOSAL.
    """
    if (len(tasks) != 3 or len(models) != 3 or
            len({t["id"] for t in tasks}) != 3 or
            len(set(models)) != 3):
        raise ValueError("Three distinct authorized tasks/models required")
    processes = []
    temp = tempfile.TemporaryDirectory(prefix="edu-w36-private-hb-")
    try:
        def spawn(task, model, lane, round_num):
            if task["kind"] != "AUTO_PROPOSAL" or task["approval_required"] is not False:
                raise ValueError("Blocked external task")
            command = [python or sys.executable, "-m",
                       "edu_workflow.autopilot_process_w33", "--worker"]
            if synthetic:
                command.append("--synthetic")
            env = {k: v for k, v in os.environ.items()
                   if k in {"PATH", "PYTHONPATH", "HOME", "LANG", "LC_ALL",
                            "SYSTEMROOT", "WINDIR", "VIRTUAL_ENV"}}
            heartbeat_path = None
            if synthetic:
                env["EDU_W33_SYNTHETIC"] = "1"
                if (round_num == 0 and
                        os.environ.get("EDU_W37_SYNTHETIC_FAIL_TASK") == task["id"]):
                    env["EDU_W37_SYNTHETIC_FAIL_ONCE"] = "1"
            else:
                heartbeat_path = str(Path(temp.name) / f"worker-{lane}-{round_num}.json")
                env["EDU_W36_HEARTBEAT_PATH"] = heartbeat_path
            proc = subprocess.Popen(
                command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL, text=True, env=env)
            item = (proc, {"task": task, "model": model}, heartbeat_path)
            processes.append(item)
            return item

        def collect(item):
            proc, payload, heartbeat_path = item
            return _collect(proc, payload, heartbeat_path)

        completed, recovered = execute_lanes(
            tasks, models, list(alternatives), spawn=spawn, collect=collect)
        results = []
        for (task, model, (proc, _, _), item) in completed:
            if (item["task_id"] != task["id"] or item["model"] != model or
                item["human_review_required"] is not True or
                item["execution_performed"] is not False or
                item["git_push_performed"] is not False or
                item["production_accepted"] is not False or
                type(item["worker_pid"]) is not int or
                item["worker_pid"] != proc.pid or
                not isinstance(item["proposal"], str) or
                not 20 <= len(item["proposal"]) <= 4000):
                raise ValueError("Worker identity or review violation")
            results.append(item)
        if len({r["worker_pid"] for r in results}) != 3:
            raise ValueError("Not three distinct OS processes")
        return results
    finally:
        for proc, _, _ in processes:
            if proc.poll() is None:
                proc.kill()
            proc.wait()
        temp.cleanup()


def run(backlog, *, synthetic=False, transport=local_ollama, meminfo=None,
        load=None, cores=None):
    eligible = [t for t in safe_tasks(backlog) if t["kind"] == "AUTO_PROPOSAL"]
    tasks = eligible[:3]
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
    reports = launch(tasks, [m for m, _ in models], synthetic=synthetic,
                     alternatives=eligible[3:])
    replaced_count = sum(r["task_id"] != t["id"] for r, t in zip(reports, tasks))
    return {
        "phase": "W33", "status": (
            "THREE_SYNTHETIC_OS_PROCESSES_NOT_REAL_OLLAMA"
            if synthetic else "THREE_REAL_OS_OLLAMA_PROCESSES_VERIFIED"),
        "independent_os_processes": len({x["worker_pid"] for x in reports}),
        "failed_lanes_replaced": replaced_count,
        "unique_tasks_completed": len({x["task_id"] for x in reports}),
        "actual_ollama_calls": 0 if synthetic else 3,
        "proposal_hashes": [
            hashlib.sha256(x["proposal"].encode("utf-8")).hexdigest()
            for x in reports
        ],
        "ollama_stream_progress_verified": not synthetic,
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
