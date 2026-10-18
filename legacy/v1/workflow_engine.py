#!/usr/bin/env python3
"""Educational administration workflow rule-engine reference (stdlib only).

This is an offline acceptance prototype, not an Outlook/Power Automate integration.
No content goes to external services unless an operator explicitly runs SMTP dispatch.
"""
import argparse
import json
import os
import sqlite3
import smtplib
import ssl
from datetime import datetime, date
from email.message import EmailMessage
from pathlib import Path
from zoneinfo import ZoneInfo

JST = ZoneInfo('Asia/Tokyo')
ACTIVE = {'NEW', 'TRIAGE', 'DRAFT', 'READY_FOR_APPROVAL', 'APPROVED', 'IN_PROGRESS'}
VALID_CLASSES = {'PUBLIC', 'INTERNAL', 'CONFIDENTIAL', 'RESTRICTED'}
VALID_KINDS = {'EMAIL', 'DOCUMENT', 'REGULATION', 'HR', 'SCHEDULE'}
SCHEMA = '''CREATE TABLE IF NOT EXISTS outbox (
 event_key TEXT PRIMARY KEY, case_id TEXT NOT NULL, kind TEXT NOT NULL,
 message TEXT NOT NULL, recipient TEXT NOT NULL, created_at TEXT NOT NULL,
 delivery_status TEXT NOT NULL DEFAULT 'QUEUED', delivered_at TEXT);
'''


def now_jst():
    return datetime.now(tz=JST)


def iso_jst(text):
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        raise ValueError('Deadline must include timezone offset')
    return parsed.astimezone(JST)


def load_cases(path):
    with open(path, encoding='utf-8') as fh:
        cases = json.load(fh)
    if not isinstance(cases, list):
        raise ValueError('Root must be a list')
    ids = set()
    for c in cases:
        case_id = c.get('case_id')
        if not case_id or case_id in ids:
            raise ValueError(f'Duplicate or missing case_id: {case_id}')
        ids.add(case_id)
        if c.get('data_class') not in VALID_CLASSES:
            raise ValueError(f'Invalid data_class: {case_id}')
        if c.get('kind') not in VALID_KINDS:
            raise ValueError(f'Invalid kind: {case_id}')
        if c.get('status') not in ACTIVE | {'COMPLETED', 'REJECTED', 'CANCELLED'}:
            raise ValueError(f'Invalid status: {case_id}')
        if c.get('due_at'):
            iso_jst(c['due_at'])
    return cases


def connection(db_file):
    con = sqlite3.connect(db_file)
    con.execute('PRAGMA busy_timeout=5000')
    con.executescript(SCHEMA)
    return con


def safe_label(c):
    # Never disclose sensitive titles in alerts/outbox.
    if c['data_class'] in {'CONFIDENTIAL', 'RESTRICTED'}:
        return f"Hồ sơ hạn chế #{c['case_id']}"
    return c.get('safe_title', c['case_id'])


def rules(c, now):
    """Return (rule_id, message) events. Rules NEVER decide HR merits."""
    if c['status'] not in ACTIVE:
        return []
    label = safe_label(c)
    events = []
    if not c.get('due_at') or not c.get('due_verified'):
        events.append(('VERIFY_DEADLINE', f'Cần xác minh thời hạn: {label}. Không tự suy đoán.'))
    else:
        due = iso_jst(c['due_at'])
        days = (due.date() - now.date()).days
        if days in (3, 1):
            events.append((f'D_MINUS_{days}', f'Nhắc hạn còn {days} ngày: {label}.'))
        elif days == 0:
            if now > due:
                events.append(('OVERDUE_0', f'Đã quá hạn trong ngày: {label}.'))
            else:
                events.append(('DUE_TODAY', f'Đến hạn hôm nay: {label}.'))
        elif days < 0:
            events.append(('OVERDUE', f'Đã quá hạn {-days} ngày: {label}.'))
    blocked_by_evidence = c['kind'] in {'HR', 'REGULATION'} and not c.get('evidence_ref')
    if c['status'] == 'READY_FOR_APPROVAL' and c.get('approval_status') != 'APPROVED' and not blocked_by_evidence:
        if c.get('approval_status') == 'REJECTED':
            events.append(('REJECTED_REVIEW', f'Yêu cầu bị từ chối, cần xử lý lại: {label}.'))
        else:
            events.append(('APPROVAL_PENDING', f'Chờ quyết định của người phụ trách: {label}.'))
    if blocked_by_evidence:
        events.append(('MISSING_EVIDENCE', f'Thiếu căn cứ xác minh, không cho phép phê duyệt: {label}.'))
    return events


def enqueue(cases, conn, now):
    created = 0
    for c in cases:
        for rule, msg in rules(c, now):
            # Events are once per calendar day: repeat unresolved conditions daily.
            key = f"{c['case_id']}|{rule}|{now.date().isoformat()}"
            cursor = conn.execute('''INSERT OR IGNORE INTO outbox
                 (event_key,case_id,kind,message,recipient,created_at) VALUES (?,?,?,?,?,?)''',
                 (key, c['case_id'], rule, msg, c.get('owner', 'INTERNAL_OWNER'), now.isoformat()))
            created += cursor.rowcount
    conn.commit()
    return created


def list_outbox(conn):
    return [dict(zip(('event_key','kind','message','recipient','delivery_status'), row))
            for row in conn.execute('SELECT event_key,kind,message,recipient,delivery_status FROM outbox ORDER BY event_key')]


def send_smtp(recipient, title, message):
    host = os.environ.get('WORKFLOW_SMTP_HOST')
    port = int(os.environ.get('WORKFLOW_SMTP_PORT', '587'))
    sender = os.environ.get('WORKFLOW_SMTP_FROM')
    allowed = os.environ.get('WORKFLOW_SMTP_ALLOWLIST', '').split(',')
    if not host or not sender or not allowed or recipient not in allowed:
        raise ValueError('Missing SMTP config or recipient not on allowlist')
    email = EmailMessage()
    email['From'] = sender
    email['To'] = recipient
    email['Subject'] = title
    email.set_content(message)
    with smtplib.SMTP(host, port, timeout=15) as smtp:
        smtp.ehlo()
        smtp.starttls(context=ssl.create_default_context())
        smtp.ehlo()
        user = os.environ.get('WORKFLOW_SMTP_USER')
        password = os.environ.get('WORKFLOW_SMTP_PASSWORD')
        if user and password:
            smtp.login(user, password)
        smtp.send_message(email)


def dispatch(conn, channel, now):
    """Send only queued events. On remote SMTP ambiguity, status may still QUEUED;
    operator must reconcile with provider before rerun (at-least-once caveat)."""
    delivered = 0
    pending = conn.execute('SELECT event_key,kind,message,recipient FROM outbox WHERE delivery_status = ? ORDER BY event_key', ('QUEUED',)).fetchall()
    for event_key, kind, message, recipient in pending:
        if channel == 'stdout':
            print(f'[{kind}] {recipient}: {message}')
        else:
            send_smtp(recipient, f'[Workflow] {kind}', message)
        conn.execute('UPDATE outbox SET delivery_status=?,delivered_at=? WHERE event_key=? AND delivery_status=?',
                     ('SENT', now.isoformat(), event_key, 'QUEUED'))
        conn.commit()
        delivered += 1
    return delivered


def approve(cases_file, case_id, decision, approver, now):
    cases = load_cases(cases_file)
    target = next((c for c in cases if c['case_id'] == case_id), None)
    if not target:
        raise ValueError('Unknown case')
    if target['status'] != 'READY_FOR_APPROVAL':
        raise ValueError('Case is not pending decision')
    if target['kind'] in {'HR', 'REGULATION'} and not target.get('evidence_ref'):
        raise ValueError('Missing evidence: cannot approve')
    if decision == 'approve':
        target['status'], target['approval_status'] = 'APPROVED', 'APPROVED'
    else:
        target['status'], target['approval_status'] = 'REJECTED', 'REJECTED'
    target['approver'], target['decision_at'] = approver, now.isoformat()
    # Atomic local-file replacement. Only for offline test data; do not use for
    # multi-writer production, where SharePoint/Dataverse handles concurrency.
    temp = str(cases_file) + '.tmp'
    with open(temp, 'w', encoding='utf-8') as f:
        json.dump(cases, f, ensure_ascii=False, indent=2)
    os.replace(temp, cases_file)
    return target


def main():
    p = argparse.ArgumentParser(description='Offline reference scheduler - educational administration')
    p.add_argument('command', choices=['run','outbox','dispatch','approve'])
    p.add_argument('--cases', default='sample_cases.json')
    p.add_argument('--db', default='workflow_state.sqlite3')
    p.add_argument('--at', help='ISO timestamp with timezone, e.g. 2026-10-19T09:00:00+09:00')
    p.add_argument('--channel', choices=['stdout','smtp'], default='stdout')
    p.add_argument('--case-id')
    p.add_argument('--decision', choices=['approve','reject'])
    p.add_argument('--approver')
    a = p.parse_args()
    now = iso_jst(a.at) if a.at else now_jst()
    if a.command == 'approve':
        if not (a.case_id and a.decision and a.approver):
            p.error('approve requires --case-id --decision --approver')
        print(json.dumps(approve(a.cases, a.case_id, a.decision, a.approver, now), ensure_ascii=False, indent=2))
        return
    with connection(a.db) as conn:
        if a.command == 'run':
            print(json.dumps({'new_alerts': enqueue(load_cases(a.cases), conn, now), 'at': now.isoformat()}))
        elif a.command == 'outbox':
            print(json.dumps(list_outbox(conn), ensure_ascii=False, indent=2))
        elif a.command == 'dispatch':
            print(json.dumps({'dispatched': dispatch(conn, a.channel, now), 'channel': a.channel}))

if __name__ == '__main__':
    main()
