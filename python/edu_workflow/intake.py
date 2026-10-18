"""Conservative email intake; never interpret untrusted email as workflow instructions.

Only explicit, uniquely consistent full timestamps are *candidates*. All candidate
deadlines remain unverified until an operator confirms them. No original message,
address, subject or body is persisted in the case record.
"""
from __future__ import annotations
import hashlib
import re
from datetime import datetime, timedelta, timezone
from email import policy
from email.parser import BytesParser
from pathlib import Path

JST = timezone(timedelta(hours=9))
MAX_EMAIL_BYTES = 1_048_576

# Require a complete timestamp, not a date-only marker with an invented time.
DUE_ISO = re.compile(
    r'(?<!\w)DUE\s*[:：]\s*(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2})?(?:\+09:00|Z))(?=\W|$)',
    re.IGNORECASE,
)
DUE_MARKER = re.compile(r'(?<!\w)DUE\s*[:：]|期限\s*[:：]', re.IGNORECASE)
DUE_JP = re.compile(
    r'期限\s*[:：]\s*(\d{4})\s*(?:年|/|-)\s*(\d{1,2})\s*(?:月|/|-)\s*'
    r'(\d{1,2})\s*日?\s+(\d{1,2})\s*(?:時|:)\s*(\d{1,2})\s*分?',
)


def parse_explicit_deadline(body):
    """Return a candidate only when every recognizable timestamp agrees.

    A conflict or an invalid date suppresses all candidates. A date-only
    deadline is deliberately not coerced to 17:00 or midnight.
    """
    if not isinstance(body, str):
        return None
    candidates = []
    try:
        for match in DUE_ISO.finditer(body):
            dt = datetime.fromisoformat(match.group(1).replace('Z', '+00:00'))
            if dt.tzinfo is None:
                return None
            candidates.append(dt.astimezone(JST).isoformat())
        for match in DUE_JP.finditer(body):
            year, month, day, hour, minute = (int(x) for x in match.groups())
            dt = datetime(year, month, day, hour, minute, tzinfo=JST)
            candidates.append(dt.isoformat())
    except ValueError:
        return None
    # If a DUE/期限 marker is incomplete or uses an unsupported timezone,
    # do not accept a different well-formed marker from the same email.
    markers = sum(1 for _ in DUE_MARKER.finditer(body))
    return candidates[0] if candidates and markers == len(candidates) and len(set(candidates)) == 1 else None


def case_id_for_source(source_key):
    """Opaque stable local ID; never include a raw Outlook EntryID in SQLite."""
    if not isinstance(source_key, str) or not source_key:
        raise ValueError('source key required')
    return 'MAIL-' + hashlib.sha256(source_key.encode('utf-8')).hexdigest()[:20].upper()


def email_to_case(data: bytes, owner='LOCAL_REVIEWER', *, source_key=None):
    if not isinstance(data, bytes) or len(data) > MAX_EMAIL_BYTES:
        raise ValueError('email must be bytes and not exceed 1 MiB')
    msg = BytesParser(policy=policy.default).parsebytes(data)
    if msg.is_multipart():
        part = msg.get_body(preferencelist=('plain',))
        body = part.get_content() if part is not None else ''
    else:
        body = msg.get_content() if msg.get_content_type() == 'text/plain' else ''
    if not isinstance(body, str):
        body = ''
    # Raw-byte hashing for exported EML prevents caller-controlled Message-ID
    # collisions. Classic Outlook may supply a *local* store/entry identity.
    digest = (hashlib.sha256(('outlook-classic:' + source_key).encode('utf-8')).hexdigest()
              if source_key is not None else hashlib.sha256(data).hexdigest())
    return {'case_id':'MAIL-' + digest[:20].upper(), 'kind':'EMAIL',
            'data_class':'RESTRICTED', 'safe_title':'要確認メール',
            'owner':owner, 'due_at':parse_explicit_deadline(body),
            'due_verified':False, 'status':'TRIAGE',
            'approval_status':'NOT_REQUIRED', 'evidence_ref':None,
            'source_ref':'sha256:' + digest}


def read_eml_folder(folder):
    base = Path(folder)
    if not base.is_dir():
        raise ValueError(f'not a folder: {base}')
    for path in sorted(base.glob('*.eml')):
        if path.is_symlink():
            continue
        # Any malformed message fails closed; repeated imports are idempotent
        # and previous successful records are not overwritten.
        yield email_to_case(path.read_bytes())
