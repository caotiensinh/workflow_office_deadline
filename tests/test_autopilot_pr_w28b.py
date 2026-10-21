"""W28B safe deterministic docs-only staging, no actual GitHub PR side effects."""
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch
from edu_workflow.autopilot_pr_w28b import (
    MAGIC, OWNED_PATH, escape_content, main, prepare, render
)
from edu_workflow.autopilot_plan_w27 import load_backlog


class W28BDocsTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root=Path(temp.name)
        (self.root/"autopilot").mkdir()
        (self.root/"docs/autopilot-proposals").mkdir(parents=True)
        source=Path(__file__).resolve().parents[1]/"autopilot/w27_backlog.json"
        shutil.copyfile(source,self.root/"autopilot/w27_backlog.json")
        self.out=self.root/OWNED_PATH

    def test_dryrun_does_not_write(self):
        info=prepare(self.root)
        self.assertFalse(info["github_pr_created"])
        self.assertFalse(info["git_push_performed"])
        self.assertFalse(info["auto_merge_performed"])
        self.assertFalse(info["production_accepted"])
        self.assertFalse(self.out.exists())

    def test_backlog_preserves_actual_blocked_external(self):
        info=prepare(self.root)
        self.assertEqual(info["auto_proposal_count"],3)
        self.assertEqual(info["blocked_external_count"],4)

    def test_write_requires_explicit_one_time_optin(self):
        with patch.dict(os.environ,{"EDU_AUTOPILOT_DOC_PR_ENABLE":"0"}):
            with self.assertRaises(ValueError):prepare(self.root,write=True)
        self.assertFalse(self.out.exists())

    def test_local_write_is_not_pull_request(self):
        with patch.dict(os.environ,{"EDU_AUTOPILOT_DOC_PR_ENABLE":"1"}):
            info=prepare(self.root,write=True)
        self.assertEqual(info["status"],"DOCS_STAGED_LOCALLY_FOR_REVIEW_NOT_PR_CREATED")
        self.assertFalse(info["github_pr_created"])
        self.assertTrue(self.out.read_text().startswith(MAGIC))
        self.assertIn("BLOCKED_EXTERNAL",self.out.read_text())

    def test_idempotent_staging(self):
        with patch.dict(os.environ,{"EDU_AUTOPILOT_DOC_PR_ENABLE":"1"}):
            prepare(self.root,write=True)
            first=self.out.read_bytes()
            prepare(self.root,write=True)
            self.assertEqual(first,self.out.read_bytes())

    def test_never_clobber_user_owned_doc(self):
        self.out.write_text("# Real human plan",encoding="utf-8")
        with patch.dict(os.environ,{"EDU_AUTOPILOT_DOC_PR_ENABLE":"1"}):
            with self.assertRaises(ValueError):prepare(self.root,write=True)
        self.assertEqual(self.out.read_text(),"# Real human plan")

    def test_symlink_output_denied(self):
        outside=self.root/"private.txt"
        outside.write_text("untouched",encoding="utf-8")
        try:self.out.symlink_to(outside)
        except (OSError,NotImplementedError):self.skipTest("symlinks unavailable")
        with patch.dict(os.environ,{"EDU_AUTOPILOT_DOC_PR_ENABLE":"1"}):
            with self.assertRaises(ValueError):prepare(self.root,write=True)
        self.assertEqual(outside.read_text(),"untouched")

    def test_unknown_model_code_is_never_used(self):
        with self.assertRaises(ValueError):escape_content("<script>alert(1)</script>")
        with self.assertRaises(ValueError):escape_content("foo\nbar")

    def test_bad_sha_refused(self):
        with self.assertRaises(ValueError):render(load_backlog(
            self.root/"autopilot/w27_backlog.json"),"NOT_SHA256")

    def test_no_approved_status_emitted(self):
        with patch.dict(os.environ,{"EDU_AUTOPILOT_DOC_PR_ENABLE":"1"}):
            prepare(self.root,write=True)
        raw=self.out.read_text()
        self.assertNotIn("status: PRODUCTION_ACCEPTED",raw)
        self.assertIn("NOT_APPROVED",raw)
        self.assertIn("No autonomous code execution",raw)

    def test_invalid_backlog_never_creates_docs(self):
        (self.root/"autopilot/w27_backlog.json").write_text('{"schema":1,"tasks":[]}')
        with patch.dict(os.environ,{"EDU_AUTOPILOT_DOC_PR_ENABLE":"1"}):
            with self.assertRaises(ValueError):prepare(self.root,write=True)
        self.assertFalse(self.out.exists())

    def test_dryrun_cli_safe(self):
        self.assertEqual(main(["--repo-root",str(self.root)]),0)
        self.assertFalse(self.out.exists())

if __name__=="__main__":
    unittest.main()
