import copy
import json
import sqlite3
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from workflow_engine import load_cases, connection, enqueue, list_outbox, safe_label, approve, rules
JST = ZoneInfo('Asia/Tokyo')
NOW = datetime(2026, 10, 19, 9, 0, tzinfo=JST)
BASE = {'case_id':'X','kind':'EMAIL','data_class':'INTERNAL','safe_title':'Mẫu kiểm thử',
        'owner':'owner@example.invalid','status':'IN_PROGRESS','due_at':'2026-10-22T17:00:00+09:00',
        'due_verified':True,'approval_status':'NOT_REQUIRED','evidence_ref':'E-01'}

class WorkflowTests(unittest.TestCase):
    def test_d3_alert(self):
        self.assertEqual(rules(BASE, NOW)[0][0], 'D_MINUS_3')
    def test_d1_alert(self):
        c = dict(BASE, due_at='2026-10-20T17:00:00+09:00')
        self.assertEqual(rules(c, NOW)[0][0], 'D_MINUS_1')
    def test_due_today(self):
        c = dict(BASE, due_at='2026-10-19T17:00:00+09:00')
        self.assertEqual(rules(c, NOW)[0][0], 'DUE_TODAY')
    def test_overdue(self):
        c = dict(BASE, due_at='2026-10-18T17:00:00+09:00')
        self.assertEqual(rules(c, NOW)[0][0], 'OVERDUE')
    def test_no_inferred_deadline(self):
        c = dict(BASE, due_at=None, due_verified=False)
        self.assertEqual(rules(c, NOW)[0][0], 'VERIFY_DEADLINE')
    def test_completed_no_notifications(self):
        self.assertEqual(rules(dict(BASE, status='COMPLETED'), NOW), [])
    def test_sensitive_masking(self):
        c = dict(BASE, data_class='RESTRICTED', safe_title='Tên nhân viên bí mật')
        self.assertNotIn('Tên nhân viên', '\n'.join(m for _,m in rules(c,NOW)))
    def test_missing_evidence_gate(self):
        c = dict(BASE, kind='HR', evidence_ref=None, status='READY_FOR_APPROVAL')
        names = [r for r,_ in rules(c,NOW)]
        self.assertIn('MISSING_EVIDENCE', names)
        self.assertNotIn('APPROVAL_PENDING', names)
    def test_same_day_deduplication(self):
        with tempfile.TemporaryDirectory() as d:
            with connection(Path(d)/'s.sqlite') as con:
                self.assertEqual(enqueue([BASE], con, NOW), 1)
                self.assertEqual(enqueue([BASE], con, NOW), 0)
                self.assertEqual(len(list_outbox(con)), 1)
    def test_duplicate_case_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            file = Path(d)/'cases.json'
            file.write_text(json.dumps([BASE, BASE]), encoding='utf-8')
            with self.assertRaises(ValueError): load_cases(file)
    def test_bad_timezone_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            file = Path(d)/'cases.json'
            file.write_text(json.dumps([dict(BASE, due_at='2026-10-22T17:00:00')]), encoding='utf-8')
            with self.assertRaises(ValueError): load_cases(file)
    def test_approval_requires_evidence(self):
        with tempfile.TemporaryDirectory() as d:
            file = Path(d)/'cases.json'
            file.write_text(json.dumps([dict(BASE, kind='HR', status='READY_FOR_APPROVAL',evidence_ref=None)]), encoding='utf-8')
            with self.assertRaises(ValueError): approve(file, 'X', 'approve', 'manager', NOW)
    def test_approval_human_decision(self):
        with tempfile.TemporaryDirectory() as d:
            file = Path(d)/'cases.json'
            file.write_text(json.dumps([dict(BASE,kind='DOCUMENT',status='READY_FOR_APPROVAL')]), encoding='utf-8')
            result = approve(file,'X','approve','manager',NOW)
            self.assertEqual(result['status'], 'APPROVED')
            self.assertEqual(load_cases(file)[0]['approver'],'manager')
    def test_reject(self):
        with tempfile.TemporaryDirectory() as d:
            file = Path(d)/'cases.json'
            file.write_text(json.dumps([dict(BASE,kind='DOCUMENT',status='READY_FOR_APPROVAL')]), encoding='utf-8')
            self.assertEqual(approve(file,'X','reject','manager',NOW)['status'],'REJECTED')
    def test_unapproved_has_no_action_execution(self):
        # Only alerts are emitted. No send/submit/calendar action exists in rules().
        c = dict(BASE, kind='DOCUMENT', status='READY_FOR_APPROVAL', approval_status='PENDING')
        self.assertTrue(all(k in {'D_MINUS_3','APPROVAL_PENDING'} for k,_ in rules(c,NOW)))

if __name__ == '__main__': unittest.main()
