"""W25A: independently reconcile fictional GUI self-report and W23 handoff.

Integrity is unkeyed SHA-256 and content consistency only: no attestation
of human identity, publisher, observed GUI, IT permission or production.
Inputs read-only, no GUI/Win32/task/mail/external network.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys

from .uat_review import review as review_report

MAX_SUMMARY_BYTES = 8192
KEYS = frozenset({
    "phase", "status", "synthetic_only", "source_report_sha256",
    "ack_receipts", "snooze_receipts", "japanese_readable_self_report",
    "sound_audible_self_report", "window_interactive_self_report",
    "human_gui_independently_verified", "windows_login_autorun_verified",
    "it_approved", "publisher_signature_verified", "production_accepted",
    "outlook_accessed", "smtp_sent",
})


def _no_duplicates(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate summary property")
        result[key] = value
    return result


def reconcile(report_path, summary_path):
    source, handoff = Path(report_path), Path(summary_path)
    if source == handoff:
        raise ValueError("Report and summary must be separate files")
    for path in (source, handoff):
        if path.is_symlink() or not path.is_file():
            raise ValueError("Require existing ordinary local evidence files")
        if not 0 < path.stat().st_size <= MAX_SUMMARY_BYTES:
            raise ValueError("Unexpected evidence size")

    review = review_report(source)
    fields = json.loads(handoff.read_text(encoding="utf-8"),
                        object_pairs_hook=_no_duplicates)
    if not isinstance(fields, dict) or set(fields) != KEYS:
        raise ValueError("Unexpected or incomplete summary schema")
    if fields["phase"] != "W23B" or fields["synthetic_only"] is not True:
        raise ValueError("Not a synthetic operator handoff")
    digest = hashlib.sha256(source.read_bytes()).hexdigest().upper()
    if not isinstance(fields["source_report_sha256"], str) or len(fields["source_report_sha256"]) != 64:
        raise ValueError("Invalid source fingerprint")
    import hmac
    if not hmac.compare_digest(digest, fields["source_report_sha256"]):
        raise ValueError("Handoff references a different UAT report")
    expected = {
        "status": review["status"],
        "ack_receipts": review["ack_receipts"],
        "snooze_receipts": review["snooze_receipts"],
        "japanese_readable_self_report": review["visual_japanese_self_report"],
        "sound_audible_self_report": review["sound_audible_self_report"],
        "window_interactive_self_report": review["window_interactive_self_report"],
    }
    for key, value in expected.items():
        if type(fields[key]) is not type(value) or fields[key] != value:
            raise ValueError("Inconsistent self-reported operator evidence")
    for key in ("human_gui_independently_verified", "windows_login_autorun_verified",
                "it_approved", "publisher_signature_verified", "production_accepted",
                "outlook_accessed", "smtp_sent"):
        if fields[key] is not False:
            raise ValueError("Unsupported claim of production or live acceptance")
    return {
        "phase": "W25A",
        "status": ("MATCHED_TWO_LOCAL_FILES_NOT_INDEPENDENT_GUI_UAT"
                   if review["status"] == "CONSISTENT_SELF_ATTESTATION_NOT_INDEPENDENTLY_VERIFIED"
                   else "MATCHED_INCOMPLETE_SELF_REPORT_NOT_INDEPENDENT_GUI_UAT"),
        "ack_receipts": review["ack_receipts"],
        "snooze_receipts": review["snooze_receipts"],
        "self_attested_only": True,
        "source_sha256_matches_handoff": True,
        "cryptographically_signed": False,
        "independent_human_gui_observation": False,
        "login_autorun_observed": False,
        "it_approved": False,
        "production_accepted": False,
        "modifies_inputs": False,
        "outlook_accessed": False,
        "smtp_sent": False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="W25A offline local UAT pair integrity review")
    parser.add_argument("--report", required=True)
    parser.add_argument("--summary", required=True)
    parser.add_argument("--out", help="New JSON output file (optional, exclusive create)")
    args = parser.parse_args(argv)
    try:
        result = reconcile(args.report, args.summary)
        if args.out:
            target = Path(args.out)
            if target.is_symlink() or not target.parent.is_dir() or target in (
                    Path(args.report), Path(args.summary)):
                raise ValueError("Unsafe output location")
            with target.open("x", encoding="utf-8") as writer:
                json.dump(result, writer, sort_keys=True, indent=2)
        print(json.dumps(result, sort_keys=True))
        return 0
    except (OSError, ValueError, UnicodeError, TypeError):
        print("W25A_UAT_PAIR_REJECTED", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
