"""W22A packaged offline GUI self-report reader, never approval."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from edu_workflow import field_uat_launcher as launcher


def sample():
    return {
        "scope": "fictional-local-data-only",
        "type": "human-self-attested-Windows-field-UAT",
        "session_interactive": True,
        "visual_japanese_self_report": True,
        "sound_audible_self_report": True,
        "window_interactive_self_report": True,
        "ack_receipts": 1,
        "snooze_receipts": 1,
        "desktop_audit_events": 2,
        "business_approvals": 0,
        "human_buttons_recorded": True,
        "actual_login_autorun_verified": False,
        "production_accepted": False,
        "status": "DESKTOP_ACTIONS_AND_HUMAN_REPORT_COMPLETE",
    }


class W22APackagedReviewerTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)
        self.source = self.dir / "self_report.json"
        self.output = self.dir / "readonly_result.json"
        self.source.write_text(json.dumps(sample()), encoding="utf-8")

    def test_complete_is_only_self_attestation(self):
        result = launcher.review_existing_uat(self.source, self.output)
        self.assertEqual(result["status"],
                         "CONSISTENT_SELF_ATTESTATION_NOT_INDEPENDENTLY_VERIFIED")
        self.assertEqual(result["ack_receipts"], 1)
        for flag in ("real_gui_independently_verified", "windows_login_autorun_verified",
                     "it_approved", "production_accepted", "opens_gui", "modifies_source"):
            self.assertFalse(result[flag])
        self.assertEqual(json.loads(self.output.read_text(encoding="utf-8")), result)

    def test_review_does_not_change_original(self):
        saved = self.source.read_bytes()
        launcher.review_existing_uat(self.source, self.output)
        self.assertEqual(self.source.read_bytes(), saved)

    def test_missing_report_does_not_create_success(self):
        self.source.unlink()
        with self.assertRaises(ValueError):
            launcher.review_existing_uat(self.source, self.output)
        self.assertFalse(self.output.exists())

    def test_tampered_approval_is_rejected(self):
        bad = sample()
        bad["production_accepted"] = True
        self.source.write_text(json.dumps(bad), encoding="utf-8")
        with self.assertRaises(ValueError):
            launcher.review_existing_uat(self.source, self.output)
        self.assertFalse(self.output.exists())

    def test_contradictory_gui_receipts_rejected(self):
        bad = sample()
        bad["ack_receipts"] = 0
        self.source.write_text(json.dumps(bad), encoding="utf-8")
        with self.assertRaises(ValueError):
            launcher.review_existing_uat(self.source, self.output)

    def test_review_existing_evidence_cannot_overwrite(self):
        self.output.write_text("OLD-EVIDENCE", encoding="utf-8")
        with self.assertRaises(FileExistsError):
            launcher.review_existing_uat(self.source, self.output)
        self.assertEqual(self.output.read_text(encoding="utf-8"), "OLD-EVIDENCE")

    def test_cli_no_desktop_or_session(self):
        with patch.object(launcher, "_require_interactive_windows") as guard, patch.object(
                launcher, "one_click") as gui, patch.object(
                launcher.session_guard, "inspect") as inspect:
            launcher.main(["--review-report-file", str(self.source),
                           "--review-output-file", str(self.output)])
        guard.assert_not_called()
        gui.assert_not_called()
        inspect.assert_not_called()

    def test_partial_self_report_is_not_complete(self):
        bad = sample()
        bad["sound_audible_self_report"] = False
        bad["status"] = "INCOMPLETE_FIELD_UAT"
        self.source.write_text(json.dumps(bad), encoding="utf-8")
        result = launcher.review_existing_uat(self.source, self.output)
        self.assertEqual(result["status"], "INCOMPLETE_SELF_ATTESTATION")
        self.assertFalse(result["production_accepted"])

    def test_unpaired_cli_flags_rejected(self):
        for args in (["--review-report-file", str(self.source)],
                     ["--review-output-file", str(self.output)]):
            with self.subTest(args=args), self.assertRaises(SystemExit):
                launcher.main(args)


if __name__ == "__main__":
    unittest.main()
