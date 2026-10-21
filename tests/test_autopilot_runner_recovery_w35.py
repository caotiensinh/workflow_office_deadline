"""W35 real recovery policy: fail closed against active work and false successors."""
import copy
from datetime import datetime, timedelta, timezone
import io
import os
import unittest
from unittest.mock import patch

from edu_workflow.autopilot_runner_recovery_w35 import (
    REPO, active_snapshot, cancel_obsolete_verified, cancel_stalled,
    confirm_stall, obsolete_snapshot, overbudget_evidence,
    queued_candidates, successful_replacement, main,
)

OLD = "a" * 40
NEW = "b" * 40
NOW = datetime(2026, 10, 22, 0, 0, tzinfo=timezone.utc)


def old_run():
    return {"id": 200, "workflow_id": 99, "status": "queued",
            "head_branch": "feat/synthetic", "head_sha": OLD,
            "created_at": "2026-10-21T20:00:00Z",
            "repository": {"full_name": REPO}}


def successor():
    return {"id": 201, "workflow_id": 99, "status": "completed",
            "conclusion": "success", "head_branch": "feat/synthetic",
            "head_sha": NEW, "repository": {"full_name": REPO}}


def old_jobs():
    return [{"id": 30, "name": "hosted-contract", "status": "completed",
             "conclusion": "success", "runner_id": 3},
            {"id": 31, "name": "linux-real-ollama-acceptance",
             "status": "queued", "conclusion": None, "runner_id": None}]


def new_jobs():
    return [{"id": 40, "name": "hosted-contract", "status": "completed",
             "conclusion": "success"},
            {"id": 41, "name": "linux-real-ollama-acceptance",
             "status": "completed", "conclusion": "success"}]


class QueueFake:
    def __init__(self):
        self.old = old_run()
        self.replacement = successor()
        self.jobs_old = old_jobs()
        self.jobs_new = new_jobs()
        self.sha = NEW
        self.posts = []
        self.old_reads = 0
        self.shift_to_active_on_second = False

    def __call__(self, path, method="GET"):
        if method == "POST":
            self.posts.append(path)
            return {}
        if path.endswith("/runs/200"):
            return copy.deepcopy(self.old)
        if path.endswith("/runs/200/jobs?per_page=100"):
            self.old_reads += 1
            if self.shift_to_active_on_second and self.old_reads >= 2:
                self.jobs_old[1]["status"] = "in_progress"
                self.jobs_old[1]["runner_id"] = 7
            return {"total_count": len(self.jobs_old),
                    "jobs": copy.deepcopy(self.jobs_old)}
        if path.endswith("/runs/201/jobs?per_page=100"):
            return {"total_count": len(self.jobs_new),
                    "jobs": copy.deepcopy(self.jobs_new)}
        if "/branches/feat%2Fsynthetic" in path:
            return {"commit": {"sha": self.sha}}
        if "/workflows/99/runs?" in path:
            return {"workflow_runs": [copy.deepcopy(self.replacement)],
                    "total_count": 1}
        if path.endswith("/actions/runs?status=queued&per_page=100"):
            return {"total_count": 1, "workflow_runs": [copy.deepcopy(self.old)]}
        raise AssertionError(path)


def active_job(name="linux-real-ollama-acceptance", step="in_progress"):
    return {"id": 55, "name": name, "status": "in_progress",
            "started_at": "2026-10-21T23:00:00Z",
            "steps": [{"number": 1, "name": "Inference", "status": step,
                       "started_at": "2026-10-21T23:01:00Z",
                       "completed_at": None, "conclusion": None}]}


def active_run():
    return {"id": 300, "workflow_id": 789, "status": "in_progress",
            "head_sha": OLD, "head_branch": "feat/llm",
            "repository": {"full_name": REPO}}


def active_bundle(job=None):
    return {"run": active_run(), "jobs": [active_job() if job is None else job]}


class ActiveFake:
    def __init__(self):
        self.run = active_run()
        self.job = active_job()
        self.posts = []
        self.read_count = 0
        self.progress_on = 0

    def __call__(self, path, method="GET"):
        if method == "POST":
            self.posts.append(path)
            return {}
        if path.endswith("/runs/300"):
            return copy.deepcopy(self.run)
        if path.endswith("/runs/300/jobs?per_page=100"):
            self.read_count += 1
            job = copy.deepcopy(self.job)
            if self.progress_on and self.read_count >= self.progress_on:
                job["steps"][0]["status"] = "completed"
                job["steps"].append({"number": 2, "name": "Validate",
                                     "status": "in_progress",
                                     "started_at": "2026-10-21T23:41:00Z"})
            return {"total_count": 1, "jobs": [job]}
        raise AssertionError(path)


def clock(count=4):
    # Simulated clock is test-only. Production uses real wall-clock deltas.
    values = iter(NOW + timedelta(seconds=i * 20) for i in range(count))
    return lambda: next(values)


class W35Recovery(unittest.TestCase):
    def test_successor_must_have_real_queued_job_success(self):
        self.assertTrue(successful_replacement(old_jobs(), new_jobs()))

    def test_mock_only_successor_is_not_replacement(self):
        hosted_only = new_jobs()[:1]
        self.assertFalse(successful_replacement(old_jobs(), hosted_only))

    def test_replacement_skipped_real_job_rejected(self):
        v = new_jobs()
        v[1]["conclusion"] = "skipped"
        self.assertFalse(successful_replacement(old_jobs(), v))

    def test_replacement_duplicate_name_rejected(self):
        v = new_jobs() + [new_jobs()[1]]
        self.assertFalse(successful_replacement(old_jobs(), v))

    def test_replacement_pending_job_rejected(self):
        v = new_jobs()
        v[1]["status"] = "in_progress"
        self.assertFalse(successful_replacement(old_jobs(), v))

    def test_replacement_has_unrelated_failure_rejected(self):
        v = new_jobs() + [{"name": "other", "status": "completed",
                           "conclusion": "failure"}]
        self.assertFalse(successful_replacement(old_jobs(), v))

    def test_successor_live_exact_current_head_eligible(self):
        x = obsolete_snapshot(200, fetch=QueueFake(), now=NOW)
        self.assertTrue(x["safe_cancel"])
        self.assertEqual(x["replacement_run_id"], 201)

    def test_live_stale_queue_no_new_real_job_success(self):
        f = QueueFake()
        f.jobs_new = new_jobs()[:1]
        x = obsolete_snapshot(200, fetch=f, now=NOW)
        self.assertFalse(x["safe_cancel"])

    def test_queue_live_head_never_cancel(self):
        f = QueueFake()
        f.sha = OLD
        self.assertFalse(obsolete_snapshot(200, fetch=f, now=NOW)["safe_cancel"])

    def test_missing_successor_listing_denies_cancel(self):
        f = QueueFake()
        f.jobs_new = new_jobs()[:1]
        self.assertFalse(obsolete_snapshot(200, fetch=f, now=NOW)["safe_cancel"])

    def test_real_double_read_cancellation_only_after_proof(self):
        f = QueueFake()
        out = cancel_obsolete_verified(200, fetch=f, now=NOW)
        self.assertTrue(out["cancel_requested"])
        self.assertEqual(f.posts, [f"repos/{REPO}/actions/runs/200/cancel"])

    def test_race_runner_assigned_during_second_poll(self):
        f = QueueFake()
        f.shift_to_active_on_second = True
        out = cancel_obsolete_verified(200, fetch=f, now=NOW)
        self.assertEqual(out["status"], "RACE_RECHECK_REFUSED_CANCEL")
        self.assertFalse(f.posts)

    def test_no_queued_candidates_when_other_status(self):
        f = QueueFake()
        f.old["status"] = "in_progress"
        self.assertFalse(obsolete_snapshot(200, fetch=f, now=NOW)["safe_cancel"])

    def test_global_queue_read_only_discovery(self):
        self.assertEqual(queued_candidates(fetch=QueueFake()), [200])

    def test_progress_must_preserve_running_job(self):
        a = active_bundle()
        b = active_bundle()
        b["jobs"][0]["steps"][0]["status"] = "completed"
        r = overbudget_evidence(a, b, NOW, NOW+timedelta(seconds=20))
        self.assertEqual(r["status"], "PROGRESS_DETECTED_KEEP_RUNNING")
        self.assertFalse(r["safe_cancel"])

    def test_no_step_progress_within_time_budget_still_keep(self):
        a = active_bundle()
        a["jobs"][0]["started_at"] = "2026-10-21T23:55:00Z"
        b = copy.deepcopy(a)
        r = overbudget_evidence(a,b,NOW,NOW+timedelta(seconds=20))
        self.assertFalse(r["safe_cancel"])

    def test_overbudget_beyond_workflow_timeout_and_grace(self):
        a = active_bundle()
        b = copy.deepcopy(a)
        r = overbudget_evidence(a,b,NOW,NOW+timedelta(seconds=20))
        self.assertTrue(r["safe_cancel"])
        self.assertEqual(r["status"], "EXCEEDED_DECLARED_TIMEOUT_NO_STEP_TRANSITION")

    def test_missing_step_details_never_confirm_stall(self):
        a = active_bundle()
        a["jobs"][0].pop("steps")
        b = copy.deepcopy(a)
        verdict = overbudget_evidence(a, b, NOW, NOW+timedelta(seconds=20))
        self.assertFalse(verdict["safe_cancel"])
        self.assertEqual(verdict["status"],
                         "INSUFFICIENT_ACTIVE_STEP_EVIDENCE_KEEP_RUNNING")

    def test_all_completed_steps_without_active_step_keep_work(self):
        a = active_bundle()
        a["jobs"][0]["steps"][0]["status"] = "completed"
        b = copy.deepcopy(a)
        verdict = overbudget_evidence(a, b, NOW, NOW+timedelta(seconds=20))
        self.assertFalse(verdict["safe_cancel"])

    def test_unknown_job_timeout_never_auto_cancels(self):
        a = active_bundle(active_job(name="production-unknown"))
        b = copy.deepcopy(a)
        self.assertFalse(overbudget_evidence(
            a,b,NOW,NOW+timedelta(seconds=20))["safe_cancel"])

    def test_20_second_observation_is_mandatory(self):
        a = active_bundle()
        self.assertFalse(overbudget_evidence(
            a,a,NOW,NOW+timedelta(seconds=19))["safe_cancel"])

    def test_unrelated_active_job_prevents_any_cancellation(self):
        a = active_bundle()
        a["jobs"].append(active_job(name="unknown-task"))
        a["jobs"][-1]["id"] = 56
        b = copy.deepcopy(a)
        self.assertFalse(overbudget_evidence(
            a,b,NOW,NOW+timedelta(seconds=20))["safe_cancel"])

    def test_any_queued_job_prevents_active_cancel(self):
        a = active_bundle()
        a["jobs"].append({"id": 56, "name": "queue", "status": "queued"})
        b = copy.deepcopy(a)
        self.assertFalse(overbudget_evidence(
            a,b,NOW,NOW+timedelta(seconds=20))["safe_cancel"])

    def test_running_task_lifecycle_change_is_detected(self):
        fake = ActiveFake()
        fake.progress_on = 2
        r,_ = confirm_stall(300, fetch=fake, sleep=lambda _: None, now=clock(2))
        self.assertEqual(r["status"], "PROGRESS_DETECTED_KEEP_RUNNING")
        self.assertFalse(fake.posts)

    def test_cancel_running_overbudget_only_after_three_snapshots(self):
        fake = ActiveFake()
        verdict = cancel_stalled(300, fetch=fake, sleep=lambda _: None,
                                 now=clock())
        self.assertTrue(verdict["cancel_requested"])
        self.assertEqual(fake.read_count, 3)
        self.assertEqual(fake.posts, [f"repos/{REPO}/actions/runs/300/cancel"])

    def test_last_moment_step_progress_stops_post(self):
        fake = ActiveFake()
        fake.progress_on = 3
        verdict = cancel_stalled(300, fetch=fake, sleep=lambda _: None,
                                 now=clock())
        self.assertFalse(verdict["cancel_requested"])
        self.assertEqual(verdict["status"], "LAST_MOMENT_PROGRESS_NO_CANCEL")
        self.assertFalse(fake.posts)

    def test_existing_running_job_within_budget_kept(self):
        fake = ActiveFake()
        fake.job["started_at"] = "2026-10-21T23:55:00Z"
        verdict = cancel_stalled(300, fetch=fake, sleep=lambda _: None,
                                 now=clock())
        self.assertFalse(verdict["safe_cancel"])
        self.assertFalse(fake.posts)

    def test_status_change_during_sampling_keeps_job(self):
        fake = ActiveFake()
        fake.run["status"] = "completed"
        verdict = cancel_stalled(300, fetch=fake, sleep=lambda _: None,
                                 now=clock())
        self.assertFalse(verdict["safe_cancel"])

    def test_write_optin_and_main_ref_required(self):
        with patch.dict(os.environ, {"EDU_W35_ACTIONS_WRITE": "false",
                                     "GITHUB_REF": "refs/heads/main"}):
            self.assertEqual(main(["--live", "--run-id", "200",
                                   "--cancel-obsolete"]), 2)

    def test_dryrun_never_contacts_github(self):
        stream = io.StringIO()
        with patch("sys.stdout", stream):
            self.assertEqual(main([]), 0)
        self.assertIn("DRY_RUN_NO_GITHUB_CALLS",stream.getvalue())


if __name__ == "__main__":
    unittest.main()
