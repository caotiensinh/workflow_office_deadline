"""W23B real local summary handoff is self-report, not independent approval."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from edu_workflow import field_uat_launcher as launcher
from edu_workflow.uat_review import review


def fixture():
    return {"scope":"fictional-local-data-only",
            "type":"human-self-attested-Windows-field-UAT",
            "session_interactive":True,
            "visual_japanese_self_report":True,
            "sound_audible_self_report":True,
            "window_interactive_self_report":True,
            "ack_receipts":1, "snooze_receipts":1, "desktop_audit_events":2,
            "business_approvals":0, "human_buttons_recorded":True,
            "actual_login_autorun_verified":False,
            "production_accepted":False,
            "status":"DESKTOP_ACTIONS_AND_HUMAN_REPORT_COMPLETE"}


class W23BOperatorSummaryTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.source=self.root/"operator_self_report.json"
        self.out=self.root/"safe_summary.json"
        self.source.write_text(json.dumps(fixture()),encoding="utf-8")

    def handoff(self, reviewed=None):
        if reviewed is None:
            reviewed=review(self.source)
        return launcher.write_operator_handoff(self.source,reviewed,output_file=self.out)

    def test_accepted_self_report_not_it_signoff(self):
        path=self.handoff()
        self.assertEqual(path,self.out)
        evidence=json.loads(self.out.read_text(encoding="utf-8"))
        self.assertTrue(evidence["synthetic_only"])
        self.assertEqual(evidence["status"],
                         "CONSISTENT_SELF_ATTESTATION_NOT_INDEPENDENTLY_VERIFIED")
        self.assertEqual(evidence["ack_receipts"],1)
        self.assertEqual(evidence["snooze_receipts"],1)
        self.assertEqual(evidence["source_report_sha256"],
                         hashlib.sha256(self.source.read_bytes()).hexdigest().upper())
        for key in ("human_gui_independently_verified",
                    "windows_login_autorun_verified","it_approved",
                    "publisher_signature_verified","production_accepted",
                    "outlook_accessed","smtp_sent"):
            self.assertFalse(evidence[key])
        for forbidden in ("PRIVATE","email","username","case_id","actor","source_path"):
            self.assertNotIn(forbidden, json.dumps(evidence).lower())

    def test_input_report_unchanged(self):
        before=self.source.read_bytes()
        self.handoff()
        self.assertEqual(self.source.read_bytes(),before)

    def test_no_overwrite_of_existing_it_report(self):
        self.out.write_text("old trusted evidence",encoding="utf-8")
        with self.assertRaises(FileExistsError):
            self.handoff()
        self.assertEqual(self.out.read_text(encoding="utf-8"),"old trusted evidence")

    def test_report_missing_blocks_new_handoff(self):
        self.source.unlink()
        with self.assertRaises(ValueError):
            launcher.write_operator_handoff(self.source,{},output_file=self.out)
        self.assertFalse(self.out.exists())

    def test_reviewed_facts_must_match_original(self):
        data=review(self.source)
        data["ack_receipts"]=10
        with self.assertRaises(ValueError):
            self.handoff(data)
        self.assertFalse(self.out.exists())

    def test_forged_production_status_rejected(self):
        data=fixture()
        data["production_accepted"]=True
        self.source.write_text(json.dumps(data),encoding="utf-8")
        with self.assertRaises(ValueError):
            self.handoff(data)
        self.assertFalse(self.out.exists())

    def test_bad_out_directory_refused(self):
        with self.assertRaises(ValueError):
            launcher.write_operator_handoff(
                self.source,review(self.source),output_file=self.root/"missing"/"out.json")

    def test_partial_report_handoff_stays_incomplete(self):
        data=fixture()
        data["sound_audible_self_report"]=False
        data["status"]="INCOMPLETE_FIELD_UAT"
        self.source.write_text(json.dumps(data),encoding="utf-8")
        self.handoff()
        report=json.loads(self.out.read_text(encoding="utf-8"))
        self.assertEqual(report["status"],"INCOMPLETE_SELF_ATTESTATION")
        self.assertFalse(report["production_accepted"])

    def test_one_click_operator_gets_report_and_handoff(self):
        def run(path):
            path.write_text(json.dumps(fixture()),encoding="utf-8")
            return {"status":"DESKTOP_ACTIONS_AND_HUMAN_REPORT_COMPLETE",
                    "production_accepted":False}
        with patch.object(launcher,"_require_interactive_windows"),patch.object(
                launcher,"_ask_consent",return_value=True),patch.object(
                launcher,"_report_path",return_value=self.root/"new_report.json"),patch.object(
                launcher,"_operator_summary_path",return_value=self.out),patch.object(
                launcher,"run_manual",side_effect=run),patch.object(
                launcher,"_show_result") as dialog:
            result=launcher.one_click()
        self.assertEqual(result["status"],"DESKTOP_ACTIONS_AND_HUMAN_REPORT_COMPLETE")
        self.assertTrue(self.out.is_file())
        self.assertIn("IT review summary:",dialog.call_args.args[0])
        self.assertIn("NOT independent GUI",dialog.call_args.args[0])


if __name__=="__main__":
    unittest.main()
