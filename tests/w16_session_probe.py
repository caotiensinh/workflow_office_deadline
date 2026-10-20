"""W16: narrow, read-only Windows session diagnostic on a portable Python runtime.

Does not open GUI, read account names, execute PowerShell, query or alter Task
Scheduler, inspect Outlook, read registry or change system execution policy.
"""
from __future__ import annotations
import argparse
import ctypes
import json
import os
import sys
from pathlib import Path

NO_CONSOLE = 0xFFFFFFFF


def _windows_session():
    """Return Windows process session and active physical console ID (numbers only)."""
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.GetCurrentProcessId.argtypes = []
    kernel.GetCurrentProcessId.restype = ctypes.c_ulong
    kernel.ProcessIdToSessionId.argtypes = [ctypes.c_ulong, ctypes.POINTER(ctypes.c_ulong)]
    kernel.ProcessIdToSessionId.restype = ctypes.c_int
    kernel.WTSGetActiveConsoleSessionId.argtypes = []
    kernel.WTSGetActiveConsoleSessionId.restype = ctypes.c_ulong
    sid = ctypes.c_ulong(0)
    pid = kernel.GetCurrentProcessId()
    if not kernel.ProcessIdToSessionId(pid, ctypes.byref(sid)):
        raise RuntimeError("SESSION_LOOKUP_FAILED")
    active = kernel.WTSGetActiveConsoleSessionId()
    return int(sid.value), None if active == NO_CONSOLE else int(active)


def _classify(process_session, active_session):
    if type(process_session) is not int or not 0 <= process_session < NO_CONSOLE:
        raise ValueError("Invalid process session ID")
    if active_session is not None and (type(active_session) is not int
                                      or not 0 <= active_session < NO_CONSOLE):
        raise ValueError("Invalid console session ID")
    if process_session == 0:
        status = "SESSION_0_GUI_UAT_BLOCKED"
    elif active_session is not None and process_session == active_session:
        status = "CONSOLE_SESSION_CANDIDATE_NOT_UAT"
    else:
        status = "NOT_ACTIVE_CONSOLE_NO_GUI_UAT"
    return {
        "schema_version": 1, "phase": "W16", "status": status,
        "process_session_id": process_session,
        "active_console_session_id": active_session,
        "live_windows_api_observed": True,
        "console_match": bool(process_session != 0 and active_session is not None
                              and process_session == active_session),
        "human_interaction_observed": False,
        "gui_accepted": False, "sound_accepted": False,
        "task_scheduler_checked": False, "task_scheduler_accepted": False,
        "outlook_accessed": False, "smtp_used": False,
        "execution_policy_changed": False, "system_modified": False,
        "production_accepted": False,
    }


def _plan():
    return {
        "schema_version": 1, "phase": "W16", "status": "PLAN_ONLY_NO_HOST_INSPECTION",
        "live_windows_api_observed": False,
        "human_interaction_observed": False, "gui_accepted": False,
        "task_scheduler_checked": False, "task_scheduler_accepted": False,
        "production_accepted": False, "system_modified": False,
    }


def _save_new(report, output):
    target = Path(output)
    # Only create in runner-generated temp directory on inspect, never other paths.
    if not os.environ.get("RUNNER_TEMP"):
        raise RuntimeError("RUNNER_TEMP_REQUIRED")
    temp = Path(os.environ["RUNNER_TEMP"]).resolve()
    parent = target.parent.resolve()
    if temp not in parent.parents or target.exists() or target.is_symlink():
        raise RuntimeError("UNSAFE_OUTPUT_PATH")
    if not parent.is_dir():
        raise RuntimeError("OUTPUT_PARENT_MISSING")
    with target.open("x", encoding="utf-8") as fd:
        json.dump(report, fd, sort_keys=True, ensure_ascii=True, indent=2)
        fd.write("\n")


def main(argv=None):
    p = argparse.ArgumentParser(description="W16 Session ID-only read-only readiness probe")
    p.add_argument("--inspect", action="store_true", help="Read current Windows process and console Session IDs")
    p.add_argument("--output", help="New JSON report under an existing runner TEMP subdirectory")
    a = p.parse_args(argv)
    try:
        if a.inspect:
            if os.name != "nt":
                raise RuntimeError("WINDOWS_REQUIRED")
            report = _classify(*_windows_session())
            if a.output:
                _save_new(report, a.output)
        else:
            if a.output:
                raise RuntimeError("PLAN_CANNOT_SAVE_OUTPUT")
            report = _plan()
        print(json.dumps(report, ensure_ascii=True, sort_keys=True))
        return 0
    except (OSError, ValueError, RuntimeError):
        print("W16_SESSION_PROBE_FAILED_CLOSED", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
