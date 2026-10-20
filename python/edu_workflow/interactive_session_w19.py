"""W19: read-only current Windows process versus active console session check.

Matching session IDs identify only a candidate for human GUI observation.
They do not prove a visible window, a human action, Windows login persistence
or organizational/production acceptance. No usernames or private host details.
"""
from __future__ import annotations

import sys

INVALID_ID = 0xFFFFFFFF


def classify(process_session_id, active_console_session_id):
    if (type(process_session_id) is not int or
            not 0 <= process_session_id < INVALID_ID):
        raise ValueError("Invalid process session ID")
    if (active_console_session_id is not None and
            (type(active_console_session_id) is not int or
             not 0 <= active_console_session_id < INVALID_ID)):
        raise ValueError("Invalid active console session ID")

    match = (process_session_id != 0 and
             active_console_session_id is not None and
             process_session_id == active_console_session_id)
    if process_session_id == 0:
        status = "W19_SESSION_0_BLOCKED"
    elif active_console_session_id is None:
        status = "W19_NO_ACTIVE_CONSOLE_BLOCKED"
    elif not match:
        status = "W19_DIFFERENT_SESSION_BLOCKED"
    else:
        status = "W19_ACTIVE_CONSOLE_CANDIDATE_NOT_GUI_UAT"

    return {
        "status": status,
        "process_session_id": process_session_id,
        "active_console_session_id": active_console_session_id,
        "active_console_match": match,
        "live_windows_api_observed": False,
        "human_interaction_observed": False,
        "actual_login_autorun_verified": False,
        "production_accepted": False,
        "modifies_system": False,
    }


def inspect():
    """Read only numerical Win32 session IDs for this very process."""
    if sys.platform != "win32":
        return {
            "status": "W19_NON_WINDOWS_BLOCKED",
            "process_session_id": None,
            "active_console_session_id": None,
            "active_console_match": False,
            "live_windows_api_observed": False,
            "human_interaction_observed": False,
            "actual_login_autorun_verified": False,
            "production_accepted": False,
            "modifies_system": False,
        }
    import ctypes
    from ctypes import wintypes

    kernel32 = ctypes.windll.kernel32
    process = wintypes.DWORD(INVALID_ID)
    pid = kernel32.GetCurrentProcessId()
    if not kernel32.ProcessIdToSessionId(pid, ctypes.byref(process)):
        raise RuntimeError("W19_SESSION_API_UNAVAILABLE")
    active = kernel32.WTSGetActiveConsoleSessionId()
    data = classify(process.value, None if active == INVALID_ID else active)
    data["live_windows_api_observed"] = True
    return data


def require_active_console():
    result = inspect()
    if (not result["live_windows_api_observed"] or
            not result["active_console_match"]):
        raise RuntimeError("W19_NOT_ACTIVE_CONSOLE_NO_GUI")
    return result
