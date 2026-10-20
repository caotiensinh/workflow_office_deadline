"""W22B: analyze *sanitized operator-supplied* 15-minute execution timestamps.

This never contacts Windows Task Scheduler or the institution. A plausible
sequence is not authenticated task evidence, IT approval or live acceptance.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import json
import sys
from pathlib import Path


def _no_duplicate_keys(pairs):
    data = {}
    for key, value in pairs:
        if key in data:
            raise ValueError("Repeated evidence field")
        data[key] = value
    return data


def _datetime_iso(s):
    if not isinstance(s, str) or len(s) != 20 or s[-1:] != "Z":
        raise ValueError("Expected UTC second-resolution timestamps")
    try:
        value = datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise ValueError("Invalid event timestamp") from exc
    if value.strftime("%Y-%m-%dT%H:%M:%SZ") != s:
        raise ValueError("Noncanonical event timestamp")
    return value


def assess(document):
    if not isinstance(document, dict) or set(document) != {
            "schema_version", "source", "task_name", "events"}:
        raise ValueError("Invalid evidence schema")
    if type(document["schema_version"]) is not int or document["schema_version"] != 1:
        raise ValueError("Unknown evidence version")
    if document["task_name"] != "EducationAIWorkflow" or document["source"] != "operator-sanitized-local-export":
        raise ValueError("Wrong task identity or source")
    events = document["events"]
    if not isinstance(events, list) or not 3 <= len(events) <= 8:
        raise ValueError("Need 3 to 8 bounded event samples")
    times = []
    for event in events:
        if not isinstance(event, dict) or set(event) != {"started_at_utc", "exit_code"}:
            raise ValueError("Malformed event")
        if type(event["exit_code"]) is not int or event["exit_code"] != 0:
            raise ValueError("Execution marked failed/unknown")
        times.append(_datetime_iso(event["started_at_utc"]))
    gaps = [int((b-a).total_seconds()) for a, b in zip(times, times[1:])]
    if any(not 840 <= gap <= 960 for gap in gaps):
        raise ValueError("Observed cadence differs from nominal 15 minutes")
    return {
        "phase": "W22B",
        "status": "SANITIZED_TIMESTAMPS_CONSISTENT_NOT_AUTHENTICATED",
        "sample_count": len(times),
        "nominal_interval_seconds": 900,
        "intervals_within_60_seconds": True,
        "source_cryptographically_verified": False,
        "live_task_scheduler_queried": False,
        "real_task_execution_independently_verified": False,
        "it_approved": False,
        "production_accepted": False,
        "modifies_machine": False,
        "outlook_accessed": False,
        "smtp_sent": False,
    }


def read_local(file):
    path = Path(file)
    if path.is_symlink() or not path.is_file() or not 0 < path.stat().st_size <= 8192:
        raise ValueError("Unsafe local operator export")
    return assess(json.loads(path.read_text(encoding="utf-8"),
                             object_pairs_hook=_no_duplicate_keys))


def main(argv=None):
    parser = argparse.ArgumentParser(description="Read-only review of sanitized task timestamps")
    parser.add_argument("--evidence", required=True)
    args = parser.parse_args(argv)
    try:
        result = read_local(args.evidence)
    except (OSError, UnicodeError, ValueError, TypeError, OverflowError):
        print("W22B_OPERATOR_TIMESTAMPS_REJECTED", file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
