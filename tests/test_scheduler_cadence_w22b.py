"""W22B exact sanitized cadence model never approves live task execution."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from edu_workflow.scheduler_cadence_w22b import assess, read_local, main


def sample():
    return {"schema_version": 1, "source": "operator-sanitized-local-export",
            "task_name": "EducationAIWorkflow",
            "events": [{"started_at_utc": f"2026-10-20T00:{minute:02d}:00Z", "exit_code": 0}
                       for minute in (0,15,30)]}


class W22BCadenceTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.dir = Path(temp.name)
        self.path = self.dir / "export.json"
        self.path.write_text(json.dumps(sample()), encoding="utf-8")

    def test_three_sanitized_events_are_not_authenticated(self):
        r = assess(sample())
        self.assertEqual(r["sample_count"], 3)
        self.assertEqual(r["status"], "SANITIZED_TIMESTAMPS_CONSISTENT_NOT_AUTHENTICATED")
        for k in ("source_cryptographically_verified", "live_task_scheduler_queried",
                  "real_task_execution_independently_verified", "it_approved",
                  "production_accepted", "modifies_machine", "outlook_accessed",
                  "smtp_sent"):
            self.assertFalse(r[k])

    def test_source_not_modified(self):
        old = self.path.read_bytes()
        read_local(self.path)
        self.assertEqual(old, self.path.read_bytes())

    def test_nonzero_exit_rejected(self):
        d = sample()
        d["events"][1]["exit_code"] = 1
        with self.assertRaises(ValueError): assess(d)

    def test_boolean_exit_rejected(self):
        d = sample()
        d["events"][1]["exit_code"] = False
        with self.assertRaises(ValueError): assess(d)

    def test_too_few_or_too_many_events(self):
        for count in (0, 1, 2, 9):
            d = sample()
            d["events"] = d["events"][:1] * count
            with self.subTest(count=count), self.assertRaises(ValueError): assess(d)

    def test_duplicate_or_reversed_events_rejected(self):
        for values in (("00:00:00","00:00:00","00:15:00"),
                       ("00:30:00","00:15:00","00:00:00")):
            d=sample()
            for event,time in zip(d["events"], values):
                event["started_at_utc"]="2026-10-20T"+time+"Z"
            with self.assertRaises(ValueError): assess(d)

    def test_cadence_early_and_late_rejected(self):
        for t in ("00:13:59","00:16:01"):
            d=sample()
            d["events"][1]["started_at_utc"]="2026-10-20T"+t+"Z"
            with self.subTest(t=t), self.assertRaises(ValueError): assess(d)

    def test_cadence_one_minute_jitter_allowed(self):
        d=sample()
        d["events"][1]["started_at_utc"]="2026-10-20T00:16:00Z"
        r=assess(d)
        self.assertTrue(r["intervals_within_60_seconds"])

    def test_forged_it_approval_field_rejected(self):
        d=sample()
        d["it_approved"]=True
        with self.assertRaises(ValueError): assess(d)

    def test_duplicate_json_properties_rejected(self):
        self.path.write_text('{"schema_version":1,"schema_version":1}',encoding="utf-8")
        with self.assertRaises(ValueError): read_local(self.path)

    def test_filename_symlink_rejected(self):
        link=self.dir/"link.json"
        try: link.symlink_to(self.path)
        except (OSError,NotImplementedError): self.skipTest("Symlink unavailable")
        with self.assertRaises(ValueError): read_local(link)

    def test_cli_bad_input_fail_closed(self):
        self.path.write_text("private",encoding="utf-8")
        self.assertEqual(main(["--evidence",str(self.path)]),2)

    def test_invalid_timezone_or_fraction_rejected(self):
        for suffix in ("+00:00","Z ", ".000Z"):
            d=sample()
            d["events"][1]["started_at_utc"]="2026-10-20T00:15:00"+suffix
            with self.subTest(suffix=suffix),self.assertRaises(ValueError): assess(d)


if __name__=="__main__":
    unittest.main()
