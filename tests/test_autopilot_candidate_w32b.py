"""W32B fail-closed compiler contract: untrusted proposals cannot ship Python text."""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from edu_workflow.autopilot_candidate_w32b import (
    MAGIC, OUTPUT_PATH, SCENARIOS, load_spec, render, prepare, main,
)

BASE = {"schema": 1, "task_id": "W27-QA", "scenarios": [
    "valid_qa_proposal", "duplicate_task_ids", "blocked_without_approval",
]}


class CandidateContractTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        (self.root / "autopilot").mkdir()
        (self.root / "tests").mkdir()
        self.backlog = self.root / "autopilot/w27_backlog.json"
        self.backlog.write_text(json.dumps({"schema": 1, "tasks": [{
            "id": "W27-QA", "title": "Propose fictional QA evidence checks",
            "description": "Safely test synthetic deadline and approval policy",
            "domain": "qa-security", "kind": "AUTO_PROPOSAL",
            "approval_required": False
        }]}), encoding="utf-8")
        self.spec = self.root / "autopilot/w32b_qa_candidate.json"
        self.save(BASE)

    def save(self, data):
        self.spec.write_text(json.dumps(data), encoding="utf-8")

    def test_default_is_read_only_without_output(self):
        report = prepare(self.root)
        self.assertEqual(report["status"], "DRY_RUN_NO_FILES_CHANGED")
        self.assertFalse((self.root / OUTPUT_PATH).exists())
        self.assertFalse(report["untrusted_code_executed"])
        self.assertFalse(report["git_writes"])
        self.assertFalse(report["approved_for_merge"])

    def test_render_same_for_case_order(self):
        reversed_data = dict(BASE, scenarios=list(reversed(BASE["scenarios"])))
        self.save(reversed_data)
        a = render(load_spec(self.spec))
        self.save(BASE)
        b = render(load_spec(self.spec))
        self.assertEqual(a, b)
        self.assertTrue(a.startswith(MAGIC))
        self.assertEqual(a.count("    def test_"), 3)

    def test_missing_write_optin_fails_without_mutation(self):
        with patch.dict(os.environ, {"EDU_AUTOPILOT_TEST_STAGE": "0"}):
            with self.assertRaises(ValueError):
                prepare(self.root, write=True)
        self.assertFalse((self.root / OUTPUT_PATH).exists())

    def test_optin_stages_only_owned_file_and_verifies(self):
        with patch.dict(os.environ, {"EDU_AUTOPILOT_TEST_STAGE": "1"}):
            out = prepare(self.root, write=True)
        self.assertEqual(out["status"], "TRUSTED_TEST_STAGED_NOT_PR_OR_CI")
        self.assertEqual(prepare(self.root, verify=True)["status"],
                         "EXACT_RENDER_VERIFIED_NOT_GITHUB_CI")
        before = (self.root / OUTPUT_PATH).read_bytes()
        with patch.dict(os.environ, {"EDU_AUTOPILOT_TEST_STAGE": "1"}):
            prepare(self.root, write=True)
        self.assertEqual((self.root / OUTPUT_PATH).read_bytes(), before)

    def test_verify_missing_file_rejected(self):
        with self.assertRaises(ValueError):
            prepare(self.root, verify=True)

    def test_existing_human_file_never_overwritten(self):
        target = self.root / OUTPUT_PATH
        target.write_text("Human-owned test\n", encoding="utf-8")
        with patch.dict(os.environ, {"EDU_AUTOPILOT_TEST_STAGE": "1"}):
            with self.assertRaises(ValueError):
                prepare(self.root, write=True)
        self.assertEqual(target.read_text(), "Human-owned test\n")

    def test_tampered_generated_file_rejected(self):
        with patch.dict(os.environ, {"EDU_AUTOPILOT_TEST_STAGE": "1"}):
            prepare(self.root, write=True)
        target = self.root / OUTPUT_PATH
        target.write_text(target.read_text() + "\n# tampered\n")
        with self.assertRaises(ValueError):
            prepare(self.root, verify=True)
        with patch.dict(os.environ, {"EDU_AUTOPILOT_TEST_STAGE": "1"}):
            with self.assertRaises(ValueError):
                prepare(self.root, write=True)

    def test_untrusted_code_is_not_a_valid_scenario(self):
        bad = dict(BASE, scenarios=["valid_qa_proposal", "import os; os.system('whoami')"])
        self.save(bad)
        with self.assertRaises(ValueError):
            prepare(self.root)

    def test_injected_object_field_rejected(self):
        bad = dict(BASE, shell="curl example.com")
        self.save(bad)
        with self.assertRaises(ValueError):
            load_spec(self.spec)

    def test_model_authored_source_field_rejected(self):
        bad = dict(BASE, python_code="print('fake pass')")
        self.save(bad)
        with self.assertRaises(ValueError):
            load_spec(self.spec)

    def test_duplicate_json_property_rejected(self):
        self.spec.write_text('{"schema":1,"schema":1,"task_id":"W27-QA","scenarios":[]}')
        with self.assertRaises(ValueError):
            load_spec(self.spec)

    def test_duplicate_scenario_rejected(self):
        self.save(dict(BASE, scenarios=["valid_qa_proposal"] * 2))
        with self.assertRaises(ValueError):
            load_spec(self.spec)

    def test_empty_cases_rejected(self):
        self.save(dict(BASE, scenarios=[]))
        with self.assertRaises(ValueError):
            load_spec(self.spec)

    def test_invalid_task_id_rejected(self):
        self.save(dict(BASE, task_id="W27-IT"))
        with self.assertRaises(ValueError):
            load_spec(self.spec)

    def test_unknown_enum_rejected(self):
        self.save(dict(BASE, scenarios=["new_arbitrary_step"]))
        with self.assertRaises(ValueError):
            load_spec(self.spec)

    def test_oversize_input_rejected(self):
        self.spec.write_text("x" * 5000)
        with self.assertRaises(ValueError):
            load_spec(self.spec)

    def test_linked_candidate_rejected(self):
        dest = self.root / "actual.json"
        dest.write_text(json.dumps(BASE))
        self.spec.unlink()
        try:
            self.spec.symlink_to(dest)
        except (NotImplementedError, OSError):
            self.skipTest("Platform does not permit symlinks")
        with self.assertRaises(ValueError):
            prepare(self.root)

    def test_linked_generated_output_rejected(self):
        dest = self.root / "outside.py"
        dest.write_text("protected")
        output = self.root / OUTPUT_PATH
        try:
            output.symlink_to(dest)
        except (NotImplementedError, OSError):
            self.skipTest("Platform does not permit symlinks")
        with patch.dict(os.environ, {"EDU_AUTOPILOT_TEST_STAGE": "1"}):
            with self.assertRaises(ValueError):
                prepare(self.root, write=True)
        self.assertEqual(dest.read_text(), "protected")

    def test_external_approval_task_rejected(self):
        obj = json.loads(self.backlog.read_text())
        obj["tasks"][0]["kind"] = "BLOCKED_EXTERNAL"
        obj["tasks"][0]["approval_required"] = True
        self.backlog.write_text(json.dumps(obj))
        with self.assertRaises(ValueError):
            prepare(self.root)

    def test_linked_tests_directory_rejected(self):
        (self.root / "tests").rmdir()
        actual = self.root / "other"
        actual.mkdir()
        try:
            (self.root / "tests").symlink_to(actual, target_is_directory=True)
        except (NotImplementedError, OSError):
            self.skipTest("Platform does not permit symlinks")
        with self.assertRaises(ValueError):
            prepare(self.root)

    def test_corrupt_schema_rejected(self):
        self.save(dict(BASE, schema=True))
        with self.assertRaises(ValueError):
            load_spec(self.spec)

    def test_render_rejects_untrusted_types(self):
        for value in (["valid_qa_proposal"], ("unknown",), (), None):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    render(value)

    def test_generated_code_compiles_without_model_text(self):
        content = render(tuple(sorted(SCENARIOS)))
        compile(content, "trusted_w32b.py", "exec")
        self.assertNotIn("curl", content)
        self.assertNotIn("subprocess", content)
        self.assertEqual(content.count("    def test_"), 6)

    def test_cli_dryrun_and_bad_input(self):
        self.assertEqual(main(["--repo-root", str(self.root)]), 0)
        self.spec.unlink()
        self.assertEqual(main(["--repo-root", str(self.root)]), 2)


if __name__ == "__main__":
    unittest.main()
