"""W22C Outlook preflight may not touch messages, credentials or approvals."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from edu_workflow.outlook_readiness_w22c import evaluate, from_file, main


def sample():
    return {"adapter":"outlook-classic","mode":"manual-opt-in",
            "scope":"unread-inbox-only","max_unread":10,
            "send_enabled":False,"modify_read_state":False,
            "it_approval_recorded":False,"use_real_data":False}


class OutlookReadinessW22CTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir=Path(tmp.name)
        self.file=self.dir/"outlook-plan.json"
        self.file.write_text(json.dumps(sample()),encoding="utf-8")

    def test_safe_plan_remains_not_authorized(self):
        result=evaluate(sample())
        self.assertEqual(result["status"],"OFFLINE_CLASSIC_READONLY_PLAN_NOT_AUTHORIZED")
        self.assertEqual(result["messages_read"],0)
        for flag in ("real_outlook_accessed","send_enabled","read_state_changed",
                     "credential_collected","it_approved","production_accepted"):
            self.assertFalse(result[flag])

    def test_no_source_write(self):
        before=self.file.read_bytes()
        from_file(self.file)
        self.assertEqual(before,self.file.read_bytes())

    def test_no_com_modules_imported(self):
        with patch.dict("sys.modules",{"win32com":None,"win32com.client":None}):
            self.assertEqual(from_file(self.file)["messages_read"],0)

    def test_other_outlook_adapter_or_graph_rejected(self):
        for adapter in ("new-outlook","graph","exchange",None):
            d=sample()
            d["adapter"]=adapter
            with self.subTest(adapter=adapter), self.assertRaises(ValueError):evaluate(d)

    def test_real_data_and_it_approval_flags_rejected(self):
        for field in ("it_approval_recorded","use_real_data","send_enabled","modify_read_state"):
            d=sample()
            d[field]=True
            with self.subTest(field=field),self.assertRaises(ValueError): evaluate(d)

    def test_wrong_mailbox_scope_rejected(self):
        d=sample()
        d["scope"]="all-mailboxes"
        with self.assertRaises(ValueError):evaluate(d)

    def test_wrong_mode_rejected(self):
        d=sample()
        d["mode"]="automatic-background"
        with self.assertRaises(ValueError): evaluate(d)

    def test_max_unread_bounded_integer(self):
        for v in (0,51,100,True,10.0):
            d=sample()
            d["max_unread"]=v
            with self.subTest(value=v),self.assertRaises(ValueError):evaluate(d)

    def test_extra_email_address_field_rejected(self):
        d=sample()
        d["email"]="private@example.invalid"
        with self.assertRaises(ValueError):evaluate(d)

    def test_repeated_keys_fail_closed(self):
        self.file.write_text('{"adapter":"outlook-classic","adapter":"graph"}', encoding="utf-8")
        with self.assertRaises(ValueError):from_file(self.file)

    def test_symlink_refused(self):
        link=self.dir/"link.json"
        try:link.symlink_to(self.file)
        except (OSError,NotImplementedError):self.skipTest("Symlink unavailable")
        with self.assertRaises(ValueError):from_file(link)

    def test_cli_invalid_json(self):
        self.file.write_text("invalid-private",encoding="utf-8")
        self.assertEqual(main(["--plan",str(self.file)]),2)


if __name__=="__main__":
    unittest.main()
