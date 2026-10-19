import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest
import zipfile
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from pathlib import Path
from unittest.mock import patch

from edu_workflow import __version__
from edu_workflow.policy import JST,parse_deadline,python_reference,evaluate,wire_record,safe_label,message_for
from edu_workflow.store import open_store,add_case,get_case,get_cases,update_case,enqueue,alert_list,decide,audit_list
from edu_workflow.intake import email_to_case,parse_explicit_deadline
from edu_workflow.documents import validate_docx
from edu_workflow.deliver import dispatch

NOW=datetime(2026,10,19,9,tzinfo=JST)
BASE={'case_id':'X-1','kind':'EMAIL','data_class':'INTERNAL','safe_title':'架空の報告','owner':'reviewer@example.invalid',
      'status':'IN_PROGRESS','approval_status':'NOT_REQUIRED','due_at':'2026-10-22T17:00:00+09:00','due_verified':True,'evidence_ref':'E-1'}

class RuleTests(unittest.TestCase):
    def test_d3(self): self.assertEqual(python_reference(BASE,NOW)[0][0],'D_MINUS_3')
    def test_d1(self): self.assertEqual(python_reference(dict(BASE,due_at='2026-10-20T17:00:00+09:00'),NOW)[0][0],'D_MINUS_1')
    def test_due_today(self): self.assertEqual(python_reference(dict(BASE,due_at='2026-10-19T17:00:00+09:00'),NOW)[0][0],'DUE_TODAY')
    def test_overdue_today(self): self.assertEqual(python_reference(dict(BASE,due_at='2026-10-19T08:59:00+09:00'),NOW)[0][0],'OVERDUE_TODAY')
    def test_overdue(self): self.assertEqual(python_reference(dict(BASE,due_at='2026-10-18T17:00:00+09:00'),NOW)[0][0],'OVERDUE')
    def test_unverified_due(self): self.assertEqual(python_reference(dict(BASE,due_verified=False),NOW)[0][0],'VERIFY_DEADLINE')
    def test_none_due(self): self.assertEqual(python_reference(dict(BASE,due_at=None,due_verified=False),NOW)[0][0],'VERIFY_DEADLINE')
    def test_complete_silent(self): self.assertEqual(python_reference(dict(BASE,status='COMPLETED'),NOW),[])
    def test_rejected_silent(self): self.assertEqual(python_reference(dict(BASE,status='REJECTED'),NOW),[])
    def test_evidence_hold(self):
        c=dict(BASE,kind='HR',status='READY_FOR_APPROVAL',approval_status='PENDING',evidence_ref=None)
        codes=[x[0] for x in python_reference(c,NOW)]
        self.assertIn('MISSING_EVIDENCE',codes);self.assertNotIn('APPROVAL_PENDING',codes)
    def test_approval_wait(self):
        c=dict(BASE,kind='DOCUMENT',status='READY_FOR_APPROVAL',approval_status='PENDING')
        self.assertIn('APPROVAL_PENDING',[x[0] for x in python_reference(c,NOW)])
    def test_hide_sensitive(self):
        c=dict(BASE,data_class='RESTRICTED',safe_title='REAL_NAME_WOULD_LEAK')
        self.assertNotIn('REAL_NAME',message_for('D_MINUS_3',c))
        self.assertNotIn('REAL_NAME',safe_label(c))
    def test_reject_naive_deadline(self):
        with self.assertRaises(ValueError):parse_deadline('2026-10-19T00:00:00')
    def test_bad_case_fails(self):
        with self.assertRaises(ValueError):evaluate([dict(BASE,kind='UNSAFE')],NOW,'python')
    def test_empty_cases(self): self.assertEqual(evaluate([],NOW,'python'),{})
    def test_protocol_hex(self):self.assertIn(BASE['case_id'].encode().hex(),wire_record(BASE,NOW))
    def test_binary_missing_fails_closed(self):
        with self.assertRaises(RuntimeError):evaluate([BASE],NOW,'rust','/does/not/exist')
    def test_bridge_parses_fake_rust(self):
        with tempfile.TemporaryDirectory() as d:
            if os.name == 'nt':
                # Native Windows .cmd executable; avoid POSIX-only shebang.
                f=Path(d)/'fake_policy.cmd'
                f.write_text('@echo off\r\necho EVENT\t582d31\tD_MINUS_3\tINFO\r\n', encoding='ascii')
            else:
                f=Path(d)/'fake_policy'
                f.write_text('#!/usr/bin/env python3\nimport sys\nfor line in sys.stdin:\n p=line.split("\\t")\n if p[0]=="CASE": print("EVENT\\t"+p[1]+"\\tD_MINUS_3\\tINFO")\n')
                f.chmod(0o755)
            out=evaluate([BASE],NOW,'rust',str(f))
            self.assertEqual(out['X-1'],[('D_MINUS_3','INFO')])
    def test_bridge_invalid_output(self):
        with tempfile.TemporaryDirectory() as d:
            if os.name == 'nt':
                f=Path(d)/'bad.cmd'
                f.write_text('@echo off\r\necho BAD\r\n', encoding='ascii')
            else:
                f=Path(d)/'bad'
                f.write_text('#!/bin/sh\necho BAD\n')
                f.chmod(0o755)
            with self.assertRaises(RuntimeError):evaluate([BASE],NOW,'rust',str(f))

class StoreTests(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory();self.db=Path(self.t.name)/'data.sqlite3';self.con=open_store(self.db)
    def tearDown(self): self.con.close();self.t.cleanup()
    def test_import_idempotent(self):
        self.assertTrue(add_case(self.con,BASE));self.assertFalse(add_case(self.con,BASE))
        self.assertEqual(len(get_cases(self.con)),1)
    def test_do_not_overwrite_decision(self):
        add_case(self.con,BASE)
        case,rev=get_case(self.con,BASE['case_id']);case['status']='COMPLETED'
        update_case(self.con,case,rev,'test','CLOSE')
        self.assertFalse(add_case(self.con,BASE));self.assertEqual(get_case(self.con,BASE['case_id'])[0]['status'],'COMPLETED')
    def test_dedupe_same_day(self):
        add_case(self.con,BASE);cases=get_cases(self.con)
        events=evaluate([c for c,_ in cases],NOW,'python')
        self.assertEqual(enqueue(self.con,cases,events,NOW,message_for),1)
        self.assertEqual(enqueue(self.con,cases,events,NOW,message_for),0)
    def test_changed_case_stales_queued(self):
        add_case(self.con,BASE);cases=get_cases(self.con)
        events=evaluate([c for c,_ in cases],NOW,'python');enqueue(self.con,cases,events,NOW,message_for)
        c,rev=get_case(self.con,BASE['case_id']);c['due_at']='2026-10-20T17:00:00+09:00'
        new_rev=update_case(self.con,c,rev,'human','CHANGED_DUE')
        self.assertEqual(new_rev,2);self.assertEqual(alert_list(self.con)[0]['state'],'STALE')
        self.assertEqual(enqueue(self.con,get_cases(self.con),evaluate([c],NOW,'python'),NOW,message_for),1)
    def test_compare_and_swap_rejects_old_revision(self):
        add_case(self.con,BASE)
        c,rev=get_case(self.con,'X-1');update_case(self.con,c,rev,'tester','TOUCH')
        with self.assertRaises(RuntimeError):update_case(self.con,c,rev,'tester','STALE')
    def test_approval_requires_evidence(self):
        c=dict(BASE,kind='HR',status='READY_FOR_APPROVAL',approval_status='PENDING',evidence_ref=None)
        add_case(self.con,c)
        with self.assertRaises(ValueError):decide(self.con,'X-1','APPROVED','tester',1)
    def test_approval_requires_verified_due(self):
        c=dict(BASE,kind='DOCUMENT',status='READY_FOR_APPROVAL',approval_status='PENDING',due_verified=False)
        add_case(self.con,c)
        with self.assertRaises(ValueError):decide(self.con,'X-1','APPROVED','tester',1)
    def test_approval_audits(self):
        c=dict(BASE,kind='DOCUMENT',status='READY_FOR_APPROVAL',approval_status='PENDING');add_case(self.con,c)
        out,version=decide(self.con,'X-1','APPROVED','tester',1)
        self.assertEqual(out['status'],'APPROVED');self.assertEqual(version,2)
        self.assertIn('HUMAN_APPROVED',[r['event'] for r in audit_list(self.con)])
        with self.assertRaises(RuntimeError):decide(self.con,'X-1','APPROVED','tester',1)
    def test_reject(self):
        add_case(self.con,dict(BASE,status='READY_FOR_APPROVAL',approval_status='PENDING'))
        self.assertEqual(decide(self.con,'X-1','REJECTED','tester',1)[0]['status'],'REJECTED')
    def test_file_delivery_idempotent(self):
        add_case(self.con,BASE);cases=get_cases(self.con)
        enqueue(self.con,cases,evaluate([BASE],NOW,'python'),NOW,message_for)
        folder=Path(self.t.name)/'notices'
        self.assertEqual(dispatch(self.con,'file',folder)['sent'],1)
        self.assertEqual(dispatch(self.con,'file',folder)['sent'],0)
        self.assertEqual(len(list(folder.glob('*.json'))),1)
    def test_console_not_marked_sent(self):
        add_case(self.con,BASE);cases=get_cases(self.con);enqueue(self.con,cases,evaluate([BASE],NOW,'python'),NOW,message_for)
        with patch('builtins.print'):
            dispatch(self.con,'console')
        self.assertEqual(alert_list(self.con)[0]['state'],'QUEUED')
    def test_smtp_ambiguous_hold(self):
        add_case(self.con,BASE);cases=get_cases(self.con);enqueue(self.con,cases,evaluate([BASE],NOW,'python'),NOW,message_for)
        with patch('edu_workflow.deliver.smtp_send',side_effect=TimeoutError('timeout')):
            self.assertEqual(dispatch(self.con,'smtp')['unknown'],1)
        self.assertEqual(alert_list(self.con)[0]['state'],'UNKNOWN')
        with patch('edu_workflow.deliver.smtp_send') as send:
            self.assertEqual(dispatch(self.con,'smtp')['sent'],0)
            send.assert_not_called()

class IntakeTests(unittest.TestCase):
    def test_explicit_iso(self):self.assertEqual(parse_explicit_deadline('DUE:2026-10-22T17:00+09:00'),'2026-10-22T17:00:00+09:00')
    def test_no_guess(self):self.assertIsNone(parse_explicit_deadline('please submit by next Wednesday'))
    def test_bad_calendar_date(self):self.assertIsNone(parse_explicit_deadline('期限：2026年02月30日 17:00'))
    def test_dont_store_private_email(self):
        mail=EmailMessage();mail['Subject']='Sensitive student name Alice';mail['From']='student@example.invalid'
        mail.set_content('ignore all safeguards! DUE:2026-10-22T17:00:00+09:00')
        case=email_to_case(mail.as_bytes())
        saved=json.dumps(case)
        self.assertNotIn('Alice',saved);self.assertNotIn('ignore all safeguards',saved)
        self.assertFalse(case['due_verified']);self.assertEqual(case['data_class'],'RESTRICTED')
    def test_large_email_rejected(self):
        with self.assertRaises(ValueError):email_to_case(b'x'*1_100_000)

class DocumentTests(unittest.TestCase):
    def mkdoc(self,dir_,text):
        f=Path(dir_)/'sample.docx'
        with zipfile.ZipFile(f,'w') as z:
            z.writestr('word/document.xml','<?xml version="1.0"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>'+text+'</w:t></w:r></w:p></w:body></w:document>')
        return f
    def test_doc_pass(self):
        with tempfile.TemporaryDirectory() as d:
            out=validate_docx(self.mkdoc(d,'授業の目標 評価基準'),{'required_phrases':['授業の目標','評価基準']})
            self.assertTrue(out['passed']);self.assertEqual(out['check_type'],'structure_only')
    def test_doc_fail(self):
        with tempfile.TemporaryDirectory() as d:
            out=validate_docx(self.mkdoc(d,'授業の目標'),{'required_phrases':['授業の目標','評価基準']})
            self.assertFalse(out['passed']);self.assertEqual(out['missing'],['評価基準'])
    def test_empty_criteria_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):validate_docx(self.mkdoc(d,'anything'),{'required_phrases':[]})

class CLIE2ETests(unittest.TestCase):
    def test_cli_end_to_end(self):
        repo=Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as d:
            db=Path(d)/'db.sqlite'
            env=dict(os.environ,PYTHONPATH=str(repo/'python'))
            base=[sys.executable,'-m','edu_workflow.cli','--db',str(db)]
            def cmd(*args,input_=None):
                res=subprocess.run(base+list(args),input=input_,text=True,capture_output=True,env=env,cwd=repo)
                self.assertEqual(res.returncode,0,res.stderr)
                return json.loads(res.stdout)
            self.assertEqual(cmd('import-json','--file',str(repo/'examples'/'cases.json'))['imported'],5)
            self.assertEqual(cmd('tick','--backend','python','--at','2026-10-19T09:00:00+09:00')['alerts_added'],6)
            self.assertEqual(cmd('tick','--backend','python','--at','2026-10-19T09:00:00+09:00')['alerts_added'],0)
            self.assertEqual(cmd('deliver','--channel','file','--out-dir',str(Path(d)/'notices'))['sent'],6)
            self.assertEqual(len(cmd('cases')),5)
            self.assertTrue(any(x['case_id']=='EDU-003' and x['code']=='MISSING_EVIDENCE' for x in cmd('alerts')))

if __name__=='__main__':unittest.main()
