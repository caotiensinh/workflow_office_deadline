"""Local-only Windows notification inbox backed by existing SQLite alerts.

This module has NO GUI dependency, network actions, or approval capability.
A desktop ACK acknowledges *visibility* only, never the workflow decision.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone
from .policy import ACTIVE
from .store import now_iso

CREATE_RECEIPTS = """
CREATE TABLE IF NOT EXISTS desktop_receipts (
    alert_id TEXT NOT NULL REFERENCES alerts(alert_id),
    actor TEXT NOT NULL,
    disposition TEXT NOT NULL CHECK(disposition IN ('ACK', 'SNOOZE')),
    snoozed_until TEXT,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (alert_id, actor)
);
CREATE INDEX IF NOT EXISTS idx_desktop_receipts_actor
    ON desktop_receipts(actor, disposition);
"""
DISPLAY_CODE = {
    'VERIFY_DEADLINE':'期限の確認が必要',
    'D_MINUS_3':'期限まで3日',
    'D_MINUS_1':'期限まで1日',
    'DUE_TODAY':'本日が期限',
    'OVERDUE_TODAY':'期限を超過しています',
    'OVERDUE':'期限超過',
    'MISSING_EVIDENCE':'根拠資料が不足',
    'APPROVAL_PENDING':'管理職の承認待ち',
    'REJECTED_REVIEW':'差し戻しの確認',
}
SEVERITIES = {'INFO', 'WARNING', 'CRITICAL'}


def _validate_actor(actor):
    if not isinstance(actor, str) or not actor.strip() or len(actor) > 128:
        raise ValueError('local OS account is required (max 128 chars)')
    return actor.strip().casefold()


def _validate_alert_id(alert_id):
    if not isinstance(alert_id, str) or not re.fullmatch(r'[0-9a-f]{64}', alert_id):
        raise ValueError('expected a 64-character hex alert ID')


def ensure_receipts(conn):
    """Idempotent, additive migration for W4 on existing SQLite installations."""
    with conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS desktop_receipts (
            alert_id TEXT NOT NULL REFERENCES alerts(alert_id),
            actor TEXT NOT NULL,
            disposition TEXT NOT NULL CHECK(disposition IN ('ACK', 'SNOOZE')),
            snoozed_until TEXT,
            updated_at TEXT NOT NULL,
            PRIMARY KEY (alert_id, actor))""")
        conn.execute("""CREATE INDEX IF NOT EXISTS idx_desktop_receipts_actor
            ON desktop_receipts(actor, disposition)""")


def list_notifications(conn, actor, *, at=None, include_snoozed=False):
    """Only show current-revision, active alerts and ambiguous deliveries.

    Case titles, email fields and raw messages are deliberately not returned.
    UNKNOWN is visible as an operational incident, not treated as delivered.
    """
    account = _validate_actor(actor)
    at = at or datetime.now(timezone.utc)
    if at.tzinfo is None:
        raise ValueError('timezone-aware time required')
    at = at.astimezone(timezone.utc)
    ensure_receipts(conn)
    rows = conn.execute("""
        SELECT a.alert_id,a.case_id,a.revision,a.code,a.severity,a.day,
               a.state AS delivery_state,c.payload,
               r.disposition,r.snoozed_until
        FROM alerts a
        JOIN cases c ON c.case_id = a.case_id AND c.revision = a.revision
        LEFT JOIN desktop_receipts r ON r.alert_id=a.alert_id AND r.actor=?
        WHERE a.state IN ('SENT','UNKNOWN')
        ORDER BY CASE a.severity WHEN 'CRITICAL' THEN 0
                                 WHEN 'WARNING' THEN 1 ELSE 2 END,
                 a.created_at DESC, a.alert_id
    """, (account,))
    results=[]
    for row in rows:
        payload=json.loads(row['payload'])
        if payload.get('status') not in ACTIVE:
            continue
        if row['disposition']=='ACK':
            continue
        snoozed = row['snoozed_until']
        if not include_snoozed and row['disposition']=='SNOOZE' and snoozed:
            try:
                if datetime.fromisoformat(snoozed).astimezone(timezone.utc)>at:
                    continue
            except ValueError as e:
                raise RuntimeError('invalid stored snooze timestamp') from e
        code=row['code']
        results.append({
            'alert_id':row['alert_id'], 'case_id':row['case_id'],
            'severity':'CRITICAL' if row['delivery_state']=='UNKNOWN' else (row['severity'] if row['severity'] in SEVERITIES else 'WARNING'),
            'code':code,
            'summary':('配信結果 UNKNOWN：手動調査が必要' if row['delivery_state']=='UNKNOWN' else DISPLAY_CODE.get(code,'業務通知：内容を確認')),
            'day':row['day'], 'delivery_state':row['delivery_state'],
            'snoozed_until':snoozed,
        })
    return results


def mark_notification(conn, alert_id, actor, action, *, at=None, snooze_minutes=30):
    """CAS-safe, local acknowledgment/snooze, with audit; no approval transitions."""
    _validate_alert_id(alert_id)
    account=_validate_actor(actor)
    if action not in ('ACK','SNOOZE'):
        raise ValueError('only ACK or SNOOZE allowed')
    if action=='SNOOZE' and (not isinstance(snooze_minutes, int) or
                            isinstance(snooze_minutes, bool) or not 5<=snooze_minutes<=1440):
        raise ValueError('snooze period must be 5..1440 minutes')
    at = at or datetime.now(timezone.utc)
    if at.tzinfo is None:
        raise ValueError('timezone-aware time required')
    when=at.astimezone(timezone.utc)
    ensure_receipts(conn)
    conn.execute('BEGIN IMMEDIATE')
    try:
        row=conn.execute("""
           SELECT a.case_id,a.revision,a.state,c.payload
           FROM alerts a JOIN cases c ON c.case_id=a.case_id AND c.revision=a.revision
           WHERE a.alert_id=?
        """,(alert_id,)).fetchone()
        if row is None or row['state'] not in ('SENT','UNKNOWN') or json.loads(row['payload']).get('status') not in ACTIVE:
            raise ValueError('alert stale, not delivered or not found')
        prior=conn.execute(
            'SELECT disposition FROM desktop_receipts WHERE alert_id=? AND actor=?',
            (alert_id,account)).fetchone()
        if row['state']=='UNKNOWN' and action=='ACK':
            raise ValueError('UNKNOWN remote delivery must be manually reconciled before acknowledgment')
        if prior and prior['disposition']=='ACK':
            if action=='ACK':
                conn.commit()
                return False
            raise ValueError('acknowledged notifications cannot be snoozed')
        expires=(when+timedelta(minutes=snooze_minutes)).isoformat() if action=='SNOOZE' else None
        conn.execute("""INSERT INTO desktop_receipts
            (alert_id,actor,disposition,snoozed_until,updated_at) VALUES(?,?,?,?,?)
            ON CONFLICT(alert_id,actor) DO UPDATE SET
                disposition=excluded.disposition,snoozed_until=excluded.snoozed_until,
                updated_at=excluded.updated_at""",
            (alert_id,account,action,expires,when.isoformat()))
        conn.execute('INSERT INTO audit(case_id,event,actor,at,detail) VALUES(?,?,?,?,?)',
                     (row['case_id'],'DESKTOP_'+action,account,now_iso(),
                      json.dumps({'alert_id':alert_id,
                                  'minutes':snooze_minutes if action=='SNOOZE' else None})))
        conn.commit()
        return True
    except BaseException:
        conn.rollback()
        raise
