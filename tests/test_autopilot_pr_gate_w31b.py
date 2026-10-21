"""Strict W31B offline regression cases: hold on unsafe or unverified bot PR."""
import os
import unittest
from unittest.mock import patch
from edu_workflow.autopilot_pr_gate_w31b import REPO, REQUIRED, TRUSTED_WORKFLOWS, gate, audit, main

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
    rows = []
    for index, name in enumerate(sorted(REQUIRED)):
        workflow_id, path = TRUSTED_WORKFLOWS[name]
        rows.append({"id": 300000 + index, "run_attempt": 1,
                     "name": name, "workflow_id": workflow_id, "path": path,
                     "head_sha": sha, "head_branch": "autopilot/w31-test",
                     "status": "completed", "conclusion": conclusion,
                     "event": "workflow_dispatch",
                     "repository": {"full_name": REPO},
                     "head_repository": {"full_name": REPO},
                     "actor": {"login": "github-actions[bot]"}})
    return rows

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

    def test_forged_same_name_different_workflow_id_is_hold(self):
        value = runs()
        value[0]["workflow_id"] += 1
        self.assertFalse(gate(pr(), files(), value)["exact_sha_ci"])

    def test_workflow_path_mismatch_is_hold(self):
        value = runs()
        value[0]["path"] = ".github/workflows/attacker.yml"
        self.assertFalse(gate(pr(), files(), value)["exact_sha_ci"])

    def test_wrong_event_is_hold(self):
        value = runs()
        value[0]["event"] = "pull_request"
        self.assertFalse(gate(pr(), files(), value)["exact_sha_ci"])

    def test_wrong_actor_is_hold(self):
        value = runs()
        value[0]["actor"]["login"] = "untrusted-user"
        self.assertFalse(gate(pr(), files(), value)["exact_sha_ci"])

    def test_wrong_run_repository_is_hold(self):
        value = runs()
        value[0]["repository"]["full_name"] = "elsewhere/repo"
        self.assertFalse(gate(pr(), files(), value)["exact_sha_ci"])

    def test_wrong_head_repository_is_hold(self):
        value = runs()
        value[0]["head_repository"]["full_name"] = "elsewhere/repo"
        self.assertFalse(gate(pr(), files(), value)["exact_sha_ci"])

    def test_wrong_branch_is_hold(self):
        value = runs()
        value[0]["head_branch"] = "autopilot/stale"
        self.assertFalse(gate(pr(), files(), value)["exact_sha_ci"])

    def test_missing_workflow_provenance_is_hold(self):
        value = runs()
        del value[0]["workflow_id"]
        self.assertFalse(gate(pr(), files(), value)["exact_sha_ci"])

    def test_newer_failed_run_supersedes_older_green(self):
        value = runs()
        failed = dict(value[0])
        failed["id"] = value[0]["id"] + 100
        failed["conclusion"] = "failure"
        value.append(failed)
        self.assertFalse(gate(pr(), files(), value)["exact_sha_ci"])

    def test_newer_pending_run_supersedes_older_green(self):
        value = runs()
        pending = dict(value[0])
        pending["id"] = value[0]["id"] + 100
        pending["status"] = "in_progress"
        pending["conclusion"] = None
        value.append(pending)
        self.assertFalse(gate(pr(), files(), value)["exact_sha_ci"])

    def test_retried_attempt_failure_overrides_initial_success(self):
        value = runs()
        retry = dict(value[0])
        retry["run_attempt"] = 2
        retry["conclusion"] = "failure"
        value.append(retry)
        self.assertFalse(gate(pr(), files(), value)["exact_sha_ci"])

    def test_latest_authorized_success_wins_against_old_fail(self):
        value = runs()
        older = dict(value[0])
        older["id"] = value[0]["id"] - 20
        older["conclusion"] = "failure"
        value.append(older)
        self.assertTrue(gate(pr(), files(), value)["exact_sha_ci"])

    def test_workflow_id_string_is_not_accepted(self):
        value = runs()
        value[0]["workflow_id"] = str(value[0]["workflow_id"])
        self.assertFalse(gate(pr(), files(), value)["exact_sha_ci"])


if __name__ == '__main__':
    unittest.main()
