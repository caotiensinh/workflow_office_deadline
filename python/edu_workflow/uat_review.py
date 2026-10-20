"""W17 offline, privacy-safe validation of a *self-attested* fictional GUI UAT report.

Reading a report never proves a human actually operated an interactive GUI.
The evidence is not a company IT/production approval, even when internally consistent.
No private names, message text or paths are exposed in the review summary.
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

MAX_SIZE = 8192
EXPECTED_KEYS = frozenset({
    "scope", "type", "session_interactive",
    "visual_japanese_self_report", "sound_audible_self_report",
    "window_interactive_self_report", "ack_receipts", "snooze_receipts",
    "desktop_audit_events", "business_approvals", "human_buttons_recorded",
    "actual_login_autorun_verified", "production_accepted", "status",
})
STATUS = {"DESKTOP_ACTIONS_AND_HUMAN_REPORT_COMPLETE", "INCOMPLETE_FIELD_UAT"}
BOOL = ("session_interactive", "visual_japanese_self_report",
        "sound_audible_self_report", "window_interactive_self_report",
        "human_buttons_recorded", "actual_login_autorun_verified",
        "production_accepted")
COUNTS = ("ack_receipts", "snooze_receipts", "desktop_audit_events",
          "business_approvals")


def _reject_duplicates(pairs):
    data = {}
    for key, value in pairs:
        if key in data:
            raise ValueError("Duplicate report property")
        data[key] = value
    return data


def review(report_file):
    source = Path(report_file)
    if source.is_symlink() or not source.is_file():
        raise ValueError("A regular local UAT report file is required")
    if source.stat().st_size > MAX_SIZE:
        raise ValueError("Unexpected report size")
    data = json.loads(source.read_text(encoding="utf-8"), object_pairs_hook=_reject_duplicates)
    if not isinstance(data, dict) or set(data) != EXPECTED_KEYS:
        raise ValueError("Report schema mismatch")
    if data["scope"] != "fictional-local-data-only" or data["type"] != "human-self-attested-Windows-field-UAT":
        raise ValueError("Not the fictional GUI UAT report")
    if data["status"] not in STATUS:
        raise ValueError("Invalid report status")
    if any(type(data[k]) is not bool for k in BOOL) or any(
        type(data[k]) is not int or data[k] < 0 for k in COUNTS
    ):
        raise ValueError("Unsafe boolean/count field")
    if data["production_accepted"] or data["actual_login_autorun_verified"]:
        raise ValueError("Report claims authority outside synthetic GUI test")
    # ACK/SNOOZE receipts and audit record must agree; forged/mismatched reports fail closed.
    valid_receipts = (data["ack_receipts"] == 1 and data["snooze_receipts"] == 1
                      and data["desktop_audit_events"] == 2
                      and data["business_approvals"] == 0
                      and data["human_buttons_recorded"])
    if data["human_buttons_recorded"] and not valid_receipts:
        raise ValueError("Action receipts/audit mismatch")
    human_answers = (data["session_interactive"] and data["visual_japanese_self_report"]
                     and data["sound_audible_self_report"] and
                     data["window_interactive_self_report"])
    complete = valid_receipts and human_answers
    if (data["status"] == "DESKTOP_ACTIONS_AND_HUMAN_REPORT_COMPLETE") != complete:
        raise ValueError("Self-reported completion contradicts evidence")
    return {
        "schema_version": 1,
        "phase": "W17",
        "status": ("CONSISTENT_SELF_ATTESTATION_NOT_INDEPENDENTLY_VERIFIED"
                   if complete else "INCOMPLETE_SELF_ATTESTATION"),
        "ack_receipts": data["ack_receipts"],
        "snooze_receipts": data["snooze_receipts"],
        "desktop_audit_events": data["desktop_audit_events"],
        "business_approvals": data["business_approvals"],
        "visual_japanese_self_report": data["visual_japanese_self_report"],
        "sound_audible_self_report": data["sound_audible_self_report"],
        "window_interactive_self_report": data["window_interactive_self_report"],
        "actual_physical_observation_independently_verified": False,
        "actual_login_autorun_verified": False,
        "signed_release_verified": False,
        "it_approved": False,
        "outlook_accessed": False, "smtp_sent": False,
        "modifies_uat_report": False,
        "production_accepted": False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="Read-only review of a fictional signed-in Windows GUI UAT report")
    parser.add_argument("--report", required=True)
    args = parser.parse_args(argv)
    try:
        result = review(args.report)
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        print("W17_REPORT_REJECTED", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=True, sort_keys=True, indent=2))
    return 0 if result["status"].startswith("CONSISTENT_") else 3


if __name__ == "__main__":
    sys.exit(main())
