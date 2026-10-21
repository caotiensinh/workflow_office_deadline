"""W31B fail-closed read-only audit of bot PRs. Never auto-merge."""

from __future__ import annotations
import argparse
import json
import os
import re
import subprocess
import sys

REPO = "caotiensinh/workflow_office_deadline"
REQUIRED = frozenset({
    "Hybrid Workflow CI", "Windows Synthetic E2E",
    "W4 Windows Desktop Alert E2E",
    "W5 Windows Desktop Package & User-Session Safety",
})
SHA = re.compile(r"[0-9a-f]{40}\Z")
DOC = re.compile(r"docs/autopilot-proposals/[A-Za-z0-9_-]+\.md\Z")


def gate(pr, files, runs):
    """Assess only exact-SHA checks and GitHub's constrained bot PR metadata."""
    result = {"number": pr.get("number") if isinstance(pr, dict) else None,
              "status": "HOLD_INVALID_PR_OR_SCOPE", "exact_sha_ci": False,
              "human_review_required": True, "auto_merge": False}
    if not isinstance(pr, dict) or not isinstance(files, list) or not isinstance(runs, list):
        return result
    head, base = pr.get("head"), pr.get("base")
    if not isinstance(head, dict) or not isinstance(base, dict):
        return result
    head_sha = head.get("sha")
    if (not isinstance(head_sha, str) or not SHA.fullmatch(head_sha)
        or pr.get("state") != "open" or pr.get("draft") is not False
        or (pr.get("user") or {}).get("login") != "github-actions[bot]"
        or not str(head.get("ref", "")).startswith("autopilot/")
        or base.get("ref") != "main"
        or (head.get("repo") or {}).get("full_name") != REPO
        or (base.get("repo") or {}).get("full_name") != REPO):
        return result
    if not 1 <= len(files) <= 2:
        return result
    names = []
    for file in files:
        if not isinstance(file, dict):
            return result
        name, patch = file.get("filename"), file.get("patch")
        if (not isinstance(name, str) or not DOC.fullmatch(name)
            or file.get("status") != "added"
            or not isinstance(patch, str) or not patch.startswith("@@")
            or len(patch.encode("utf-8")) > 8192
            or type(file.get("additions")) is not int or file["additions"] > 150
            or file["additions"] < 1 or file.get("deletions") != 0):
            return result
        names.append(name)
    if len(names) != len(set(names)):
        return result
    result["status"] = "HOLD_EXACT_SHA_CI_NOT_PROVEN"
    passes = set()
    for item in runs:
        if not isinstance(item, dict) or item.get("head_sha") != head_sha:
            continue
        if (item.get("name") in REQUIRED and item.get("status") == "completed"
            and item.get("conclusion") == "success"
            and item.get("event") in ("push", "pull_request", "workflow_dispatch")):
            passes.add(item["name"])
    if passes == REQUIRED:
        result["status"] = "CI_VERIFIED_STILL_REQUIRES_HUMAN_REVIEW"
        result["exact_sha_ci"] = True
    return result


def github_json(path):
    """Read-only gh api GET; never checkout or run bot PR content."""
    proc = subprocess.run(["gh", "api", "--method", "GET", path],
                          capture_output=True, text=True, check=True, timeout=30)
    return json.loads(proc.stdout)


def audit(repo=REPO, fetch=github_json):
    if repo != REPO or not os.getenv("GH_TOKEN"):
        raise ValueError("Repository or credential scope missing")
    prs = fetch(f"repos/{repo}/pulls?state=open&per_page=100")
    if not isinstance(prs, list):
        raise ValueError("Invalid pull request collection")
    results = []
    for pr in prs:
        if not isinstance(pr, dict):
            raise ValueError("Malformed PR data")
        if (pr.get("user") or {}).get("login") != "github-actions[bot]":
            continue
        if not (pr.get("head") or {}).get("ref", "").startswith("autopilot/"):
            continue
        number = pr.get("number")
        if type(number) is not int or not 1 <= number <= 999999:
            raise ValueError("Unsafe pull request number")
        sha = (pr.get("head") or {}).get("sha")
        if not isinstance(sha, str) or not SHA.fullmatch(sha):
            raise ValueError("Invalid pull request SHA")
        files = fetch(f"repos/{repo}/pulls/{number}/files?per_page=100")
        data = fetch(f"repos/{repo}/actions/runs?head_sha={sha}&per_page=100")
        if not isinstance(data, dict) or not isinstance(data.get("workflow_runs"), list):
            raise ValueError("Invalid workflow run response")
        results.append(gate(pr, files, data["workflow_runs"]))
    return {"phase": "W31B", "status": "READ_ONLY_REVIEW_GATES_AUDITED",
            "prs": results, "total": len(results), "remote_writes": False,
            "production_approved": False}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Read-only gate for bot PRs")
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args(argv)
    if not args.live:
        print(json.dumps({"phase": "W31B", "status": "DRY_RUN_NO_GITHUB_CALLS"}))
        return 0
    try:
        print(json.dumps(audit(), sort_keys=True))
        return 0
    except (OSError, ValueError, TypeError, KeyError, subprocess.SubprocessError):
        print("W31B_READ_ONLY_AUDIT_FAILED_CLOSED", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
