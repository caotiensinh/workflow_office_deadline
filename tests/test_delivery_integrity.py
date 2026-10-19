"""Failure, concurrency and stale-revision regression tests for notification and approvals."""
import json
import sqlite3
import tempfile
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch

from edu_workflow.store import open_store, add_case, get_case, get_cases, update_case, enqueue, decide, alert_list, audit_list
from edu_workflow.policy import evaluate, message_for
from edu_workflow.deliver import dispatch

NOW = datetime(2026, 10, 19, 9, tzinfo=timezone(timedelta(hours=9)))
CASE = {'case_id':'X-11', 'kind':'EMAIL', 'data_class':'INTERNAL', 'safe_title':'Fictional',
        'owner':'nobody@example.invalid', 'status':'IN_PROGRESS', 'approval_status':'NOT_REQUIRED',
        'due_at':'2026-10-22T17:00:00+09:00', 'due_verified':True, 'evidence_ref':None}


class IntegrityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.con = open_store(Path(self.tmp.name) / 'state.sqlite')
        self.addCleanup(self.con.close)
        add_case(self.con, dict(CASE))

    def queue(self):
        snapshot = get_cases(self.con)
        return enqueue(self.con, snapshot, evaluate([c for c, _ in snapshot], NOW, 'python'), NOW, message_for)

    def test_stale_snapshot_cannot_enqueue_after_human_change(self):
        snapshot = get_cases(self.con)
        case, rev = get_case(self.con, CASE['case_id'])
        case['status'] = 'COMPLETED'
        update_case(self.con, case, rev, 'human', 'CLOSE')
        signals = evaluate([c for c, _ in snapshot], NOW, 'python')
        self.assertEqual(enqueue(self.con, snapshot, signals, NOW, message_for), 0)
        self.assertEqual(alert_list(self.con), [])

    def test_stale_alert_is_never_delivered_after_case_change(self):
        self.assertEqual(self.queue(), 1)
        case, rev = get_case(self.con, CASE['case_id'])
        case['due_at'] = '2026-10-23T17:00:00+09:00'
        update_case(self.con, case, rev, 'human', 'MOVE_DEADLINE')
        result = dispatch(self.con, 'file', Path(self.tmp.name) / 'out')
        self.assertEqual(result['sent'], 0)
        self.assertEqual(alert_list(self.con)[0]['state'], 'STALE')
        self.assertFalse(list((Path(self.tmp.name) / 'out').glob('*.json')))

    def test_corrupted_existing_file_quarantines_unknown(self):
        self.queue()
        alert = alert_list(self.con)[0]
        output = Path(self.tmp.name) / 'out'; output.mkdir()
        (output / (alert['alert_id'] + '.json')).write_text('"tampered"', encoding='utf-8')
        result = dispatch(self.con, 'file', output)
        self.assertEqual(result['unknown'], 1)
        self.assertEqual(alert_list(self.con)[0]['state'], 'UNKNOWN')
        self.assertEqual(dispatch(self.con, 'file', output)['sent'], 0)

    def test_crash_after_durable_write_recovers_without_resend(self):
        self.queue()
        alert = alert_list(self.con)[0]
        output = Path(self.tmp.name) / 'out'; output.mkdir()
        (output / (alert['alert_id'] + '.json')).write_text(json.dumps({
            'id': alert['alert_id'], 'case_id': alert['case_id'], 'severity': alert['severity'],
            'message': alert['message']}), encoding='utf-8')
        with self.con:
            self.con.execute("UPDATE alerts SET state='SENDING' WHERE alert_id=?", (alert['alert_id'],))
        result = dispatch(self.con, 'file', output)
        self.assertEqual((result['recovered'], result['sent']), (1, 0))
        self.assertEqual(alert_list(self.con)[0]['state'], 'SENT')

    def test_crashed_remote_send_is_unknown_without_retry(self):
        self.queue()
        with self.con:
            self.con.execute("UPDATE alerts SET state='SENDING'")
        with patch('edu_workflow.deliver.smtp_send') as send:
            result = dispatch(self.con, 'smtp')
        self.assertEqual(result['unknown'], 1)
        self.assertEqual(alert_list(self.con)[0]['state'], 'UNKNOWN')
        send.assert_not_called()

    def test_approval_atomic_if_insert_decision_fails(self):
        case, rev = get_case(self.con, CASE['case_id'])
        case.update(kind='DOCUMENT', status='READY_FOR_APPROVAL', approval_status='PENDING', evidence_ref='FICTIONAL')
        rev = update_case(self.con, case, rev, 'tester', 'READY')
        with self.con:
            self.con.execute("CREATE TRIGGER reject_decision BEFORE INSERT ON decisions BEGIN SELECT RAISE(ABORT,'synthetic failure'); END")
        with self.assertRaises(sqlite3.DatabaseError):
            decide(self.con, CASE['case_id'], 'APPROVED', 'human', rev)
        stored, actual = get_case(self.con, CASE['case_id'])
        self.assertEqual((stored['status'], actual), ('READY_FOR_APPROVAL', rev))
        self.assertNotIn('HUMAN_APPROVED', [x['event'] for x in audit_list(self.con)])
        self.assertEqual(self.con.execute('SELECT COUNT(*) FROM decisions').fetchone()[0], 0)


if __name__ == '__main__':
    unittest.main()
