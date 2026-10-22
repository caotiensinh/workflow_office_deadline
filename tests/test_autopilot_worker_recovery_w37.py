"""W37: independent-worker fault isolation and one safe successor dispatch."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from edu_workflow.autopilot_worker_recovery_w37 import execute_lanes
from edu_workflow.autopilot_process_w33 import launch, run


def task(identifier, domain="documentation", *, allowed=True):
    return {
        "id": identifier, "domain": domain,
        "title": "Fictional workflow QA proposal",
        "description": "Review safe synthetic office event boundaries",
        "kind": "AUTO_PROPOSAL" if allowed else "BLOCKED_EXTERNAL",
        "approval_required": not allowed,
    }


PRIMARY = [task("W27-DOCS"), task("W27-QA", "qa-security"),
           task("W27-UX", "ui")]
ALTERNATES = [task("W27-EXTRA", "qa-security"),
              task("W27-ALT", "documentation")]


class W37Supervisor(unittest.TestCase):
    def test_three_successful_lanes_have_no_extra_spawn(self):
        calls = []
        def spawn(t, model, lane, round_num):
            calls.append((t["id"], lane, round_num))
            return {"task": t, "model": model}
        def collect(p):
            return {"task_id": p["task"]["id"]}
        output, recovered = execute_lanes(
            PRIMARY, ["a", "b", "c"], ALTERNATES,
            spawn=spawn, collect=collect)
        self.assertEqual(len(output), 3)
        self.assertEqual(recovered, [])
        self.assertEqual(len(calls), 3)

    def test_initial_three_launch_before_collection_and_keep_siblings(self):
        started, completed = [], []
        def spawn(t, model, lane, round_num):
            started.append((t["id"], round_num))
            return {"id": t["id"], "round": round_num}
        def collect(p):
            completed.append(p["id"])
            if p["id"] == "W27-QA":
                raise ValueError("one OS worker exited")
            return p
        results, replaced = execute_lanes(
            PRIMARY, ["a", "b", "c"], ALTERNATES,
            spawn=spawn, collect=collect)
        self.assertEqual(len(started), 4)
        self.assertEqual(results[0][0]["id"], "W27-DOCS")
        self.assertEqual(results[1][0]["id"], "W27-EXTRA")
        self.assertEqual(results[2][0]["id"], "W27-UX")
        self.assertEqual([x["id"] for x in completed].count("W27-DOCS"), 1)
        self.assertEqual([x["id"] for x in completed].count("W27-UX"), 1)
        self.assertEqual(replaced, [{"failed_task_id": "W27-QA",
                                     "replacement_task_id": "W27-EXTRA"}])

    def test_two_failed_lanes_get_two_distinct_new_tasks(self):
        def spawn(t, m, lane, round_num):
            return {"id": t["id"]}
        def collect(p):
            if p["id"] in ("W27-DOCS", "W27-QA"):
                raise ValueError("child crash")
            return p
        results, replacements = execute_lanes(
            PRIMARY, ["a", "b", "c"], ALTERNATES,
            spawn=spawn, collect=collect)
        self.assertEqual(len(results), 3)
        self.assertEqual({x[0]["id"] for x in results},
                         {"W27-EXTRA", "W27-ALT", "W27-UX"})
        self.assertEqual(len(replacements), 2)

    def test_no_alternate_is_fail_closed_not_success(self):
        def spawn(t,m,l,r): return t
        def collect(t):
            if t["id"] == "W27-QA":
                raise ValueError("dead process")
            return t
        with self.assertRaisesRegex(ValueError, "No distinct authorized"):
            execute_lanes(PRIMARY, ["a", "b", "c"], [],
                          spawn=spawn, collect=collect)

    def test_only_one_retry_for_new_task(self):
        attempted = []
        def spawn(t,m,l,r):
            attempted.append((t["id"], r))
            return t
        def collect(t):
            if t["id"] in ("W27-QA", "W27-EXTRA"):
                raise ValueError("both failed")
            return t
        with self.assertRaisesRegex(ValueError, "no infinite retries"):
            execute_lanes(PRIMARY, ["a", "b", "c"], ALTERNATES,
                          spawn=spawn, collect=collect)
        self.assertEqual(len(attempted), 4)
        self.assertNotIn(("W27-ALT", 2), attempted)

    def test_blocked_external_alternate_is_never_dispatched(self):
        with self.assertRaises(ValueError):
            execute_lanes(PRIMARY, ["a", "b", "c"],
                          [task("W27-IT", allowed=False)],
                          spawn=lambda *args: self.fail("must not spawn"),
                          collect=lambda _: {})

    def test_duplicate_alternate_identity_is_never_dispatched(self):
        with self.assertRaises(ValueError):
            execute_lanes(PRIMARY, ["a", "b", "c"],
                          [task("W27-DOCS")],
                          spawn=lambda *args: self.fail("must not spawn"),
                          collect=lambda _: {})

    def test_duplicate_models_are_never_dispatched(self):
        with self.assertRaises(ValueError):
            execute_lanes(PRIMARY, ["a", "a", "b"], [],
                          spawn=lambda *args: self.fail("must not spawn"),
                          collect=lambda _: {})

    def test_no_hidden_extra_task_if_all_three_finish(self):
        output, replacements = execute_lanes(
            PRIMARY, ["a", "b", "c"], ALTERNATES,
            spawn=lambda t,m,l,r: t,
            collect=lambda t: t)
        self.assertEqual([x[0]["id"] for x in output],
                         [x["id"] for x in PRIMARY])
        self.assertEqual(replacements, [])

    def test_failures_never_send_exception_text_to_report(self):
        def fail(_):
            raise ValueError("private user model token and filesystem path")
        with self.assertRaisesRegex(ValueError, "No distinct authorized") as cm:
            execute_lanes(PRIMARY, ["a", "b", "c"], [],
                          spawn=lambda t,m,l,r: t, collect=fail)
        self.assertNotIn("private user model", str(cm.exception))

    def test_real_three_subprocess_synthetic_fault_preserves_good_pids(self):
        with patch.dict(os.environ, {"EDU_W37_SYNTHETIC_FAIL_TASK": "W27-QA"}):
            outputs = launch(PRIMARY, ["fixture:a", "fixture:b", "fixture:c"],
                             synthetic=True, alternatives=ALTERNATES)
        self.assertEqual(len(outputs), 3)
        self.assertEqual({r["task_id"] for r in outputs},
                         {"W27-DOCS", "W27-EXTRA", "W27-UX"})
        self.assertEqual(len({r["worker_pid"] for r in outputs}), 3)
        self.assertTrue(all(r["human_review_required"] for r in outputs))
        self.assertTrue(all(r["execution_performed"] is False for r in outputs))

    def test_real_os_failed_slot_with_no_approved_next_task_returns_failure(self):
        with patch.dict(os.environ, {"EDU_W37_SYNTHETIC_FAIL_TASK": "W27-QA"}):
            with self.assertRaisesRegex(ValueError, "No distinct authorized"):
                launch(PRIMARY, ["fixture:a", "fixture:b", "fixture:c"],
                       synthetic=True, alternatives=[])

    def test_backlog_dispatch_does_not_count_fixture_as_real_model(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "tasks.json"
            path.write_text(json.dumps({
                "schema": 1, "tasks": PRIMARY + ALTERNATES
            }), encoding="utf-8")
            with patch.dict(os.environ, {
                "EDU_W37_SYNTHETIC_FAIL_TASK": "W27-QA"}):
                output = run(path, synthetic=True)
        self.assertEqual(output["failed_lanes_replaced"], 1)
        self.assertEqual(output["unique_tasks_completed"], 3)
        self.assertEqual(output["actual_ollama_calls"], 0)
        self.assertEqual(
            output["status"], "THREE_SYNTHETIC_OS_PROCESSES_NOT_REAL_OLLAMA")
        self.assertFalse(output["git_writes"])
        self.assertFalse(output["production_accepted"])


if __name__ == "__main__":
    unittest.main()
