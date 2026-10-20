"""Transactional local SQLite store. Single-node reference, not a tenant-wide database."""
from __future__ import annotations
import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from .policy import validate_case, ACTIVE, parse_deadline

DDL = '''
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS cases (
 case_id TEXT PRIMARY KEY, payload TEXT NOT NULL, revision INTEGER NOT NULL DEFAULT 1,
 updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS alerts (
 alert_id TEXT PRIMARY KEY, case_id TEXT NOT NULL REFERENCES cases(case_id),
 revision INTEGER NOT NULL, code TEXT NOT NULL, severity TEXT NOT NULL,
 day TEXT NOT NULL, message TEXT NOT NULL,
 state TEXT NOT NULL DEFAULT 'QUEUED', created_at TEXT NOT NULL, delivered_at TEXT,
 CHECK(state IN ('QUEUED','SENDING','SENT','UNKNOWN','STALE'))
);
CREATE TABLE IF NOT EXISTS decisions (
 id INTEGER PRIMARY KEY AUTOINCREMENT, case_id TEXT NOT NULL, revision INTEGER NOT NULL,
 actor TEXT NOT NULL, decision TEXT NOT NULL, made_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS audit (
 id INTEGER PRIMARY KEY AUTOINCREMENT, case_id TEXT NOT NULL, event TEXT NOT NULL,
 actor TEXT NOT NULL, at TEXT NOT NULL, detail TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_alert_state ON alerts(state);
'''


def open_store(path):
    path=Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn=sqlite3.connect(path, timeout=10)
    conn.row_factory=sqlite3.Row
    conn.execute('PRAGMA busy_timeout=10000')
    conn.execute('PRAGMA journal_mode=WAL')
    conn.executescript(DDL)
    return conn


def now_iso(): return datetime.now(timezone.utc).isoformat()


def add_case(conn, case, actor='importer'):
    validate_case(case)
    with conn:
        row=conn.execute('SELECT case_id FROM cases WHERE case_id=?',(case['case_id'],)).fetchone()
        if row: return False  # Never overwrite verified deadlines or human decisions during rescan.
        conn.execute('INSERT INTO cases (case_id,payload,updated_at) VALUES (?,?,?)',
                     (case['case_id'],json.dumps(case,ensure_ascii=False,sort_keys=True),now_iso()))
        conn.execute('INSERT INTO audit(case_id,event,actor,at) VALUES (?,?,?,?)',
                     (case['case_id'],'IMPORTED',actor,now_iso()))
    return True


def get_cases(conn):
    return [(json.loads(r['payload']),r['revision']) for r in conn.execute('SELECT * FROM cases ORDER BY case_id')]


def get_case(conn, case_id):
    row=conn.execute('SELECT * FROM cases WHERE case_id=?',(case_id,)).fetchone()
    if not row: raise ValueError(f'Unknown case_id: {case_id}')
    return json.loads(row['payload']),row['revision']


def _write_case(conn, case, expected_revision, actor, action, now):
    """Execute a revision-checked update inside the caller's transaction."""
    cursor = conn.execute(
        'UPDATE cases SET payload=?,revision=revision+1,updated_at=? WHERE case_id=? AND revision=?',
        (json.dumps(case, ensure_ascii=False, sort_keys=True), now, case['case_id'], expected_revision),
    )
    if cursor.rowcount != 1:
        raise RuntimeError('Concurrent update: revision changed; reload before approval')
    conn.execute("UPDATE alerts SET state='STALE' WHERE case_id=? AND state='QUEUED'", (case['case_id'],))
    conn.execute('INSERT INTO audit(case_id,event,actor,at) VALUES(?,?,?,?)',
                 (case['case_id'], action, actor, now))
    return expected_revision + 1


def update_case(conn, case, expected_revision, actor, action):
    validate_case(case)
    # BEGIN IMMEDIATE prevents two scheduler processes from editing at the same time.
    conn.execute('BEGIN IMMEDIATE')
    try:
        version = _write_case(conn, case, expected_revision, actor, action, now_iso())
        conn.commit()
        return version
    except BaseException:
        conn.rollback()
        raise



# Only a human operator with an approved local account may call this operation
# through the CLI. This store function is a transactional capability, not SSO.
CONFIRMABLE = {'NEW', 'TRIAGE', 'DRAFT', 'IN_PROGRESS', 'READY_FOR_APPROVAL'}
VERIFICATION_METHODS = {'SOURCE_REVIEWED', 'INSTITUTION_REVIEWED'}


def confirm_deadline(conn, case_id, due, actor, expected_revision, method):
    """Confirm a human-reviewed deadline atomically and invalidate old alerts.

    Require explicit method, optimistic revision and an open, unapproved case.
    Never trust parsed email candidate or silently accept a changed revision.
    """
    if method not in VERIFICATION_METHODS:
        raise ValueError('invalid deadline verification method')
    if not isinstance(actor, str) or not actor.strip():
        raise ValueError('verified actor is required')
    normalized = parse_deadline(due).isoformat()
    conn.execute('BEGIN IMMEDIATE')
    try:
        case, revision = get_case(conn, case_id)
        if revision != expected_revision:
            raise RuntimeError('stale expected revision')
        if case['status'] not in CONFIRMABLE:
            raise ValueError('case cannot be modified after approval or closure')
        case['due_at'] = normalized
        case['due_verified'] = True
        validate_case(case)
        new_revision = _write_case(conn, case, revision, actor,
                                   'HUMAN_VERIFIED_DEADLINE', now_iso())
        # Do not copy human-entered notes or original email into audit log.
        conn.execute('UPDATE audit SET detail=? WHERE id=last_insert_rowid()',
                     (json.dumps({'method': method, 'due_at': normalized}),))
        conn.commit()
        return case, new_revision
    except BaseException:
        conn.rollback()
        raise


def review_queue(conn, registry_path=None, as_of=None, hr_packet_path=None):
    """Return masked exception-only tasks. Routine work is never in this queue."""
    result = []
    for case, revision in get_cases(conn):
        if case['status'] not in ACTIVE:
            continue
        reasons = []
        if not case.get('due_verified') or not case.get('due_at'):
            reasons.append('VERIFY_DEADLINE')
        if case['kind'] in {'DOCUMENT', 'HR', 'REGULATION'} and not case.get('evidence_ref'):
            reasons.append('MISSING_EVIDENCE')
        if case['kind'] == 'HR':
            from .hr_evidence import verify_for_hr_approval
            try:
                verify_for_hr_approval(hr_packet_path, case['case_id'],
                                       case.get('evidence_ref'), as_of=as_of)
            except (ValueError, OSError):
                reasons.append('VERIFY_HR_EVIDENCE_PACKET')
        if case['kind'] == 'REGULATION':
            from .regulation import verify_reference
            try:
                check = verify_reference(registry_path, case.get('evidence_ref'), as_of=as_of)
                if check['status'] != 'SOURCE_SNAPSHOT_PASS':
                    reasons.append('VERIFY_REGULATION_SOURCE')
            except (ValueError, OSError):
                reasons.append('VERIFY_REGULATION_SOURCE')
        if case['status'] == 'READY_FOR_APPROVAL' and case['approval_status'] == 'PENDING':
            reasons.append('APPROVAL_PENDING')
        if reasons:
            result.append({
                'case_id': case['case_id'], 'revision': revision,
                'kind': case['kind'], 'status': case['status'],
                'reasons': reasons,
                'candidate_due': case.get('due_at') if not case['due_verified'] else None,
            })
    return result

def enqueue(conn, cases, events, now, message_for):
    """Never enqueue alerts derived from a stale workflow snapshot."""
    created = 0
    conn.execute('BEGIN IMMEDIATE')
    try:
        for case, rev in cases:
            row = conn.execute('SELECT revision,payload FROM cases WHERE case_id=?', (case['case_id'],)).fetchone()
            if row is None or row['revision'] != rev:
                continue
            current = json.loads(row['payload'])
            if current['status'] not in ACTIVE:
                continue
            for code, severity in events[case['case_id']]:
                day = now.date().isoformat()
                key = hashlib.sha256(f'{case["case_id"]}|{rev}|{code}|{day}'.encode('utf-8')).hexdigest()
                cursor = conn.execute(
                    'INSERT OR IGNORE INTO alerts(alert_id,case_id,revision,code,severity,day,message,created_at) VALUES (?,?,?,?,?,?,?,?)',
                    (key, case['case_id'], rev, code, severity, day, message_for(code, current), now_iso()),
                )
                created += cursor.rowcount
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
    return created


def alert_list(conn, state=None):
    if state:
        rows=conn.execute('SELECT * FROM alerts WHERE state=? ORDER BY created_at,alert_id',(state,))
    else:
        rows=conn.execute('SELECT * FROM alerts ORDER BY created_at,alert_id')
    return [dict(row) for row in rows]


def audit_list(conn): return [dict(r) for r in conn.execute('SELECT * FROM audit ORDER BY id')]


def decide(conn, case_id, decision, actor, expected_rev, registry_path=None, as_of=None, hr_packet_path=None):
    """Persist approval, audit and revision atomically, never as separate commits."""
    conn.execute('BEGIN IMMEDIATE')
    try:
        case, rev = get_case(conn, case_id)
        if rev != expected_rev:
            raise RuntimeError('stale expected revision')
        if case['status'] != 'READY_FOR_APPROVAL':
            raise ValueError('case is not awaiting approval')
        if decision not in {'APPROVED', 'REJECTED'}:
            raise ValueError('invalid decision')
        if decision == 'APPROVED' and case['kind'] in {'DOCUMENT', 'HR', 'REGULATION'} and not case.get('evidence_ref'):
            raise ValueError('cannot approve: evidence_ref missing')
        if decision == 'APPROVED' and case.get('due_at') and not case.get('due_verified'):
            raise ValueError('cannot approve: deadline is not verified')
        proof = None
        if decision == 'APPROVED' and case['kind'] == 'REGULATION':
            from .regulation import verify_for_approval
            proof = verify_for_approval(registry_path, case.get('evidence_ref'), as_of=as_of)
        if decision == 'APPROVED' and case['kind'] == 'HR':
            from .hr_evidence import verify_for_hr_approval
            proof = verify_for_hr_approval(
                hr_packet_path, case_id, case.get('evidence_ref'), as_of=as_of)
        case['status'] = decision
        case['approval_status'] = decision
        validate_case(case)
        new_rev = _write_case(conn, case, rev, actor, 'HUMAN_' + decision, now_iso())
        if proof is not None:
            # Pin the checked source's opaque IDs and digests atomically to the
            # human approval audit, never its free-form content.
            conn.execute('UPDATE audit SET detail=? WHERE id=last_insert_rowid()',
                         (json.dumps(proof, sort_keys=True),))
        conn.execute('INSERT INTO decisions(case_id,revision,actor,decision,made_at) VALUES(?,?,?,?,?)',
                     (case_id, new_rev, actor, decision, now_iso()))
        conn.commit()
        return case, new_rev
    except BaseException:
        conn.rollback()
        raise
