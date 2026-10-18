"""Versioned tab protocol between Python and the dependency-free Rust rules engine.
The Python implementation is an offline test/reference fallback, NOT evidence that Rust compiled.
"""
from __future__ import annotations
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

JST = timezone(timedelta(hours=9))  # Japan has no DST.
ACTIVE = {'NEW','TRIAGE','DRAFT','IN_PROGRESS','READY_FOR_APPROVAL','APPROVED'}
STATUS = ACTIVE | {'COMPLETED','REJECTED','CANCELLED'}
KINDS = {'EMAIL','DOCUMENT','REGULATION','HR','SCHEDULE'}
CLASSIFICATIONS = {'PUBLIC','INTERNAL','CONFIDENTIAL','RESTRICTED'}
APPROVALS = {'NOT_REQUIRED','PENDING','APPROVED','REJECTED'}
EVENT_CODES = {'VERIFY_DEADLINE','D_MINUS_3','D_MINUS_1','DUE_TODAY','OVERDUE_TODAY','OVERDUE','MISSING_EVIDENCE','APPROVAL_PENDING','REJECTED_REVIEW'}
SEVERITIES = {'INFO','WARNING','CRITICAL'}


def parse_deadline(value: str) -> datetime:
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        raise ValueError('due_at must carry timezone offset, e.g. +09:00')
    return dt.astimezone(JST)


def validate_case(case):
    if not isinstance(case, dict) or not isinstance(case.get('case_id'), str) or not case['case_id'].strip():
        raise ValueError('case_id required')
    for field, choices in [('kind',KINDS),('data_class',CLASSIFICATIONS),('status',STATUS),('approval_status',APPROVALS)]:
        if case.get(field) not in choices:
            raise ValueError(f'{case["case_id"]}: invalid {field}')
    if not isinstance(case.get('due_verified'), bool):
        raise ValueError('due_verified must be bool')
    if case.get('due_at'):
        parse_deadline(case['due_at'])
    if case['due_verified'] and not case.get('due_at'):
        raise ValueError('verified deadline requires due_at')
    if not isinstance(case.get('safe_title'), str) or len(case['safe_title']) > 256:
        raise ValueError('safe_title must be string with <= 256 chars')
    if not isinstance(case.get('owner'), str) or not case['owner']:
        raise ValueError('owner required')
    return case


def wire_record(case, now):
    validate_case(case)
    due = parse_deadline(case['due_at']) if case.get('due_at') else None
    due_state = 'VERIFIED' if due and case['due_verified'] else 'UNVERIFIED' if due else 'NONE'
    days = (due.date()-now.astimezone(JST).date()).days if due else 0
    expired = int(bool(due and now.astimezone(timezone.utc) > due.astimezone(timezone.utc)))
    evidence = int(bool(case.get('evidence_ref')))
    values = ['CASE', case['case_id'].encode('utf-8').hex(),case['kind'],case['data_class'],case['status'],str(days),due_state,str(expired),str(evidence),case['approval_status']]
    return '\t'.join(values)


def python_reference(case, now):
    if case['status'] not in ACTIVE: return []
    due = parse_deadline(case['due_at']) if case.get('due_at') else None
    out = []
    if not due or not case['due_verified']:
        out.append(('VERIFY_DEADLINE','WARNING'))
    else:
        days = (due.date()-now.astimezone(JST).date()).days
        if days == 3: out.append(('D_MINUS_3','INFO'))
        elif days == 1: out.append(('D_MINUS_1','WARNING'))
        elif days == 0:
            out.append(('OVERDUE_TODAY' if now > due else 'DUE_TODAY','WARNING'))
        elif days < 0: out.append(('OVERDUE','CRITICAL'))
    missing = case['kind'] in {'DOCUMENT','HR','REGULATION'} and not case.get('evidence_ref')
    if missing: out.append(('MISSING_EVIDENCE','CRITICAL'))
    elif case['status'] == 'READY_FOR_APPROVAL' and case['approval_status'] != 'APPROVED':
        out.append(('REJECTED_REVIEW' if case['approval_status']=='REJECTED' else 'APPROVAL_PENDING','WARNING'))
    return out


def evaluate(cases, now, backend='rust', rust_bin=None):
    """Fail closed: backend=rust NEVER falls back silently to Python."""
    for case in cases: validate_case(case)
    if backend == 'python':
        return {c['case_id']:python_reference(c,now) for c in cases}
    if backend != 'rust': raise ValueError('backend must be rust or python')
    if not rust_bin: raise RuntimeError('Rust binary is required; build with cargo build --release')
    path = Path(rust_bin)
    if not path.is_file(): raise RuntimeError(f'Rust binary not found: {path}')
    data = '\n'.join(wire_record(c,now) for c in cases)+'\n'
    result = subprocess.run([str(path)],input=data,encoding='utf-8',capture_output=True,timeout=10,check=False)
    if result.returncode: raise RuntimeError(f'Rust engine failed rc={result.returncode}: {result.stderr[:300]}')
    ids = {c['case_id'] for c in cases}
    output = {id_:[] for id_ in ids}
    for line in result.stdout.splitlines():
        fields = line.split('\t')
        if len(fields)!=4 or fields[0]!='EVENT': raise RuntimeError('malformed Rust response')
        try: case_id=bytes.fromhex(fields[1]).decode('utf-8')
        except (UnicodeDecodeError,ValueError) as exc: raise RuntimeError('malformed Rust case_id') from exc
        if case_id not in ids or fields[2] not in EVENT_CODES or fields[3] not in SEVERITIES:
            raise RuntimeError('Rust emitted invalid event')
        pair=(fields[2],fields[3])
        if pair in output[case_id]: raise RuntimeError('Rust emitted duplicate event')
        output[case_id].append(pair)
    return output


def safe_label(case):
    if case['data_class'] in ('CONFIDENTIAL','RESTRICTED'):
        return f'管理対象 [{case["case_id"]}]'
    return case.get('safe_title') or case['case_id']


def message_for(code,case):
    label=safe_label(case)
    labels={'VERIFY_DEADLINE':'期限確認が必要','D_MINUS_3':'期限まで3日','D_MINUS_1':'期限まで1日','DUE_TODAY':'本日が期限',
        'OVERDUE_TODAY':'本日期限超過','OVERDUE':'期限超過','MISSING_EVIDENCE':'根拠資料不足・確認保留',
        'APPROVAL_PENDING':'管理職の判断待ち','REJECTED_REVIEW':'差戻し内容の確認待ち'}
    return f'{labels[code]}：{label}'
