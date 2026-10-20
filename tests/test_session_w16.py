"""W16 safety tests: do not substitute Session ID for human GUI acceptance."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from w16_session_probe import _classify, _plan, _save_new

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/w16-selfhost-session-probe.yml"


class W16SessionTests(unittest.TestCase):
    def test_plan_only_has_no_host_data_or_uat(self):
        x = _plan()
        self.assertEqual(x["status"], "PLAN_ONLY_NO_HOST_INSPECTION")
        self.assertFalse(x["live_windows_api_observed"])
        self.assertFalse(x["gui_accepted"])
        self.assertFalse(x["task_scheduler_checked"])
        self.assertFalse(x["production_accepted"])

    def test_service_session_zero_does_not_pass_gui(self):
        x = _classify(0, 1)
        self.assertEqual(x["status"], "SESSION_0_GUI_UAT_BLOCKED")
        self.assertFalse(x["console_match"])
        self.assertFalse(x["human_interaction_observed"])

    def test_service_session_zero_with_active_console_zero_still_blocked(self):
        x = _classify(0, 0)
        self.assertEqual(x["status"], "SESSION_0_GUI_UAT_BLOCKED")
        self.assertFalse(x["gui_accepted"])

    def test_active_console_matching_session_is_only_candidate(self):
        x = _classify(2, 2)
        self.assertEqual(x["status"], "CONSOLE_SESSION_CANDIDATE_NOT_UAT")
        self.assertTrue(x["console_match"])
        self.assertFalse(x["gui_accepted"])
        self.assertFalse(x["human_interaction_observed"])

    def test_different_remote_session_does_not_pass(self):
        x = _classify(3, 2)
        self.assertEqual(x["status"], "NOT_ACTIVE_CONSOLE_NO_GUI_UAT")
        self.assertFalse(x["console_match"])

    def test_no_active_console_is_not_uat(self):
        x = _classify(3, None)
        self.assertEqual(x["status"], "NOT_ACTIVE_CONSOLE_NO_GUI_UAT")
        self.assertIsNone(x["active_console_session_id"])

    def test_no_real_account_or_source_in_report(self):
        result = json.dumps(_classify(1, 1))
        for forbidden in ("user", "email", "hostname", "domain", "password",
                          "task_name", "registry", "Outlook", "token"):
            self.assertNotIn(forbidden, result)
        self.assertFalse(_classify(1, 1)["production_accepted"])

    def test_invalid_ids_fail_closed(self):
        for sid, active in ((True, 1), (-1, 1), (4294967295, 1),
                            (1, -1), (1, True), ("1", 1), (1, "2"),
                            (1, 4294967295)):
            with self.subTest(sid=sid, active=active), self.assertRaises(ValueError):
                _classify(sid, active)

    def test_report_is_exclusive_and_only_runner_temp_subdir(self):
        with tempfile.TemporaryDirectory() as tmp:
            safe = Path(tmp) / "job"
            safe.mkdir()
            file = safe / "session.json"
            with patch.dict(os.environ, {"RUNNER_TEMP": tmp}):
                _save_new(_classify(0, 1), file)
                before = file.read_bytes()
                with self.assertRaises(RuntimeError):
                    _save_new(_classify(0, 1), file)
            self.assertEqual(before, file.read_bytes())
            self.assertFalse(json.loads(before)["production_accepted"])

    def test_report_rejects_outside_temp_without_creating(self):
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            external = Path(b) / "no.json"
            with patch.dict(os.environ, {"RUNNER_TEMP": a}):
                with self.assertRaises(RuntimeError):
                    _save_new(_classify(0, 1), external)
            self.assertFalse(external.exists())

    def test_cli_default_plan_is_side_effect_free(self):
        with tempfile.TemporaryDirectory() as p:
            result = subprocess.run([sys.executable, str(ROOT / "tests" / "w16_session_probe.py")],
                                    capture_output=True, text=True, cwd=p)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)["status"],
                             "PLAN_ONLY_NO_HOST_INSPECTION")
            self.assertEqual(list(Path(p).iterdir()), [])

    def test_w16_selfhost_uses_cmd_and_no_powershell_or_scheduler(self):
        yaml = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("feat/w16-session-readonly-e2e", yaml)
        self.assertIn("runs-on: [self-hosted, Windows]", yaml)
        host = yaml.split("  selfhost-cmd-e2e:", 1)[1]
        self.assertIn("shell: cmd", host)
        self.assertIn("--inspect", host)
        self.assertIn("W16_SELFHOST_SESSION_PROBE_PASS", host)
        for forbidden in ("shell: pwsh", "powershell.exe", "schtasks",
                          "Set-ExecutionPolicy", "-ExecutionPolicy", "OpenInputDesktop",
                          "import-outlook-classic"):
            self.assertNotIn(forbidden, host)


if __name__ == "__main__":
    unittest.main()
