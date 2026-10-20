"""W21B offline validation of the Windows 15-minute scheduler PLAN.

Input comes from install_task.ps1 -PlanOnly, NOT a live machine inspection.
A valid plan is never proof of Task Scheduler registration, successful
execution, IT consent or production acceptance.
"""
from __future__ import annotations
import argparse
import json
import re
import sys
from pathlib import Path

FIELDS = frozenset({"task_name", "interval_minutes", "command", "source",
                    "notification_channel", "replaces_existing"})
ACTION = re.compile(
    r'^powershell\.exe -NoProfile -File "([A-Za-z]:\\[^"\r\n]+\\run_once\.ps1)" -Channel file$',
    re.IGNORECASE,
)


def validate(plan):
    if not isinstance(plan, dict) or set(plan) != FIELDS:
        raise ValueError("Unexpected plan fields")
    if plan["task_name"] != "EducationAIWorkflow":
        raise ValueError("Task name mismatch")
    if type(plan["interval_minutes"]) is not int or plan["interval_minutes"] != 15:
        raise ValueError("Require exact 15-minute interval")
    if plan["source"] != "none" or plan["notification_channel"] != "file":
        raise ValueError("External source/channel forbidden")
    if plan["replaces_existing"] is not False:
        raise ValueError("Task replacement forbidden")
    command = plan["command"]
    if not isinstance(command, str) or len(command) > 2048:
        raise ValueError("Command missing or oversized")
    match = ACTION.fullmatch(command)
    if not match:
        raise ValueError("Task action not exact file-only command")
    path = match.group(1)
    if any(s in path for s in ("..\\", "\\..", "%", "$", chr(96), "&",
                               "|", ";", "!", "^", "\n", "\r", "<", ">")):
        raise ValueError("Unsafe source script path")
    return {
        "phase": "W21B",
        "status": "OFFLINE_15_MIN_PLAN_CONSISTENT_NOT_REGISTERED",
        "planned_interval_minutes": 15, "source": "none", "channel": "file",
        "task_created": False, "actual_15minute_execution_observed": False,
        "task_scheduler_read": False, "outlook_accessed": False,
        "smtp_sent": False, "policy_changed": False, "it_approved": False,
        "production_accepted": False,
    }


def _strict_keys(pairs):
    data = {}
    for key, value in pairs:
        if key in data:
            raise ValueError("Duplicate JSON field")
        data[key] = value
    return data


def read_plan(file):
    source = Path(file)
    if source.is_symlink() or not source.is_file() or not 0 < source.stat().st_size <= 12288:
        raise ValueError("Unsafe plan file")
    return validate(json.loads(source.read_text(encoding="utf-8"),
                               object_pairs_hook=_strict_keys))


def main(argv=None):
    p = argparse.ArgumentParser(description="Offline scheduler PLAN validator, not approval")
    p.add_argument("--plan", required=True)
    a = p.parse_args(argv)
    try:
        result = read_plan(a.plan)
    except (OSError, UnicodeError, ValueError, TypeError):
        print("W21B_SCHEDULER_PLAN_REJECTED", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=True, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
