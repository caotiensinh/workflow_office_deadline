"""W34 GitHub Actions capacity watchdog: distinguish unassigned queue from a hang.

No secrets, no worker shell, no automatic runner reboot. A queued job without
an assigned runner cannot be 'killed' to free compute. Cancellation is
restricted to *superseded* queued runs with verified newer SUCCESS and
rechecked exact branch HEAD; running tasks are never cancelled.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
import re
import subprocess
import sys
from urllib.parse import quote

REPO = "caotiensinh/workflow_office_deadline"
SHA = re.compile(r"[0-9a-f]{40}\Z")
REF = re.compile(r"[A-Za-z0-9][A-Za-z0-9._/-]{0,150}\Z")
MIN_STALE_SECONDS = 1800
MAX_REPORT_BYTES = 2 * 1024 * 1024


def gh_json(path, method="GET"):
    """GitHub CLI GET/POST, never shell or unbounded output."""
    if (not isinstance(path, str) or not path.startswith("repos/" + REPO + "/")
            or method not in ("GET", "POST")):
        raise ValueError("Unsafe GitHub path")
    p = subprocess.run(["gh", "api", "--method", method, path], text=True,
                       capture_output=True, timeout=30, check=True)
    if len(p.stdout) > MAX_REPORT_BYTES:
        raise ValueError("GitHub API output exceeds budget")
    return json.loads(p.stdout) if p.stdout.strip() else {}


def parse_time(value):
    if not isinstance(value, str):
        raise ValueError("Missing timestamp")
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def jobs_of(payload):
    if not isinstance(payload, dict) or not isinstance(payload.get("jobs"), list):
        raise ValueError("Missing GitHub jobs")
    jobs = payload["jobs"]
    if not jobs or len(jobs) > 100 or any(not isinstance(j, dict) for j in jobs):
        raise ValueError("Malformed jobs")
    return jobs


def inspect(run, jobs):
    """Return evidence-based diagnosis; never infer that a runner is offline."""
    if not isinstance(run, dict) or not isinstance(jobs, list) or not jobs:
        raise ValueError("Invalid run snapshot")
    statuses = {j.get("status") for j in jobs if isinstance(j, dict)}
    if len(statuses) == 0 or not statuses.issubset(
            {"queued", "pending", "in_progress", "completed", "waiting"}):
        raise ValueError("Unknown GitHub job state")
    def is_assigned(job):
        runner_id, runner_name = job.get("runner_id"), job.get("runner_name")
        return ((type(runner_id) is int and runner_id > 0)
                or (isinstance(runner_name, str) and bool(runner_name.strip())))

    assigned = [j for j in jobs if is_assigned(j)]
    active = [j for j in jobs if j.get("status") == "in_progress"]
    queued = [j for j in jobs if j.get("status") in ("queued", "pending", "waiting")]
    queued_assigned = [j for j in queued if is_assigned(j)]
    if active:
        state = "RUNNING_DO_NOT_CANCEL"
    elif queued_assigned:
        state = "QUEUED_RUNNER_ASSIGNED_NO_PROGRESS_PROOF"
    elif queued:
        state = "QUEUED_UNASSIGNED_RUNNER_OR_CAPACITY_UNKNOWN"
    elif run.get("status") == "completed":
        state = "COMPLETED"
    else:
        state = "INCONSISTENT_SNAPSHOT_RECHECK"
    return {
        "state": state, "run_id": run.get("id"),
        "active_jobs": len(active), "queued_jobs": len(queued),
        "assigned_jobs": len(assigned), "queued_assigned_jobs": len(queued_assigned),
        "terminal_jobs": len(jobs)-len(active)-len(queued),
        "running_process_proven": bool(active),
        "runner_inventory_known": False,
        "automatic_kill_now": False,
    }


def obsolete_candidate(run, jobs, successor, branch_sha, now):
    """Allow cancelling only unassigned, queued, superseded *old* runs.

    A valid newer completed success at the current branch SHA is mandatory;
    otherwise cancellation cannot help start the workload and is forbidden.
    """
    if not isinstance(run, dict) or not isinstance(successor, dict):
        return False
    if not isinstance(branch_sha, str) or not SHA.fullmatch(branch_sha):
        return False
    if not isinstance(now, datetime) or now.tzinfo is None:
        return False
    if (type(run.get("id")) is not int or type(successor.get("id")) is not int
            or successor["id"] <= run["id"]
            or run.get("status") != "queued"
            or successor.get("status") != "completed"
            or successor.get("conclusion") != "success"
            or run.get("workflow_id") != successor.get("workflow_id")
            or type(run.get("workflow_id")) is not int
            or run.get("head_branch") != successor.get("head_branch")
            or not isinstance(run.get("head_branch"), str)
            or not REF.fullmatch(run["head_branch"])
            or run.get("head_sha") == branch_sha
            or successor.get("head_sha") != branch_sha
            or run.get("repository", {}).get("full_name") != REPO
            or successor.get("repository", {}).get("full_name") != REPO):
        return False
    try:
        if (now.astimezone(timezone.utc) - parse_time(run["created_at"])
                ).total_seconds() < MIN_STALE_SECONDS:
            return False
    except (KeyError, ValueError, TypeError, OverflowError):
        return False
    return bool(jobs) and all(
        isinstance(j, dict) and
        j.get("status") in ("queued", "completed") and
        (j.get("status") == "completed" or (
            (type(j.get("runner_id")) is not int or j["runner_id"] <= 0) and
            not (isinstance(j.get("runner_name"), str) and
                 j["runner_name"].strip()))) and
        j.get("conclusion") != "failure"
        for j in jobs
    ) and any(j.get("status") == "queued" for j in jobs)


def runner_inventory(fetch=gh_json):
    """Useful only when GitHub admin grants access; 403 means unknown, not none."""
    try:
        data = fetch(f"repos/{REPO}/actions/runners?per_page=100")
        if not isinstance(data, dict) or not isinstance(data.get("runners"), list):
            raise ValueError("Bad runner inventory")
        return {"available": True, "total": data.get("total_count"),
                "matching_online_idle_linux": sum(
                    1 for r in data["runners"]
                    if isinstance(r, dict) and r.get("status") == "online"
                    and r.get("busy") is False
                    and {"self-hosted", "Linux"}.issubset({
                        v.get("name") for v in r.get("labels", [])
                        if isinstance(v, dict)}))}
    except (OSError, ValueError, subprocess.SubprocessError):
        return {"available": False, "reason": "RUNNER_INVENTORY_PERMISSION_OR_API_UNAVAILABLE"}


def check_run(run_id, fetch=gh_json, now=None, *, inventory=False):
    if type(run_id) is not int or run_id <= 0:
        raise ValueError("Invalid run identifier")
    base = f"repos/{REPO}/actions"
    run = fetch(f"{base}/runs/{run_id}")
    jobs = jobs_of(fetch(f"{base}/runs/{run_id}/jobs?per_page=100"))
    result = inspect(run, jobs)
    result["run_status"] = run.get("status")
    result["head_sha"] = run.get("head_sha")
    result["cancel_safe_obsolete"] = False
    branch = run.get("head_branch")
    if isinstance(branch, str) and REF.fullmatch(branch):
        # Fetch branch HEAD and newest same-workflow runs; if either cannot be
        # read the audit fails closed and cancels nothing.
        try:
            data = fetch(f"repos/{REPO}/branches/{quote(branch, safe='')}")
            sha = data["commit"]["sha"]
            candidates = fetch(
                f"{base}/workflows/{run['workflow_id']}/runs"
                f"?branch={quote(branch, safe='')}&per_page=40")["workflow_runs"]
            if not isinstance(candidates, list):
                raise ValueError("Invalid workflow runs list")
            now = now or datetime.now(timezone.utc)
            result["cancel_safe_obsolete"] = any(
                obsolete_candidate(run, jobs, new, sha, now) for new in candidates)
            result["current_branch_sha_matches"] = run.get("head_sha") == sha
        except (OSError, KeyError, TypeError, ValueError, subprocess.SubprocessError):
            result["branch_verification"] = "UNAVAILABLE_CANCEL_DENIED"
    if inventory:
        result["runner_inventory"] = runner_inventory(fetch)
        result["runner_inventory_known"] = result["runner_inventory"]["available"]
    return result


def cancel_obsolete(run_id, fetch=gh_json, now=None):
    """Double-check all REST state immediately before a single narrow cancel."""
    before = check_run(run_id, fetch=fetch, now=now, inventory=False)
    if not before["cancel_safe_obsolete"] or before["active_jobs"]:
        return {"run_id": run_id, "status": "NO_ELIGIBLE_OBSOLETE_QUEUE",
                "cancel_requested": False, "cancelled_running_jobs": False}
    # A fresh second GET is required; GitHub may assign a runner meanwhile.
    after = check_run(run_id, fetch=fetch, now=now, inventory=False)
    if not after["cancel_safe_obsolete"] or after["active_jobs"]:
        return {"run_id": run_id, "status": "STATE_CHANGED_NO_CANCEL",
                "cancel_requested": False, "cancelled_running_jobs": False}
    fetch(f"repos/{REPO}/actions/runs/{run_id}/cancel", "POST")
    return {"run_id": run_id, "status": "OBSOLETE_QUEUED_RUN_CANCEL_REQUESTED",
            "cancel_requested": True, "production_access": False,
            "cancelled_running_jobs": False}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Diagnose GitHub runner queue safely")
    parser.add_argument("--run-id", type=int, default=39546648473)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--inventory", action="store_true")
    parser.add_argument("--cancel-obsolete", action="store_true")
    args = parser.parse_args(argv)
    if not args.live:
        print(json.dumps({"phase": "W34", "status": "DRY_RUN_NO_GITHUB_CALLS"}))
        return 0
    try:
        if args.cancel_obsolete:
            if (os.getenv("W34_CANCEL_OBSOLETE") != "true" or
                    os.getenv("W34_MANUAL_DISPATCH") != "true"):
                raise ValueError("Explicit manual cancellation authorization missing")
            result = cancel_obsolete(args.run_id)
        else:
            result = check_run(args.run_id, inventory=args.inventory)
        print(json.dumps(result, sort_keys=True))
        return 0
    except (OSError, ValueError, TypeError, KeyError, subprocess.SubprocessError):
        print("W34_RUNNER_DIAGNOSIS_FAIL_CLOSED", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
