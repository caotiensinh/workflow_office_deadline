"""W27B local-model parallel proposal workers; no external Ollama required in CI."""
import json
import os
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from edu_workflow.autopilot_worker_w27 import (
    NoRedirect, choose_models, dispatch, local_ollama, main, proposed_task,
    safe_output_dir, safe_tasks,
)


def task(id,domain="documentation",blocked=False):
    return {
        "id": id, "title": "Prepare fictional safe review proposal",
        "description": "Generate a proposal with no production side effects or API",
        "domain":domain,"kind":"BLOCKED_EXTERNAL" if blocked else "AUTO_PROPOSAL",
        "approval_required":blocked
    }


class WorkerW27BTests(unittest.TestCase):
    def setUp(self):
        self.dir=tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.root=Path(self.dir.name)
        self.backlog=self.root/"tasks.json"
        self.save([task("W27-TEST")])

    def save(self,tasks):
        self.backlog.write_text(json.dumps({"schema":1,"tasks":tasks}),encoding="utf-8")

    @staticmethod
    def fake(route,payload=None):
        if route=="/api/tags":
            return {"models":[{"name":"qwen3-coder:30b"},{"name":"qwen3:30b"}]}
        assert route=="/api/generate"
        ident=payload["prompt"].split("TASK_ID: ")[1].split("\n")[0]
        return {"response":json.dumps({
            "task_id":ident,
            "proposal":"Suggest a fictional-only documentation section with regression coverage.",
            "validation":"Run Python tests and verify the existing audit requirements.",
            "risks":["Human review mandatory"],"requires_human_review":True
        })}

    def test_default_dry_run_no_model_access(self):
        def never(*args,**kwargs):
            self.fail("Ollama must not be contacted during dry run")
        self.assertEqual(main(["--backlog",str(self.backlog)],transport=never),0)

    def test_blocked_tasks_never_dispatched(self):
        tasks=[task("W27-EXT",blocked=True),task("W27-TEST")]
        result=dispatch(tasks,["qwen3-coder:30b"],self.fake)
        self.assertEqual(len(result),1)
        self.assertEqual(result[0]["task_id"],"W27-TEST")

    def test_real_three_independent_inference_calls_concurrent(self):
        tasks=[task("W27-ONE"),task("W27-TWO","ui"),task("W27-THREE","qa-security")]
        wait=threading.Barrier(3,timeout=6)
        called=[]
        lock=threading.Lock()
        def concurrent(route,payload):
            with lock:called.append(threading.get_ident())
            wait.wait()
            return self.fake(route,payload)
        r=dispatch(tasks,["qwen3-coder:30b"],concurrent)
        self.assertEqual(len(set(called)),3)
        self.assertEqual(len(r),3)
        self.assertTrue(all(x["human_review_required"] for x in r))
        self.assertTrue(all(not x["execution_performed"] and not x["git_push_performed"] for x in r))

    def test_model_must_keep_human_review(self):
        def unsafe(route,payload):
            response=self.fake(route,payload)
            data=json.loads(response["response"])
            data["requires_human_review"]=False
            return {"response":json.dumps(data)}
        with self.assertRaises(ValueError):
            dispatch([task("W27-TEST")],["qwen3-coder:30b"],unsafe)

    def test_model_identity_mismatch_rejected(self):
        def unsafe(route,payload):
            data=json.loads(self.fake(route,payload)["response"])
            data["task_id"]="W27-OTHER"
            return {"response":json.dumps(data)}
        with self.assertRaises(ValueError):
            proposed_task(task("W27-TEST"),"qwen3-coder:30b",unsafe)

    def test_no_arbitrary_model_endpoint(self):
        with self.assertRaises(ValueError):
            local_ollama("/admin/delete")

    def test_redirect_rejected(self):
        with self.assertRaises(ValueError):
            NoRedirect().redirect_request(None,None,302,"Redirect",{}, "https://external.invalid")

    def test_models_selected_from_installed_list(self):
        result=choose_models({"models":[{"name":"glm-4.7:latest"},
                                                {"name":"qwen3-coder:30b"},
                                                {"name":"qwen2.5-coder:7b"}]})
        self.assertEqual(result[0],"qwen3-coder:30b")
        self.assertEqual(len(result),3)

    def test_unexpected_model_paths_ignored(self):
        with self.assertRaises(ValueError):
            choose_models({"models":[{"name":"https://evil.invalid/"}]})

    def test_no_auto_download_or_mock_without_enable(self):
        self.assertEqual(main(["--backlog",str(self.backlog),
                               "--execute","--output-dir",str(self.root)],
                              transport=self.fake),2)

    def test_execute_creates_only_ephemeral_proposal(self):
        with patch.dict(os.environ,{"EDU_AUTOPILOT_ENABLE":"1", "RUNNER_TEMP":tempfile.gettempdir()}):
            code=main(["--backlog",str(self.backlog),"--execute",
                       "--output-dir",str(self.root)],transport=self.fake)
        self.assertEqual(code,0)
        proposal=json.loads((self.root/"W27-TEST.proposal.json").read_text(encoding="utf-8"))
        self.assertTrue(proposal["human_review_required"])
        self.assertFalse(proposal["production_accepted"])
        self.assertFalse(proposal["git_push_performed"])

    def test_second_execute_refuses_to_overwrite(self):
        with patch.dict(os.environ,{"EDU_AUTOPILOT_ENABLE":"1", "RUNNER_TEMP":tempfile.gettempdir()}):
            args=["--backlog",str(self.backlog),"--execute","--output-dir",str(self.root)]
            self.assertEqual(main(args,transport=self.fake),0)
            self.assertEqual(main(args,transport=self.fake),2)

    def test_repo_output_is_refused(self):
        with self.assertRaises(ValueError):
            safe_output_dir(Path(__file__).parent)

    def test_symlink_backlog_denied(self):
        link=self.root/"link.json"
        try:link.symlink_to(self.backlog)
        except (OSError,NotImplementedError):self.skipTest("No symlink")
        with self.assertRaises(ValueError):safe_tasks(link)

    def test_invalid_task_gate_rejected(self):
        t=task("W27-TEST",blocked=True)
        t["approval_required"]=False
        self.save([t])
        with self.assertRaises(ValueError):safe_tasks(self.backlog)

    def test_invalid_response_json_rejected(self):
        with self.assertRaises(ValueError):
            proposed_task(task("W27-TEST"),"qwen3",lambda *_:{"response":"not JSON"})


if __name__=="__main__":
    unittest.main()
