"""W11 WF05: anonymous-only, evidence-cited HR review drafts and approval guard."""
import copy
import getpass
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from edu_workflow.hr_evidence import draft_from_packet, read_packet, verify_for_hr_approval
from edu_workflow.store import open_store, add_case, decide, get_case, audit_list, review_queue

ROOT = Path(__file__).resolve().parents[1]
CASE_ID = "ANON-0123456789ABCDEF"
SOURCE = b"FICTIONAL HR SUPPORTING RECORD - NOT A PERSON\n"
FAKE = {
    "schema_version": 1,
    "case_ref": CASE_ID,
    "required_codes": ["TRAINING_COMPLETED", "DOCUMENT_SUBMITTED"],
    "claims": [
        {"claim_id": "CL-00000001", "fact_code": "TRAINING_COMPLETED",
         "observed_on": "2026-10-11", "evidence_id": "EV-00000001"},
        {"claim_id": "CL-00000002", "fact_code": "DOCUMENT_SUBMITTED",
         "observed_on": "2026-10-12", "evidence_id": "EV-00000002"},
    ],
    "sources": [
        {"evidence_id": "EV-00000001", "document": "fictional.txt",
         "sha256": hashlib.sha256(SOURCE).hexdigest(), "reviewed": True},
        {"evidence_id": "EV-00000002", "document": "fictional.txt",
         "sha256": hashlib.sha256(SOURCE).hexdigest(), "reviewed": True},
    ],
}
CASE = {
    "case_id": CASE_ID, "kind": "HR", "data_class": "RESTRICTED",
    "safe_title": "NEVER_EMIT_PRIVATE_TITLE", "owner": "hidden@example.invalid",
    "due_at": None, "due_verified": False, "status": "READY_FOR_APPROVAL",
    "approval_status": "PENDING", "evidence_ref": None,
}


def fixture(folder, data=None):
    root = Path(folder)
    root.joinpath("fictional.txt").write_bytes(SOURCE)
    file = root / "hr_packet.json"
    file.write_text(json.dumps(data if data is not None else FAKE, sort_keys=True),
                    encoding="utf-8")
    return file


def pinned(path):
    return "HR-PACKET:" + hashlib.sha256(Path(path).read_bytes()).hexdigest()


class HRDraftTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.file = fixture(self.root)

    def report(self, as_of="2026-10-20"):
        return draft_from_packet(self.file, as_of=as_of)

    def test_source_cited_draft_is_reviewer_only(self):
        report = self.report()
        self.assertEqual(report["status"], "READY_FOR_HUMAN_REVIEW")
        self.assertEqual(report["case_ref"], CASE_ID)
        self.assertEqual(len(report["draft_sections"]), 2)
        self.assertEqual(report["gaps"], [])
        self.assertEqual(report["claim_count"], 2)
        self.assertTrue(report["human_review_required"])
        for field in ("source_authenticity_verified", "hr_assessment_performed",
                      "ranking_performed", "employment_decision_performed",
                      "external_actions_performed", "writes_database"):
            self.assertFalse(report[field])
        for row in report["draft_sections"]:
            self.assertIn("未確認", row["draft_ja"])
            self.assertEqual(len(row["source_ids"]), 1)
        serialized = json.dumps(report, ensure_ascii=False)
        self.assertNotIn("NEVER_EMIT_PRIVATE_TITLE", serialized)
        self.assertNotIn("example.invalid", serialized)

    def test_source_corruption_becomes_gap_without_fabricated_fact(self):
        (self.root / "fictional.txt").write_bytes(b"tampered")
        r = self.report()
        self.assertEqual(r["status"], "EVIDENCE_GAPS")
        self.assertEqual(r["draft_sections"], [])
        self.assertEqual(sum(x["reason"] == "SOURCE_HASH_MISMATCH" for x in r["gaps"]), 2)

    def test_review_flag_blocks_unreviewed_citation(self):
        data = copy.deepcopy(FAKE)
        data["sources"][0]["reviewed"] = False
        fixture(self.root, data)
        x = self.report()
        self.assertEqual(x["status"], "EVIDENCE_GAPS")
        self.assertIn("SOURCE_REVIEW_REQUIRED", [y["reason"] for y in x["gaps"]])
        self.assertEqual(len(x["draft_sections"]), 1)

    def test_missing_evidence_and_unsupported_required_category(self):
        data = copy.deepcopy(FAKE)
        data["claims"][0]["evidence_id"] = None
        fixture(self.root, data)
        r = self.report()
        self.assertIn("MISSING_EVIDENCE", [x["reason"] for x in r["gaps"]])
        self.assertIn("REQUIRED_CATEGORY_NOT_SUPPORTED", [x["reason"] for x in r["gaps"]])

    def test_unlisted_and_missing_file(self):
        data = copy.deepcopy(FAKE)
        data["claims"][0]["evidence_id"] = "EV-99999999"
        fixture(self.root, data)
        self.assertIn("UNLISTED_EVIDENCE", [x["reason"] for x in self.report()["gaps"]])
        (self.root / "fictional.txt").unlink()
        self.assertIn("SOURCE_UNAVAILABLE", [x["reason"] for x in self.report()["gaps"]])

    def test_future_dated_observation_not_asserted(self):
        data = copy.deepcopy(FAKE)
        data["claims"][1]["observed_on"] = "2027-01-01"
        fixture(self.root, data)
        self.assertIn("FUTURE_OBSERVATION", [x["reason"] for x in self.report()["gaps"]])

    def test_order_independence_and_hash_pin(self):
        a = self.report()
        data = copy.deepcopy(FAKE)
        data["claims"].reverse()
        data["sources"].reverse()
        fixture(self.root, data)
        b = self.report()
        self.assertEqual(a["draft_sections"], b["draft_sections"])
        self.assertNotEqual(a["packet_sha256"], b["packet_sha256"])

    def test_rejects_identity_fields_and_freeform_comments(self):
        for k, v in (("name", "someone"), ("rating", 5), ("comment", "personal")):
            data = copy.deepcopy(FAKE)
            data[k] = v
            fixture(self.root, data)
            with self.assertRaisesRegex(ValueError, "HR_PACKET_INVALID"):
                self.report()
        data = copy.deepcopy(FAKE)
        data["claims"][0]["comment"] = "something private"
        fixture(self.root, data)
        with self.assertRaises(ValueError):
            self.report()

    def test_case_ref_must_be_nonreversible_opaque_shape(self):
        data = copy.deepcopy(FAKE)
        data["case_ref"] = "john@example.invalid"
        fixture(self.root, data)
        with self.assertRaises(ValueError):
            self.report()

    def test_duplicate_claims_sources_codes_and_json_keys(self):
        for key in ("claims", "sources"):
            data = copy.deepcopy(FAKE)
            data[key].append(copy.deepcopy(data[key][0]))
            fixture(self.root, data)
            with self.assertRaises(ValueError):
                self.report()
        data = copy.deepcopy(FAKE)
        data["required_codes"].append("TRAINING_COMPLETED")
        fixture(self.root, data)
        with self.assertRaises(ValueError):
            self.report()
        self.file.write_text('{"schema_version":1,"schema_version":1}', encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "duplicate JSON member"):
            self.report()

    def test_traversal_symlink_oversize_and_naive_as_of_blocked(self):
        data = copy.deepcopy(FAKE)
        data["sources"][0]["document"] = "../private.txt"
        fixture(self.root, data)
        with self.assertRaises(ValueError):
            self.report()
        fixture(self.root)
        self.file.write_bytes(b"x" * 128_001)
        with self.assertRaises(ValueError):
            self.report()
        fixture(self.root)
        (self.root / "fictional.txt").unlink()
        try:
            (self.root / "fictional.txt").symlink_to(self.file)
        except (OSError, NotImplementedError):
            pass
        else:
            self.assertIn("SOURCE_UNAVAILABLE", [x["reason"] for x in self.report()["gaps"]])
        with self.assertRaises(ValueError):
            draft_from_packet(self.file, as_of="2026-10-20T12:00")

    def test_boolean_schema_version_rejected(self):
        data = copy.deepcopy(FAKE)
        data["schema_version"] = True
        fixture(self.root, data)
        with self.assertRaises(ValueError):
            self.report()

    def test_boundaries_and_unicode_templates(self):
        data = copy.deepcopy(FAKE)
        data["required_codes"] = ["SUPPORT_ACTIVITY"]
        data["claims"][0]["fact_code"] = "SUPPORT_ACTIVITY"
        fixture(self.root, data)
        x = self.report()
        self.assertEqual(x["status"], "READY_FOR_HUMAN_REVIEW")
        self.assertIn("支援活動", next(s["draft_ja"] for s in x["draft_sections"]
                                  if s["fact_code"] == "SUPPORT_ACTIVITY"))

class HRApprovalGateTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.file = fixture(self.root)
        self.db = self.root / "state.sqlite"
        self.conn = open_store(self.db)
        self.addCleanup(self.conn.close)
        self.case = copy.deepcopy(CASE)
        self.case["evidence_ref"] = pinned(self.file)
        add_case(self.conn, self.case)

    def test_no_packet_or_mismatched_hash_fails_closed(self):
        for path in (None, self.file):
            ref = self.case["evidence_ref"] if path is None else "HR-PACKET:" + "0"*64
            with self.assertRaisesRegex(ValueError, "HR_APPROVAL_BLOCKED"):
                verify_for_hr_approval(path, CASE_ID, ref, as_of="2026-10-20")
        with self.assertRaisesRegex(ValueError, "HR_APPROVAL_BLOCKED"):
            decide(self.conn, CASE_ID, "APPROVED", "human", 1)
        self.assertEqual(get_case(self.conn, CASE_ID)[1], 1)

    def test_attested_human_approval_is_atomic_and_source_cited(self):
        out, rev = decide(self.conn, CASE_ID, "APPROVED", "human", 1,
                          hr_packet_path=self.file, as_of="2026-10-20")
        self.assertEqual((out["status"], rev), ("APPROVED", 2))
        audits = [r for r in audit_list(self.conn) if r["event"] == "HUMAN_APPROVED"]
        self.assertEqual(len(audits), 1)
        data = json.loads(audits[0]["detail"])
        self.assertEqual(data["packet_sha256"], pinned(self.file).split(":")[1])
        self.assertEqual(data["scope"], "structural-source-check-only-no-hr-appraisal")
        self.assertNotIn("NEVER_EMIT_PRIVATE_TITLE", json.dumps(data))
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM decisions").fetchone()[0], 1)

    def test_mutated_packet_requires_new_binding_and_revision(self):
        data = copy.deepcopy(FAKE)
        data["claims"].reverse()
        fixture(self.root, data)
        with self.assertRaises(ValueError):
            decide(self.conn, CASE_ID, "APPROVED", "human", 1,
                   hr_packet_path=self.file, as_of="2026-10-20")
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM decisions").fetchone()[0], 0)
        self.assertEqual(get_case(self.conn, CASE_ID)[1], 1)

    def test_evidence_gaps_block_approval_even_when_hash_pinned(self):
        (self.root / "fictional.txt").write_bytes(b"changed")
        with self.assertRaisesRegex(ValueError, "HR_APPROVAL_BLOCKED"):
            decide(self.conn, CASE_ID, "APPROVED", "human", 1,
                   hr_packet_path=self.file, as_of="2026-10-20")
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM decisions").fetchone()[0], 0)

    def test_masked_exception_queue_with_and_without_source_packet(self):
        r = review_queue(self.conn)
        self.assertIn("VERIFY_HR_EVIDENCE_PACKET", r[0]["reasons"])
        r = review_queue(self.conn, hr_packet_path=self.file, as_of="2026-10-20")
        self.assertNotIn("VERIFY_HR_EVIDENCE_PACKET", r[0]["reasons"])
        self.assertIn("APPROVAL_PENDING", r[0]["reasons"])

    def test_rejection_without_packet_remains_available(self):
        out, rev = decide(self.conn, CASE_ID, "REJECTED", "human", 1)
        self.assertEqual((out["status"], rev), ("REJECTED", 2))

    def test_audit_failure_rolls_back_revision_and_decision(self):
        with self.conn:
            self.conn.execute("CREATE TRIGGER fail_audit BEFORE UPDATE ON audit "
                              "BEGIN SELECT RAISE(ABORT,'test'); END")
        with self.assertRaises(Exception):
            decide(self.conn, CASE_ID, "APPROVED", "human", 1,
                   hr_packet_path=self.file, as_of="2026-10-20")
        self.assertEqual(get_case(self.conn, CASE_ID)[1], 1)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM decisions").fetchone()[0], 0)

class HRCLIIntegration(unittest.TestCase):
    def test_cli_draft_has_no_db_side_effects_and_missing_returns_3(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            file = fixture(root)
            db = root / "MUST_NOT_EXIST.sqlite"
            env = dict(os.environ, PYTHONPATH=str(ROOT / "python"))
            args = [sys.executable, "-m", "edu_workflow.cli", "--db", str(db),
                    "hr-draft", "--packet-file", str(file), "--as-of", "2026-10-20"]
            p = subprocess.run(args, cwd=ROOT, env=env, text=True, capture_output=True)
            self.assertEqual(p.returncode, 0, p.stderr)
            self.assertEqual(json.loads(p.stdout)["status"], "READY_FOR_HUMAN_REVIEW")
            self.assertFalse(db.exists())
            (root / "fictional.txt").unlink()
            p = subprocess.run(args, cwd=ROOT, env=env, text=True, capture_output=True)
            self.assertEqual(p.returncode, 3)
            self.assertEqual(json.loads(p.stdout)["status"], "EVIDENCE_GAPS")
            self.assertFalse(db.exists())

if __name__ == "__main__":
    unittest.main()
