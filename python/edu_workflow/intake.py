"""Conservative, read-only intake. Untrusted email text is NEVER interpreted as instructions."""
import hashlib
import re
from datetime import datetime, timedelta, timezone
from email import policy
from email.parser import BytesParser
from pathlib import Path

# Explicit markers only. Dates remain UNVERIFIED until a human confirms the due time.
DUE_ISO = re.compile(r'\bDUE:\s*(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2})?[+]09:00)\b',re.I)
DUE_JP = re.compile(r'期限\s*[：:]\s*(\d{4})[年/-](\d{1,2})[月/-](\d{1,2})日?\s*(\d{1,2})?(?:[:時](\d{1,2}))?')
JST=timezone(timedelta(hours=9))


def parse_explicit_deadline(body):
    m=DUE_ISO.search(body)
    if m:
        try: return datetime.fromisoformat(m.group(1)).isoformat()
        except ValueError: return None
    m=DUE_JP.search(body)
    if m:
        try:
            h=int(m.group(4) or 17); mi=int(m.group(5) or 0)
            return datetime(int(m.group(1)),int(m.group(2)),int(m.group(3)),h,mi,tzinfo=JST).isoformat()
        except ValueError: return None
    return None


def email_to_case(data: bytes, owner='LOCAL_REVIEWER'):
    if len(data)>1_048_576: raise ValueError('email exceeds 1 MiB safety limit')
    msg=BytesParser(policy=policy.default).parsebytes(data)
    if msg.is_multipart():
        part=msg.get_body(preferencelist=('plain',))
        body=part.get_content() if part else ''
    else:
        body=msg.get_content() if msg.get_content_type()=='text/plain' else ''
    if not isinstance(body,str): body=''
    source_id=hashlib.sha256(data).hexdigest()
    # Never persist message body, sender, or subject: even subjects can reveal personal data.
    return {'case_id':'MAIL-'+source_id[:20].upper(),'kind':'EMAIL','data_class':'RESTRICTED',
            'safe_title':'要確認メール','owner':owner,'due_at':parse_explicit_deadline(body),
            'due_verified':False,'status':'TRIAGE','approval_status':'NOT_REQUIRED',
            'evidence_ref':None,'source_ref':'sha256:'+source_id}


def read_eml_folder(folder):
    base=Path(folder)
    if not base.is_dir(): raise ValueError(f'not a folder: {base}')
    for file in sorted(base.glob('*.eml')):
        if file.is_symlink(): continue
        yield email_to_case(file.read_bytes())
