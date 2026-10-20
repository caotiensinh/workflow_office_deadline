"""W8 single-file UAT launcher: no service GUI, no silent consent, no overwrite."""
from __future__ import annotations
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from edu_workflow import field_uat_launcher as uat


class OneClickUATTests(unittest.TestCase):
    def test_preflight_is_read_only_synthetic_and_preserves_evidence(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "preflight.json"
            with patch.object(uat.sys, "platform", "linux"):
                result = uat.preflight(target)
            self.assertEqual(result["packaged_entrypoint"], "OK")
            self.assertTrue(result["synthetic_only"])
            self.assertFalse(result["changes_startup"])
            self.assertFalse(result["opens_outlook"])
            self.assertFalse(result["sends_smtp"])
            self.assertFalse(result["actual_login_autorun_verified"])
            self.assertFalse(result["production_accepted"])
            self.assertFalse(result["session_interactive"])
            self.assertEqual(json.loads(target.read_text(encoding="utf-8")), result)
            with self.assertRaises(FileExistsError):
                uat.preflight(target)

    def test_preflight_rejects_unknown_directory(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "does-not-exist" / "proof.json"
            with self.assertRaises(FileNotFoundError):
                uat.preflight(target)
            self.assertFalse(target.exists())

    def test_no_args_in_session_zero_fail_closed(self):
        # W19 now demands a *live active console* match (not merely sid != 0).
        with patch.object(
            uat.session_guard, "require_active_console",
            side_effect=RuntimeError("W19_NOT_ACTIVE_CONSOLE_NO_GUI")
        ), patch.object(uat, "_ask_consent") as ask:
            with self.assertRaisesRegex(RuntimeError, "W19_NOT_ACTIVE_CONSOLE"):
                uat.one_click()
            ask.assert_not_called()

    def test_consent_denied_must_not_create_a_fixture(self):
        with patch.object(uat, "_require_interactive_windows"), patch.object(
            uat, "_ask_consent", return_value=False
        ), patch.object(uat, "run_manual") as run, patch.object(
            uat, "_report_path"
        ) as get_path:
            result = uat.one_click()
            self.assertEqual(result["status"], "CANCELLED")
            self.assertFalse(result["production_accepted"])
            run.assert_not_called()
            get_path.assert_not_called()

    def test_consent_then_partial_uat_keeps_production_false(self):
        with patch.object(uat, "_require_interactive_windows"), patch.object(
            uat, "_ask_consent", return_value=True
        ), patch.object(
            uat, "_report_path", return_value=Path("fictional-only.json")
        ), patch.object(
            uat, "run_manual",
            return_value={"status": "INCOMPLETE_FIELD_UAT", "production_accepted": False}
        ) as run, patch.object(uat, "review_uat_report", return_value={
            "status": "INCOMPLETE_SELF_ATTESTATION",
            "production_accepted": False, "it_approved": False,
            "actual_physical_observation_independently_verified": False,
            "actual_login_autorun_verified": False
        }), patch.object(uat, "write_operator_handoff", return_value=Path("handoff.json")), patch.object(uat, "_show_result") as show:
            result = uat.one_click()
            run.assert_called_once_with(Path("fictional-only.json"))
            self.assertFalse(result["production_accepted"])
            self.assertIn("未完了", show.call_args.args[0])

    def test_error_not_misreported_as_success(self):
        with patch.object(uat, "_require_interactive_windows"), patch.object(
            uat, "_ask_consent", return_value=True
        ), patch.object(
            uat, "_report_path", return_value=Path("fictional-only.json")
        ), patch.object(
            uat, "run_manual", side_effect=RuntimeError("simulated failure")
        ), patch.object(uat, "_show_result") as show:
            with self.assertRaisesRegex(RuntimeError, "simulated failure"):
                uat.one_click()
            self.assertTrue(show.call_args.kwargs["error"])

    def test_entrypoint_preflight_never_starts_manual_gui(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "proof.json"
            with patch.object(uat, "one_click") as run:
                uat.main(["--preflight-file", str(target)])
            run.assert_not_called()
            self.assertTrue(target.is_file())


if __name__ == "__main__":
    unittest.main()
