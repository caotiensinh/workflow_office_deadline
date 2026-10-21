"""W27B isolated independent local Ollama *proposal* workers.

Model text is NEVER executed as commands, applied to a repository, approved
as institutional evidence, or submitted to GitHub. No remote model API and no
automatic model download. The only network access is loopback Ollama.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import urllib.error
import urllib.request

MAX_BACKLOG = 65536
ALLOWED_ROLES = frozenset({"documentation", "ui", "python-rust", "qa-security"})
LOCAL_URL = "http://127.0.0.1:11434"
MODEL_PRIORITIES = ("qwen3-coder", "qwen2.5-coder", "qwen3", "glm", "deepseek")
OUTPUT_KEYS = frozenset({"task_id", "proposal", "validation", "risks", "requires_human_review"})


def no_duplicates(pairs):
    d = {}
    for k, v in pairs:
        if k in d:
            raise ValueError("Duplicate JSON key")
        d[k] = v
    return d


def safe_tasks(path):
    src = Path(path)
    if src.is_symlink() or not src.is_file() or not 0 < src.stat().st_size <= MAX_BACKLOG:
        raise ValueError("Unsafe backlog path")
    obj = json.loads(src.read_text(encoding="utf-8"), object_pairs_hook=no_duplicates)
    if not isinstance(obj, dict) or set(obj) != {"schema", "tasks"} or obj["schema"] != 1:
        raise ValueError("Unknown backlog schema")
    tasks = obj["tasks"]
    if not isinstance(tasks, list) or not 1 <= len(tasks) <= 100:
        raise ValueError("Invalid task count")
    ids = set()
    for t in tasks:
        if not isinstance(t, dict) or set(t) != {
            "id", "title", "description", "domain", "kind", "approval_required"
        }:
            raise ValueError("Untrusted task shape")
        ident = t["id"]
        if not isinstance(ident, str) or re.fullmatch(r"W27-[A-Z0-9]{2,8}", ident) is None:
            raise ValueError("Unsafe task identity")
        if ident in ids:
            raise ValueError("Duplicate task ID")
        ids.add(ident)
        if t["domain"] not in ALLOWED_ROLES:
            raise ValueError("Unsupported worker domain")
        if t["kind"] not in ("AUTO_PROPOSAL", "BLOCKED_EXTERNAL") or (
            type(t["approval_required"]) is not bool or
            t["approval_required"] != (t["kind"] == "BLOCKED_EXTERNAL")
        ):
            raise ValueError("Unapproved external decision")
        if not all(isinstance(t[k], str) and 8 <= len(t[k]) <= 400
                   for k in ("title", "description")):
            raise ValueError("Unbounded task text")
    return tasks


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("Model server attempted redirect outside loopback")


def local_ollama(route, payload=None):
    if route not in ("/api/tags", "/api/generate"):
        raise ValueError("Disallowed Ollama endpoint")
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        LOCAL_URL + route, data=data,
        headers={"Content-Type": "application/json"},
        method="GET" if data is None else "POST"
    )
    opener = urllib.request.build_opener(NoRedirect)
    with opener.open(request, timeout=180 if payload else 5) as res:
        if res.status != 200:
            raise ValueError("Ollama non-success response")
        raw = res.read(1024 * 1024 + 1)
    if len(raw) > 1024 * 1024:
        raise ValueError("Oversize model response")
    return json.loads(raw.decode("utf-8"), object_pairs_hook=no_duplicates)


def choose_models(tag_response):
    if not isinstance(tag_response, dict) or not isinstance(tag_response.get("models"), list):
        raise ValueError("No Ollama model inventory")
    names = []
    for model in tag_response["models"]:
        if not isinstance(model, dict):
            continue
        value = model.get("name")
        if isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]{1,100}", value):
            names.append(value)
    ranked = sorted(set(names), key=lambda name: (
        next((i for i, prefix in enumerate(MODEL_PRIORITIES)
              if name.lower().startswith(prefix)), len(MODEL_PRIORITIES)), name))
    if not ranked:
        raise ValueError("No safe installed models")
    return ranked[:3]


def proposed_task(task, model, transport):
    prompt = (
        "You are an independent sandboxed research/coding PROPOSAL worker. "
        "This is a PUBLIC fictional-data-only Python+Rust school office app. "
        "You cannot grant IT approval, inspect real mail, execute shell commands, "
        "change GitHub/main, edit endpoints or declare GUI/production acceptance. "
        "Propose specific code/documentation/test changes for later human review. "
        "Return ONLY JSON object with keys task_id, proposal, validation, risks, "
        "requires_human_review=true. Keep proposal under 4000 characters.\n"
        f"ROLE: {task['domain']}\nTASK_ID: {task['id']}\n"
        f"TITLE: {task['title']}\nDESCRIPTION: {task['description']}"
    )
    r = transport("/api/generate", {
        "model": model, "prompt": prompt, "stream": False,
        "format": "json", "options": {"temperature": 0.1, "num_predict": 650}
    })
    if not isinstance(r, dict) or not isinstance(r.get("response"), str):
        raise ValueError("Model did not provide JSON proposal")
    proposal = json.loads(r["response"], object_pairs_hook=no_duplicates)
    if not isinstance(proposal, dict) or set(proposal) != OUTPUT_KEYS:
        raise ValueError("Unexpected proposal format")
    if proposal["task_id"] != task["id"] or proposal["requires_human_review"] is not True:
        raise ValueError("AI attempted identity or approval bypass")
    if (not isinstance(proposal["proposal"], str) or
        not 20 <= len(proposal["proposal"]) <= 4000 or
        not isinstance(proposal["validation"], str) or
        not 8 <= len(proposal["validation"]) <= 1500 or
        not isinstance(proposal["risks"], list) or
        len(proposal["risks"]) > 12 or
        any(not isinstance(x, str) or len(x) > 300 for x in proposal["risks"])):
        raise ValueError("Invalid proposal data")
    return {
        "task_id": task["id"], "role": task["domain"], "model": model,
        "status": "AI_PROPOSED_PENDING_REVIEW", "human_review_required": True,
        "execution_performed": False, "git_push_performed": False,
        "production_accepted": False, "proposal": proposal["proposal"],
        "validation": proposal["validation"], "risks": proposal["risks"],
    }


def dispatch(tasks, models, transport):
    """Up to 3 separate concurrent inference calls, never a shell executor."""
    selected = [t for t in tasks if t["kind"] == "AUTO_PROPOSAL"][:3]
    if not selected:
        return []
    if not isinstance(models, list) or not models or not all(isinstance(m, str) for m in models):
        raise ValueError("Installed model list required")
    with ThreadPoolExecutor(max_workers=min(3, len(selected))) as executor:
        futures = [
            executor.submit(proposed_task, task, models[i % len(models)], transport)
            for i, task in enumerate(selected)
        ]
        return [future.result() for future in futures]


def safe_output_dir(root):
    """Only use ephemeral runner temp or OS temp; never write inside project tree."""
    base = Path(os.environ.get("RUNNER_TEMP") or tempfile.gettempdir()).resolve()
    root = Path(root)
    if root.is_symlink() or not root.is_dir() or root.resolve() == base or (
        base not in root.resolve().parents
    ):
        raise ValueError("Output must be an existing subdirectory of runner/OS temp")
    return root


def main(argv=None, transport=local_ollama):
    parser = argparse.ArgumentParser(description="W27B safe local Ollama proposal workers")
    parser.add_argument("--backlog", required=True)
    parser.add_argument("--output-dir", help="Existing folder below RUNNER_TEMP/OS temp")
    parser.add_argument("--execute", action="store_true", help="Explicit Ollama opt-in")
    args = parser.parse_args(argv)
    try:
        tasks = safe_tasks(args.backlog)
        selected = [t for t in tasks if t["kind"] == "AUTO_PROPOSAL"][:3]
        if not args.execute:
            print(json.dumps({
                "phase": "W27B", "status": "DRY_RUN_NO_MODEL_CALL",
                "queued": [t["id"] for t in selected],
                "blocked_external": len(tasks) - len([t for t in tasks if t["kind"] == "AUTO_PROPOSAL"]),
                "agents_started": 0, "production_accepted": False
            }, sort_keys=True))
            return 0
        if os.environ.get("EDU_AUTOPILOT_ENABLE") != "1" or not args.output_dir:
            raise ValueError("Explicit worker enable and ephemeral output directory required")
        folder = safe_output_dir(args.output_dir)
        models = choose_models(transport("/api/tags"))
        results = dispatch(tasks, models, transport)
        for item in results:
            filepath = folder / (item["task_id"] + ".proposal.json")
            with filepath.open("x", encoding="utf-8") as fd:
                json.dump(item, fd, ensure_ascii=True, sort_keys=True, indent=2)
        print(json.dumps({
            "phase": "W27B", "status": "MODEL_PROPOSALS_CREATED_NOT_MERGED",
            "model_calls": len(results), "agents_started": len(results),
            "proposal_files": len(results), "human_review_required": True,
            "production_accepted": False
        }, sort_keys=True))
        return 0
    except (OSError, ValueError, TypeError, KeyError, UnicodeError,
            urllib.error.URLError):
        print("W27B_LOCAL_WORKERS_FAIL_CLOSED", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
