"""W27A offline, deterministic policy controller for an unattended *proposal* queue.

No shell, GitHub token, privileged endpoint, mail, writes to repository, or
artificial acceptance. Agent inference and merge are separate opt-in gates.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

MAX_SIZE = 65536
KINDS = frozenset({"AUTO_PROPOSAL", "BLOCKED_EXTERNAL"})
ALLOWED_DOMAINS = frozenset({"documentation", "ui", "python-rust", "qa-security"})
PROTECTED_PREFIXES = (
    ".github/", "windows/", "python/", "rust-core/", "security/", "secrets/",
)
REQUIRED_CI = frozenset({
    "Hybrid Workflow CI",
    "Windows Synthetic E2E",
    "W4 Windows Desktop Alert E2E",
    "W5 Windows Desktop Package & User-Session Safety",
})


def reject_duplicates(pairs):
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise ValueError("Duplicate JSON property")
        obj[key] = value
    return obj


def load_backlog(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file() or not 0 < path.stat().st_size <= MAX_SIZE:
        raise ValueError("Invalid local backlog file")
    obj = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=reject_duplicates)
    if not isinstance(obj, dict) or set(obj) != {"schema", "tasks"} or obj["schema"] != 1:
        raise ValueError("Invalid backlog schema")
    tasks = obj["tasks"]
    if not isinstance(tasks, list) or not 1 <= len(tasks) <= 100:
        raise ValueError("Backlog must contain 1..100 tasks")
    seen = set()
    for task in tasks:
        if not isinstance(task, dict) or set(task) != {
            "id", "title", "domain", "kind", "approval_required", "description"
        }:
            raise ValueError("Unexpected backlog task shape")
        ident = task["id"]
        if not isinstance(ident, str) or not re.fullmatch(r"W27-[A-Z0-9]{2,8}", ident):
            raise ValueError("Unsafe task ID")
        if ident in seen:
            raise ValueError("Duplicate task ID")
        seen.add(ident)
        if task["domain"] not in ALLOWED_DOMAINS or task["kind"] not in KINDS:
            raise ValueError("Unknown task domain or execution mode")
        if type(task["approval_required"]) is not bool or (
            task["approval_required"] != (task["kind"] == "BLOCKED_EXTERNAL")
        ):
            raise ValueError("Task approval boundary inconsistent")
        if not all(isinstance(task[k], str) and
                   8 <= len(task[k]) <= 400 for k in ("title", "description")):
            raise ValueError("Task title/description invalid")
        if any(ord(ch) < 32 for k in ("title", "description") for ch in task[k]):
            raise ValueError("Control characters in task")
    return tasks


def plan(tasks):
    """Grounded queue allocation; does not mark tasks started or done."""
    return {
        "phase": "W27A",
        "status": "PLANNED_ONLY_NOT_RUNNING_AGENTS",
        "count": len(tasks),
        "auto_proposals": [
            {"id": x["id"], "domain": x["domain"], "requires_review": True}
            for x in tasks if x["kind"] == "AUTO_PROPOSAL"
        ],
        "blocked_external": [
            {"id": x["id"], "reason": "INDEPENDENT_IT_OR_HUMAN_APPROVAL_REQUIRED"}
            for x in tasks if x["kind"] == "BLOCKED_EXTERNAL"
        ],
        "model_calls_executed": 0,
        "agents_spawned": 0,
        "main_mutated": False,
        "it_approved": False,
        "production_accepted": False,
        "workflow_signoffs": 0,
    }


def evaluate_merge(evidence):
    """Fail closed: only docs-only PR eligible for auto-merge recommendation.

    Deliberately no GitHub API or merge side-effect. The orchestrator never
    trusts an LLM to grant approval, and refuses all executable paths.
    """
    out = {
        "phase": "W27A",
        "status": "HOLD",
        "eligible_for_docs_only_merge": False,
        "is_actual_merge": False,
        "production_accepted": False,
    }
    if not isinstance(evidence, dict) or set(evidence) != {
        "head_sha", "base_branch", "changed_files", "checks", "human_gate"
    }:
        return out
    head = evidence["head_sha"]
    if not isinstance(head, str) or re.fullmatch("[0-9a-f]{40}", head) is None:
        return out
    if evidence["base_branch"] != "main" or evidence["human_gate"] is not False:
        return out
    changed = evidence["changed_files"]
    if not isinstance(changed, list) or not 1 <= len(changed) <= 30 or (
        len(changed) != len(set(x for x in changed if isinstance(x, str)))
    ):
        return out
    if any(not isinstance(p, str) or not p.startswith("docs/") or
           ".." in p.split("/") or p.endswith("/") or
           not re.fullmatch(r"[A-Za-z0-9_./-]+", p) for p in changed):
        return out
    checks = evidence["checks"]
    if not isinstance(checks, list) or len(checks) != len(REQUIRED_CI):
        return out
    names = set()
    for c in checks:
        if not isinstance(c, dict) or set(c) != {
            "name", "head_sha", "status", "conclusion"
        }:
            return out
        if not isinstance(c["name"], str) or c["name"] in names:
            return out
        names.add(c["name"])
        if (c["head_sha"] != head or c["status"] != "completed" or
            c["conclusion"] != "success"):
            return out
    if names != REQUIRED_CI:
        return out
    out["status"] = "DOCS_ONLY_ELIGIBLE_FOR_GITHUB_POLICY_REVIEW"
    out["eligible_for_docs_only_merge"] = True
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(description="W27A deterministic proposal plan, no agents started")
    parser.add_argument("--backlog", required=True)
    parser.add_argument("--merge-evidence", help="Optional local JSON containing exact-HEAD CI evidence")
    args = parser.parse_args(argv)
    try:
        result = plan(load_backlog(args.backlog))
        if args.merge_evidence:
            path = Path(args.merge_evidence)
            if path.is_symlink() or not path.is_file() or not 0 < path.stat().st_size <= MAX_SIZE:
                raise ValueError("Invalid merge evidence")
            raw = json.loads(path.read_text(encoding="utf-8"),
                             object_pairs_hook=reject_duplicates)
            result["merge_policy"] = evaluate_merge(raw)
        print(json.dumps(result, sort_keys=True))
        return 0
    except (OSError, ValueError, TypeError, UnicodeError):
        print("W27A_SAFE_QUEUE_REJECTED", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
