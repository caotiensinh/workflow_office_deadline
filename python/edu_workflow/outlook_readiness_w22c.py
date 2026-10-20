"""W22C Outlook Classic least-privilege *plan*, never mailbox access.

Only fictional static operator-proposed settings are read. No credentials,
COM, Graph, SMTP, mailbox identifiers or machine probes.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys

KEYS = frozenset({"adapter", "mode", "scope", "max_unread", "send_enabled",
                 "modify_read_state", "it_approval_recorded", "use_real_data"})


def evaluate(data):
    if not isinstance(data, dict) or set(data) != KEYS:
        raise ValueError("Unknown approval plan schema")
    if (data["adapter"] != "outlook-classic" or
            data["mode"] != "manual-opt-in" or
            data["scope"] != "unread-inbox-only"):
        raise ValueError("Unsupported or excessive mailbox scope")
    if type(data["max_unread"]) is not int or not 1 <= data["max_unread"] <= 50:
        raise ValueError("Max read count unsafe")
    for key in ("send_enabled", "modify_read_state", "it_approval_recorded", "use_real_data"):
        if type(data[key]) is not bool or data[key]:
            raise ValueError("Mail mutation, real data, or artificial IT approval")
    return {
        "phase": "W22C",
        "status": "OFFLINE_CLASSIC_READONLY_PLAN_NOT_AUTHORIZED",
        "adapter": "outlook-classic",
        "scope": "unread-inbox-only",
        "max_unread": data["max_unread"],
        "real_outlook_accessed": False,
        "messages_read": 0,
        "send_enabled": False,
        "read_state_changed": False,
        "credential_collected": False,
        "it_approved": False,
        "production_accepted": False,
    }


def _strict_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate field in mail plan")
        result[key] = value
    return result


def from_file(path):
    src = Path(path)
    if src.is_symlink() or not src.is_file() or not 0 < src.stat().st_size <= 4096:
        raise ValueError("Invalid plan source")
    return evaluate(json.loads(src.read_text(encoding="utf-8"), object_pairs_hook=_strict_pairs))


def main(argv=None):
    parser = argparse.ArgumentParser(description="Outlook planning metadata only; no COM/Graph/mail")
    parser.add_argument("--plan", required=True)
    args = parser.parse_args(argv)
    try:
        result = from_file(args.plan)
    except (OSError, ValueError, UnicodeError, TypeError):
        print("W22C_OUTLOOK_PLAN_REJECTED", file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
