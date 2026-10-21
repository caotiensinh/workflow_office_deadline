"""Strict W31B offline regression cases: hold on unsafe or unverified bot PR."""
import os
import unittest
from unittest.mock import patch
from edu_workflow.autopilot_pr_gate_w31b import REPO, REQUIRED, gate, audit, main

SHA = 'e' * 40

def pr():
    return {"number": 61, "state": "open", "draft": False,
            "user": {"login": "github-actions[bot]"},
            "head": {"sha": SHA, "ref": "autopilot/w31-test", "repo": {"full_name": REPO}},
            "base": {"ref": "main", "repo": {"full_name": REPO}}}

def files():
    return [{"filename": "docs/autopilot-proposals/SMOKE.md", "status": "added",
             "patch": "@@ -0,0 +1 @@\n+Test", "additions": 1, "deletions": 0}]

def runs(sha=SHA, conclusion="success"):
    return [{"name": name, "head_sha": sha, "status": "completed",
             "conclusion": conclusion, "event": "push"} for name in REQUIRED]


class TestBotGates(unittest.TestCase):
    def test_proven_exact_head_still_requires_review(self):
        state = gate(pr(), files(), runs())
        self.assertTrue(state["exact_sha_ci"])
        self.assertFalse(state["auto_merge"])
        self.assertTrue(state["human_review_required"])

    def test_no_ci_is_hold(self):
        self.assertEqual(gate(pr(), files(), [])["status"], "HOLD_EXACT_SHA_CI_NOT_PROVEN")

    def test_action_required_is_not_pass(self):
        self.assertFalse(gate(pr(), files(), runs(conclusion="action_required"))["exact_sha_ci"])

    def test_wrong_sha_is_not_pass(self):
        self.assertFalse(gate(pr(), files(), runs(sha='a'*40))["exact_sha_ci"])

    def test_missing_one_required_check_fails(self):
        self.assertFalse(gate(pr(), files(), runs()[:-1])["exact_sha_ci"])

    def test_source_code_is_not_docs(self):
        f = files(); f[0]["filename"] = "python/edu_workflow/unsafe.py"
        self.assertEqual(gate(pr(), f, runs())["status"], "HOLD_INVALID_PR_OR_SCOPE")

    def test_oversize_patch_fails(self):
        f = files(); f[0]["patch"] = "@@" + 'x'*9000
        self.assertEqual(gate(pr(), f, runs())["status"], "HOLD_INVALID_PR_OR_SCOPE")

    def test_non_bot_fails(self):
        p = pr(); p["user"]["login"] = "caotiensinh"
        self.assertEqual(gate(p, files(), runs())["status"], "HOLD_INVALID_PR_OR_SCOPE")

    def test_non_main_target_fails(self):
        p = pr(); p["base"]["ref"] = "other"
        self.assertEqual(gate(p, files(), runs())["status"], "HOLD_INVALID_PR_OR_SCOPE")

    def test_draft_is_hold(self):
        p = pr(); p["draft"] = True
        self.assertEqual(gate(p, files(), runs())["status"], "HOLD_INVALID_PR_OR_SCOPE")

    def test_repeated_file_fails(self):
        self.assertEqual(gate(pr(), files()*2, runs())["status"], "HOLD_INVALID_PR_OR_SCOPE")

    def test_audit_read_only_transport(self):
        calls=[]
        def fake(path):
            calls.append(path)
            if '/pulls?' in path: return [pr()]
            if '/files?' in path: return files()
            return {"workflow_runs": runs()}
        with patch.dict(os.environ, {"GH_TOKEN":"fictional"}):
            report = audit(fetch=fake)
        self.assertEqual(report["total"], 1)
        self.assertEqual(len(calls), 3)
        self.assertFalse(report["remote_writes"])

    def test_no_opt_in_means_no_network(self):
        self.assertEqual(main([]),0)


if __name__ == '__main__':
    unittest.main()
