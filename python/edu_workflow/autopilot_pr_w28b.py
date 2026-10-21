"""W28B: deterministic, review-required docs-only PR staging.

Only repo-owned backlog text, NO model-generated text or executable scripts.
No remote GitHub writes from this module. Action workflow may create a PR
only with a separate explicit repo variable, and never auto-merges.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

from .autopilot_plan_w27 import load_backlog

OWNED_PATH = Path("docs/autopilot-proposals/BACKLOG_STATUS.md")
MAGIC = "<!-- EDU_AUTOPILOT_W28B_SAFE_DOCS_ONLY -->"


def escape_content(value):
    if not isinstance(value, str) or len(value) > 400:
        raise ValueError("Unbounded text in backlog")
    # Keep headings/links/HTML and control characters out of generated Markdown.
    if any(c in value for c in "<>[]`\\|\r\n") or any(ord(c) < 32 for c in value):
        raise ValueError("Unsafe Markdown metadata in backlog")
    return value.replace("&", "&amp;")


def render(tasks, fingerprint):
    if not isinstance(fingerprint, str) or len(fingerprint) != 64 or any(
        c not in "0123456789abcdef" for c in fingerprint
    ):
        raise ValueError("Invalid backlog content digest")
    if not isinstance(tasks, list) or not tasks:
        raise ValueError("No safe backlog")
    rows = [MAGIC, "# Autopilot backlog status (review required)", "",
            "Generated from repository-controlled fictional tasks, NOT a model output.",
            "No workflow is production approved; no live agents are claimed.",
            "", "Backlog SHA-256: `" + fingerprint + "`", "",
            "## AUTO_PROPOSAL (not completed)", ""]
    selected = [t for t in tasks if t["kind"] == "AUTO_PROPOSAL"]
    blocked = [t for t in tasks if t["kind"] == "BLOCKED_EXTERNAL"]
    for task in selected:
        rows.append("- **" + task["id"] + "** — " + escape_content(task["title"]) +
                    " (" + task["domain"] + "); status: PROPOSAL_ONLY")
    rows += ["", "## BLOCKED_EXTERNAL (requires authorized human / IT)", ""]
    for task in blocked:
        rows.append("- **" + task["id"] + "** — " + escape_content(task["title"]) +
                    "; status: NOT_APPROVED")
    rows += ["", "## Unchanged safety gates", "",
             "- IT approval is external and not inferred from CI.",
             "- No real Outlook, SMTP, workplace Windows mutation or pilot sign-off.",
             "- No autonomous code execution or GitHub merge occurred.",
             "- Every pull request requires review and project CI.",
             ""]
    return "\n".join(rows)


def prepare(repo_root, write=False):
    root = Path(repo_root)
    if root.is_symlink() or not root.is_dir():
        raise ValueError("Unsafe repository root")
    root = root.resolve()
    source = root / "autopilot" / "w27_backlog.json"
    if source.is_symlink() or not source.is_file():
        raise ValueError("Missing repository-controlled backlog")
    tasks = load_backlog(source)
    fp = hashlib.sha256(source.read_bytes()).hexdigest()
    markdown = render(tasks, fp)
    result = {
        "phase": "W28B", "status": "DRY_RUN_DOCS_ONLY_NOT_PR_CREATED",
        "owned_path": str(OWNED_PATH), "auto_proposal_count": sum(
            t["kind"] == "AUTO_PROPOSAL" for t in tasks),
        "blocked_external_count": sum(t["kind"] == "BLOCKED_EXTERNAL" for t in tasks),
        "model_calls_executed": 0, "github_pr_created": False,
        "git_push_performed": False, "auto_merge_performed": False,
        "production_accepted": False,
    }
    if not write:
        return result
    if os.environ.get("EDU_AUTOPILOT_DOC_PR_ENABLE") != "1":
        raise ValueError("Docs-only staging requires explicit enable")
    target = root / OWNED_PATH
    directory = target.parent
    if not directory.is_dir() or directory.is_symlink():
        raise ValueError("Preexisting owned docs directory required")
    if target.is_symlink():
        raise ValueError("Symlink destination forbidden")
    if target.exists():
        if not target.is_file() or target.stat().st_size > 8192:
            raise ValueError("Unowned or oversized destination")
        if not target.read_text(encoding="utf-8").startswith(MAGIC + "\n"):
            raise ValueError("Refuse to replace human documentation")
    target.write_text(markdown, encoding="utf-8")
    result["status"] = "DOCS_STAGED_LOCALLY_FOR_REVIEW_NOT_PR_CREATED"
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description="W28B safe deterministic docs-only PR staging")
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)
    try:
        print(json.dumps(prepare(args.repo_root, write=args.write), sort_keys=True))
        return 0
    except (OSError, ValueError, TypeError, UnicodeError, KeyError):
        print("W28B_DOC_PR_PREPARATION_REJECTED", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
