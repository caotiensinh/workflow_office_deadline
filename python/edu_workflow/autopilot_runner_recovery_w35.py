"""W35: bounded queue-recovery plus over-budget active job progress watchdog.

This module NEVER kills a host process. It can request GitHub to cancel an
obsolete queued *workflow run* if the corresponding job(s) really succeeded
on a newer exact-HEAD run, or an allowlisted in-progress job after three
consistent observations beyond its explicit CI timeout.

Each side effect is opt-in, main-only via workflow permissions; default scan
is read-only. An in-progress job making step progress must not be cancelled.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
import time

from .autopilot_runner_watch_w34 import (
    REPO, SHA, gh_json, jobs_of, obsolete_candidate, parse_time,
)

# Known timeout-minutes from reviewed workflow YAML, not inferred from age.
# Unknown jobs are *never* eligible for active cancellation.
ACTIVE_TIMEOUT_MINUTES = {
    "linux-real-ollama-acceptance": 15,        # W31A
    "selfhost-real-ollama-three-processes": 17, # W33
}
OVER_BUDGET_GRACE_SECONDS = 15 * 60
MIN_OBSERVE_SECONDS = 20
MAX_SCANNED_RUNS = 30


def get_jobs(fetch, run_id):
    reply = fetch(f"repos/{REPO}/actions/runs/{run_id}/jobs?per_page=100")
    result = jobs_of(reply)
    if type(reply.get("total_count")) is not int or reply["total_count"] != len(result):
        raise ValueError("Incomplete job listing: refuse cancellation")
    return result


def successful_replacement(old_jobs, newer_jobs):
    """Successor must complete the specific jobs left queued by the old run.

    A new workflow with only a successful hosted/mock job is not a replacement
    for the missing Linux Ollama job. GitHub overall SUCCESS is not enough.
    """
    if not isinstance(old_jobs, list) or not isinstance(newer_jobs, list):
        return False
    queued = [j.get("name") for j in old_jobs
              if isinstance(j, dict) and j.get("status") == "queued"]
    if not queued or any(not isinstance(n, str) or not n for n in queued):
        return False
    for name in queued:
        matches = [j for j in newer_jobs
                   if isinstance(j, dict) and j.get("name") == name]
        if len(matches) != 1 or matches[0].get("status") != "completed" or (
                matches[0].get("conclusion") != "success"):
            return False
    # The newer attempt must have no pending, failed, cancelled or skipped jobs.
    return bool(newer_jobs) and all(
        isinstance(j, dict) and j.get("status") == "completed"
        and j.get("conclusion") == "success" for j in newer_jobs)


def obsolete_snapshot(run_id, fetch=gh_json, *, now=None):
    """Re-fetch SHA, job inventory, and candidate's actual successor job proof."""
    if type(run_id) is not int or run_id < 1:
        raise ValueError("Bad run identifier")
    base = f"repos/{REPO}/actions"
    old = fetch(f"{base}/runs/{run_id}")
    jobs = get_jobs(fetch, run_id)
    result = {"run_id": run_id, "state": "HOLD_NO_SAFE_OBSOLETE_EVIDENCE",
              "safe_cancel": False, "queued_jobs": sum(
                  j.get("status") == "queued" for j in jobs),
              "running_jobs": sum(j.get("status") == "in_progress" for j in jobs)}
    if not isinstance(old, dict) or old.get("status") != "queued" or (
            old.get("repository") or {}).get("full_name") != REPO:
        return result
    branch = old.get("head_branch")
    if (not isinstance(branch, str) or not branch.startswith(("feat/", "autopilot/"))
            or ".." in branch or "\\" in branch or len(branch) > 150):
        return result
    # GitHub requires ref slashes percent-encoded in this path.
    from urllib.parse import quote
    sha = fetch(f"repos/{REPO}/branches/{quote(branch, safe='')}")["commit"]["sha"]
    if not isinstance(sha, str) or not SHA.fullmatch(sha):
        return result
    successors = fetch(
        f"{base}/workflows/{old['workflow_id']}/runs?branch={quote(branch, safe='')}&per_page=100")
    records = successors.get("workflow_runs", [])
    if not isinstance(records, list):
        raise ValueError("Malformed workflow history")
    # Partial history may omit an older successor; absence yields HOLD.
    # Presence is verified against an individual exact-run job listing.
    seen = now or datetime.now(timezone.utc)
    for new in records:
        if not obsolete_candidate(old, jobs, new, sha, seen):
            continue
        new_jobs = get_jobs(fetch, new["id"])
        if not successful_replacement(jobs, new_jobs):
            continue
        result.update(
            state="OBSOLETE_QUEUE_REPLACED_BY_REAL_JOB_SUCCESS",
            safe_cancel=True,
            replacement_run_id=new["id"],
            current_head_sha=sha,
            obsolete_head_sha=old.get("head_sha"))
        return result
    return result


def step_evidence(job):
    """Stable, bounded digest of visible Actions job/step lifecycle fields."""
    return (
        job.get("status"), job.get("started_at"),
        tuple((s.get("number"), s.get("name"), s.get("status"),
               s.get("started_at"), s.get("completed_at"), s.get("conclusion"))
              for s in job.get("steps", []) if isinstance(s, dict)),
    )


def active_snapshot(run_id, fetch=gh_json):
    run = fetch(f"repos/{REPO}/actions/runs/{run_id}")
    jobs = get_jobs(fetch, run_id)
    return {"run": run, "jobs": jobs}


def overbudget_evidence(before, after, start, end):
    """Classify two active-job snapshots, never infer a hang from age alone.

    Eligibility is an *overrun of the reviewed workflow's hard timeout* PLUS
    unchanged job/step lifecycle across a sampled interval. Such a finding is
    not proof that model inference did no work, but is a bounded safe reason
    to request workflow cancellation after explicit opt-in and final recheck.
    """
    outcome = {"status": "DO_NOT_CANCEL_NO_CONFIRMED_OVERRUN",
               "safe_cancel": False, "active_jobs": 0}
    if (not isinstance(start, datetime) or not isinstance(end, datetime)
            or start.tzinfo is None or end.tzinfo is None
            or (end - start).total_seconds() < MIN_OBSERVE_SECONDS):
        return outcome
    if not isinstance(before, dict) or not isinstance(after, dict):
        return outcome
    a, b = before.get("run"), after.get("run")
    if (not isinstance(a, dict) or not isinstance(b, dict)
            or a.get("id") != b.get("id")
            or a.get("head_sha") != b.get("head_sha")
            or a.get("head_branch") != b.get("head_branch")
            or a.get("workflow_id") != b.get("workflow_id")
            or a.get("status") != "in_progress"
            or b.get("status") != "in_progress"
            or (a.get("repository") or {}).get("full_name") != REPO
            or (b.get("repository") or {}).get("full_name") != REPO):
        return outcome
    aj, bj = before.get("jobs"), after.get("jobs")
    if not isinstance(aj, list) or not isinstance(bj, list):
        return outcome
    if (len(aj) != len(bj)
            or {j.get("id") for j in aj} != {j.get("id") for j in bj}
            or any(j.get("status") not in ("in_progress", "completed") for j in bj)):
        return outcome
    active = [j for j in bj if j.get("status") == "in_progress"]
    outcome["active_jobs"] = len(active)
    if not active or len(active) > 3:
        return outcome
    old_by_id = {j["id"]: j for j in aj}
    for job in active:
        old = old_by_id[job["id"]]
        if old.get("status") != "in_progress":
            outcome["status"] = "PROGRESS_DETECTED_KEEP_RUNNING"
            return outcome
        if step_evidence(old) != step_evidence(job):
            outcome["status"] = "PROGRESS_DETECTED_KEEP_RUNNING"
            return outcome
        if job.get("name") not in ACTIVE_TIMEOUT_MINUTES:
            outcome["status"] = "UNRECOGNIZED_ACTIVE_JOB_KEEP_RUNNING"
            return outcome
        try:
            age = (end.astimezone(timezone.utc)
                   - parse_time(job["started_at"])).total_seconds()
        except (KeyError, TypeError, ValueError, OverflowError):
            return outcome
        limit = 60 * ACTIVE_TIMEOUT_MINUTES[job["name"]] + OVER_BUDGET_GRACE_SECONDS
        if age < limit:
            outcome["status"] = "WITHIN_TIMEOUT_BUDGET_KEEP_RUNNING"
            return outcome
    outcome["status"] = "EXCEEDED_DECLARED_TIMEOUT_NO_STEP_TRANSITION"
    outcome["safe_cancel"] = True
    return outcome


def confirm_stall(run_id, fetch=gh_json, sleep=time.sleep, now=None, *,
                  observe_seconds=20):
    if type(run_id) is not int or run_id < 1:
        raise ValueError("Invalid run id")
    if not 20 <= observe_seconds <= 60:
        raise ValueError("Unsafe sampling interval")
    start = now() if now else datetime.now(timezone.utc)
    before = active_snapshot(run_id, fetch)
    sleep(observe_seconds)
    end = now() if now else datetime.now(timezone.utc)
    after = active_snapshot(run_id, fetch)
    verdict = overbudget_evidence(before, after, start, end)
    verdict["run_id"] = run_id
    verdict["cancel_requested"] = False
    return verdict, after


def cancel_stalled(run_id, fetch=gh_json, sleep=time.sleep, now=None):
    """Three snapshots; cancellation restricted to explicit over-budget jobs."""
    verdict, last = confirm_stall(run_id, fetch=fetch, sleep=sleep, now=now)
    if not verdict["safe_cancel"]:
        return verdict
    # Require a *real second 20-second observation*, never synthetic time.
    third_start = now() if now else datetime.now(timezone.utc)
    sleep(MIN_OBSERVE_SECONDS)
    third_end = now() if now else datetime.now(timezone.utc)
    final = active_snapshot(run_id, fetch)
    again = overbudget_evidence(last, final, third_start, third_end)
    if not again["safe_cancel"]:
        verdict["status"] = "LAST_MOMENT_PROGRESS_NO_CANCEL"
        verdict["safe_cancel"] = False
        return verdict
    fetch(f"repos/{REPO}/actions/runs/{run_id}/cancel", "POST")
    verdict["status"] = "OVER_BUDGET_RUN_CANCEL_REQUESTED_NOT_HOST_KILL"
    verdict["cancel_requested"] = True
    return verdict


def cancel_obsolete_verified(run_id, fetch=gh_json, *, now=None):
    one = obsolete_snapshot(run_id, fetch=fetch, now=now)
    if not one["safe_cancel"]:
        return one
    two = obsolete_snapshot(run_id, fetch=fetch, now=now)
    if not two["safe_cancel"] or (
            one.get("replacement_run_id") != two.get("replacement_run_id")
            or one.get("current_head_sha") != two.get("current_head_sha")):
        return {"run_id": run_id, "safe_cancel": False,
                "status": "RACE_RECHECK_REFUSED_CANCEL"}
    fetch(f"repos/{REPO}/actions/runs/{run_id}/cancel", "POST")
    return {"run_id": run_id, "status": "VERIFIED_OBSOLETE_QUEUE_CANCEL_REQUESTED",
            "cancel_requested": True, "replacement_run_id": two["replacement_run_id"]}


def queued_candidates(fetch=gh_json, *, limit=MAX_SCANNED_RUNS):
    x = fetch(f"repos/{REPO}/actions/runs?status=queued&per_page=100")
    rows = x.get("workflow_runs")
    if not isinstance(rows, list) or not isinstance(x.get("total_count"), int):
        raise ValueError("Incomplete queued run listing")
    if x["total_count"] > len(rows):
        raise ValueError("Queued run listing truncated")
    return [r["id"] for r in rows if isinstance(r, dict)
            and type(r.get("id")) is int][:limit]


def main(argv=None):
    p = argparse.ArgumentParser(description="W35 real Actions stall/obsolete audit")
    p.add_argument("--live", action="store_true")
    p.add_argument("--run-id", type=int)
    p.add_argument("--scan-queued", action="store_true")
    p.add_argument("--cancel-obsolete", action="store_true")
    p.add_argument("--cancel-stalled", action="store_true")
    args = p.parse_args(argv)
    if not args.live:
        print(json.dumps({"phase": "W35", "status": "DRY_RUN_NO_GITHUB_CALLS"}))
        return 0
    if args.cancel_obsolete and args.cancel_stalled:
        print("W35_AMBIGUOUS_WRITE_MODE_REFUSED", file=__import__("sys").stderr)
        return 2
    if args.cancel_obsolete or args.cancel_stalled:
        if (os.getenv("EDU_W35_ACTIONS_WRITE") != "true"
                or os.getenv("GITHUB_REF") != "refs/heads/main"):
            print("W35_MAIN_ONLY_WRITE_OPTIN_REQUIRED", file=__import__("sys").stderr)
            return 2
    try:
        ids = queued_candidates() if args.scan_queued else [args.run_id]
        if any(type(x) is not int or x <= 0 for x in ids):
            raise ValueError("Explicit --run-id required")
        results = []
        for ident in ids:
            if args.cancel_obsolete:
                results.append(cancel_obsolete_verified(ident))
            elif args.cancel_stalled:
                results.append(cancel_stalled(ident))
            else:
                results.append(obsolete_snapshot(ident))
        print(json.dumps({"phase": "W35", "results": results}, sort_keys=True))
        return 0
    except (OSError, ValueError, KeyError, TypeError):
        print("W35_RECOVERY_FAIL_CLOSED", file=__import__("sys").stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
