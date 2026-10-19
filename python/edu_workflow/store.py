"""Transactional local SQLite store. Single-node reference, not a tenant-wide database."""
from __future__ import annotations
import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from .policy import validate_case

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


def update_case(conn,case, expected_revision, actor, action):
    validate_case(case)
    now=now_iso()
    with conn:
        cursor=conn.execute('UPDATE cases SET payload=?,revision=revision+1,updated_at=? WHERE case_id=? AND revision=?',
             (json.dumps(case,ensure_ascii=False,sort_keys=True),now,case['case_id'],expected_revision))
        if cursor.rowcount != 1: raise RuntimeError('Concurrent update: revision changed; reload before approval')
        conn.execute("UPDATE alerts SET state='STALE' WHERE case_id=? AND state='QUEUED'",(case['case_id'],))
        conn.execute('INSERT INTO audit(case_id,event,actor,at) VALUES(?,?,?,?)',
                     (case['case_id'],action,actor,now))
    return expected_revision+1


def enqueue(conn, cases, events, now, message_for):
    created=0
    with conn:
        for case, rev in cases:
            for code,severity in events[case['case_id']]:
                day=now.date().isoformat()
                key=hashlib.sha256(f'{case["case_id"]}|{rev}|{code}|{day}'.encode('utf-8')).hexdigest()
                cursor=conn.execute('INSERT OR IGNORE INTO alerts(alert_id,case_id,revision,code,severity,day,message,created_at) VALUES (?,?,?,?,?,?,?,?)',
                                    (key,case['case_id'],rev,code,severity,day,message_for(code,case),now_iso()))
                created += cursor.rowcount
    return created


def alert_list(conn, state=None):
    if state:
        rows=conn.execute('SELECT * FROM alerts WHERE state=? ORDER BY created_at,alert_id',(state,))
    else:
        rows=conn.execute('SELECT * FROM alerts ORDER BY created_at,alert_id')
    return [dict(row) for row in rows]


def audit_list(conn): return [dict(r) for r in conn.execute('SELECT * FROM audit ORDER BY id')]


def decide(conn,case_id,decision,actor,expected_rev):
    case,rev=get_case(conn,case_id)
    if rev!=expected_rev: raise RuntimeError('stale expected revision')
    if case['status']!='READY_FOR_APPROVAL': raise ValueError('case is not awaiting approval')
    if decision not in {'APPROVED','REJECTED'}: raise ValueError('invalid decision')
    if decision=='APPROVED' and case['kind'] in {'DOCUMENT','HR','REGULATION'} and not case.get('evidence_ref'):
        raise ValueError('cannot approve: evidence_ref missing')
    if decision=='APPROVED' and case.get('due_at') and not case.get('due_verified'):
        raise ValueError('cannot approve: deadline is not verified')
    case['status']=decision
    case['approval_status']=decision
    new_rev=update_case(conn,case,rev,actor,'HUMAN_'+decision)
    with conn:
        conn.execute('INSERT INTO decisions(case_id,revision,actor,decision,made_at) VALUES(?,?,?,?,?)',
                     (case_id,new_rev,actor,decision,now_iso()))
    return case,new_rev
