"""W25A fail-closed offline original UAT ↔ handoff review."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from edu_workflow import field_uat_launcher as launcher
from edu_workflow.uat_pair_w25a import reconcile, main
from test_operator_handoff_w23b import fixture
from edu_workflow.uat_review import review


class W25APairTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.source=self.root/"source.json"
        self.summary=self.root/"summary.json"
        self.out=self.root/"checked.json"
        self.source.write_text(json.dumps(fixture()), encoding="utf-8")
        launcher.write_operator_handoff(self.source, review(self.source),
                                        output_file=self.summary)

    def test_real_w23_pair_reconciles_no_authority(self):
        r=reconcile(self.source,self.summary)
        self.assertEqual(r["status"],"MATCHED_TWO_LOCAL_FILES_NOT_INDEPENDENT_GUI_UAT")
        self.assertTrue(r["source_sha256_matches_handoff"])
        self.assertEqual(r["ack_receipts"],1)
        for key in ("cryptographically_signed","independent_human_gui_observation",
                    "login_autorun_observed","it_approved","production_accepted",
                    "modifies_inputs","outlook_accessed","smtp_sent"):
            self.assertFalse(r[key])

    def test_report_bytes_unchanged(self):
        old=(self.source.read_bytes(),self.summary.read_bytes())
        reconcile(self.source,self.summary)
        self.assertEqual(old,(self.source.read_bytes(),self.summary.read_bytes()))

    def test_digest_tamper_rejected(self):
        d=json.loads(self.summary.read_text(encoding="utf-8"))
        d["source_report_sha256"]="F"*64
        self.summary.write_text(json.dumps(d),encoding="utf-8")
        with self.assertRaises(ValueError):reconcile(self.source,self.summary)

    def test_report_reformat_has_new_digest(self):
        self.source.write_text(json.dumps(fixture(),indent=4),encoding="utf-8")
        with self.assertRaises(ValueError):reconcile(self.source,self.summary)

    def test_forged_authority_flag_rejected(self):
        for key in ("it_approved","production_accepted","human_gui_independently_verified",
                    "publisher_signature_verified","windows_login_autorun_verified"):
            d=json.loads(self.summary.read_text(encoding="utf-8"))
            d[key]=True
            self.summary.write_text(json.dumps(d),encoding="utf-8")
            with self.subTest(key=key),self.assertRaises(ValueError):
                reconcile(self.source,self.summary)
            d[key]=False
            self.summary.write_text(json.dumps(d),encoding="utf-8")

    def test_receipt_count_mismatch_rejected(self):
        d=json.loads(self.summary.read_text(encoding="utf-8"))
        d["ack_receipts"]=2
        self.summary.write_text(json.dumps(d),encoding="utf-8")
        with self.assertRaises(ValueError):reconcile(self.source,self.summary)

    def test_private_unknown_field_rejected(self):
        d=json.loads(self.summary.read_text(encoding="utf-8"))
        d["recipient"]="private@example.invalid"
        self.summary.write_text(json.dumps(d),encoding="utf-8")
        with self.assertRaises(ValueError):reconcile(self.source,self.summary)

    def test_duplicate_json_field_rejected(self):
        self.summary.write_text(self.summary.read_text(encoding="utf-8").replace(
            '"status":','"status":"FAKE","status":'),encoding="utf-8")
        with self.assertRaises(ValueError):reconcile(self.source,self.summary)

    def test_symlink_or_missing_rejected(self):
        self.summary.unlink()
        with self.assertRaises(ValueError):reconcile(self.source,self.summary)
        try:self.summary.symlink_to(self.source)
        except (OSError,NotImplementedError):return
        with self.assertRaises(ValueError):reconcile(self.source,self.summary)

    def test_incomplete_self_report_still_consistent_but_not_approval(self):
        d=fixture()
        d["sound_audible_self_report"]=False
        d["status"]="INCOMPLETE_FIELD_UAT"
        self.source.write_text(json.dumps(d),encoding="utf-8")
        self.summary.unlink()
        launcher.write_operator_handoff(self.source, review(self.source),output_file=self.summary)
        r=reconcile(self.source,self.summary)
        self.assertEqual(r["status"],"MATCHED_INCOMPLETE_SELF_REPORT_NOT_INDEPENDENT_GUI_UAT")
        self.assertFalse(r["production_accepted"])

    def test_cli_output_exclusive(self):
        self.assertEqual(main(["--report",str(self.source),"--summary",str(self.summary),
                               "--out",str(self.out)]),0)
        self.assertTrue(self.out.is_file())
        with self.assertRaises(FileExistsError):
            # direct write refuses old files; CLI catches and returns code 2
            with self.out.open("x",encoding="utf-8"):pass
        self.assertEqual(main(["--report",str(self.source),"--summary",str(self.summary),
                               "--out",str(self.out)]),2)

    def test_packaged_launcher_cli_never_opens_gui_or_checks_session(self):
        with patch.object(launcher,"one_click") as gui,patch.object(
                launcher.session_guard,"inspect") as guard:
            launcher.main(["--pair-report-file",str(self.source),
                           "--pair-summary-file",str(self.summary),
                           "--pair-output-file",str(self.out)])
        gui.assert_not_called()
        guard.assert_not_called()
        self.assertFalse(json.loads(self.out.read_text())["production_accepted"])

    def test_launcher_rejects_wrong_pair_silently(self):
        d=json.loads(self.summary.read_text(encoding="utf-8"))
        d["status"]="INCOMPLETE_SELF_ATTESTATION"
        self.summary.write_text(json.dumps(d),encoding="utf-8")
        with self.assertRaises(SystemExit) as cm:
            launcher.main(["--pair-report-file",str(self.source),
                           "--pair-summary-file",str(self.summary),
                           "--pair-output-file",str(self.out)])
        self.assertEqual(cm.exception.code,2)
        self.assertFalse(self.out.exists())


if __name__=="__main__":
    unittest.main()
