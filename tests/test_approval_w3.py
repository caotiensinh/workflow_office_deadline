"""W3 safety tests: transactional human confirmation, stale alerts and approval gates."""
import getpass
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from edu_workflow.store import (
    open_store, add_case, confirm_deadline, decide, enqueue, get_case,
    get_cases, alert_list, audit_list, review_queue,
)
from edu_workflow.policy import JST, evaluate, message_for

NOW=datetime(2026, 10, 19, 9, tzinfo=JST)
CASE={
    'case_id':'SYNTH-VERIFY-1', 'kind':'EMAIL', 'data_class':'RESTRICTED',
    'safe_title':'SENSITIVE_DO_NOT_PRINT', 'owner':'reviewer@example.invalid',
    'due_at':'2026-10-22T17:00:00+09:00', 'due_verified':False,
    'status':'TRIAGE', 'approval_status':'NOT_REQUIRED', 'evidence_ref':None,
}


class ConfirmationTests(unittest.TestCase):
    def setUp(self):
        self.d=tempfile.TemporaryDirectory()
        self.addCleanup(self.d.cleanup)
        self.con=open_store(Path(self.d.name)/'workflow.sqlite3')
        self.addCleanup(self.con.close)
        add_case(self.con,dict(CASE))

    def test_review_queue_is_masked(self):
        rows=review_queue(self.con)
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]['reasons'],['VERIFY_DEADLINE'])
        serialized=json.dumps(rows)
        self.assertNotIn('SENSITIVE_DO_NOT_PRINT',serialized)
        self.assertNotIn('example.invalid',serialized)

    def test_confirm_changes_to_verified_and_stales_old_queue(self):
        before=get_cases(self.con)
        alerts=evaluate([c for c,_ in before],NOW,'python')
        self.assertEqual(enqueue(self.con,before,alerts,NOW,message_for),1)
        self.assertEqual(alert_list(self.con)[0]['code'],'VERIFY_DEADLINE')
        case,version=confirm_deadline(self.con,CASE['case_id'],CASE['due_at'],'operator',1,'SOURCE_REVIEWED')
        self.assertTrue(case['due_verified'])
        self.assertEqual(version,2)
        self.assertEqual(alert_list(self.con)[0]['state'],'STALE')
        after=get_cases(self.con)
        events=evaluate([c for c,_ in after],NOW,'python')
        self.assertEqual(enqueue(self.con,after,events,NOW,message_for),1)
        self.assertEqual(sorted((x['code'],x['state']) for x in alert_list(self.con)),
                         [('D_MINUS_3','QUEUED'),('VERIFY_DEADLINE','STALE')])
        audit=[a for a in audit_list(self.con) if a['event']=='HUMAN_VERIFIED_DEADLINE']
        self.assertEqual(len(audit),1)
        self.assertEqual(json.loads(audit[0]['detail'])['method'],'SOURCE_REVIEWED')

    def test_old_revision_cannot_reconfirm(self):
        confirm_deadline(self.con,CASE['case_id'],CASE['due_at'],'operator',1,'SOURCE_REVIEWED')
        with self.assertRaises(RuntimeError):
            confirm_deadline(self.con,CASE['case_id'],CASE['due_at'],'operator',1,'SOURCE_REVIEWED')
        self.assertEqual(get_case(self.con,CASE['case_id'])[1],2)

    def test_terminal_or_approved_cannot_change_date(self):
        with self.con:
            case,rev=get_case(self.con,CASE['case_id'])
            case['status']='APPROVED'
            self.con.execute('UPDATE cases SET payload=? WHERE case_id=?',(json.dumps(case),CASE['case_id']))
        with self.assertRaises(ValueError):
            confirm_deadline(self.con,CASE['case_id'],CASE['due_at'],'operator',1,'SOURCE_REVIEWED')
        self.assertEqual(get_case(self.con,CASE['case_id'])[1],1)

    def test_unapproved_method_rejected_without_update(self):
        with self.assertRaises(ValueError):
            confirm_deadline(self.con,CASE['case_id'],CASE['due_at'],'operator',1,'AI_GUESSED')
        self.assertFalse(get_case(self.con,CASE['case_id'])[0]['due_verified'])

    def test_unauthorized_empty_actor_rejected(self):
        with self.assertRaises(ValueError):
            confirm_deadline(self.con,CASE['case_id'],CASE['due_at'],'',1,'SOURCE_REVIEWED')

    def test_invalid_naive_date_rejected(self):
        with self.assertRaises(ValueError):
            confirm_deadline(self.con,CASE['case_id'],'2026-10-22T17:00','operator',1,'SOURCE_REVIEWED')

    def test_rollback_on_audit_failure(self):
        with self.con:
            self.con.execute("CREATE TRIGGER reject_audit BEFORE INSERT ON audit BEGIN SELECT RAISE(ABORT,'test-failure'); END")
        with self.assertRaises(sqlite3.DatabaseError):
            confirm_deadline(self.con,CASE['case_id'],CASE['due_at'],'operator',1,'SOURCE_REVIEWED')
        case,rev=get_case(self.con,CASE['case_id'])
        self.assertFalse(case['due_verified'])
        self.assertEqual(rev,1)

    def test_approval_queue_requires_evidence(self):
        c=dict(CASE,case_id='HR-SYNTH',kind='HR',status='READY_FOR_APPROVAL',approval_status='PENDING')
        add_case(self.con,c)
        row=next(x for x in review_queue(self.con) if x['case_id']=='HR-SYNTH')
        self.assertIn('VERIFY_DEADLINE',row['reasons'])
        self.assertIn('MISSING_EVIDENCE',row['reasons'])
        self.assertIn('APPROVAL_PENDING',row['reasons'])
        with self.assertRaises(ValueError):
            decide(self.con,'HR-SYNTH','APPROVED','operator',1)


class CLIHumanGateTests(unittest.TestCase):
    def setUp(self):
        self.d=tempfile.TemporaryDirectory()
        self.addCleanup(self.d.cleanup)
        self.root=Path(__file__).resolve().parents[1]
        self.db=Path(self.d.name)/'db.sqlite'
        con=open_store(self.db)
        add_case(con,dict(CASE))
        con.close()
        self.base=[sys.executable,'-m','edu_workflow.cli','--db',str(self.db)]
        self.env=dict(os.environ,PYTHONPATH=str(self.root/'python'))
        self.actor=getpass.getuser()

    def run_cli(self,*args,typed=''):
        return subprocess.run(self.base+list(args),input=typed,text=True,capture_output=True,
                              cwd=self.root,env=self.env)

    def test_no_verifier_allowlist_is_fail_closed(self):
        self.env.pop('EDU_VERIFIER_USERS',None)
        p=self.run_cli('confirm-deadline','--case-id',CASE['case_id'],'--due',CASE['due_at'],
                       '--revision','1','--method','source-reviewed')
        self.assertEqual(p.returncode,2)
        self.assertNotIn('SENSITIVE_DO_NOT_PRINT',p.stderr)

    def test_wrong_token_does_not_confirm(self):
        self.env['EDU_VERIFIER_USERS']=self.actor
        p=self.run_cli('confirm-deadline','--case-id',CASE['case_id'],'--due',CASE['due_at'],
                       '--revision','1','--method','source-reviewed',typed='CONFIRM WRONG\n')
        self.assertEqual(p.returncode,2)
        con=open_store(self.db)
        try:
            self.assertFalse(get_case(con,CASE['case_id'])[0]['due_verified'])
        finally:
            con.close()

    def test_full_cli_success_then_stale_retry_blocked(self):
        self.env['EDU_VERIFIER_USERS']=self.actor
        command=('confirm-deadline','--case-id',CASE['case_id'],'--due',CASE['due_at'],
                 '--revision','1','--method','source-reviewed')
        p=self.run_cli(*command,typed=f"CONFIRM {CASE['case_id']} {CASE['due_at']}\n")
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertEqual(json.loads(p.stdout)['revision'],2)
        old=self.run_cli(*command,typed=f"CONFIRM {CASE['case_id']} {CASE['due_at']}\n")
        self.assertEqual(old.returncode,2)
        queue=self.run_cli('review-queue')
        self.assertEqual(queue.returncode,0)
        self.assertEqual(json.loads(queue.stdout),[])


if __name__=='__main__':
    unittest.main()
