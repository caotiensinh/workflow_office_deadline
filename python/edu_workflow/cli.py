"""Operator CLI for an offline-first automatic workflow. All external effects opt in."""
import argparse
import getpass
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from .policy import JST,evaluate,parse_deadline,message_for
from .store import open_store,add_case,get_cases,get_case,enqueue,alert_list,audit_list,decide,confirm_deadline,review_queue
from .intake import read_eml_folder
from .documents import validate_docx
from .deliver import dispatch

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BIN = ROOT/'rust-core'/'target'/'release'/('edu_rules.exe' if os.name=='nt' else 'edu_rules')


def parser():
    p=argparse.ArgumentParser(prog='edu_workflow',description='Education workflow: approval-gated Python + Rust automation')
    p.add_argument('--db',default=str(ROOT/'data'/'workflow.sqlite3'))
    sub=p.add_subparsers(dest='cmd',required=True)
    i=sub.add_parser('import-json',help='Import fictional/approved data from JSON array')
    i.add_argument('--file',required=True)
    intake=sub.add_parser('import-eml',help='Read .eml files; dates always unverified')
    intake.add_argument('--dir',required=True)
    classic=sub.add_parser('import-outlook-classic',help='Explicit opt-in, COM, Windows, pywin32')
    classic.add_argument('--limit',type=int,default=50)
    classic.add_argument('--owner',default='LOCAL_REVIEWER')
    tick=sub.add_parser('tick',help='Apply deterministic rules, store idempotent notifications')
    tick.add_argument('--backend',choices=['rust','python'],default='rust')
    tick.add_argument('--rust-bin',default=str(DEFAULT_BIN))
    tick.add_argument('--at',help='ISO datetime with timezone; for simulation only')
    sub.add_parser('cases')
    sub.add_parser('alerts')
    sub.add_parser('audit')
    sub.add_parser('review-queue',help='Masked human-only exceptions: date verification, missing evidence and approval')
    delivery=sub.add_parser('deliver',help='Explicit notification sending; console never marks delivered')
    delivery.add_argument('--channel',choices=['file','smtp','console'],default='console')
    delivery.add_argument('--out-dir',default=str(ROOT/'notifications'))
    due=sub.add_parser('confirm-deadline',help='Require human confirmation of extracted due date')
    due.add_argument('--case-id',required=True)
    due.add_argument('--due',required=True,help='ISO timestamp with +09:00')
    due.add_argument('--revision',type=int,required=True)
    due.add_argument('--method',choices=['source-reviewed','institution-reviewed'],required=True)
    approval=sub.add_parser('decide',help='Human approval, bound to local account and revision')
    approval.add_argument('--case-id',required=True)
    approval.add_argument('--revision',type=int,required=True)
    approval.add_argument('--decision',choices=['approve','reject'],required=True)
    doc=sub.add_parser('check-docx',help='Check required phrases in local DOCX')
    doc.add_argument('--file',required=True)
    doc.add_argument('--criteria',required=True)
    return p


def human_confirm(expected):
    print(f'Type exactly: {expected}',file=sys.stderr)
    print('> ',file=sys.stderr,end='',flush=True)
    entered=input()
    if entered != expected: raise PermissionError('human confirmation cancelled')


def main(argv=None):
    args=parser().parse_args(argv)
    if args.cmd=='check-docx':
        criteria=json.loads(Path(args.criteria).read_text(encoding='utf-8'))
        print(json.dumps(validate_docx(args.file,criteria),ensure_ascii=False,indent=2))
        return 0
    with open_store(args.db) as con:
        if args.cmd=='import-json':
            data=json.loads(Path(args.file).read_text(encoding='utf-8'))
            if not isinstance(data,list): raise ValueError('Expected JSON list')
            # Validate all first: invalid file never partially imports.
            from .policy import validate_case
            ids=set()
            for case in data:
                validate_case(case)
                if case['case_id'] in ids: raise ValueError('duplicate case_id in file')
                ids.add(case['case_id'])
            imported=sum(add_case(con,c) for c in data)
            print(json.dumps({'imported':imported,'skipped_existing':len(data)-imported}))
        elif args.cmd in ('import-eml','import-outlook-classic'):
            if args.cmd=='import-eml': cases=read_eml_folder(args.dir)
            else:
                from .outlook_classic import unread_cases
                cases=unread_cases(args.limit,args.owner,existing_ids={c['case_id'] for c,_ in get_cases(con)})
            total=0; new=0
            for c in cases:
                total+=1; new+=add_case(con,c,'read_only_adapter')
            print(json.dumps({'observed':total,'imported':new}))
        elif args.cmd=='tick':
            now=parse_deadline(args.at) if args.at else datetime.now(JST)
            cases=get_cases(con)
            signals=evaluate([c for c,_ in cases],now,args.backend,args.rust_bin)
            created=enqueue(con,cases,signals,now,message_for)
            print(json.dumps({'backend':args.backend,'evaluated':len(cases),'alerts_added':created,'at':now.isoformat()}))
        elif args.cmd=='cases':
            # Intentionally suppress internal/sensitive titles, all owner addresses and source IDs.
            from .policy import safe_label
            print(json.dumps([{'case_id':c['case_id'],'kind':c['kind'],'status':c['status'],'approval_status':c['approval_status'],
                                'revision':rev,'due_at':c.get('due_at'),'due_verified':c['due_verified'],
                                'has_evidence':bool(c.get('evidence_ref')),'safe_label':safe_label(c)} for c,rev in get_cases(con)],ensure_ascii=False,indent=2))
        elif args.cmd=='alerts':
            print(json.dumps([{k:r[k] for k in ('alert_id','case_id','code','severity','message','state','day')} for r in alert_list(con)],ensure_ascii=False,indent=2))
        elif args.cmd=='audit':
            print(json.dumps(audit_list(con),ensure_ascii=False,indent=2))
        elif args.cmd=='review-queue':
            print(json.dumps(review_queue(con),ensure_ascii=False,indent=2))
        elif args.cmd=='deliver':
            print(json.dumps(dispatch(con,args.channel,args.out_dir),ensure_ascii=False))
        elif args.cmd=='confirm-deadline':
            actor=getpass.getuser()
            allowed={name.strip().casefold() for name in os.environ.get('EDU_VERIFIER_USERS','').split(',') if name.strip()}
            if actor.casefold() not in allowed:
                raise PermissionError('deadline verifier local account not on EDU_VERIFIER_USERS allowlist')
            due=parse_deadline(args.due)
            # Re-read before prompting to prevent operator confirmation of a stale revision.
            case,rev=get_case(con,args.case_id)
            if rev!=args.revision: raise RuntimeError('stale revision')
            human_confirm(f'CONFIRM {args.case_id} {due.isoformat()}')
            case,version=confirm_deadline(con,args.case_id,due.isoformat(),actor,args.revision,
                                          args.method.upper().replace('-','_'))
            print(json.dumps({'case_id':args.case_id,'revision':version,'due_at':case['due_at']}))
        elif args.cmd=='decide':
            actor=getpass.getuser()
            allow={s.strip().casefold() for s in os.environ.get('EDU_APPROVER_USERS','').split(',') if s.strip()}
            if actor.casefold() not in allow:
                raise PermissionError('approver local account not on EDU_APPROVER_USERS allowlist')
            action=args.decision.upper()
            human_confirm(f'{action} {args.case_id}')
            case,rev=decide(con,args.case_id,'APPROVED' if args.decision=='approve' else 'REJECTED',actor,args.revision)
            print(json.dumps({'case_id':case['case_id'],'status':case['status'],'revision':rev}))
        else: raise AssertionError('unhandled command')
    return 0


if __name__ == '__main__':
    try: sys.exit(main())
    except (ValueError,RuntimeError,PermissionError,OSError) as exc:
        print(f'ERROR [{type(exc).__name__}]: {exc}',file=sys.stderr)
        sys.exit(2)
