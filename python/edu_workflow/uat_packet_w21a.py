"""W21A combine *independent, read-only* UAT ZIP integrity and user self-report review.

Both inputs remain local and unchanged. Neither passes real GUI observation, IT
permissions, signing or production gates. Never accept a report alone as proof
that it was produced by the EXE inside a particular ZIP.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .kit_integrity_w18 import verify as verify_zip
from .uat_review import review as review_report


def review_packet(zip_file, report_file, expected_zip_sha256=None):
    archive = verify_zip(zip_file, expected_zip_sha256=expected_zip_sha256)
    report = review_report(report_file)
    consistent = report["status"] == "CONSISTENT_SELF_ATTESTATION_NOT_INDEPENDENTLY_VERIFIED"
    return {
        "phase": "W21A",
        "status": "LOCAL_CONTENT_AND_SELF_REPORT_CONSISTENT_NOT_INDEPENDENT_UAT"
                  if consistent else "INCOMPLETE_SELF_REPORTED_GUI_UAT",
        "zip_sha256": archive["zip_sha256"],
        "exe_sha256": archive["exe_sha256"],
        "archive_members": archive["archive_members"],
        "ack_receipts": report["ack_receipts"],
        "snooze_receipts": report["snooze_receipts"],
        "business_approvals": report["business_approvals"],
        "self_attested_only": True,
        "independent_session1_gui_verified": False,
        "report_bound_cryptographically_to_binary": False,
        "signed_publisher_verified": False,
        "windows_login_autorun_verified": False,
        "scheduler_15minute_verified": False,
        "outlook_accessed": False,
        "smtp_sent": False,
        "it_approved": False,
        "production_accepted": False,
        "modifies_system": False,
        "modifies_zip_or_report": False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="Read-only local fictional UAT handoff reviewer")
    parser.add_argument("--kit-zip", required=True)
    parser.add_argument("--uat-report", required=True)
    parser.add_argument("--expected-zip-sha256")
    parser.add_argument("--out", help="New JSON result in existing local folder (exclusive creation)")
    args = parser.parse_args(argv)
    try:
        result = review_packet(args.kit_zip, args.uat_report, args.expected_zip_sha256)
        if args.out:
            target = Path(args.out)
            if target.is_symlink() or not target.parent.is_dir():
                raise ValueError("Unsafe output target")
            with target.open("x", encoding="utf-8") as stream:
                json.dump(result, stream, ensure_ascii=True, sort_keys=True, indent=2)
        print(json.dumps(result, ensure_ascii=True, sort_keys=True))
        return 0 if result["status"].startswith("LOCAL_CONTENT_") else 3
    except (OSError, ValueError, RuntimeError, TypeError, EOFError, KeyError):
        print("W21A_EVIDENCE_REJECTED", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
