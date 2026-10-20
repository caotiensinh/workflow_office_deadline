"""WF-06 safety: offline-only, bounded, deterministic, anonymous proposals."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from edu_workflow.schedule import propose_slots, propose_from_file

W = {"start": "2026-10-23T09:00:00+09:00", "end": "2026-10-23T12:00:00+09:00"}
FULL = [W]
BASE = {
    "window": W,
    "duration_minutes": 30,
    "slot_minutes": 15,
    "max_proposals": 4,
    "participants": [
        {"available": FULL, "busy": [{"start": "2026-10-23T09:30:00+09:00",
                                      "end": "2026-10-23T10:00:00+09:00"}]},
        {"available": [{"start": "2026-10-23T09:15:00+09:00",
                        "end": "2026-10-23T11:15:00+09:00"}],
         "busy": [{"start": "2026-10-23T10:30:00+09:00",
                   "end": "2026-10-23T10:45:00+09:00"}]},
    ],
}


class WF06ScheduleProposals(unittest.TestCase):
    def test_conflicts_skipped_and_earliest_fitting_proposals(self):
        result = propose_slots(deepcopy(BASE))
        self.assertEqual(result["status"], "PROPOSALS")
        self.assertEqual([x["start"][11:16] for x in result["proposals"]],
                         ["10:00", "10:45"])
        self.assertTrue(result["requires_human_approval"])
        self.assertFalse(result["calendar_verified"])
        self.assertFalse(result["external_actions_performed"])
        self.assertFalse(result["writes_database"])
        self.assertEqual(result["participant_count"], 2)

    def test_no_common_availability_is_not_approval(self):
        payload = deepcopy(BASE)
        payload["participants"][1]["available"] = [{
            "start": "2026-10-23T12:00:00+09:00",
            "end": "2026-10-23T13:00:00+09:00",
        }]
        result = propose_slots(payload)
        self.assertEqual(result["status"], "NO_COMMON_AVAILABILITY")
        self.assertEqual(result["proposals"], [])

    def test_timezone_offsets_normalize_to_jst(self):
        payload = deepcopy(BASE)
        payload["window"] = {"start": "2026-10-23T00:00:00+00:00",
                             "end": "2026-10-23T03:00:00+00:00"}
        x = propose_slots(payload)
        self.assertEqual(x["proposals"][0]["start"], "2026-10-23T10:00+09:00")

    def test_busy_end_boundary_is_available(self):
        payload = deepcopy(BASE)
        payload["participants"] = [
            {"available": FULL, "busy": [{"start": "2026-10-23T09:00:00+09:00",
                                            "end": "2026-10-23T09:30:00+09:00"}]},
            {"available": FULL, "busy": []},
        ]
        self.assertEqual(propose_slots(payload)["proposals"][0]["start"],
                         "2026-10-23T09:30+09:00")

    def test_rounds_partial_slot_up_not_backwards(self):
        payload = deepcopy(BASE)
        payload["participants"] = [
            {"available": [{"start": "2026-10-23T09:07:00+09:00",
                            "end": "2026-10-23T10:00:00+09:00"}]},
            {"available": FULL},
        ]
        self.assertEqual(propose_slots(payload)["proposals"][0]["start"],
                         "2026-10-23T09:15+09:00")

    def test_overlapping_availability_is_deduplicated(self):
        payload = deepcopy(BASE)
        payload["participants"] = [
            {"available": [W, W], "busy": []},
            {"available": FULL, "busy": []},
        ]
        result = propose_slots(payload)
        self.assertEqual(len({x["start"] for x in result["proposals"]}), 4)

    def test_naive_datetime_and_reversed_interval_fail_closed(self):
        for bad in (
            {"start": "2026-10-23T09:00:00", "end": W["end"]},
            {"start": W["end"], "end": W["start"]},
        ):
            payload = deepcopy(BASE)
            payload["window"] = bad
            with self.assertRaises(ValueError):
                propose_slots(payload)

    def test_rejects_unknown_fields_instead_of_recording_names(self):
        payload = deepcopy(BASE)
        payload["participants"][0]["name"] = "PRIVATE_EMPLOYEE_NAME"
        with self.assertRaises(ValueError) as ctx:
            propose_slots(payload)
        self.assertNotIn("PRIVATE_EMPLOYEE_NAME", str(ctx.exception))

    def test_limits_participants_intervals_and_dates(self):
        payload = deepcopy(BASE)
        payload["participants"] = payload["participants"] * 11
        with self.assertRaises(ValueError):
            propose_slots(payload)
        payload = deepcopy(BASE)
        payload["participants"][0]["busy"] = [W] * 33
        with self.assertRaises(ValueError):
            propose_slots(payload)
        payload = deepcopy(BASE)
        payload["window"]["end"] = "2026-12-23T12:00:00+09:00"
        with self.assertRaises(ValueError):
            propose_slots(payload)

    def test_boolean_integer_options_not_accepted(self):
        for key in ("duration_minutes", "slot_minutes", "max_proposals"):
            payload = deepcopy(BASE)
            payload[key] = True
            with self.assertRaises(ValueError):
                propose_slots(payload)

    def test_no_real_db_created_by_cli(self):
        project = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            src, db = root / "anonymous.json", root / "must-not-exist.sqlite"
            src.write_text(json.dumps(BASE), encoding="utf-8")
            env = dict(os.environ, PYTHONPATH=str(project / "python"))
            command = [sys.executable, "-m", "edu_workflow.cli",
                       "--db", str(db), "schedule-propose", "--file", str(src)]
            first = subprocess.run(command, cwd=project, env=env, text=True,
                                   capture_output=True, check=True)
            second = subprocess.run(command, cwd=project, env=env, text=True,
                                    capture_output=True, check=True)
            self.assertEqual(json.loads(first.stdout), json.loads(second.stdout))
            self.assertFalse(db.exists())
            self.assertFalse(any(root.glob("*-journal")))
            self.assertNotIn("PRIVATE_EMPLOYEE_NAME", first.stdout)

    def test_rejects_symlink_and_oversized_file(self):
        with tempfile.TemporaryDirectory() as folder:
            src = Path(folder) / "schedule.json"
            src.write_text(json.dumps(BASE), encoding="utf-8")
            self.assertEqual(propose_from_file(src)["status"], "PROPOSALS")
            src.write_bytes(b"x" * 256_001)
            with self.assertRaises(ValueError):
                propose_from_file(src)
            link = Path(folder) / "alias.json"
            try:
                link.symlink_to(src)
            except (OSError, NotImplementedError):
                pass
            else:
                with self.assertRaises(ValueError):
                    propose_from_file(link)


if __name__ == "__main__":
    unittest.main()
