"""W12 monitor: actual SQLite read-only aggregate dashboard with no unsafe recovery."""
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from edu_workflow.monitoring import html_dashboard, save_html_new, snapshot
from edu_workflow.store import add_case, open_store

ROOT = Path(__file__).resolve().parents[1]
NOW = "2026-10-20T15:00:00+09:00"
UTC = "2026-10-20T06:00:00+00:00"
PRIVATE = "DO_NOT_EXPOSE_PRIVATE_HR_TEXT@example.invalid"
CASE = {
    "case_id": "W12-SYNTH", "kind": "EMAIL", "data_class": "RESTRICTED",
    "safe_title": PRIVATE, "owner": PRIVATE,
    "status": "IN_PROGRESS", "approval_status": "NOT_REQUIRED",
    "due_at": "2026-10-22T17:00:00+09:00",
    "due_verified": True, "evidence_ref": None,
}


class MonitoringTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)
        self.file = self.dir / "source.sqlite"
        self.con = open_store(self.file)
        self.addCleanup(self.con.close)
        add_case(self.con, dict(CASE))

    def insert(self, state, age=0, id_no=1, when=None):
        from datetime import timedelta
        dt = datetime.fromisoformat(UTC) - timedelta(minutes=age)
        timestamp = when if when is not None else dt.isoformat()
        with self.con:
            self.con.execute(
                "INSERT INTO alerts(alert_id,case_id,revision,code,severity,day,message,state,created_at) "
                "VALUES(?,?,?,?,?,?,?,?,?)",
                (f"{id_no:064x}", "W12-SYNTH", 1, "DUE", "HIGH", "2026-10-20",
                 PRIVATE, state, timestamp),
            )

    def snap(self, **kw):
        return snapshot(self.file, at=NOW, **kw)

    def test_healthy_with_no_alerts(self):
        x = self.snap()
        self.assertEqual(x["status"], "HEALTHY")
        self.assertEqual(x["db_integrity"], "PASS")
        self.assertEqual(sum(x["counts"].values()), 0)
        self.assertEqual((x["cases_count"], x["audit_count"], x["decisions_count"]),
                         (1, 1, 0))
        self.assertEqual(x["incidents"], [])
        self.assertFalse(x["requires_human"])
        self.assertTrue(x["read_only"])
        for k in ("database_created", "messages_resent",
                  "production_accepted", "external_actions_performed"):
            self.assertFalse(x[k])

    def test_healthy_sent_and_stale(self):
        self.insert("SENT", age=300, id_no=1)
        self.insert("STALE", age=300, id_no=2)
        x = self.snap()
        self.assertEqual(x["status"], "HEALTHY")
        self.assertEqual((x["counts"]["SENT"], x["counts"]["STALE"]), (1, 1))

    def test_recent_queue_not_old(self):
        self.insert("QUEUED", age=29)
        x = self.snap()
        self.assertEqual(x["status"], "HEALTHY")
        self.assertEqual(x["oldest_queued_age_minutes"], 29)

    def test_exact_queue_threshold(self):
        self.insert("QUEUED", age=30)
        x = self.snap(queue_max_minutes=30)
        self.assertEqual(x["status"], "WARNING")
        self.assertEqual(x["incidents"][0]["code"], "OVERDUE_QUEUED")

    def test_queue_minimum_age_is_oldest_event(self):
        self.insert("QUEUED", age=8, id_no=1)
        self.insert("QUEUED", age=99, id_no=2)
        x = self.snap(queue_max_minutes=90)
        self.assertEqual(x["oldest_queued_age_minutes"], 99)
        self.assertEqual(x["counts"]["QUEUED"], 2)
        self.assertEqual(len(x["incidents"]), 1)

    def test_unknown_remains_quarantined_without_retries(self):
        self.insert("UNKNOWN", age=120)
        before = self.con.execute("SELECT state FROM alerts").fetchone()[0]
        x = self.snap()
        after = self.con.execute("SELECT state FROM alerts").fetchone()[0]
        self.assertEqual((before, after), ("UNKNOWN", "UNKNOWN"))
        self.assertEqual(x["status"], "CRITICAL")
        self.assertEqual(x["incidents"][0]["code"], "UNKNOWN_DELIVERY")
        self.assertFalse(x["incidents"][0]["automated_retry_allowed"])
        self.assertNotIn(PRIVATE, json.dumps(x, ensure_ascii=False))

    def test_sending_any_age_requires_reconciliation(self):
        self.insert("SENDING", age=1)
        x = self.snap()
        self.assertEqual(x["status"], "CRITICAL")
        self.assertEqual(x["incidents"][0]["code"], "SENDING_RECONCILIATION")
        self.assertEqual(x["oldest_sending_age_minutes"], 1)

    def test_multiple_incidents_are_sorted_and_priority_critical(self):
        self.insert("SENDING", age=15, id_no=1)
        self.insert("UNKNOWN", age=40, id_no=2)
        self.insert("QUEUED", age=80, id_no=3)
        x = self.snap()
        self.assertEqual(x["status"], "CRITICAL")
        self.assertEqual([r["code"] for r in x["incidents"]],
                         ["OVERDUE_QUEUED", "SENDING_RECONCILIATION", "UNKNOWN_DELIVERY"])

    def test_invalid_date_fails_as_warning_not_healthy(self):
        self.insert("QUEUED", when="not-a-date")
        x = self.snap()
        self.assertEqual(x["status"], "WARNING")
        self.assertEqual(x["incidents"][0]["code"], "INVALID_TIME_METADATA")

    def test_future_date_fails_closed(self):
        self.insert("QUEUED", when="2027-01-01T00:00:00+00:00")
        self.assertEqual(self.snap()["incidents"][0]["code"], "INVALID_TIME_METADATA")

    def test_read_only_existing_db_not_mutated(self):
        self.insert("UNKNOWN", age=5)
        baseline = self.con.execute("SELECT state, message FROM alerts").fetchall()
        before = set(p.name for p in self.dir.iterdir())
        for i in range(4):
            self.snap()
        after = set(p.name for p in self.dir.iterdir())
        self.assertEqual(before, after)
        self.assertEqual([tuple(x) for x in baseline],
                         [tuple(x) for x in self.con.execute("SELECT state,message FROM alerts")])
        self.assertEqual(self.con.execute("SELECT COUNT(*) FROM decisions").fetchone()[0], 0)

    def test_missing_db_stays_missing(self):
        missing = self.dir / "never.sqlite"
        x = snapshot(missing, at=NOW)
        self.assertEqual(x["status"], "CRITICAL")
        self.assertEqual(x["incidents"][0]["code"], "DATABASE_MISSING")
        self.assertFalse(missing.exists())
        self.assertEqual(list(self.dir.glob("never.sqlite*")), [])

    def test_corrupt_db_does_not_attempt_repair(self):
        corrupt = self.dir / "corrupt.sqlite"
        original = b"not a sqlite file"
        corrupt.write_bytes(original)
        x = snapshot(corrupt, at=NOW)
        self.assertEqual(x["status"], "CRITICAL")
        self.assertEqual(x["incidents"][0]["code"], "DATABASE_READ_FAILED")
        self.assertEqual(corrupt.read_bytes(), original)

    def test_schema_mismatch(self):
        bad = self.dir / "empty.sqlite"
        # sqlite3 Connection context-manager commits but does NOT close;
        # Windows holds a filesystem lock until the handle is explicitly closed.
        con = sqlite3.connect(bad)
        try:
            con.execute("CREATE TABLE unrelated(x int)")
            con.commit()
        finally:
            con.close()
        x = snapshot(bad, at=NOW)
        self.assertEqual(x["incidents"][0]["code"], "SCHEMA_MISMATCH")

    def test_symlink_db_rejected(self):
        target = self.dir / "source_alias.sqlite"
        try:
            target.symlink_to(self.file)
        except (OSError, NotImplementedError):
            self.skipTest("symlink unsupported on this Windows endpoint")
        self.assertEqual(snapshot(target, at=NOW)["incidents"][0]["code"], "DATABASE_MISSING")

    def test_clock_threshold_input_guards(self):
        for age in (0, 10081, True, "30"):
            with self.assertRaises(ValueError):
                self.snap(queue_max_minutes=age)
        with self.assertRaises(ValueError):
            snapshot(self.file, at="2026-10-20")
        with self.assertRaises(ValueError):
            snapshot(self.file, at="yesterday")
        with self.assertRaises(ValueError):
            self.snap(quick_check=1)
        self.assertEqual(self.snap(quick_check=False)["db_integrity"], "NOT_CHECKED")

    def test_html_offline_no_network_script_or_personal_data(self):
        self.insert("UNKNOWN", age=2)
        x = self.snap()
        out = html_dashboard(x)
        self.assertIn('lang="ja"', out)
        self.assertIn("ローカル監視", out)
        self.assertIn("default-src 'none'", out)
        self.assertIn("UNKNOWN", out)
        self.assertNotIn("<script", out.lower())
        self.assertNotIn("http:", out)
        self.assertNotIn("https:", out)
        self.assertNotIn(PRIVATE, out)
        self.assertNotIn("case_id", out)

    def test_output_file_exclusive_no_existing_report_overwrite(self):
        p = self.dir / "monitor.html"
        x = self.snap()
        self.assertEqual(save_html_new(x, p), p)
        old = p.read_bytes()
        with self.assertRaises(FileExistsError):
            save_html_new(x, p)
        self.assertEqual(p.read_bytes(), old)
        self.assertNotIn(PRIVATE.encode("utf-8"), old)

    def test_cli_missing_db_exit_three_no_sqlite(self):
        missing = self.dir / "must-not-exist.sqlite"
        p = subprocess.run(
            [sys.executable, "-m", "edu_workflow.cli", "--db", str(missing),
             "monitor", "--at", NOW],
            cwd=ROOT, env=dict(os.environ, PYTHONPATH=str(ROOT / "python"),
                               PYTHONIOENCODING="cp1252"),
            text=True, capture_output=True)
        self.assertEqual(p.returncode, 3, p.stderr)
        self.assertEqual(json.loads(p.stdout)["status"], "CRITICAL")
        self.assertFalse(missing.exists())

    def test_cli_html_report_from_actual_db_and_no_mutations(self):
        self.insert("UNKNOWN", age=1)
        file = self.dir / "report.html"
        args = [sys.executable, "-m", "edu_workflow.cli", "--db", str(self.file),
                "monitor", "--at", NOW, "--format", "html", "--output", str(file)]
        p = subprocess.run(args, cwd=ROOT,
                           env=dict(os.environ, PYTHONPATH=str(ROOT / "python"),
                                    PYTHONIOENCODING="cp1252"),
                           capture_output=True, text=True)
        self.assertEqual(p.returncode, 3, p.stderr)
        self.assertEqual(json.loads(p.stdout)["status"], "CRITICAL")
        self.assertIn("ローカル監視", file.read_text(encoding="utf-8"))
        self.assertEqual(self.con.execute("SELECT state FROM alerts").fetchone()[0], "UNKNOWN")
        second = subprocess.run(args, cwd=ROOT,
                                env=dict(os.environ, PYTHONPATH=str(ROOT / "python")),
                                text=True, capture_output=True)
        self.assertEqual(second.returncode, 2)
        self.assertEqual(len(list(self.dir.glob("report.html"))), 1)

if __name__ == "__main__":
    unittest.main()
