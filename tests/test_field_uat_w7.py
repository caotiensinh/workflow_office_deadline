"""Safety/regression tests for W7 synthetic-only field acceptance fixtures."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from edu_workflow.desktop_center import list_notifications, mark_notification
from edu_workflow.field_uat import ALERT_IDS, inspect_actions, seed_synthetic
from edu_workflow.store import open_store


class W7FieldUATTests(unittest.TestCase):
    def test_synthetic_fixture_requires_absent_db_and_never_approves(self):
        with tempfile.TemporaryDirectory() as folder:
            db = Path(folder) / "synthetic.sqlite3"
            self.assertEqual(seed_synthetic(db), db)
            conn = open_store(db)
            try:
                items = list_notifications(conn, "field-user")
                self.assertEqual({x["alert_id"] for x in items}, set(ALERT_IDS))
                self.assertEqual(conn.execute("SELECT COUNT(*) FROM decisions").fetchone()[0], 0)
                for item in items:
                    self.assertNotIn("SYNTHETIC_NEVER_REAL_DATA", str(item))
            finally:
                conn.close()
            with self.assertRaises(FileExistsError):
                seed_synthetic(db)

    def test_manual_receipts_are_visibility_only_and_audited(self):
        with tempfile.TemporaryDirectory() as folder:
            db = seed_synthetic(Path(folder) / "synthetic.sqlite3")
            conn = open_store(db)
            try:
                self.assertFalse(inspect_actions(db, "tester")["human_buttons_recorded"])
                self.assertTrue(mark_notification(conn, ALERT_IDS[0], "tester", "ACK"))
                self.assertTrue(mark_notification(conn, ALERT_IDS[1], "tester", "SNOOZE"))
                self.assertEqual(len(list_notifications(conn, "tester")), 0)
                self.assertEqual(len(list_notifications(conn, "another-tester")), 2)
            finally:
                conn.close()
            status = inspect_actions(db, "tester")
            self.assertTrue(status["human_buttons_recorded"])
            self.assertEqual(status["business_approvals"], 0)
            self.assertEqual(status["desktop_audit_events"], 2)
            self.assertEqual((status["ack_receipts"], status["snooze_receipts"]), (1, 1))

    def test_cli_plan_only_does_not_create_database_or_report(self):
        with tempfile.TemporaryDirectory() as folder:
            result = subprocess.run(
                [sys.executable, "-m", "edu_workflow.field_uat", "--plan-only"],
                capture_output=True, text=True, check=True,
                cwd=folder,
            )
            plan = json.loads(result.stdout)
            self.assertEqual(plan["mode"], "plan-only")
            self.assertFalse(plan["changes_startup"])
            self.assertFalse(plan["production_accepted"])
            self.assertEqual(list(Path(folder).iterdir()), [])

    def test_manual_run_rejected_without_interactive_windows(self):
        from unittest.mock import patch
        from edu_workflow.field_uat import run_manual
        with tempfile.TemporaryDirectory() as folder:
            report = Path(folder) / "proof.json"
            with patch("edu_workflow.field_uat.sys.platform", "win32"), patch(
                "edu_workflow.field_uat.desktop_app._interactive_desktop_available",
                return_value=False,
            ):
                with self.assertRaisesRegex(RuntimeError, "BLOCKED_SESSION_0"):
                    run_manual(report)
            self.assertFalse(report.exists())


if __name__ == "__main__":
    unittest.main()
