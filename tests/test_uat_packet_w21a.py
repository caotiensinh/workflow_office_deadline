"""W21A fictional archive + independently saved report combinations."""
import hashlib
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from edu_workflow.uat_packet_w21a import review_packet, main
from edu_workflow.kit_integrity_w18 import TEMPLATE
from test_uat_review_w17 import complete


class W21AUATPacketTests(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.root = Path(t.name)
        self.exe = b"MZ" + b"synthetic not a real executable" * 5
        self.kit = self.root / "kit.zip"
        self.report = self.root / "report.json"
        template = TEMPLATE.read_text(encoding="utf-8")
        launcher = template.replace(
            "__EXPECTED_SHA256__", hashlib.sha256(self.exe).hexdigest().upper()
        )
        with zipfile.ZipFile(self.kit, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("EDUFieldUAT.exe", self.exe)
            zf.writestr("00_START_UAT.cmd", launcher.encode("ascii"))
            zf.writestr("W17_README_JP.txt", "架空通知テスト".encode("utf-8"))
        self.report.write_text(json.dumps(complete()), encoding="utf-8")

    def test_consistent_not_independent(self):
        result = review_packet(self.kit, self.report)
        self.assertTrue(result["status"].startswith("LOCAL_CONTENT_"))
        self.assertEqual(result["ack_receipts"], 1)
        self.assertEqual(result["snooze_receipts"], 1)
        self.assertTrue(result["self_attested_only"])
        for key in ("independent_session1_gui_verified",
                    "report_bound_cryptographically_to_binary",
                    "signed_publisher_verified", "windows_login_autorun_verified",
                    "scheduler_15minute_verified", "outlook_accessed",
                    "smtp_sent", "it_approved", "production_accepted",
                    "modifies_system", "modifies_zip_or_report"):
            self.assertFalse(result[key])

    def test_no_input_mutation(self):
        before = (self.kit.read_bytes(), self.report.read_bytes())
        review_packet(self.kit, self.report)
        self.assertEqual(before, (self.kit.read_bytes(), self.report.read_bytes()))

    def test_checked_expected_archive_sha(self):
        expected = hashlib.sha256(self.kit.read_bytes()).hexdigest()
        self.assertEqual(review_packet(self.kit, self.report, expected)["zip_sha256"], expected.upper())

    def test_wrong_archive_checksum_rejected(self):
        with self.assertRaises(ValueError):
            review_packet(self.kit, self.report, "0" * 64)

    def test_modified_zip_rejected(self):
        with zipfile.ZipFile(self.kit, "a") as zf:
            zf.writestr("unexpected.cmd", "should never run")
        with self.assertRaises(ValueError):
            review_packet(self.kit, self.report)

    def test_forged_business_approval_rejected(self):
        data = complete()
        data["business_approvals"] = 1
        self.report.write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaises(ValueError):
            review_packet(self.kit, self.report)

    def test_partial_report_not_pass(self):
        data = complete()
        data["sound_audible_self_report"] = False
        data["status"] = "INCOMPLETE_FIELD_UAT"
        self.report.write_text(json.dumps(data), encoding="utf-8")
        result = review_packet(self.kit, self.report)
        self.assertEqual(result["status"], "INCOMPLETE_SELF_REPORTED_GUI_UAT")
        self.assertFalse(result["production_accepted"])

    def test_missing_report_fails_closed(self):
        self.report.unlink()
        with self.assertRaises(ValueError):
            review_packet(self.kit, self.report)

    def test_outfile_exclusive_and_sanitized(self):
        out = self.root / "verified.json"
        self.assertEqual(main(["--kit-zip", str(self.kit),
                               "--uat-report", str(self.report),
                               "--out", str(out)]), 0)
        result = json.loads(out.read_text(encoding="utf-8"))
        self.assertNotIn("account", result)
        self.assertEqual(main(["--kit-zip", str(self.kit),
                               "--uat-report", str(self.report),
                               "--out", str(out)]), 2)

    def test_no_report_cannot_be_replaced_by_zip_hash(self):
        self.report.unlink()
        sha = hashlib.sha256(self.kit.read_bytes()).hexdigest()
        self.assertEqual(main(["--kit-zip", str(self.kit),
                               "--uat-report", str(self.report),
                               "--expected-zip-sha256", sha]), 2)


if __name__ == "__main__":
    unittest.main()
