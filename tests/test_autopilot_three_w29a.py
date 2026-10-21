"""W29A offline admission and concurrent inference checks."""
import json
import os
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch
from edu_workflow.autopilot_probe_w28a import GIB
from edu_workflow.autopilot_three_w29a import select_three_models, admit, run, main

def inventory():
    return {"models":[{"name":"tiny1:latest","size":1*GIB},{"name":"tiny2:latest","size":2*GIB},
                      {"name":"tiny3:latest","size":3*GIB},{"name":"heavy:latest","size":9*GIB}]}

def example(ident):
    return {"id":ident,"title":"Fictional review of institutional operator docs",
            "description":"Plan synthetic-only improvements for later human code review",
            "domain":"documentation","kind":"AUTO_PROPOSAL","approval_required":False}

class W29AResourceAndWorkerTests(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.root=Path(t.name)
        self.backlog=self.root/"backlog.json"
        self.backlog.write_text(json.dumps({"schema":1,"tasks":[example("W27-A01"),example("W27-A02"),example("W27-A03")]}))

    def test_bounded_small_models_only(self):
        self.assertEqual([x[0] for x in select_three_models(inventory())],["tiny1:latest","tiny2:latest","tiny3:latest"])

    def test_missing_model_fails(self):
        with self.assertRaises(ValueError):select_three_models({"models":[{"name":"one","size":GIB}]})

    def test_duplicate_models_fails(self):
        with self.assertRaises(ValueError):admit([("same",GIB)]*3,24*GIB,0,16)

    def test_memory_bound(self):
        with self.assertRaises(ValueError):admit(select_three_models(inventory()),10*GIB,0,16)

    def test_cpu_bound(self):
        with self.assertRaises(ValueError):admit(select_three_models(inventory()),24*GIB,9,16)

    def test_minimum_cpu_count(self):
        with self.assertRaises(ValueError):admit(select_three_models(inventory()),24*GIB,0,4)

    def test_three_concurrent_distinct_models_and_no_public_proposal(self):
        barrier=threading.Barrier(3,timeout=7)
        seen=[]
        lock=threading.Lock()
        def fake(route,payload=None):
            if route=="/api/tags":return inventory()
            self.assertEqual(route,"/api/generate")
            self.assertEqual(payload["options"]["num_gpu"],0)
            self.assertEqual(payload["options"]["num_thread"],2)
            self.assertEqual(payload["keep_alive"],0)
            with lock:seen.append((threading.get_ident(),payload["model"]))
            barrier.wait()
            ident=payload["prompt"].split("TASK_ID: ")[1].split("\n")[0]
            return {"response":json.dumps({"task_id":ident,"proposal":"Fictional documentation change proposal only.",
                    "validation":"Validate using synthetic cases and CI.","risks":[],
                    "requires_human_review":True})}
        report=run(self.backlog,fake,"MemAvailable: 24000000 kB\n",0,16)
        self.assertEqual(report["actual_model_calls"],3)
        self.assertEqual(len({x[0] for x in seen}),3)
        self.assertEqual(len({x[1] for x in seen}),3)
        self.assertFalse(report["independent_processes_proven"])
        self.assertFalse(report["github_write"])
        self.assertNotIn("proposal",json.dumps(report).replace("proposal_hashes","hashes"))

    def test_dryrun_never_connects(self):
        self.assertEqual(main(["--backlog",str(self.backlog)],transport=lambda *_:self.fail("Unexpected network")),0)

    def test_live_explicit_optin_required(self):
        with patch.dict(os.environ,{"EDU_AUTOPILOT_ENABLE":"0","EDU_AUTOPILOT_THREE_CPU_PROPOSALS":"0"}):
            self.assertEqual(main(["--backlog",str(self.backlog),"--execute"],
                                  transport=lambda *_:self.fail("Unexpected network")),2)

    def test_corrupt_response_does_not_pass(self):
        def malformed(route,payload=None):
            if route=="/api/tags":return inventory()
            return {"response":'{"unexpected": true}'}
        with self.assertRaises(ValueError):
            run(self.backlog,malformed,"MemAvailable: 24000000 kB\n",0,16)

if __name__=="__main__":
    unittest.main()
