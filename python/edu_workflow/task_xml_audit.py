"""W14: offline fail-closed audit of IT-exported Windows Task Scheduler XML.

It does NOT connect to Task Scheduler, read a live machine, execute a script,
change a task, prove that a job ever ran, or establish IT authorization.
"""
from __future__ import annotations
import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

NS = "{http://schemas.microsoft.com/windows/2004/02/mit/task}"
MAX_BYTES = 131072
# An explicitly quoted Windows script path with no expansion/metacharacters.
ARGS = re.compile(
    r'^-NoProfile -File "[A-Za-z]:\\(?:[A-Za-z0-9 _.-]+\\)*run_once\.ps1" -Channel file$',
    re.ASCII | re.IGNORECASE,
)
EXECUTABLES = {"powershell.exe",
               r"c:\windows\system32\windowspowershell\v1.0\powershell.exe"}


def _n(tag):
    return NS + tag


def _text(node, relative):
    if node is None:
        return None
    item = node.find(relative)
    return None if item is None else item.text


def _evidence(match, checks):
    return {
        "schema_version": 1,
        "status": "CONFIG_MATCH_UNVERIFIED" if match else "CONFIG_MISMATCH",
        "checks": [{"id": name, "pass": bool(ok)} for name, ok in checks],
        "configured_only": True,
        "task_existence_verified": False,
        "task_executed_verified": False,
        "fifteen_minute_runs_observed": False,
        "machine_policy_changed": False,
        "external_actions_performed": False,
        "production_accepted": False,
    }


def inspect_xml(file):
    """Inspect a bounded, local, exported XML file, never a scheduler API."""
    path = Path(file)
    if path.is_symlink() or not path.is_file():
        raise ValueError("Source is not a regular local file")
    if path.stat().st_size > MAX_BYTES:
        raise ValueError("Source too large")
    raw = path.read_bytes()
    if len(raw) > MAX_BYTES or b"<!DOCTYPE" in raw.upper() or b"<!ENTITY" in raw.upper():
        raise ValueError("Unsafe XML")
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as exc:
        raise ValueError("Malformed XML") from exc
    if root.tag != _n("Task"):
        raise ValueError("Unexpected Task XML namespace or root")
    checks = []
    def check(name, outcome):
        checks.append((name, outcome))
    actions = root.find(_n("Actions"))
    act = list(actions) if actions is not None else []
    check("SINGLE_EXEC_ACTION", len(act) == 1 and act[0].tag == _n("Exec"))
    command = _text(act[0], _n("Command")) if len(act) == 1 else None
    args = _text(act[0], _n("Arguments")) if len(act) == 1 else None
    wd = _text(act[0], _n("WorkingDirectory")) if len(act) == 1 else None
    check("POWERSHELL_COMMAND_FIXED", isinstance(command, str) and command.lower() in EXECUTABLES)
    check("FILE_ONLY_NO_ADDITIONAL_FLAGS", isinstance(args, str) and ARGS.fullmatch(args) is not None)
    check("NO_ACTION_WORKDIR", wd is None)
    principals = root.find(_n("Principals"))
    principal_list = list(principals) if principals is not None else []
    level = _text(principal_list[0], _n("RunLevel")) if len(principal_list) == 1 else None
    check("LIMITED_RUN_LEVEL", len(principal_list) == 1 and level == "LeastPrivilege")
    settings = root.find(_n("Settings"))
    check("TASK_ENABLED", _text(settings, _n("Enabled")) == "true")
    triggers = root.find(_n("Triggers"))
    triggers_list = list(triggers) if triggers is not None else []
    trig = triggers_list[0] if len(triggers_list) == 1 else None
    check("SINGLE_ENABLED_TIME_TRIGGER", trig is not None
          and trig.tag in {_n("TimeTrigger"), _n("CalendarTrigger")}
          and _text(trig, _n("Enabled")) == "true")
    check("EXACT_15_MIN_REPEAT", _text(trig, _n("Repetition") + "/" + _n("Interval")) == "PT15M")
    # Intentionally no task-identity or user-account fields, XML or paths in report.
    return _evidence(all(y for _, y in checks), checks)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Offline Task Scheduler configuration audit only")
    parser.add_argument("--xml", required=True, help="Explicitly exported, locally approved task XML")
    args = parser.parse_args(argv)
    try:
        report = inspect_xml(args.xml)
    except (OSError, ValueError):
        print("W14_TASK_XML_REJECTED", file=sys.stderr)
        return 2
    print(json.dumps(report, ensure_ascii=True, indent=2))
    return 0 if report["status"] == "CONFIG_MATCH_UNVERIFIED" else 3


if __name__ == "__main__":
    sys.exit(main())
