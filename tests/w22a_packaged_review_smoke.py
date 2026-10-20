"""Hosted-Windows proof: execute the built EXE in review-only mode, no GUI."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import subprocess
import time


def synthetic():
    return {
        "scope":"fictional-local-data-only",
        "type":"human-self-attested-Windows-field-UAT",
        "session_interactive":True,
        "visual_japanese_self_report":True,
        "sound_audible_self_report":True,
        "window_interactive_self_report":True,
        "ack_receipts":1,"snooze_receipts":1,"desktop_audit_events":2,
        "business_approvals":0,"human_buttons_recorded":True,
        "actual_login_autorun_verified":False,"production_accepted":False,
        "status":"DESKTOP_ACTIONS_AND_HUMAN_REPORT_COMPLETE",
    }


def run(exe, folder):
    root=Path(folder)
    if root.exists():
        raise FileExistsError("W22A smoke folder must be new")
    root.mkdir()
    report=root/"fictional-only.json"
    reviewed=root/"reviewed.json"
    report.write_text(json.dumps(synthetic()),encoding="utf-8")
    immutable=report.read_bytes()
    p=subprocess.Popen([str(exe),"--review-report-file",str(report),
                        "--review-output-file",str(reviewed)],
                       stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL)
    try:
        for _ in range(80):
            if reviewed.is_file():break
            if p.poll() is not None and p.returncode != 0:
                raise RuntimeError("W22A packaged EXE returned nonzero")
            time.sleep(0.25)
        if not reviewed.is_file():
            raise RuntimeError("W22A packaged reviewer produced no evidence")
        r=json.loads(reviewed.read_text(encoding="utf-8"))
        if (r["status"]!="CONSISTENT_SELF_ATTESTATION_NOT_INDEPENDENTLY_VERIFIED"
            or r["it_approved"] or r["production_accepted"]
            or r["real_gui_independently_verified"] or r["opens_gui"]
            or report.read_bytes()!=immutable):
            raise RuntimeError("W22A packaged evidence is unsafe")
        print("W22A_PACKAGED_REVIEW_EXE_PASS_SELF_ATTESTED_NOT_PHYSICAL_UAT")
    finally:
        if p.poll() is None:
            p.terminate()
            try:p.wait(timeout=5)
            except subprocess.TimeoutExpired:p.kill()


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--exe",required=True)
    parser.add_argument("--root",required=True)
    args=parser.parse_args()
    run(Path(args.exe),args.root)
