"""Opt-in notification channels. SMTP uncertain outcomes are held, never retried blindly."""
import json
import os
import smtplib
import ssl
import tempfile
from email.message import EmailMessage
from pathlib import Path
from .store import now_iso


def smtp_send(alert,recipient):
    allowed={x.strip() for x in os.environ.get('EDU_SMTP_ALLOWLIST','').split(',') if x.strip()}
    sender=os.environ.get('EDU_SMTP_FROM')
    host=os.environ.get('EDU_SMTP_HOST')
    if not host or not sender or recipient not in allowed:
        raise ValueError('SMTP host/from/recipient allowlist is not configured')
    msg=EmailMessage()
    msg['From']=sender; msg['To']=recipient
    msg['Subject']='[Education Workflow] '+alert['code']
    msg.set_content(alert['message'])
    port=int(os.environ.get('EDU_SMTP_PORT','587'))
    if port==465:
        with smtplib.SMTP_SSL(host,port,timeout=20,context=ssl.create_default_context()) as server:
            if os.environ.get('EDU_SMTP_USER'):
                server.login(os.environ['EDU_SMTP_USER'],os.environ['EDU_SMTP_PASSWORD'])
            server.send_message(msg)
    elif port==587:
        with smtplib.SMTP(host,port,timeout=20) as server:
            server.ehlo(); server.starttls(context=ssl.create_default_context()); server.ehlo()
            if os.environ.get('EDU_SMTP_USER'):
                server.login(os.environ['EDU_SMTP_USER'],os.environ['EDU_SMTP_PASSWORD'])
            server.send_message(msg)
    else:
        raise ValueError('Only TLS SMTP ports 465/587 supported')


def dispatch(conn,channel,out_dir=None):
    if channel not in {'file','smtp','console'}: raise ValueError('unsupported channel')
    if channel=='file' and not out_dir: raise ValueError('--out-dir required for file channel')
    target=Path(out_dir) if out_dir else None
    if target: target.mkdir(parents=True,exist_ok=True)
    sent=0; unknown=0
    alerts=[dict(row) for row in conn.execute("SELECT * FROM alerts WHERE state='QUEUED' ORDER BY created_at,alert_id")]
    for a in alerts:
        case_row=conn.execute('SELECT payload FROM cases WHERE case_id=?',(a['case_id'],)).fetchone()
        if not case_row: raise RuntimeError('orphan alert')
        case=json.loads(case_row['payload'])
        if channel=='file':
            # Write a durable, locally owned event; content already privacy-masked.
            out=target/(a['alert_id']+'.json')
            data={'id':a['alert_id'],'case_id':a['case_id'],'severity':a['severity'],'message':a['message']}
            if out.exists():
                if json.loads(out.read_text(encoding='utf-8'))!=data: raise RuntimeError('existing file contents differ')
            else:
                fd,tmp=tempfile.mkstemp(dir=target,prefix='.tmp_')
                try:
                    with os.fdopen(fd,'w',encoding='utf-8') as f:
                        json.dump(data,f,ensure_ascii=False); f.flush(); os.fsync(f.fileno())
                    os.replace(tmp,out)
                finally:
                    if os.path.exists(tmp): os.unlink(tmp)
            with conn:
                conn.execute("UPDATE alerts SET state='SENT',delivered_at=? WHERE alert_id=? AND state='QUEUED'",(now_iso(),a['alert_id']))
            sent+=1
        elif channel=='console':
            print(f"[{a['severity']}] {a['message']}")
            # Console is not durable delivery: event remains QUEUED for actual notification.
        else:
            # Before any remote side effect: mark SENDING, then SENT only after acknowledgement.
            with conn:
                con=conn.execute("UPDATE alerts SET state='SENDING' WHERE alert_id=? AND state='QUEUED'",(a['alert_id'],))
            if con.rowcount!=1: continue
            try:
                smtp_send(a,case['owner'])
            except Exception:
                with conn: conn.execute("UPDATE alerts SET state='UNKNOWN' WHERE alert_id=? AND state='SENDING'",(a['alert_id'],))
                unknown+=1
                continue
            with conn:
                conn.execute("UPDATE alerts SET state='SENT',delivered_at=? WHERE alert_id=? AND state='SENDING'",(now_iso(),a['alert_id']))
            sent+=1
    return {'sent':sent,'unknown':unknown,'previewed':len(alerts) if channel=='console' else 0}
