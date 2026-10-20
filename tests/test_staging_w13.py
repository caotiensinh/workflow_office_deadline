"""W13 safe staging plan regression: no policy bypass, credentials or task mutation."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from edu_workflow.staging_preflight import preflight, save_report, PROJECT_FILES

ROOT = Path(__file__).resolve().parents[1]
BASE = {"platform": "nt", "session_id": 0,
        "execution_policy": "Restricted", "task_exists": False}


class W13PreflightTests(unittest.TestCase):
    def test_default_static_plan_has_zero_host_calls(self):
        with patch("edu_workflow.staging_preflight._probe_windows",
                   side_effect=AssertionError("HOST PROBE FORBIDDEN")):
            result = preflight(ROOT)
        self.assertEqual(result["status"], "PLAN_REVIEW_ONLY")
        self.assertEqual(result["mode"], "plan")
        self.assertIn("NOT_REQUESTED", [x["status"] for x in result["checks"]])
        self.assertTrue(all(x["status"] == "PASS" for x in result["checks"]
                            if x["id"].startswith("FILE_")))
        self.assertFalse(result["production_accepted"])

    def test_real_approval_flag_is_required_for_probe(self):
        with patch("edu_workflow.staging_preflight._probe_windows",
                   side_effect=AssertionError("UNAUTHORIZED HOST ACCESS")):
            with self.assertRaises(PermissionError):
                preflight(ROOT, mode="machine-readonly")
            with self.assertRaises(PermissionError):
                preflight(ROOT, mode="machine-readonly", authorized=False)

    def test_restricted_session0_is_blocked_without_claiming_it_pass(self):
        r = preflight(ROOT, mode="machine-readonly", authorized=True, evidence=dict(BASE))
        by_id = {x["id"]: x["status"] for x in r["checks"]}
        self.assertEqual(by_id["WINDOWS_SESSION"], "BLOCKED_FOR_GUI")
        self.assertEqual(by_id["POWERSHELL_POLICY"], "BLOCKED_NEEDS_IT")
        self.assertEqual(by_id["TASK_EXISTS"], "MISSING")
        self.assertFalse(r["production_accepted"])
        self.assertFalse(r["execution_policy_changed"])

    def test_nonzero_session_still_not_human_acceptance(self):
        e = dict(BASE, session_id=2, execution_policy="RemoteSigned", task_exists=True)
        r = preflight(ROOT, mode="machine-readonly", authorized=True, evidence=e)
        by_id = {x["id"]: x["status"] for x in r["checks"]}
        self.assertEqual(by_id["WINDOWS_SESSION"], "OBSERVED_NOT_HUMAN_UAT")
        self.assertEqual(by_id["POWERSHELL_POLICY"], "IT_REVIEW_REQUIRED")
        self.assertEqual(by_id["TASK_EXISTS"], "EXISTS_NOT_VALIDATED")
        self.assertFalse(r["human_pilot_accepted"])

    def test_allsigned_needs_it_review_no_bypass(self):
        e = dict(BASE, execution_policy="AllSigned")
        r = preflight(ROOT, mode="machine-readonly", authorized=True, evidence=e)
        x = {c["id"]: c for c in r["checks"]}
        self.assertEqual(x["POWERSHELL_POLICY"]["status"], "BLOCKED_NEEDS_IT")
        self.assertFalse(r["machine_changes_performed"])

    def test_unavailable_policy_is_not_reported_clear(self):
        e = dict(BASE, execution_policy="UNAVAILABLE", session_id=None, task_exists=None)
        r = preflight(ROOT, mode="machine-readonly", authorized=True, evidence=e)
        x = {c["id"]: c["status"] for c in r["checks"]}
        self.assertEqual(x["WINDOWS_SESSION"], "UNVERIFIED")
        self.assertEqual(x["POWERSHELL_POLICY"], "UNVERIFIED")
        self.assertEqual(x["TASK_EXISTS"], "UNVERIFIED")

    def test_non_windows_is_not_endpoint_acceptance(self):
        e = {"platform": "posix", "session_id": None,
             "execution_policy": "UNAVAILABLE", "task_exists": None}
        r = preflight(ROOT, mode="machine-readonly", authorized=True, evidence=e)
        self.assertIn("NOT_APPLICABLE", [x["status"] for x in r["checks"]])

    def test_reject_malformed_or_forged_os_facts(self):
        for e in (
            {"platform": "nt"},
            dict(BASE, session_id=True),
            dict(BASE, session_id=-1),
            dict(BASE, task_exists=1),
            dict(BASE, execution_policy="Anything"),
            dict(BASE, platform="fake"),
            dict(BASE, platform="posix", session_id=0),
            dict(BASE, private_password="SECRET"),
        ):
            with self.subTest(e=e), self.assertRaises(ValueError):
                preflight(ROOT, mode="machine-readonly", authorized=True, evidence=e)

    def test_invalid_mode_and_authorization_input_fail(self):
        with self.assertRaises(ValueError):
            preflight(ROOT, mode="production")
        with self.assertRaises(ValueError):
            preflight(ROOT, authorized=1)

    def test_missing_project_must_not_create_directories(self):
        with tempfile.TemporaryDirectory() as tmp:
            nonexistent = Path(tmp) / "missingproject"
            r = preflight(nonexistent)
            self.assertEqual(r["status"], "SOURCE_BLOCKED")
            self.assertFalse(nonexistent.exists())
            self.assertTrue(any(x["status"] == "BLOCKED" for x in r["checks"]))

    def test_symlink_required_file_cannot_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            fake = Path(tmp)
            for rel in PROJECT_FILES:
                p = fake / rel
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text("fixture", encoding="utf-8")
            target = fake / PROJECT_FILES[0]
            target.unlink()
            try:
                target.symlink_to(fake / PROJECT_FILES[1])
            except (OSError, NotImplementedError):
                self.skipTest("symlink unavailable")
            x = preflight(fake)
            self.assertEqual(x["status"], "SOURCE_BLOCKED")

    def test_no_production_gate_is_misreported_as_pass(self):
        r = preflight(ROOT)
        for gate in ("IT_ENDPOINT_APPROVAL", "SCHEDULED_15_MIN",
                     "OUTLOOK_READ_ONLY", "NOTIFICATION_TEST",
                     "IDENTITY_PRIVACY", "PILOTS"):
            status = next(x["status"] for x in r["checks"] if x["id"] == gate)
            self.assertEqual(status, "PENDING_AUTHORIZED_EVIDENCE")
        self.assertFalse(r["real_outlook_accessed"])
        self.assertFalse(r["smtp_used"])
        self.assertFalse(r["task_created_or_changed"])
        self.assertFalse(r["database_opened_or_modified"])

    def test_explicit_report_exclusive_no_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "staging.json"
            report = preflight(ROOT)
            save_report(report, p)
            data = p.read_bytes()
            self.assertEqual(json.loads(data)["production_accepted"], False)
            with self.assertRaises(FileExistsError):
                save_report(report, p)
            self.assertEqual(p.read_bytes(), data)
            self.assertEqual(len(list(Path(tmp).iterdir())), 1)

    def test_invalid_output_parent_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / "nonexisting" / "report.json"
            with self.assertRaises(ValueError):
                save_report(preflight(ROOT), missing)
            self.assertFalse(missing.parent.exists())

    def test_cli_plan_is_json_and_no_output_db_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "evidence.json"
            env = dict(os.environ, PYTHONPATH=str(ROOT / "python"),
                       PYTHONIOENCODING="cp1252")
            run = subprocess.run(
                [sys.executable, "-m", "edu_workflow.staging_preflight",
                 "--project", str(ROOT), "--output", str(out)],
                cwd=ROOT, env=env, capture_output=True, text=True, check=False,
            )
            self.assertEqual(run.returncode, 0, run.stderr)
            result = json.loads(run.stdout)
            self.assertEqual(result["status"], "PLAN_REVIEW_ONLY")
            self.assertEqual(json.loads(out.read_text(encoding="utf-8")), result)
            self.assertEqual({x.name for x in Path(tmp).iterdir()}, {"evidence.json"})

    def test_cli_does_not_probe_without_approval(self):
        env = dict(os.environ, PYTHONPATH=str(ROOT / "python"),
                   PYTHONIOENCODING="cp1252")
        run = subprocess.run(
            [sys.executable, "-m", "edu_workflow.staging_preflight",
             "--project", str(ROOT), "--mode", "machine-readonly"],
            cwd=ROOT, env=env, capture_output=True, text=True,
        )
        self.assertEqual(run.returncode, 2)
        self.assertIn("PermissionError", run.stderr)
        self.assertNotIn("SECRET", run.stderr)

if __name__ == "__main__":
    unittest.main()
