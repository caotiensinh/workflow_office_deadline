"""WF-04 regression: declared source hashes, versions and human decision gates."""
import copy
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from edu_workflow.regulation import read_registry, verify_reference
from edu_workflow.store import (
    add_case, audit_list, decide, get_case, open_store, review_queue
)

DOC = b"FICTIONAL REGULATION UNIT TEST - NO OFFICIAL LAW\n"
CASE = {
    "case_id": "SYN-REG-CASE", "kind": "REGULATION",
    "data_class": "RESTRICTED", "safe_title": "PRIVATE_HR_TITLE_NEVER_PRINT",
    "owner": "private@example.invalid", "status": "READY_FOR_APPROVAL",
    "approval_status": "PENDING", "due_at": None, "due_verified": False,
    "evidence_ref": "SYN-REG-001@V1",
}

def fixture(folder):
    folder = Path(folder)
    doc = folder / "reference.txt"
    doc.write_bytes(DOC)
    manifest = folder / "manifest.json"
    entry = {
        "reference_id": "SYN-REG-001", "version": "V1",
        "document": "reference.txt", "sha256": hashlib.sha256(DOC).hexdigest(),
        "citation_id": "SEC-1", "authority_code": "DEMO-ONLY",
        "effective_from": "2026-01-01", "effective_until": "2027-01-01",
        "human_reviewed": True, "superseded_by": None,
    }
    manifest.write_text(json.dumps({"schema_version": 1, "references": [entry]}),
                        encoding="utf-8")
    return manifest, entry, doc

def save(manifest, entries):
    manifest.write_text(json.dumps({"schema_version": 1, "references": entries}),
                        encoding="utf-8")

class SourceSnapshotTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.path, self.entry, self.doc = fixture(self.folder.name)

    def assess(self, ref="SYN-REG-001@V1", *, when="2026-10-20"):
        return verify_reference(self.path, ref, as_of=when)

    def test_valid_reference_is_not_legal_verification(self):
        result = self.assess()
        self.assertEqual(result["status"], "SOURCE_SNAPSHOT_PASS")
        self.assertEqual(result["document_sha256"], hashlib.sha256(DOC).hexdigest())
        self.assertEqual(result["citation_id"], "SEC-1")
        self.assertFalse(result["official_authenticity_verified"])
        self.assertFalse(result["legal_applicability_verified"])
        self.assertFalse(result["external_actions_performed"])
        self.assertTrue(result["human_decision_required"])

    def test_unsupported_and_unknown_reference_are_review_only(self):
        for key, why in ((None, "INVALID_REFERENCE"), ("XYZ@V1", "UNKNOWN_REFERENCE"),
                         ("SYN-REG-001@V2", "UNKNOWN_REFERENCE"), ("SYN-REG-001", "INVALID_REFERENCE")):
            self.assertEqual(self.assess(key)["reason"], why)
        self.assertEqual(verify_reference(None, "SYN-REG-001@V1")["reason"],
                         "REGISTRY_NOT_CONFIGURED")

    def test_declared_expiry_and_future_window(self):
        for when in ("2025-12-31", "2027-01-01"):
            self.assertEqual(self.assess(when=when)["reason"], "OUTSIDE_DECLARED_WINDOW")
        self.assertEqual(self.assess(when="2026-01-01")["status"], "SOURCE_SNAPSHOT_PASS")

    def test_human_review_required(self):
        self.entry["human_reviewed"] = False
        save(self.path, [self.entry])
        self.assertEqual(self.assess()["reason"], "SOURCE_REVIEW_REQUIRED")

    def test_superseded_revision_rejected(self):
        self.entry["superseded_by"] = "V2"
        save(self.path, [self.entry])
        self.assertEqual(self.assess()["reason"], "SUPERSEDED_REFERENCE")

    def test_document_changed_after_recorded_hash(self):
        self.doc.write_bytes(b"CHANGED CONTENT\n")
        self.assertEqual(self.assess()["reason"], "DOCUMENT_HASH_MISMATCH")

    def test_missing_and_symlinked_source_rejected(self):
        self.doc.unlink()
        self.assertEqual(self.assess()["reason"], "SOURCE_FILE_MISSING")
        target = Path(self.folder.name) / "elsewhere.txt"
        target.write_bytes(DOC)
        try:
            self.doc.symlink_to(target)
        except (NotImplementedError, OSError):
            pass
        else:
            self.assertEqual(self.assess()["reason"], "SOURCE_FILE_MISSING")

    def test_path_traversal_and_unexpected_fields_rejected(self):
        for change in ({"document": "../private.txt"}, {"title": "SECRET"},
                       {"human_reviewed": 1}, {"sha256": "NOT-A-HASH"}):
            candidate = dict(self.entry, **change)
            save(self.path, [candidate])
            with self.assertRaisesRegex(ValueError, "REGULATION_REGISTRY_INVALID"):
                self.assess()

    def test_duplicate_references_or_json_keys_rejected(self):
        save(self.path, [self.entry, self.entry])
        with self.assertRaises(ValueError):
            read_registry(self.path)
        self.path.write_text('{"schema_version":1,"schema_version":1,"references":[]}',
                             encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "duplicate JSON field"):
            read_registry(self.path)

    def test_explicit_bounds_and_no_symlinked_manifest(self):
        self.path.write_bytes(b"x" * 128_001)
        with self.assertRaises(ValueError):
            read_registry(self.path)
        self.path.unlink()
        other = Path(self.folder.name) / "target.json"
        other.write_text("{}", encoding="utf-8")
        try:
            self.path.symlink_to(other)
        except (NotImplementedError, OSError):
            pass
        else:
            with self.assertRaises(ValueError):
                read_registry(self.path)

    def test_malformed_calendar_and_schema_rejected(self):
        self.entry["effective_from"] = "2026-99-99"
        save(self.path, [self.entry])
        with self.assertRaises(ValueError):
            read_registry(self.path)
        self.entry["effective_from"] = "2026-01-01"
        self.entry["effective_until"] = "2025-01-01"
        save(self.path, [self.entry])
        with self.assertRaises(ValueError):
            read_registry(self.path)

class HumanDecisionGateTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.path, self.entry, self.doc = fixture(self.folder.name)
        self.db = Path(self.folder.name) / "workflow.sqlite3"
        self.conn = open_store(self.db)
        self.addCleanup(self.conn.close)
        add_case(self.conn, dict(CASE))

    def test_missing_registry_blocks_approval_unchanged(self):
        with self.assertRaisesRegex(ValueError, "REGULATION_APPROVAL_BLOCKED"):
            decide(self.conn, CASE["case_id"], "APPROVED", "human", 1)
        self.assertEqual(get_case(self.conn, CASE["case_id"])[1], 1)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM decisions").fetchone()[0], 0)

    def test_reference_review_queue_warns_without_config(self):
        self.assertIn("VERIFY_REGULATION_SOURCE", review_queue(self.conn)[0]["reasons"])
        self.assertNotIn("VERIFY_REGULATION_SOURCE",
                         review_queue(self.conn, registry_path=self.path, as_of="2026-10-20")[0]["reasons"])

    def test_valid_source_still_requires_human_and_audits_digest(self):
        result, revision = decide(self.conn, CASE["case_id"], "APPROVED", "human", 1,
                                  registry_path=self.path, as_of="2026-10-20")
        self.assertEqual((result["status"], revision), ("APPROVED", 2))
        audits = [a for a in audit_list(self.conn) if a["event"] == "HUMAN_APPROVED"]
        self.assertEqual(len(audits), 1)
        proof = json.loads(audits[0]["detail"])
        self.assertEqual(proof["document_sha256"], hashlib.sha256(DOC).hexdigest())
        self.assertEqual(proof["version"], "V1")
        self.assertNotIn("PRIVATE_HR_TITLE_NEVER_PRINT", json.dumps(proof))
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM decisions").fetchone()[0], 1)
        with self.assertRaises(RuntimeError):
            decide(self.conn, CASE["case_id"], "APPROVED", "human", 1, registry_path=self.path)

    def test_tampering_blocks_transaction_and_audit(self):
        self.doc.write_bytes(b"CHANGED")
        with self.assertRaisesRegex(ValueError, "DOCUMENT_HASH_MISMATCH"):
            decide(self.conn, CASE["case_id"], "APPROVED", "human", 1,
                   registry_path=self.path, as_of="2026-10-20")
        self.assertEqual(get_case(self.conn, CASE["case_id"])[1], 1)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM decisions").fetchone()[0], 0)
        self.assertEqual(len([a for a in audit_list(self.conn) if a["event"] == "HUMAN_APPROVED"]), 0)

    def test_reject_does_not_require_regulation_registry(self):
        result, revision = decide(self.conn, CASE["case_id"], "REJECTED", "human", 1)
        self.assertEqual((result["status"], revision), ("REJECTED", 2))

    def test_failed_audit_rolls_back_all(self):
        with self.conn:
            self.conn.execute("CREATE TRIGGER deny_reg_audit BEFORE UPDATE ON audit "
                              "BEGIN SELECT RAISE(ABORT,'failure'); END")
        with self.assertRaises(Exception):
            decide(self.conn, CASE["case_id"], "APPROVED", "human", 1,
                   registry_path=self.path, as_of="2026-10-20")
        self.assertEqual(get_case(self.conn, CASE["case_id"])[1], 1)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM decisions").fetchone()[0], 0)

class CLIIntegration(unittest.TestCase):
    def test_readonly_check_does_not_open_or_create_workflow_database(self):
        project = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as folder:
            path, _, _ = fixture(folder)
            db = Path(folder) / "NEVER.sqlite"
            env = dict(os.environ, PYTHONPATH=str(project / "python"))
            base = [sys.executable, "-m", "edu_workflow.cli", "--db", str(db),
                    "check-regulations", "--registry-file", str(path),
                    "--reference", "SYN-REG-001@V1", "--as-of", "2026-10-20"]
            proc = subprocess.run(base, cwd=project, env=env, text=True, capture_output=True)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            report = json.loads(proc.stdout)
            self.assertEqual(report["status"], "SOURCE_SNAPSHOT_PASS")
            self.assertFalse(db.exists())
            bad = subprocess.run(base[:-3] + ["UNKNOWN@V1", "--as-of", "2026-10-20"],
                                 cwd=project, env=env, text=True, capture_output=True)
            self.assertEqual(bad.returncode, 3)
            self.assertFalse(db.exists())

if __name__ == "__main__":
    unittest.main()
