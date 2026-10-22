"""W38 durable lease acceptance: fencing, crash/restart, concurrency, exact output IDs."""
import json
import os
from pathlib import Path
import tempfile
from concurrent.futures import ThreadPoolExecutor
import unittest
from unittest.mock import patch

from edu_workflow.autopilot_task_lease_w38 import (
    MAX_ATTEMPTS, LeaseStore, authorized_state_db,
)

DIGEST = "a" * 64


def task(ident, *, kind="AUTO_PROPOSAL"):
    return {
        "id": ident,
        "title": "Propose fictional workflow lease safety",
        "description": "Review only synthetic task reclaims, never production endpoint",
        "domain": "qa-security",
        "kind": kind,
        "approval_required": kind != "AUTO_PROPOSAL",
    }


class W38DurableLease(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.backlog = self.root / "backlog.json"
        self.tasks = [task("W27-DOCS"), task("W27-QA"),
                      task("W27-UX"), task("W27-LEASE")]
        self.write()
        self.db_path = self.root / "lease.sqlite3"
        self.store = LeaseStore(self.db_path)
        self.assertEqual(self.store.seed(self.backlog), 4)

    def write(self, tasks=None):
        self.backlog.write_text(json.dumps({
            "schema": 1, "tasks": self.tasks if tasks is None else tasks
        }), encoding="utf-8")

    def test_seeding_is_idempotent_and_no_duplicate_claimable_rows(self):
        self.assertEqual(self.store.seed(self.backlog), 4)
        self.assertEqual(len(self.store.inspect()), 4)

    def test_atomic_single_claim_across_two_thread_owners(self):
        def claim(i):
            return self.store.claim(self.tasks[0], "owner-%02d" % i,
                                    now=1000, ttl=90)
        with ThreadPoolExecutor(max_workers=12) as pool:
            results = list(pool.map(claim, range(12)))
        winners = [r for r in results if r]
        self.assertEqual(len(winners), 1)
        self.assertEqual(winners[0]["attempt"], 1)

    def test_restart_reclaims_expired_lease_only(self):
        first = self.store.claim(self.tasks[0], "process-A", now=100, ttl=60)
        self.assertEqual(
            LeaseStore(self.db_path).claim(self.tasks[0], "process-B",
                                           now=159, ttl=60), None)
        second = LeaseStore(self.db_path).claim(self.tasks[0], "process-B",
                                                now=160, ttl=60)
        self.assertIsNotNone(second)
        self.assertNotEqual(first["token"], second["token"])
        self.assertEqual(second["attempt"], 2)

    def test_fenced_old_owner_never_completes_new_lease(self):
        stale = self.store.claim(self.tasks[0], "process-A", now=100, ttl=60)
        new = self.store.claim(self.tasks[0], "process-B", now=160, ttl=60)
        with self.assertRaises(ValueError):
            self.store.complete(stale, result_digest=DIGEST, now=161)
        self.assertEqual(self.store.complete(new, result_digest=DIGEST,
                                             now=162)["state"], "DONE")

    def test_duplicate_complete_cannot_overwrite_result(self):
        a = self.store.claim(self.tasks[0], "process-A", now=100, ttl=60)
        self.store.complete(a, result_digest=DIGEST, now=102)
        with self.assertRaises(ValueError):
            self.store.complete(a, result_digest="b"*64, now=103)
        self.assertEqual(LeaseStore(self.db_path).inspect()[0]["state"], "DONE")

    def test_done_task_not_rerun_after_restart(self):
        a = self.store.claim(self.tasks[0], "owner-A", now=100, ttl=60)
        self.store.complete(a, result_digest=DIGEST, now=110)
        self.assertIsNone(LeaseStore(self.db_path).claim(
            self.tasks[0], "owner-B", now=2000, ttl=60))

    def test_progress_requires_monotonically_increasing_real_chunks(self):
        a = self.store.claim(self.tasks[0], "owner-A", now=100, ttl=60)
        self.assertEqual(self.store.renew_progress(a, chunks=1,
                                                   now=120, ttl=90), 210)
        with self.assertRaises(ValueError):
            self.store.renew_progress(a, chunks=1, now=150, ttl=90)
        self.assertEqual(self.store.renew_progress(a, chunks=2,
                                                   now=160, ttl=90), 250)
        self.assertEqual(self.store.inspect()[0]["chunks"], 2)

    def test_fake_heartbeat_clock_tick_does_not_extend_lease(self):
        a = self.store.claim(self.tasks[0], "owner-A", now=100, ttl=60)
        with self.assertRaises(ValueError):
            self.store.renew_progress(a, chunks=0, now=130)
        with self.assertRaises(ValueError):
            self.store.renew_progress(a, chunks=1, now=161)

    def test_lifetime_hard_cap_even_with_advancing_progress(self):
        a = self.store.claim(self.tasks[0], "owner-A", now=100, ttl=120)
        for step in range(1, 5):
            self.store.renew_progress(a, chunks=step,
                                      now=100 + step*100, ttl=180)
        self.assertEqual(self.store.renew_progress(
            a, chunks=5, now=600, ttl=180), 700)
        with self.assertRaises(ValueError):
            self.store.renew_progress(a, chunks=6, now=700, ttl=180)

    def test_fail_makes_task_pending_once_then_permanent_failure(self):
        a = self.store.claim(self.tasks[0], "owner-A", now=100, ttl=60)
        self.assertEqual(self.store.fail(a, now=101), "PENDING")
        b = self.store.claim(self.tasks[0], "owner-B", now=110, ttl=60)
        self.assertEqual(b["attempt"], MAX_ATTEMPTS)
        self.assertEqual(self.store.fail(b, now=111), "FAILED")
        self.assertIsNone(self.store.claim(
            self.tasks[0], "owner-C", now=112, ttl=60))

    def test_crash_twice_exhausts_budget_without_third_run(self):
        a = self.store.claim(self.tasks[0], "owner-A", now=100, ttl=60)
        b = self.store.claim(self.tasks[0], "owner-B", now=160, ttl=60)
        self.assertIsNotNone(b)
        self.assertIsNone(self.store.claim(self.tasks[0], "owner-C",
                                           now=220, ttl=60))
        self.assertEqual(self.store.inspect()[0]["state"], "FAILED")

    def test_unauthorized_backlog_mutation_rejected(self):
        altered = [dict(self.tasks[0], title="Changed signed work plan")] + self.tasks[1:]
        self.write(altered)
        with self.assertRaises(ValueError):
            LeaseStore(self.db_path).seed(self.backlog)

    def test_blocked_external_task_is_not_seeded(self):
        self.write(self.tasks + [task("W27-IT", kind="BLOCKED_EXTERNAL")])
        self.assertEqual(self.store.seed(self.backlog), 4)
        self.assertEqual(len(self.store.inspect()), 4)

    def test_unregistered_task_never_claimed(self):
        with self.assertRaises(ValueError):
            self.store.claim(task("W27-UNKNOWN"), "owner-A",
                             now=100, ttl=60)

    def test_invalid_model_result_digest_rejected_before_done(self):
        a = self.store.claim(self.tasks[0], "owner-A", now=100, ttl=60)
        with self.assertRaises(ValueError):
            self.store.complete(a, result_digest="broken", now=110)
        self.assertEqual(self.store.inspect()[0]["state"], "LEASED")

    def test_invalid_user_owned_db_symlink_refused(self):
        alias = self.root / "alias.sqlite3"
        try:
            alias.symlink_to(self.db_path)
        except (OSError, NotImplementedError):
            self.skipTest("Symlink support unavailable")
        with self.assertRaises(ValueError):
            LeaseStore(alias)

    def test_bad_clock_or_owner_rejected(self):
        with self.assertRaises(ValueError):
            self.store.claim(self.tasks[0], "bad shell ; token",
                             now=100, ttl=90)
        with self.assertRaises(ValueError):
            self.store.claim(self.tasks[0], "owner-A", now=-2, ttl=90)
        with self.assertRaises(ValueError):
            self.store.claim(self.tasks[0], "owner-A", now=100, ttl=5000)

    def test_owner_token_never_exposed_in_public_audit(self):
        lease = self.store.claim(self.tasks[0], "owner-A", now=100, ttl=60)
        status = json.dumps(self.store.inspect())
        self.assertNotIn(lease["token"], status)
        self.assertNotIn("private", status)
        self.assertNotIn("result_digest", status)

    def test_state_directory_optin_and_repo_guard(self):
        with patch.dict(os.environ, {"EDU_W38_PERSISTENT_LEASES": "0"}):
            with self.assertRaises(ValueError):
                authorized_state_db(str(self.root))
        with patch.dict(os.environ, {"EDU_W38_PERSISTENT_LEASES": "1"}):
            self.assertEqual(authorized_state_db(str(self.root)),
                             self.root / "autopilot-proposals.sqlite3")
            with self.assertRaises(ValueError):
                authorized_state_db(str(Path.cwd()))

    def test_integrated_real_os_children_resume_one_remaining_task_then_idle(self):
        from edu_workflow.autopilot_process_w33 import run
        with patch.dict(os.environ, {"EDU_W38_PERSISTENT_LEASES": "1"}):
            result = run(self.backlog, synthetic=True, state_dir=str(self.root))
            self.assertEqual(result["independent_os_processes"], 3)
            self.assertTrue(result["durable_state_enabled"])
            self.assertEqual(result["actual_ollama_calls"], 0)
            self.assertEqual(
                sum(x["state"]=="DONE" for x in LeaseStore(self.root /
                      "autopilot-proposals.sqlite3").inspect()), 3)
            second = run(self.backlog, synthetic=True, state_dir=str(self.root))
            self.assertEqual(second["independent_os_processes"], 1)
            self.assertEqual(second["unique_tasks_completed"], 1)
            third = run(self.backlog, synthetic=True, state_dir=str(self.root))
            self.assertEqual(third["status"], "IDLE_NO_APPROVED_READY_TASKS")
            self.assertEqual(third["actual_ollama_calls"], 0)
            self.assertEqual(
                sum(x["state"]=="DONE" for x in LeaseStore(self.root /
                    "autopilot-proposals.sqlite3").inspect()), 4)

    def test_integrated_failed_worker_keeps_completed_siblings_across_restart(self):
        from edu_workflow.autopilot_process_w33 import run
        with patch.dict(os.environ, {
            "EDU_W38_PERSISTENT_LEASES": "1",
            "EDU_W37_SYNTHETIC_FAIL_TASK": "W27-QA",
        }):
            first = run(self.backlog, synthetic=True, state_dir=str(self.root))
        self.assertEqual(first["failed_lanes_replaced"], 1)
        self.assertEqual(first["unique_tasks_completed"], 3)
        fresh = LeaseStore(self.root / "autopilot-proposals.sqlite3").inspect()
        by_id = {d["task_id"]:d for d in fresh}
        self.assertEqual(by_id["W27-DOCS"]["state"], "DONE")
        self.assertEqual(by_id["W27-UX"]["state"], "DONE")
        self.assertEqual(by_id["W27-LEASE"]["state"], "DONE")
        self.assertEqual(by_id["W27-QA"]["state"], "PENDING")
        self.assertEqual(by_id["W27-DOCS"]["attempts"], 1)
        with patch.dict(os.environ, {"EDU_W38_PERSISTENT_LEASES": "1"},
                        clear=False):
            with patch.dict(os.environ, {"EDU_W37_SYNTHETIC_FAIL_TASK": ""},
                            clear=False):
                second = run(self.backlog, synthetic=True, state_dir=str(self.root))
        self.assertEqual(second["unique_tasks_completed"], 1)
        status = LeaseStore(self.root / "autopilot-proposals.sqlite3").inspect()
        by_id = {d["task_id"]:d for d in status}
        self.assertEqual(by_id["W27-QA"]["state"], "DONE")
        self.assertEqual(by_id["W27-QA"]["attempts"], 2)
        self.assertEqual(by_id["W27-DOCS"]["attempts"], 1)

    def test_integrated_write_denied_without_state_optin(self):
        from edu_workflow.autopilot_process_w33 import run
        with patch.dict(os.environ, {"EDU_W38_PERSISTENT_LEASES": "0"}):
            with self.assertRaises(ValueError):
                run(self.backlog, synthetic=True, state_dir=str(self.root))
        self.assertFalse((self.root/"autopilot-proposals.sqlite3").exists())

    def test_restart_available_task_excludes_leased_and_done(self):
        now = 1000
        first = self.store.claim(self.tasks[0], "owner-A", now=now, ttl=60)
        second = self.store.claim(self.tasks[1], "owner-B", now=now, ttl=60)
        self.store.complete(second, result_digest=DIGEST, now=1001)
        self.assertNotIn("W27-DOCS", self.store.available_task_ids(now=1059))
        self.assertNotIn("W27-QA", self.store.available_task_ids(now=1100))
        self.assertIn("W27-DOCS", self.store.available_task_ids(now=1060))
        self.assertIn("W27-LEASE", self.store.available_task_ids(now=1060))

    def test_no_external_service_or_code_execution_in_staging(self):
        self.assertEqual(len(self.store.inspect()), 4)
        self.assertFalse(any("outlook" in item["task_id"].lower()
                             for item in self.store.inspect()))


if __name__ == "__main__":
    unittest.main()
