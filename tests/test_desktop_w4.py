"""W4 regression + E2E: notification visibility, snooze, ACK, no approvals."""
import importlib
import json
import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from edu_workflow.store import open_store, add_case, get_case, get_cases, update_case, enqueue, audit_list
from edu_workflow.policy import JST, evaluate, message_for
from edu_workflow.deliver import dispatch
from edu_workflow.desktop_center import ensure_receipts, list_notifications, mark_notification

NOW=datetime(2026,10,19,9,tzinfo=JST)
BASE={
    'case_id':'W4-SYNTH', 'kind':'EMAIL', 'data_class':'RESTRICTED',
    'safe_title':'PRIVATE_STUDENT_RECORD', 'owner':'private@example.invalid',
    'status':'IN_PROGRESS','approval_status':'NOT_REQUIRED',
    'due_at':'2026-10-22T17:00:00+09:00','due_verified':True,'evidence_ref':None,
}
UTC=timezone.utc

class DesktopCenterTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/'demo.sqlite3'
        self.conn=open_store(self.path)
        self.addCleanup(self.conn.close)
        add_case(self.conn,dict(BASE))
        self.actor='demo-user'
        self.at=datetime(2026,10,19,9,tzinfo=JST)

    def queue(self):
        cases=get_cases(self.conn)
        ev=evaluate([c for c,_ in cases],NOW,'python')
        self.assertEqual(enqueue(self.conn,cases,ev,NOW,message_for),1)
        return self.conn.execute('SELECT alert_id FROM alerts').fetchone()['alert_id']

    def deliver_file(self):
        aid=self.queue()
        result=dispatch(self.conn,'file',Path(self.tmp.name)/'notice')
        self.assertEqual(result['sent'],1)
        return aid

    def test_migration_idempotent_preserves_existing_records(self):
        self.deliver_file()
        ensure_receipts(self.conn); ensure_receipts(self.conn)
        self.assertEqual(len(list_notifications(self.conn,self.actor)),1)

    def test_queued_not_displayed_until_durable_delivery(self):
        self.queue()
        self.assertEqual(list_notifications(self.conn,self.actor),[])

    def test_private_titles_and_addresses_never_displayed(self):
        self.deliver_file()
        payload=json.dumps(list_notifications(self.conn,self.actor))
        self.assertNotIn('PRIVATE_STUDENT_RECORD',payload)
        self.assertNotIn('private@example.invalid',payload)
        self.assertEqual(list_notifications(self.conn,self.actor)[0]['summary'],'期限まで3日')

    def test_delivery_ack_is_per_actor(self):
        aid=self.deliver_file()
        self.assertTrue(mark_notification(self.conn,aid,self.actor,'ACK',at=self.at))
        self.assertEqual(list_notifications(self.conn,self.actor),[])
        self.assertEqual(len(list_notifications(self.conn,'different-user')),1)

    def test_ack_idempotent_with_single_audit(self):
        aid=self.deliver_file()
        self.assertTrue(mark_notification(self.conn,aid,self.actor,'ACK',at=self.at))
        self.assertFalse(mark_notification(self.conn,aid,self.actor,'ACK',at=self.at))
        logs=[x for x in audit_list(self.conn) if x['event']=='DESKTOP_ACK']
        self.assertEqual(len(logs),1)
        self.assertEqual(self.conn.execute('SELECT COUNT(*) FROM decisions').fetchone()[0],0)
        self.assertEqual(get_case(self.conn,BASE['case_id'])[1],1)

    def test_snooze_hide_until_expiration(self):
        aid=self.deliver_file()
        mark_notification(self.conn,aid,self.actor,'SNOOZE',at=self.at,snooze_minutes=30)
        self.assertEqual(list_notifications(self.conn,self.actor,at=self.at+timedelta(minutes=29)),[])
        self.assertEqual(len(list_notifications(self.conn,self.actor,at=self.at+timedelta(minutes=30))),1)
        self.assertEqual(len(list_notifications(self.conn,self.actor,at=self.at+timedelta(minutes=1),include_snoozed=True)),1)

    def test_ack_after_snooze_and_no_resnooze(self):
        aid=self.deliver_file()
        mark_notification(self.conn,aid,self.actor,'SNOOZE',at=self.at)
        mark_notification(self.conn,aid,self.actor,'ACK',at=self.at)
        with self.assertRaises(ValueError):
            mark_notification(self.conn,aid,self.actor,'SNOOZE',at=self.at)
        self.assertEqual(list_notifications(self.conn,self.actor,at=self.at+timedelta(days=2)),[])

    def test_bad_snooze_bounds_and_boolean(self):
        aid=self.deliver_file()
        for v in (0,4,1441,True,-100):
            with self.subTest(v=v),self.assertRaises(ValueError):
                mark_notification(self.conn,aid,self.actor,'SNOOZE',at=self.at,snooze_minutes=v)
        self.assertEqual(len(list_notifications(self.conn,self.actor)),1)

    def test_unknown_alert_id_or_action_fail_closed(self):
        self.deliver_file()
        with self.assertRaises(ValueError):
            mark_notification(self.conn,'bogus',self.actor,'ACK')
        with self.assertRaises(ValueError):
            mark_notification(self.conn,'1'*64,self.actor,'ACK')
        with self.assertRaises(ValueError):
            mark_notification(self.conn,'1'*64,self.actor,'APPROVE')
        self.assertEqual(self.conn.execute('SELECT count(*) FROM desktop_receipts').fetchone()[0],0)

    def test_stale_version_is_never_displayed(self):
        aid=self.deliver_file()
        case,rev=get_case(self.conn,BASE['case_id'])
        case['due_at']='2026-10-23T17:00:00+09:00'
        update_case(self.conn,case,rev,'operator','CHANGE_DUE')
        self.assertEqual(list_notifications(self.conn,self.actor),[])
        with self.assertRaises(ValueError):
            mark_notification(self.conn,aid,self.actor,'ACK')
        self.assertEqual(self.conn.execute('SELECT COUNT(*) FROM decisions').fetchone()[0],0)

    def test_closed_case_not_displayed(self):
        aid=self.deliver_file()
        case,rev=get_case(self.conn,BASE['case_id'])
        case['status']='COMPLETED'
        update_case(self.conn,case,rev,'operator','CLOSE')
        self.assertEqual(list_notifications(self.conn,self.actor),[])
        with self.assertRaises(ValueError):
            mark_notification(self.conn,aid,self.actor,'ACK')

    def test_unknown_is_incident_and_cannot_be_acked(self):
        aid=self.queue()
        with self.conn:
            self.conn.execute("UPDATE alerts SET state='UNKNOWN' WHERE alert_id=?",(aid,))
        items=list_notifications(self.conn,self.actor)
        self.assertEqual(len(items),1)
        self.assertEqual(items[0]['severity'],'CRITICAL')
        self.assertIn('UNKNOWN',items[0]['summary'])
        with self.assertRaises(ValueError):
            mark_notification(self.conn,aid,self.actor,'ACK',at=self.at)
        self.assertTrue(mark_notification(self.conn,aid,self.actor,'SNOOZE',at=self.at))
        self.assertEqual(self.conn.execute('SELECT state FROM alerts WHERE alert_id=?',(aid,)).fetchone()[0],'UNKNOWN')

    def test_queued_unknown_sending_never_automatically_retried(self):
        aid=self.queue()
        with self.conn:
            self.conn.execute("UPDATE alerts SET state='SENDING' WHERE alert_id=?",(aid,))
        self.assertEqual(list_notifications(self.conn,self.actor),[])
        with self.assertRaises(ValueError):
            mark_notification(self.conn,aid,self.actor,'ACK')

    def test_closed_then_outdated_receipt_stays_ignored(self):
        aid=self.deliver_file()
        mark_notification(self.conn,aid,self.actor,'SNOOZE',at=self.at)
        case,rev=get_case(self.conn,BASE['case_id'])
        case['status']='CANCELLED'
        update_case(self.conn,case,rev,'operator','CANCEL')
        self.assertEqual(list_notifications(self.conn,self.actor,at=self.at+timedelta(days=4)),[])

    def test_rollback_when_audit_write_fails(self):
        aid=self.deliver_file()
        with self.conn:
            self.conn.execute("""CREATE TRIGGER reject_w4 BEFORE INSERT ON audit
                BEGIN SELECT RAISE(ABORT,'synthetic audit failure'); END""")
        with self.assertRaises(sqlite3.DatabaseError):
            mark_notification(self.conn,aid,self.actor,'ACK')
        self.assertEqual(self.conn.execute('SELECT count(*) FROM desktop_receipts').fetchone()[0],0)

    def test_account_checks_and_naive_clock(self):
        aid=self.deliver_file()
        with self.assertRaises(ValueError):
            list_notifications(self.conn,'')
        with self.assertRaises(ValueError):
            list_notifications(self.conn,self.actor,at=datetime(2026,10,19))
        with self.assertRaises(ValueError):
            mark_notification(self.conn,aid,'', 'ACK')
        with self.assertRaises(ValueError):
            mark_notification(self.conn,aid,self.actor,'ACK',at=datetime(2026,10,19))

    def test_second_process_reuses_ack_receipt(self):
        aid=self.deliver_file()
        mark_notification(self.conn,aid,self.actor,'ACK',at=self.at)
        other=open_store(self.path)
        try:
            self.assertEqual(list_notifications(other,self.actor),[])
            self.assertEqual(len(list_notifications(other,'someone-else')),1)
        finally:
            other.close()

    def test_desktop_gui_module_imports_without_starting_gui(self):
        app=importlib.import_module('edu_workflow.desktop_app')
        self.assertTrue(callable(app.launch))
        with self.assertRaises(ValueError):
            app.launch(self.path,poll_seconds=0)


if __name__=='__main__':
    unittest.main()
