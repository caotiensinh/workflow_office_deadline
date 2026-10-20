"""W20A: one-click GUI handoff must verify its *written* fictional UAT report."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from edu_workflow import field_uat_launcher as launcher


def valid_report():
    return {
        "scope": "fictional-local-data-only",
        "type": "human-self-attested-Windows-field-UAT",
        "session_interactive": True,
        "visual_japanese_self_report": True,
        "sound_audible_self_report": True,
        "window_interactive_self_report": True,
        "ack_receipts": 1, "snooze_receipts": 1,
        "desktop_audit_events": 2, "business_approvals": 0,
        "human_buttons_recorded": True,
        "actual_login_autorun_verified": False,
        "production_accepted": False,
        "status": "DESKTOP_ACTIONS_AND_HUMAN_REPORT_COMPLETE",
    }


class W20APersistedUatReviewTests(unittest.TestCase):
    def _run(self, data=None, *, status="DESKTOP_ACTIONS_AND_HUMAN_REPORT_COMPLETE", raw=None,
             missing=False):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        target = Path(temporary.name) / "fictional.json"

        def fake_run(path):
            self.assertEqual(path, target)
            if not missing:
                target.write_text(raw if raw is not None else json.dumps(data if data is not None else valid_report()),
                                  encoding="utf-8")
            return {"status": status, "production_accepted": False}

        with patch.object(launcher, "_require_interactive_windows") as session, \
             patch.object(launcher, "_ask_consent", return_value=True), \
             patch.object(launcher, "_report_path", return_value=target), \
             patch.object(launcher, "run_manual", side_effect=fake_run), \
             patch.object(launcher, "_show_result") as dialog:
            try:
                result = launcher.one_click()
                error = None
            except (ValueError, OSError) as exc:
                result, error = None, type(exc)
        return result, error, dialog.call_args, target, session.call_count

    def test_valid_written_report_checked_and_remains_self_attested(self):
        result, error, msg, target, count = self._run()
        self.assertIsNone(error)
        self.assertEqual(result["status"], "DESKTOP_ACTIONS_AND_HUMAN_REPORT_COMPLETE")
        self.assertIn("自己申告", msg.args[0])
        self.assertIn("NOT independent GUI", msg.args[0])
        self.assertFalse(json.loads(target.read_text(encoding="utf-8"))["production_accepted"])
        self.assertEqual(count, 2)

    def test_incomplete_report_is_displayed_as_incomplete(self):
        data = valid_report()
        data["sound_audible_self_report"] = False
        data["status"] = "INCOMPLETE_FIELD_UAT"
        result, error, msg, _, _ = self._run(data, status="INCOMPLETE_FIELD_UAT")
        self.assertIsNone(error)
        self.assertEqual(result["status"], "INCOMPLETE_FIELD_UAT")
        self.assertIn("未完了", msg.args[0])
        self.assertNotIn("NOT independent GUI", msg.kwargs)

    def test_forged_production_approval_is_rejected(self):
        data = valid_report()
        data["production_accepted"] = True
        _, error, msg, _, _ = self._run(data)
        self.assertEqual(error, ValueError)
        self.assertTrue(msg.kwargs["error"])

    def test_business_decisions_cannot_be_disguised_as_receipts(self):
        data = valid_report()
        data["business_approvals"] = 1
        _, error, msg, _, _ = self._run(data)
        self.assertEqual(error, ValueError)
        self.assertTrue(msg.kwargs["error"])

    def test_duplicate_json_keys_fail_closed(self):
        raw = json.dumps(valid_report()).replace('"status":', '"status": "INCOMPLETE_FIELD_UAT", "status":')
        _, error, msg, _, _ = self._run(raw=raw)
        self.assertEqual(error, ValueError)
        self.assertTrue(msg.kwargs["error"])

    def test_unknown_private_extra_field_is_rejected(self):
        data = valid_report()
        data["school_email"] = "private@example.invalid"
        _, error, msg, _, _ = self._run(data)
        self.assertEqual(error, ValueError)
        self.assertNotIn("private@example.invalid", msg.args[0])

    def test_missing_persisted_file_must_not_trust_in_memory_success(self):
        _, error, msg, path, _ = self._run(missing=True)
        self.assertEqual(error, ValueError)
        self.assertTrue(msg.kwargs["error"])
        self.assertFalse(path.exists())

    def test_valid_file_disagreeing_with_run_result_fails(self):
        _, error, msg, _, _ = self._run(status="INCOMPLETE_FIELD_UAT")
        self.assertEqual(error, ValueError)
        self.assertTrue(msg.kwargs["error"])

    def test_boolean_count_in_report_rejected(self):
        data = valid_report()
        data["ack_receipts"] = True
        _, error, msg, _, _ = self._run(data)
        self.assertEqual(error, ValueError)
        self.assertTrue(msg.kwargs["error"])


if __name__ == "__main__":
    unittest.main()
