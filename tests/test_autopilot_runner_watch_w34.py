"""W34 runner queue watchdog and strictly superseded-only cancellation tests."""
import io
import os
import subprocess
import unittest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch

from edu_workflow.autopilot_runner_watch_w34 import (
    REPO, MIN_STALE_SECONDS, cancel_obsolete, check_run, inspect,
    main, obsolete_candidate, runner_inventory,
)

SHA_OLD = "a" * 40
SHA_NEW = "b" * 40
NOW = datetime(2026, 10, 21, 9, 0, tzinfo=timezone.utc)


def old_run():
    return {"id": 100, "workflow_id": 123, "name": "W34",
            "status": "queued", "conclusion": None,
            "head_sha": SHA_OLD, "head_branch": "feat/synthetic",
            "created_at": "2026-10-21T07:00:00Z",
            "repository": {"full_name": REPO}}


def newer_success():
    return {"id": 101, "workflow_id": 123, "name": "W34",
            "status": "completed", "conclusion": "success",
            "head_sha": SHA_NEW, "head_branch": "feat/synthetic",
            "created_at": "2026-10-21T08:00:00Z",
            "repository": {"full_name": REPO}}


def jobs():
    return [
        {"id": 1, "name": "hosted-contract", "status": "completed",
         "conclusion": "success", "runner_id": None, "runner_name": None},
        {"id": 2, "name": "linux-real", "status": "queued",
         "conclusion": None, "runner_id": None, "runner_name": None},
    ]


class RepoStub:
    def __init__(self):
        self.run = old_run()
        self.jobs = jobs()
        self.successors = [newer_success()]
        self.sha = SHA_NEW
        self.calls = []
        self.on_second_poll = None

    def __call__(self, path, method="GET"):
        self.calls.append((path, method))
        if path.endswith("/runs/100"):
            return self.run
        if path.endswith("/runs/100/jobs?per_page=100"):
            if self.on_second_poll and self.calls.count(
                    (path, "GET")) > 1:
                self.on_second_poll(self)
            return {"jobs": self.jobs}
        if "/branches/feat%2Fsynthetic" in path:
            return {"commit": {"sha": self.sha}}
        if "/workflows/123/runs?" in path:
            return {"workflow_runs": self.successors}
        if path.endswith("/runs/100/cancel") and method == "POST":
            return {}
        raise ValueError("Unexpected test API route: " + path)


class W34QueueWatchdog(unittest.TestCase):
    def test_unassigned_queued_is_not_a_running_job(self):
        report = inspect(old_run(), jobs())
        self.assertEqual(report["state"],
                         "QUEUED_UNASSIGNED_RUNNER_OR_CAPACITY_UNKNOWN")
        self.assertEqual(report["active_jobs"], 0)
        self.assertEqual(report["queued_jobs"], 1)
        self.assertFalse(report["running_process_proven"])
        self.assertFalse(report["automatic_kill_now"])

    def test_running_worker_is_never_auto_cancel(self):
        data = jobs()
        data[1].update(status="in_progress", runner_id=5, runner_name="linux-1")
        report = inspect(old_run(), data)
        self.assertEqual(report["state"], "RUNNING_DO_NOT_CANCEL")
        self.assertEqual(report["active_jobs"], 1)
        self.assertFalse(obsolete_candidate(old_run(), data, newer_success(), SHA_NEW, NOW))

    def test_queue_with_runner_assigned_not_proven_stuck(self):
        data = jobs()
        data[1]["runner_id"] = 200
        report = inspect(old_run(), data)
        self.assertEqual(report["state"],
                         "QUEUED_RUNNER_ASSIGNED_NO_PROGRESS_PROOF")

    def test_same_head_queue_never_cancelled(self):
        self.assertFalse(obsolete_candidate(old_run(), jobs(), newer_success(),
                                            SHA_OLD, NOW))

    def test_no_new_success_never_cancel(self):
        self.assertFalse(obsolete_candidate(old_run(), jobs(), {}, SHA_NEW, NOW))

    def test_success_from_another_workflow_is_irrelevant(self):
        later = dict(newer_success(), workflow_id=999)
        self.assertFalse(obsolete_candidate(old_run(), jobs(), later, SHA_NEW, NOW))

    def test_wrong_success_branch_is_irrelevant(self):
        later = dict(newer_success(), head_branch="elsewhere")
        self.assertFalse(obsolete_candidate(old_run(), jobs(), later, SHA_NEW, NOW))

    def test_wrong_success_repository_is_irrelevant(self):
        later = dict(newer_success(), repository={"full_name": "outsider/repo"})
        self.assertFalse(obsolete_candidate(old_run(), jobs(), later, SHA_NEW, NOW))

    def test_unapproved_queued_old_run_cannot_cancel_too_soon(self):
        instant = datetime(2026, 10, 21, 7, 10, tzinfo=timezone.utc)
        self.assertFalse(obsolete_candidate(old_run(), jobs(), newer_success(),
                                            SHA_NEW, instant))

    def test_queued_old_with_verified_successor_can_cancel(self):
        self.assertTrue(obsolete_candidate(old_run(), jobs(), newer_success(),
                                           SHA_NEW, NOW))

    def test_newer_pending_not_valid_successor(self):
        later = dict(newer_success(), status="in_progress", conclusion=None)
        self.assertFalse(obsolete_candidate(old_run(), jobs(), later, SHA_NEW, NOW))

    def test_failure_in_old_job_blocks_cancellation(self):
        data = jobs()
        data[0]["conclusion"] = "failure"
        self.assertFalse(obsolete_candidate(old_run(), data, newer_success(),
                                            SHA_NEW, NOW))

    def test_completed_hosted_runner_does_not_block_old_queued_cleanup(self):
        data = jobs()
        data[0]["runner_id"] = 12
        data[0]["runner_name"] = "ephemeral-completed-worker"
        report = inspect(old_run(), data)
        self.assertEqual(report["state"],
                         "QUEUED_UNASSIGNED_RUNNER_OR_CAPACITY_UNKNOWN")
        self.assertEqual(report["queued_assigned_jobs"], 0)
        self.assertEqual(report["assigned_jobs"], 1)
        self.assertTrue(obsolete_candidate(old_run(), data, newer_success(),
                                           SHA_NEW, NOW))

    def test_unassigned_queue_runner_id_zero_is_not_real_assignment(self):
        data = jobs()
        data[1]["runner_id"] = 0
        self.assertEqual(inspect(old_run(), data)["queued_assigned_jobs"], 0)

    def test_queued_assigned_runner_blocks_cancellation(self):
        data = jobs()
        data[1]["runner_id"] = 12
        self.assertFalse(obsolete_candidate(old_run(), data, newer_success(),
                                            SHA_NEW, NOW))

    def test_live_read_only_queue_reports_no_action(self):
        stub = RepoStub()
        stub.sha = SHA_OLD
        report = check_run(100, fetch=stub, now=NOW)
        self.assertFalse(report["cancel_safe_obsolete"])
        self.assertEqual(report["state"],
                         "QUEUED_UNASSIGNED_RUNNER_OR_CAPACITY_UNKNOWN")
        self.assertFalse(any(method == "POST" for _, method in stub.calls))

    def test_obsolete_live_report_identifies_safe_old_queue(self):
        stub = RepoStub()
        report = check_run(100, fetch=stub, now=NOW)
        self.assertTrue(report["cancel_safe_obsolete"])
        self.assertFalse(report["automatic_kill_now"])
        self.assertFalse(any(method == "POST" for _, method in stub.calls))

    def test_double_checked_safe_request_cancels_only_obsolete_run(self):
        stub = RepoStub()
        result = cancel_obsolete(100, fetch=stub, now=NOW)
        self.assertEqual(result["status"], "OBSOLETE_QUEUED_RUN_CANCEL_REQUESTED")
        self.assertEqual(
            [method for _, method in stub.calls if method == "POST"], ["POST"])
        self.assertEqual(stub.calls[-1][0],
                         f"repos/{REPO}/actions/runs/100/cancel")

    def test_last_moment_running_job_prevents_post(self):
        stub = RepoStub()
        def turn_running(obj):
            obj.jobs[1]["status"] = "in_progress"
            obj.jobs[1]["runner_id"] = 55
        stub.on_second_poll = turn_running
        with self.assertRaises(ValueError):
            cancel_obsolete(100, fetch=stub, now=NOW)
        self.assertFalse(any(method == "POST" for _, method in stub.calls))

    def test_runner_inventory_403_must_not_mean_zero_runners(self):
        def deny(_):
            raise subprocess.CalledProcessError(1, ["gh", "api"])
        result = runner_inventory(deny)
        self.assertFalse(result["available"])
        self.assertIn("UNAVAILABLE", result["reason"])

    def test_runner_inventory_online_capacity_is_only_evidence_if_authorized(self):
        data = {"total_count": 2, "runners": [
            {"status": "online", "busy": False,
             "labels": [{"name": "self-hosted"}, {"name": "Linux"}]},
            {"status": "offline", "busy": False,
             "labels": [{"name": "self-hosted"}, {"name": "Linux"}]}
        ]}
        report = runner_inventory(lambda _: data)
        self.assertTrue(report["available"])
        self.assertEqual(report["matching_online_idle_linux"], 1)

    def test_cli_dryrun_never_uses_network(self):
        stream = io.StringIO()
        with patch("sys.stdout", stream):
            self.assertEqual(main([]), 0)
        self.assertIn("DRY_RUN_NO_GITHUB_CALLS", stream.getvalue())

    def test_live_cancel_requires_two_owner_optins(self):
        with patch.dict(os.environ, {"W34_CANCEL_OBSOLETE": "false",
                                     "W34_MANUAL_DISPATCH": "true"}):
            self.assertEqual(main(["--live", "--cancel-obsolete"]), 2)

    def test_no_unknown_job_status_can_trigger_cancel(self):
        data = jobs()
        data[1]["status"] = "mystery"
        with self.assertRaises(ValueError):
            inspect(old_run(), data)

    def test_bad_branch_or_sha_rejects_candidate(self):
        self.assertFalse(obsolete_candidate(old_run(), jobs(), newer_success(),
                                            "not-a-sha", NOW))
        r = dict(old_run(), head_branch="../secrets")
        self.assertFalse(obsolete_candidate(r, jobs(), newer_success(), SHA_NEW, NOW))


if __name__ == "__main__":
    unittest.main()
