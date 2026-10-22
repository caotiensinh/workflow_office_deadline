"""W36: real NDJSON token-progress signal, no raw model-text heartbeat."""
import io
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from edu_workflow.autopilot_ollama_heartbeat_w36 import (
    Heartbeat, read_progress, stream_generate,
)
from edu_workflow.autopilot_process_w33 import _collect, cpu_transport, worker


def ndjson(*items):
    return b"".join(json.dumps(item).encode("utf-8") + b"\n" for item in items)


class DummyResponse(io.BytesIO):
    status = 200


class DummyOpener:
    def __init__(self, response):
        self.response = response
        self.calls = []
    def open(self, req, timeout):
        self.calls.append((req.full_url, req.get_method(), timeout))
        return self.response


def request():
    return {"model": "installed-small", "prompt": "fictional only",
            "stream": True, "keep_alive": 0,
            "format": "json", "options": {"num_gpu": 0, "num_thread": 2}}


class StreamHeartbeatW36(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name)

    def test_true_stream_reassembles_and_only_counts_real_token_chunks(self):
        a = DummyOpener(DummyResponse(ndjson(
            {"response": '{"task', "done": False},
            {"response": "", "done": False},
            {"response": '_id":"W27-QA"}', "done": False},
            {"response": "", "done": True}
        )))
        calls = []
        result = stream_generate(request(), progress=calls.append, opener=a)
        self.assertEqual(result["response"], '{"task_id":"W27-QA"}')
        self.assertEqual(calls, [1, 2])
        self.assertEqual(a.calls[0][0], "http://127.0.0.1:11434/api/generate")
        self.assertEqual(a.calls[0][1], "POST")

    def test_eof_without_done_marker_rejected(self):
        a = DummyOpener(DummyResponse(ndjson({"response": "hello", "done": False})))
        with self.assertRaises(ValueError):
            stream_generate(request(), opener=a)

    def test_done_with_zero_progress_rejected(self):
        a = DummyOpener(DummyResponse(ndjson({"response": "", "done": True})))
        with self.assertRaises(ValueError):
            stream_generate(request(), opener=a)

    def test_duplicate_json_keys_rejected(self):
        body = b'{"response":"one","response":"two","done":true}\n'
        with self.assertRaises(ValueError):
            stream_generate(request(), opener=DummyOpener(DummyResponse(body)))

    def test_untrusted_streamed_error_rejected_without_leaking_text(self):
        body = ndjson({"response": "", "error": "private model data", "done": True})
        with self.assertRaises(ValueError) as err:
            stream_generate(request(), opener=DummyOpener(DummyResponse(body)))
        self.assertNotIn("private", str(err.exception))

    def test_bad_chunk_type_rejected(self):
        body = ndjson({"response": ["unsafe"], "done": False})
        with self.assertRaises(ValueError):
            stream_generate(request(), opener=DummyOpener(DummyResponse(body)))

    def test_missing_done_type_rejected(self):
        body = ndjson({"response": "text", "done": "false"})
        with self.assertRaises(ValueError):
            stream_generate(request(), opener=DummyOpener(DummyResponse(body)))

    def test_single_giant_line_rejected(self):
        a = DummyOpener(DummyResponse(b'{"response":"' + b"x"*40000 + b'","done":true}\n'))
        with self.assertRaises(ValueError):
            stream_generate(request(), opener=a)

    def test_cpu_only_contract_blocks_gpu(self):
        req = dict(request(), options={"num_gpu": 1})
        with self.assertRaises(ValueError):
            stream_generate(req, opener=DummyOpener(DummyResponse()))

    def test_nonstream_and_keepalive_forbidden(self):
        for req in [dict(request(), stream=False), dict(request(), keep_alive=60)]:
            with self.subTest(req=req):
                with self.assertRaises(ValueError):
                    stream_generate(req, opener=DummyOpener(DummyResponse()))

    def test_worker_progress_heartbeat_numeric_only_and_completed(self):
        path = self.root / "worker-0.json"
        hb = Heartbeat(path)
        hb.progress(1)
        hb.progress(2)
        hb.completed()
        data = path.read_text()
        self.assertEqual(json.loads(data),
                         {"pid": os.getpid(), "chunks": 2, "state": "complete"})
        self.assertNotIn("model", data)
        self.assertNotIn("token", data)
        self.assertEqual(read_progress(path, os.getpid()), 2)
        self.assertEqual(read_progress(path, os.getpid() + 1), 0)

    def test_nonmonotonic_heartbeat_rejected(self):
        hb = Heartbeat(self.root / "hb.json")
        hb.progress(2)
        with self.assertRaises(ValueError):
            hb.progress(1)
        with self.assertRaises(ValueError):
            hb.progress(2)

    def test_completed_heartbeat_without_model_response_forbidden(self):
        hb = Heartbeat(self.root / "hb.json")
        with self.assertRaises(ValueError):
            hb.completed()

    def test_existing_heartbeat_file_not_overwritten(self):
        dest = self.root / "hb.json"
        dest.write_text("keep-owner-file")
        with self.assertRaises(ValueError):
            Heartbeat(dest)
        self.assertEqual(dest.read_text(), "keep-owner-file")

    def test_symlink_receipt_not_accepted(self):
        path = self.root / "real.json"
        hb = Heartbeat(path)
        hb.progress(1)
        link = self.root / "alias.json"
        try:
            link.symlink_to(path)
        except (OSError, NotImplementedError):
            self.skipTest("No symlink permission")
        self.assertEqual(read_progress(link, os.getpid()), 0)
        with self.assertRaises(ValueError):
            Heartbeat(link)

    def test_oversized_receipt_rejected(self):
        p = self.root / "fake.json"
        p.write_text("x" * 400)
        self.assertEqual(read_progress(p, os.getpid()), 0)

    def test_streaming_cpu_transport_forces_cpu_options(self):
        records = []
        with patch("edu_workflow.autopilot_process_w33.stream_generate",
                   side_effect=lambda payload, progress: records.append(payload)
                   or {"response": "{}"}):
            cpu_transport("/api/generate", {"model": "m", "prompt": "abc",
                                           "options": {"num_gpu": 10}},
                          progress=lambda _: None)
        self.assertTrue(records[0]["stream"])
        self.assertEqual(records[0]["options"]["num_gpu"], 0)
        self.assertEqual(records[0]["keep_alive"], 0)

    def test_real_worker_fails_without_private_heartbeat(self):
        t = {"id": "W27-QA", "domain": "qa-security", "kind": "AUTO_PROPOSAL",
             "approval_required": False, "title": "Synthetic task",
             "description": "Only fictional QA checks"}
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ValueError):
                worker(io.StringIO(json.dumps({"task": t, "model": "m:1"})),
                       io.StringIO(), synthetic=False)

    def test_worker_private_heartbeat_reaches_finished_after_mocked_stream(self):
        t = {"id": "W27-QA", "domain": "qa-security", "kind": "AUTO_PROPOSAL",
             "approval_required": False, "title": "Synthetic task",
             "description": "Only fictional QA checks"}
        model_response = json.dumps({
            "task_id": "W27-QA",
            "proposal": "A synthetic implementation proposal only, for review",
            "validation": "Run Python policy regression",
            "risks": [],
            "requires_human_review": True
        })
        heartbeat = self.root / "worker-1.json"
        output = io.StringIO()
        def stream_side_effect(payload, progress):
            progress(1)
            progress(2)
            return {"response": model_response}
        with patch.dict(os.environ, {"EDU_W36_HEARTBEAT_PATH": str(heartbeat)}):
            with patch("edu_workflow.autopilot_process_w33.stream_generate",
                       side_effect=stream_side_effect):
                worker(io.StringIO(json.dumps({"task": t, "model": "m:1"})),
                       output, synthetic=False)
        self.assertTrue(json.loads(output.getvalue())["human_review_required"])
        self.assertEqual(json.loads(heartbeat.read_text())["state"], "complete")
        self.assertEqual(read_progress(heartbeat, os.getpid()), 2)

    def test_real_parent_rejects_absent_progress(self):
        class FakeProc:
            returncode = 0
            pid = os.getpid()
            def communicate(self, data, timeout):
                result = {
                    "task_id":"W27-QA","role":"qa-security","model":"m",
                    "status":"AI_PROPOSED_PENDING_REVIEW",
                    "human_review_required":True,"execution_performed":False,
                    "git_push_performed":False,"production_accepted":False,
                    "proposal":"Synthetic code proposal, no network",
                    "validation":"Only synthetic checks","risks":[],
                    "worker_pid":os.getpid()
                }
                return json.dumps(result), ""
        with self.assertRaises(ValueError):
            _collect(FakeProc(), {"task":{}, "model":"m"}, self.root/"absent.json")

    def test_parent_accepts_positive_progress_from_private_matching_pid(self):
        path = self.root / "hb.json"
        hb = Heartbeat(path)
        hb.progress(1)
        hb.completed()
        class FakeProc:
            returncode = 0
            pid = os.getpid()
            def communicate(self, data, timeout):
                return json.dumps({
                    "task_id":"W27-QA","role":"qa-security","model":"m",
                    "status":"AI_PROPOSED_PENDING_REVIEW",
                    "human_review_required":True,"execution_performed":False,
                    "git_push_performed":False,"production_accepted":False,
                    "proposal":"Synthetic proposal for test only",
                    "validation":"Test only","risks":[],"worker_pid":os.getpid()
                }), ""
        self.assertEqual(_collect(FakeProc(), {"task":{}, "model":"m"}, path)["worker_pid"],
                         os.getpid())


if __name__ == "__main__":
    unittest.main()
