"""W2 regression tests: conservative email extraction, idempotency and Outlook pagination."""
import hashlib
import json
import sys
import tempfile
import types
import unittest
from email.message import EmailMessage
from pathlib import Path
from unittest.mock import patch

from edu_workflow.intake import (
    MAX_EMAIL_BYTES, case_id_for_source, email_to_case, parse_explicit_deadline, read_eml_folder,
)
from edu_workflow.outlook_classic import unread_cases
from edu_workflow.store import add_case, get_cases, open_store


def eml(body, *, identifier='<untrusted@example.invalid>'):
    msg = EmailMessage()
    msg['Message-ID'] = identifier
    msg['From'] = 'fictional-user@example.invalid'
    msg['Subject'] = 'Fictional personnel review: private subject'
    msg.set_content(body)
    return msg.as_bytes()


class SafeIntakeTests(unittest.TestCase):
    def test_iso_explicit_candidate_unverified(self):
        raw = eml('DUE:2026-10-22T17:00:00+09:00')
        case = email_to_case(raw)
        self.assertEqual(case['due_at'], '2026-10-22T17:00:00+09:00')
        self.assertFalse(case['due_verified'])
        self.assertEqual(case['status'], 'TRIAGE')

    def test_conflicting_timestamps_do_not_choose_first(self):
        txt = 'DUE:2026-10-22T17:00+09:00 and DUE:2026-10-23T17:00+09:00'
        self.assertIsNone(parse_explicit_deadline(txt))

    def test_duplicate_equivalent_timestamps_are_not_a_conflict(self):
        txt = 'DUE:2026-10-22T17:00+09:00 期限：2026年10月22日 17時00分'
        self.assertEqual(parse_explicit_deadline(txt), '2026-10-22T17:00:00+09:00')

    def test_invalid_iso_suppresses_other_candidate(self):
        txt = 'DUE:2026-10-22T17:00+09:00 DUE:2026-02-30T17:00+09:00'
        self.assertIsNone(parse_explicit_deadline(txt))

    def test_invalid_japanese_suppresses_other_candidate(self):
        txt = '期限：2026年10月22日 17時00分 期限：2026年02月30日 17時00分'
        self.assertIsNone(parse_explicit_deadline(txt))

    def test_date_only_not_assigned_an_invented_time(self):
        self.assertIsNone(parse_explicit_deadline('期限：2026年10月22日'))
        self.assertIsNone(parse_explicit_deadline('DUE:2026-10-22'))

    def test_relative_time_never_guessed(self):
        self.assertIsNone(parse_explicit_deadline('明日の夕方までに提出してください'))

    def test_html_only_not_semantically_processed(self):
        raw = b'MIME-Version: 1.0\nContent-Type: text/html; charset=utf-8\n\n<b>DUE:2026-10-22T17:00+09:00</b>'
        self.assertIsNone(email_to_case(raw)['due_at'])

    def test_exported_eml_case_id_backward_compatible(self):
        raw = eml('DUE:2026-10-22T17:00+09:00')
        self.assertEqual(email_to_case(raw)['case_id'], 'MAIL-' + hashlib.sha256(raw).hexdigest()[:20].upper())

    def test_source_key_not_in_persisted_case(self):
        key='SIMULATED-MAPI-ENTRY-ID-DO-NOT-LEAK'
        raw=eml('DUE:2026-10-22T17:00+09:00')
        saved=json.dumps(email_to_case(raw,source_key=key))
        self.assertNotIn(key, saved)
        self.assertNotIn('Fictional personnel review', saved)
        self.assertEqual(email_to_case(raw,source_key=key)['case_id'],
                         case_id_for_source('outlook-classic:' + key))

    def test_message_id_collision_does_not_merge_two_distinct_eml(self):
        first=email_to_case(eml('DUE:2026-10-22T17:00+09:00'))
        second=email_to_case(eml('DUE:2026-10-23T17:00+09:00'))
        self.assertNotEqual(first['case_id'], second['case_id'])

    def test_repeated_directory_import_preserves_human_changes(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)
            (p/'a.eml').write_bytes(eml('期限：2026年10月22日 17時00分'))
            db=open_store(p/'local.sqlite')
            try:
                self.assertEqual(sum(add_case(db,x) for x in read_eml_folder(p)),1)
                self.assertEqual(sum(add_case(db,x) for x in read_eml_folder(p)),0)
                self.assertEqual(len(get_cases(db)),1)
            finally:
                db.close()

    def test_oversized_email_refused(self):
        with self.assertRaises(ValueError):
            email_to_case(b'x' * (MAX_EMAIL_BYTES + 1))


class OutlookPaginationTests(unittest.TestCase):
    def mock_outlook(self):
        class FakeMail:
            Class=43
            UnRead=True
            Subject='Do not log real school subject'
            Body='DUE:2026-10-22T17:00+09:00'
            def __init__(self, entry_id):
                self.EntryID=entry_id
        class FakeItems:
            def __init__(self):
                self.data=[FakeMail('E1'),FakeMail('E2'),FakeMail('E3')]
                self.Count=len(self.data)
            def Sort(self,*args):
                pass
            def Item(self,i):
                return self.data[i-1]
        class FakeInbox:
            StoreID='FAKE-STORE'
            Items=FakeItems()
        class FakeNamespace:
            def GetDefaultFolder(self,_):
                return FakeInbox()
        class FakeApp:
            def GetNamespace(self,_):
                return FakeNamespace()
        client=types.ModuleType('win32com.client')
        client.Dispatch=lambda _: FakeApp()
        package=types.ModuleType('win32com')
        package.client=client
        return patch.dict(sys.modules,{'win32com':package,'win32com.client':client})

    def test_skips_already_seen_to_avoid_inbox_starvation(self):
        existing = {case_id_for_source('outlook-classic:FAKE-STORE:E1'),
                    case_id_for_source('outlook-classic:FAKE-STORE:E2')}
        with self.mock_outlook():
            items=list(unread_cases(limit=1,existing_ids=existing))
        self.assertEqual(len(items),1)
        self.assertEqual(items[0]['case_id'],case_id_for_source('outlook-classic:FAKE-STORE:E3'))
        self.assertEqual(items[0]['due_verified'],False)

    def test_outlook_limit_rejected_before_com_import(self):
        with self.assertRaises(ValueError):
            list(unread_cases(limit=0))
        with self.assertRaises(ValueError):
            list(unread_cases(limit=300))

    def test_scanned_emails_are_still_unread(self):
        with self.mock_outlook():
            imported=list(unread_cases(limit=2))
        self.assertEqual(len(imported),2)
        self.assertNotEqual(imported[0]['case_id'],imported[1]['case_id'])

    def test_no_new_mail_after_all_seen(self):
        ids={case_id_for_source('outlook-classic:FAKE-STORE:E'+str(i)) for i in (1,2,3)}
        with self.mock_outlook():
            self.assertEqual(list(unread_cases(limit=2,existing_ids=ids)), [])


if __name__ == '__main__':
    unittest.main()
