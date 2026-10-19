"""Opt-in channels with revision-checked outbox claims and crash-safe UNKNOWN handling.

Remote sends cannot be transactionally rolled back with SQLite. A crashed SENDING
entry is quarantined; no automatic retry is allowed without external reconciliation.
"""
import json
import os
import smtplib
import ssl
import tempfile
from email.message import EmailMessage
from pathlib import Path
from .store import now_iso
from .policy import ACTIVE


def smtp_send(alert, recipient):
    allowed = {x.strip() for x in os.environ.get('EDU_SMTP_ALLOWLIST', '').split(',') if x.strip()}
    sender = os.environ.get('EDU_SMTP_FROM')
    host = os.environ.get('EDU_SMTP_HOST')
    if not host or not sender or recipient not in allowed:
        raise ValueError('SMTP host/from/recipient allowlist is not configured')
    msg = EmailMessage()
    msg['From'] = sender
    msg['To'] = recipient
    msg['Subject'] = '[Education Workflow] ' + alert['code']
    msg.set_content(alert['message'])
    port = int(os.environ.get('EDU_SMTP_PORT', '587'))
    if port == 465:
        with smtplib.SMTP_SSL(host, port, timeout=20, context=ssl.create_default_context()) as server:
            if os.environ.get('EDU_SMTP_USER'):
                server.login(os.environ['EDU_SMTP_USER'], os.environ['EDU_SMTP_PASSWORD'])
            server.send_message(msg)
    elif port == 587:
        with smtplib.SMTP(host, port, timeout=20) as server:
            server.ehlo()
            server.starttls(context=ssl.create_default_context())
            server.ehlo()
            if os.environ.get('EDU_SMTP_USER'):
                server.login(os.environ['EDU_SMTP_USER'], os.environ['EDU_SMTP_PASSWORD'])
            server.send_message(msg)
    else:
        raise ValueError('Only TLS SMTP ports 465/587 supported')


def _notification(alert):
    return {'id': alert['alert_id'], 'case_id': alert['case_id'],
            'severity': alert['severity'], 'message': alert['message']}


def _write_file(path, content):
    if path.exists():
        if json.loads(path.read_text(encoding='utf-8')) != content:
            raise RuntimeError('existing file contents differ; operator review required')
        return
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix='.tmp_')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(content, f, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def _finish(conn, alert_id, state):
    with conn:
        conn.execute('UPDATE alerts SET state=?,delivered_at=? WHERE alert_id=? AND state=\'SENDING\'',
                     (state, now_iso() if state == 'SENT' else None, alert_id))


def _recover(conn, channel, target):
    """Reconcile *only* durable local files; never assume a remote SMTP outcome."""
    recovered, unknown = 0, 0
    inflight = [dict(r) for r in conn.execute("SELECT * FROM alerts WHERE state='SENDING'")]
    for alert in inflight:
        valid_file = False
        if channel == 'file' and target is not None:
            try:
                path = target / (alert['alert_id'] + '.json')
                valid_file = path.is_file() and json.loads(path.read_text(encoding='utf-8')) == _notification(alert)
            except (OSError, ValueError, TypeError):
                valid_file = False
        _finish(conn, alert['alert_id'], 'SENT' if valid_file else 'UNKNOWN')
        recovered += int(valid_file)
        unknown += int(not valid_file)
    return recovered, unknown


def _claim(conn, alert_id, mark_sending=True):
    """Atomically compare queued alert with case revision and claim it for sending."""
    conn.execute('BEGIN IMMEDIATE')
    try:
        alert = conn.execute('SELECT * FROM alerts WHERE alert_id=?', (alert_id,)).fetchone()
        if alert is None or alert['state'] != 'QUEUED':
            conn.commit()
            return None
        row = conn.execute('SELECT revision,payload FROM cases WHERE case_id=?', (alert['case_id'],)).fetchone()
        current = json.loads(row['payload']) if row else None
        if row is None or row['revision'] != alert['revision'] or current['status'] not in ACTIVE:
            conn.execute("UPDATE alerts SET state='STALE' WHERE alert_id=? AND state='QUEUED'", (alert_id,))
            conn.commit()
            return None
        if mark_sending:
            conn.execute("UPDATE alerts SET state='SENDING' WHERE alert_id=? AND state='QUEUED'", (alert_id,))
        conn.commit()
        return dict(alert), current
    except BaseException:
        conn.rollback()
        raise


def dispatch(conn, channel, out_dir=None):
    if channel not in {'file', 'smtp', 'console'}:
        raise ValueError('unsupported channel')
    if channel == 'file' and not out_dir:
        raise ValueError('--out-dir required for file channel')
    target = Path(out_dir) if channel == 'file' else None
    if target:
        target.mkdir(parents=True, exist_ok=True)
    recovered, unknown = _recover(conn, channel, target)
    sent, previewed = 0, 0
    ids = [r['alert_id'] for r in conn.execute("SELECT alert_id FROM alerts WHERE state='QUEUED' ORDER BY created_at,alert_id")]
    for alert_id in ids:
        claimed = _claim(conn, alert_id, mark_sending=(channel != 'console'))
        if not claimed:
            continue
        alert, case = claimed
        if channel == 'console':
            print(f"[{alert['severity']}] {alert['message']}")
            previewed += 1
            continue
        try:
            if channel == 'file':
                _write_file(target / (alert_id + '.json'), _notification(alert))
            else:
                smtp_send(alert, case['owner'])
        except Exception:
            _finish(conn, alert_id, 'UNKNOWN')
            unknown += 1
            continue
        _finish(conn, alert_id, 'SENT')
        sent += 1
    return {'sent': sent, 'unknown': unknown, 'recovered': recovered, 'previewed': previewed}
