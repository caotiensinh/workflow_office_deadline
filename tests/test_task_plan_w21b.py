"""W21B cannot confuse safe static scheduler plan with actual execution."""
import copy
import json
import tempfile
import unittest
from pathlib import Path

from edu_workflow.task_plan_w21b import read_plan, validate, main


def safe():
    return {"task_name": "EducationAIWorkflow", "interval_minutes": 15,
            "command": 'powershell.exe -NoProfile -File "C:\\test\\repo\\windows\\run_once.ps1" -Channel file',
            "source": "none", "notification_channel": "file",
            "replaces_existing": False}


class W21BTaskPlanTests(unittest.TestCase):
    def setUp(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        self.root = Path(td.name)
        self.plan = self.root / "plan.json"
        self.plan.write_text(json.dumps(safe()), encoding="utf-8")

    def test_static_15min_plan_not_live_acceptance(self):
        r = validate(safe())
        self.assertEqual(r["status"], "OFFLINE_15_MIN_PLAN_CONSISTENT_NOT_REGISTERED")
        self.assertEqual(r["planned_interval_minutes"], 15)
        for name in ("task_created","actual_15minute_execution_observed","task_scheduler_read",
                     "outlook_accessed","smtp_sent","policy_changed","it_approved",
                     "production_accepted"):
            self.assertFalse(r[name])

    def test_plan_file_is_not_modified(self):
        before = self.plan.read_bytes()
        self.assertEqual(read_plan(self.plan)["channel"], "file")
        self.assertEqual(before, self.plan.read_bytes())

    def test_wrong_interval_rejected(self):
        for interval in (0, 5, 10, 30, 60, True, 15.0):
            d = safe()
            d["interval_minutes"] = interval
            with self.subTest(interval=interval), self.assertRaises(ValueError):
                validate(d)

    def test_outlook_or_smtp_flags_rejected(self):
        for key, value in (("source","outlook-classic"), ("notification_channel","smtp")):
            d = safe()
            d[key] = value
            with self.assertRaises(ValueError):
                validate(d)

    def test_force_replacement_rejected(self):
        d = safe()
        d["replaces_existing"] = True
        with self.assertRaises(ValueError):
            validate(d)

    def test_wrong_task_name_rejected(self):
        d = safe()
        d["task_name"] = "Microsoft Update"
        with self.assertRaises(ValueError):
            validate(d)

    def test_unapproved_command_flags_rejected(self):
        for change in (" -ImportOutlookClassic", " -Channel smtp",
                       " -ExecutionPolicy Bypass", " & whoami", " | curl"):
            d = safe()
            d["command"] += change
            with self.subTest(change=change), self.assertRaises(ValueError):
                validate(d)

    def test_path_metacharacters_rejected(self):
        for token in ("%USERNAME%", "$env:TOKEN", "!", "^", ";", "..\\"):
            d = safe()
            d["command"] = d["command"].replace("repo", "rep" + token + "o")
            with self.subTest(token=token), self.assertRaises(ValueError):
                validate(d)

    def test_duplicate_keys_rejected(self):
        self.plan.write_text('{"task_name":"EducationAIWorkflow","task_name":"Forged"}',
                             encoding="utf-8")
        with self.assertRaises(ValueError):
            read_plan(self.plan)

    def test_extra_fields_rejected(self):
        d = safe()
        d["private_email"] = "sensitive@example.invalid"
        with self.assertRaises(ValueError):
            validate(d)

    def test_symlink_rejected(self):
        link = self.root / "symlink.json"
        try:
            link.symlink_to(self.plan)
        except (OSError, NotImplementedError):
            self.skipTest("Host cannot create symlinks")
        with self.assertRaises(ValueError):
            read_plan(link)

    def test_cli_invalid_exposes_no_input_details(self):
        self.plan.write_text("invalid", encoding="utf-8")
        self.assertEqual(main(["--plan", str(self.plan)]), 2)


if __name__ == "__main__":
    unittest.main()
