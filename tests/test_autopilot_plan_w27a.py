"""W27A autonomous *planner* boundaries; no model/host is invoked by tests."""
import json
import tempfile
import unittest
from pathlib import Path

from edu_workflow.autopilot_plan_w27 import (
    REQUIRED_CI, evaluate_merge, load_backlog, main, plan,
)


def task(kind="AUTO_PROPOSAL"):
    return {
        "id": "W27-TEST", "title": "Propose fictional reference documentation",
        "domain": "documentation", "kind": kind,
        "approval_required": kind == "BLOCKED_EXTERNAL",
        "description": "Only synthetic, no production changes or human signoff",
    }


def evidence():
    sha = "a"*40
    return {
        "head_sha": sha, "base_branch": "main", "human_gate": False,
        "changed_files": ["docs/PHASE_W27.md"],
        "checks": [
            {"name": n, "head_sha": sha, "status": "completed", "conclusion": "success"}
            for n in sorted(REQUIRED_CI)
        ],
    }


class W27APlanTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.src = Path(self.tmp.name) / "backlog.json"
        self.save([task()])

    def save(self, tasks):
        self.src.write_text(json.dumps({"schema": 1, "tasks": tasks}), encoding="utf-8")

    def test_plans_only_not_actual_agent(self):
        r = plan(load_backlog(self.src))
        self.assertEqual(r["status"], "PLANNED_ONLY_NOT_RUNNING_AGENTS")
        self.assertEqual(r["agents_spawned"], 0)
        self.assertEqual(r["model_calls_executed"], 0)
        self.assertFalse(r["production_accepted"])

    def test_blocked_external_cannot_be_dispatched(self):
        self.save([task("BLOCKED_EXTERNAL")])
        r = plan(load_backlog(self.src))
        self.assertEqual(len(r["auto_proposals"]), 0)
        self.assertEqual(len(r["blocked_external"]), 1)

    def test_rejects_forged_approval_mode(self):
        bad = task("BLOCKED_EXTERNAL")
        bad["approval_required"] = False
        self.save([bad])
        with self.assertRaises(ValueError): load_backlog(self.src)

    def test_rejects_duplicate_id(self):
        self.save([task(), task()])
        with self.assertRaises(ValueError): load_backlog(self.src)

    def test_rejects_unknown_field(self):
        bad = task()
        bad["accept_production"] = True
        self.save([bad])
        with self.assertRaises(ValueError): load_backlog(self.src)

    def test_duplicate_json_keys_rejected(self):
        self.src.write_text('{"schema":1,"schema":1,"tasks":[]}',encoding="utf-8")
        with self.assertRaises(ValueError): load_backlog(self.src)

    def test_symlink_rejected(self):
        link = Path(self.tmp.name) / "link.json"
        try: link.symlink_to(self.src)
        except (OSError, NotImplementedError): self.skipTest("No symlink support")
        with self.assertRaises(ValueError): load_backlog(link)

    def test_unknown_domain_fails(self):
        bad = task()
        bad["domain"] = "send-real-outlook"
        self.save([bad])
        with self.assertRaises(ValueError): load_backlog(self.src)

    def test_docs_only_exact_four_successes_can_recommend_review(self):
        r = evaluate_merge(evidence())
        self.assertTrue(r["eligible_for_docs_only_merge"])
        self.assertFalse(r["is_actual_merge"])

    def test_code_or_workflow_change_never_auto_merges(self):
        for path in ("python/edu_workflow/cli.py", ".github/workflows/ci.yml",
                     "windows/run_once.ps1", "docs/../python/x.py"):
            x = evidence()
            x["changed_files"] = [path]
            with self.subTest(path=path):
                self.assertFalse(evaluate_merge(x)["eligible_for_docs_only_merge"])

    def test_sha_mismatch_or_missing_ci_holds(self):
        for kind in ("sha", "missing", "not-success"):
            x = evidence()
            if kind == "sha": x["checks"][1]["head_sha"] = "b"*40
            elif kind == "missing": x["checks"].pop()
            else: x["checks"][1]["conclusion"] = "failure"
            with self.subTest(kind=kind):
                self.assertEqual(evaluate_merge(x)["status"], "HOLD")

    def test_human_gate_blocks_even_docs(self):
        x = evidence()
        x["human_gate"] = True
        self.assertFalse(evaluate_merge(x)["eligible_for_docs_only_merge"])

    def test_cli_plan_synthetic(self):
        self.assertEqual(main(["--backlog",str(self.src)]),0)

    def test_cli_invalid_file_fails_closed(self):
        self.src.unlink()
        self.assertEqual(main(["--backlog",str(self.src)]),2)


if __name__ == "__main__":
    unittest.main()
