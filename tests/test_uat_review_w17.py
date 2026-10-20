"""W17: consent-first GUI UAT handoff remains self-attestation, never IT approval."""
import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from edu_workflow.uat_review import review, EXPECTED_KEYS

ROOT = Path(__file__).resolve().parents[1]
CMD = ROOT / "windows" / "W17_START_UAT.cmd.in"


def complete():
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


class W17UATReviewTests(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.root = Path(t.name)
        self.report = self.root / "uat.json"

    def write(self, data):
        self.report.write_text(json.dumps(data), encoding="utf-8")
        return self.report

    def test_self_attested_complete_never_production(self):
        result = review(self.write(complete()))
        self.assertEqual(result["status"], "CONSISTENT_SELF_ATTESTATION_NOT_INDEPENDENTLY_VERIFIED")
        self.assertEqual(result["ack_receipts"], 1)
        for field in ("actual_physical_observation_independently_verified",
                      "production_accepted", "it_approved",
                      "actual_login_autorun_verified", "signed_release_verified"):
            self.assertFalse(result[field])

    def test_partial_report_is_not_completion(self):
        d = complete()
        d["sound_audible_self_report"] = False
        d["status"] = "INCOMPLETE_FIELD_UAT"
        result = review(self.write(d))
        self.assertEqual(result["status"], "INCOMPLETE_SELF_ATTESTATION")
        self.assertFalse(result["sound_audible_self_report"])

    def test_no_ack_can_be_incomplete_not_pass(self):
        d = complete()
        d.update(ack_receipts=0, desktop_audit_events=1,
                 human_buttons_recorded=False, status="INCOMPLETE_FIELD_UAT")
        self.assertEqual(review(self.write(d))["status"], "INCOMPLETE_SELF_ATTESTATION")

    def test_mismatched_audit_must_reject(self):
        d = complete()
        d["desktop_audit_events"] = 0
        with self.assertRaises(ValueError):
            review(self.write(d))

    def test_forged_completion_flag_must_reject(self):
        d = complete()
        d["sound_audible_self_report"] = False
        with self.assertRaises(ValueError):
            review(self.write(d))

    def test_human_only_does_not_equal_business_decision(self):
        d = complete()
        d["business_approvals"] = 1
        with self.assertRaises(ValueError):
            review(self.write(d))

    def test_forced_production_or_login_autorun_rejected(self):
        for field in ("production_accepted", "actual_login_autorun_verified"):
            d = complete()
            d[field] = True
            with self.subTest(field=field), self.assertRaises(ValueError):
                review(self.write(d))

    def test_boolean_masquerading_as_integer_rejected(self):
        for field in ("ack_receipts", "business_approvals", "desktop_audit_events"):
            d = complete()
            d[field] = True
            with self.subTest(field=field), self.assertRaises(ValueError):
                review(self.write(d))

    def test_boolean_masquerading_as_number_rejected(self):
        d = complete()
        d["session_interactive"] = 1
        with self.assertRaises(ValueError):
            review(self.write(d))

    def test_unknown_fields_must_not_leak_private_data(self):
        d = complete()
        d["user_email"] = "school-secret@example.invalid"
        with self.assertRaises(ValueError):
            review(self.write(d))

    def test_reject_duplicate_json_fields(self):
        raw = json.dumps(complete()).replace('"status":', '"status": "INCOMPLETE_FIELD_UAT", "status":')
        self.report.write_text(raw, encoding="utf-8")
        with self.assertRaises(ValueError):
            review(self.report)

    def test_symlink_and_oversize_rejected(self):
        self.write(complete())
        link = self.root / "link.json"
        try:
            link.symlink_to(self.report)
        except (OSError, NotImplementedError):
            pass
        else:
            with self.assertRaises(ValueError):
                review(link)
        self.report.write_bytes(b" " * 8193)
        with self.assertRaises(ValueError):
            review(self.report)

    def test_read_only_report_unmodified(self):
        self.write(complete())
        old = self.report.read_bytes()
        review(self.report)
        self.assertEqual(old, self.report.read_bytes())
        self.assertEqual({p.name for p in self.root.iterdir()}, {"uat.json"})

    def test_cli_safe_ascii_and_no_sensitive_paths(self):
        self.write(complete())
        cp = subprocess.run(
            [sys.executable, "-m", "edu_workflow.uat_review", "--report", str(self.report)],
            cwd=ROOT, env=dict(os.environ, PYTHONPATH=str(ROOT / "python"),
                               PYTHONIOENCODING="cp1252"),
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(cp.returncode, 0, cp.stderr)
        data = json.loads(cp.stdout)
        self.assertFalse(data["production_accepted"])
        self.assertNotIn(str(self.report), cp.stdout)

    def test_invalid_cli_returns_code_two_without_report_detail(self):
        self.report.write_text('{"status": "FAKE"}', encoding="utf-8")
        cp = subprocess.run(
            [sys.executable, "-m", "edu_workflow.uat_review", "--report", str(self.report)],
            cwd=ROOT, env=dict(os.environ, PYTHONPATH=str(ROOT / "python")),
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(cp.returncode, 2)
        self.assertEqual(cp.stderr.strip(), "W17_REPORT_REJECTED")

    def test_cmd_template_hardcodes_hash_never_bypasses_policy(self):
        script = CMD.read_text(encoding="utf-8")
        self.assertIn("__EXPECTED_SHA256__", script)
        self.assertIn('start "" /wait', script)
        self.assertIn("W17_KIT_HASH_VERIFIED_NO_GUI", script)
        self.assertIn('"%~1"=="--verify-only"', script)
        self.assertIn("certutil -hashfile", script)
        for forbidden in ("-ExecutionPolicy", "powershell.exe", "schtasks",
                          "reg add", "taskkill", "setx ", "Outlook.Application",
                          "Invoke-WebRequest", "curl "):
            self.assertNotIn(forbidden, script)
        self.assertNotIn("wscript", script.lower())


if __name__ == "__main__":
    unittest.main()
