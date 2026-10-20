"""W19: active console candidate only, never physical GUI/user/IT acceptance."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, call

from edu_workflow import interactive_session_w19 as guard
from edu_workflow import field_uat_launcher as launcher


class ActiveConsoleW19Tests(unittest.TestCase):
    def test_service_session_zero_blocked(self):
        x = guard.classify(0, 1)
        self.assertEqual(x["status"], "W19_SESSION_0_BLOCKED")
        self.assertFalse(x["active_console_match"])

    def test_service_session_zero_even_if_console_zero(self):
        self.assertEqual(guard.classify(0, 0)["status"], "W19_SESSION_0_BLOCKED")

    def test_no_active_console_blocked(self):
        x = guard.classify(1, None)
        self.assertEqual(x["status"], "W19_NO_ACTIVE_CONSOLE_BLOCKED")

    def test_different_session_blocked(self):
        x = guard.classify(3, 1)
        self.assertEqual(x["status"], "W19_DIFFERENT_SESSION_BLOCKED")
        self.assertFalse(x["human_interaction_observed"])

    def test_matching_console_is_only_candidate(self):
        x = guard.classify(1, 1)
        self.assertTrue(x["active_console_match"])
        self.assertEqual(x["status"], "W19_ACTIVE_CONSOLE_CANDIDATE_NOT_GUI_UAT")
        for name in ("human_interaction_observed", "production_accepted",
                     "actual_login_autorun_verified", "modifies_system"):
            self.assertFalse(x[name])

    def test_other_active_session_not_hardcoded_to_id_one(self):
        self.assertTrue(guard.classify(2, 2)["active_console_match"])

    def test_invalid_process_ids_rejected(self):
        for value in (-1, guard.INVALID_ID, "1", None, 1.0):
            with self.subTest(value=value), self.assertRaises(ValueError):
                guard.classify(value, 1)

    def test_invalid_console_ids_rejected(self):
        for value in (-1, guard.INVALID_ID, "1", 1.0):
            with self.subTest(value=value), self.assertRaises(ValueError):
                guard.classify(1, value)

    def test_boolean_is_not_valid_session_id(self):
        for x, y in ((True, 1), (1, True), (False, 0)):
            with self.subTest(x=x, y=y), self.assertRaises(ValueError):
                guard.classify(x, y)

    def test_non_windows_inspection_is_read_only_blocked(self):
        with patch.object(guard.sys, "platform", "linux"):
            result = guard.inspect()
        self.assertEqual(result["status"], "W19_NON_WINDOWS_BLOCKED")
        self.assertFalse(result["live_windows_api_observed"])
        self.assertFalse(result["active_console_match"])

    def test_require_active_console_fails_closed_without_live_windows_api(self):
        candidate = guard.classify(2, 2)  # injected shape, NOT actually read from OS
        with patch.object(guard, "inspect", return_value=candidate):
            with self.assertRaisesRegex(RuntimeError, "W19_NOT_ACTIVE_CONSOLE"):
                guard.require_active_console()

    def test_require_console_accepts_only_live_match_not_human_signoff(self):
        candidate = guard.classify(2, 2)
        candidate["live_windows_api_observed"] = True
        with patch.object(guard, "inspect", return_value=candidate):
            self.assertEqual(guard.require_active_console()["status"],
                             "W19_ACTIVE_CONSOLE_CANDIDATE_NOT_GUI_UAT")

    def test_cli_numeric_diagnostic_does_not_launch_gui(self):
        with tempfile.TemporaryDirectory() as root:
            result = guard.classify(0, 1)
            result["live_windows_api_observed"] = True
            path = Path(root) / "session.json"
            with patch.object(launcher.session_guard, "inspect", return_value=result), patch.object(
                launcher, "one_click"
            ) as gui:
                launcher.main(["--session-check-file", str(path)])
            gui.assert_not_called()
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), result)
            self.assertEqual({p.name for p in Path(root).iterdir()}, {"session.json"})

    def test_numeric_diagnostic_exclusive_no_evidence_overwrite(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "prior.json"
            path.write_text("PREVIOUS", encoding="utf-8")
            with patch.object(launcher.session_guard, "inspect") as inspect:
                with self.assertRaises(FileExistsError):
                    launcher.session_check(path)
            self.assertEqual(path.read_text(encoding="utf-8"), "PREVIOUS")

    def test_consent_cancellation_prevents_second_guard_and_db(self):
        with patch.object(launcher, "_require_interactive_windows") as check, patch.object(
                launcher, "_ask_consent", return_value=False), patch.object(
                launcher, "_report_path") as path, patch.object(
                launcher, "run_manual") as run:
            self.assertEqual(launcher.one_click()["status"], "CANCELLED")
            check.assert_called_once()
            path.assert_not_called()
            run.assert_not_called()

    def test_session_mismatch_after_consent_prevents_fixture(self):
        with patch.object(launcher, "_require_interactive_windows",
                          side_effect=[None, RuntimeError("W19_NOT_ACTIVE_CONSOLE")]) as check, patch.object(
                launcher, "_ask_consent", return_value=True), patch.object(
                launcher, "_report_path") as path, patch.object(
                launcher, "run_manual") as run:
            with self.assertRaisesRegex(RuntimeError, "W19_NOT_ACTIVE_CONSOLE"):
                launcher.one_click()
            self.assertEqual(check.call_count, 2)
            path.assert_not_called()
            run.assert_not_called()

    def test_guard_invoked_twice_on_successful_user_consent(self):
        with patch.object(launcher, "_require_interactive_windows") as check, patch.object(
                launcher, "_ask_consent", return_value=True), patch.object(
                launcher, "_report_path", return_value=Path("synthetic.json")), patch.object(
                launcher, "run_manual", return_value={
                    "status": "INCOMPLETE_FIELD_UAT", "production_accepted": False
                }) as run, patch.object(launcher, "review_uat_report", return_value={
                    "status": "INCOMPLETE_SELF_ATTESTATION",
                    "production_accepted": False, "it_approved": False,
                    "actual_physical_observation_independently_verified": False,
                    "actual_login_autorun_verified": False
                }), patch.object(launcher, "write_operator_handoff", return_value=Path("handoff.json")), patch.object(launcher, "_show_result"):
            result = launcher.one_click()
            self.assertEqual(check.call_count, 2)
            run.assert_called_once()
            self.assertFalse(result["production_accepted"])

    def test_preflight_only_flags_true_active_console_match(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "preflight.json"
            with patch.object(launcher.session_guard, "inspect",
                              return_value=guard.classify(3, 1)):
                result = launcher.preflight(path)
            self.assertFalse(result["session_interactive"])
            self.assertFalse(result["production_accepted"])


if __name__ == "__main__":
    unittest.main()
