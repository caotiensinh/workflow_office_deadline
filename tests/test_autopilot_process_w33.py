"""W33: three independent OS process smoke + strict fail-closed boundaries."""
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from edu_workflow.autopilot_process_w33 import (
    SYNTHETIC_MODELS, cpu_transport, fake_ollama, launch, main, run, worker,
)

GIB = 1024**3


class W33ProcessAcceptance(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.backlog = Path(temp.name) / "backlog.json"
        self.tasks = [
            {"id": "W27-" + key, "title": "Synthetic proposal " + key,
             "description": "Review fictional school office content only",
             "domain": domain, "kind": "AUTO_PROPOSAL",
             "approval_required": False}
            for key, domain in [
                ("DOCS", "documentation"),
                ("QA", "qa-security"),
                ("UX", "ui"),
            ]
        ]
        self.write(self.tasks)

    def write(self, tasks):
        self.backlog.write_text(json.dumps({"schema": 1, "tasks": tasks}),
                                encoding="utf-8")

    def test_actual_os_child_processes_synthetic_receipt(self):
        result = run(self.backlog, synthetic=True)
        self.assertEqual(result["independent_os_processes"], 3)
        self.assertEqual(result["actual_ollama_calls"], 0)
        self.assertEqual(result["status"],
                         "THREE_SYNTHETIC_OS_PROCESSES_NOT_REAL_OLLAMA")
        self.assertEqual(len(result["proposal_hashes"]), 3)
        self.assertFalse(result["git_writes"])
        self.assertFalse(result["model_authored_code_executed"])
        self.assertFalse(result["production_accepted"])
        self.assertTrue(result["human_review_required"])

    def test_synthetic_launch_produces_three_distinct_pids(self):
        values = launch(self.tasks, [x[0] for x in SYNTHETIC_MODELS], synthetic=True)
        self.assertEqual(len({r["worker_pid"] for r in values}), 3)
        self.assertEqual([r["task_id"] for r in values],
                         [t["id"] for t in self.tasks])
        self.assertTrue(all(r["human_review_required"] for r in values))

    def test_real_transport_forces_cpu_only(self):
        captured = []
        def fake(route, payload):
            captured.append((route, payload))
            return {"response": "{}"}
        with patch("edu_workflow.autopilot_process_w33.local_ollama", fake):
            cpu_transport("/api/generate", {
                "model": "already-installed", "prompt": "fictional",
                "options": {"num_gpu": 999}, "keep_alive": "6h"})
        self.assertEqual(captured[0][0], "/api/generate")
        self.assertEqual(captured[0][1]["options"]["num_gpu"], 0)
        self.assertEqual(captured[0][1]["options"]["num_thread"], 2)
        self.assertEqual(captured[0][1]["options"]["num_ctx"], 1024)
        self.assertEqual(captured[0][1]["keep_alive"], 0)

    def test_other_routes_rejected_before_any_network(self):
        with self.assertRaises(ValueError):
            cpu_transport("/api/pull", {})

    def test_worker_bad_payload_fails(self):
        with self.assertRaises(ValueError):
            worker(io.StringIO('{"task":{}}'), io.StringIO(), synthetic=True)

    def test_worker_cannot_accept_blocked_external(self):
        task = dict(self.tasks[0], kind="BLOCKED_EXTERNAL",
                    approval_required=True)
        with self.assertRaises(ValueError):
            worker(io.StringIO(json.dumps({"task": task, "model": "fake"})),
                   io.StringIO(), synthetic=True)

    def test_worker_rejects_unsafe_model_string(self):
        with self.assertRaises(ValueError):
            worker(io.StringIO(json.dumps({
                "task": self.tasks[0], "model": "m; echo exploit"})),
                io.StringIO(), synthetic=True)

    def test_worker_synthetic_returns_review_required_receipt(self):
        dest = io.StringIO()
        worker(io.StringIO(json.dumps({
            "task": self.tasks[0], "model": "w33-test-a"
        })), dest, synthetic=True)
        result = json.loads(dest.getvalue())
        self.assertFalse(result["execution_performed"])
        self.assertTrue(result["human_review_required"])
        self.assertGreater(result["worker_pid"], 0)

    def test_synthetic_ollama_is_explicit_fixture_not_live(self):
        payload = {"prompt": "ROLE: ui\nTASK_ID: W27-QA\nTITLE: fictional"}
        data = json.loads(fake_ollama("/api/generate", payload)["response"])
        self.assertIn("Synthetic-only", data["proposal"])
        self.assertEqual(data["task_id"], "W27-QA")

    def test_requires_three_authorized_backlog_tasks(self):
        self.write(self.tasks[:2])
        with self.assertRaises(ValueError):
            run(self.backlog, synthetic=True)

    def test_external_task_is_not_dispatched(self):
        blocked = dict(self.tasks[2], kind="BLOCKED_EXTERNAL",
                       approval_required=True)
        self.write(self.tasks[:2] + [blocked])
        with self.assertRaises(ValueError):
            run(self.backlog, synthetic=True)

    def test_rejects_duplicate_model(self):
        with self.assertRaises(ValueError):
            launch(self.tasks, ["a", "a", "c"], synthetic=True)

    def test_real_admission_requires_three_small_installed_models(self):
        with self.assertRaises(ValueError):
            run(self.backlog, transport=lambda _: {
                "models": [{"name": "too-big:latest", "size": 8*GIB}]} ,
                meminfo="MemAvailable:       30000000 kB\n", load=0, cores=8)

    def test_real_admission_rejects_cpu_overload(self):
        tags = {"models": [{"name": k, "size": 2*GIB}
                           for k in ("model:a", "model:b", "model:c")]}
        with self.assertRaises(ValueError):
            run(self.backlog, transport=lambda _: tags,
                meminfo="MemAvailable:       30000000 kB\n",
                load=7.8, cores=8)

    def test_dryrun_performs_zero_processes(self):
        stream = io.StringIO()
        with patch("sys.stdout", stream):
            self.assertEqual(main(["--backlog", str(self.backlog)]), 0)
        data = json.loads(stream.getvalue())
        self.assertEqual(data["actual_ollama_calls"], 0)

    def test_synthetic_mode_requires_distinct_optin(self):
        with patch.dict(os.environ, {"EDU_W33_SYNTHETIC": "0"}):
            self.assertEqual(main(["--execute", "--synthetic",
                                   "--backlog", str(self.backlog)]), 2)

    def test_hosted_cli_three_os_processes_never_claim_ollama(self):
        stream = io.StringIO()
        with patch.dict(os.environ, {"EDU_W33_SYNTHETIC": "1"}):
            with patch("sys.stdout", stream):
                self.assertEqual(main(["--execute", "--synthetic",
                                       "--backlog", str(self.backlog)]), 0)
        result = json.loads(stream.getvalue())
        self.assertEqual(result["independent_os_processes"], 3)
        self.assertEqual(result["actual_ollama_calls"], 0)

    def test_true_real_mode_rejects_synthetic_flag_env(self):
        with patch.dict(os.environ, {
            "EDU_AUTOPILOT_ENABLE": "1",
            "EDU_AUTOPILOT_THREE_CPU_PROPOSALS": "1",
            "EDU_W33_SYNTHETIC": "1",
        }):
            self.assertEqual(main(["--execute", "--backlog",
                                   str(self.backlog)]), 2)


if __name__ == "__main__":
    unittest.main()
