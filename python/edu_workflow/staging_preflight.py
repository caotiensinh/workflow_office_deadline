"""W13 institutional staging *preflight*, never deployment or approval.

Machine inspection is explicitly opt-in, read-only, and limited to session,
PowerShell effective execution policy and existence of an exact task name.
No personal messages, production DBs, credentials, SMTP or Graph are touched.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

PROJECT_FILES = (
    "docs/PROJECT_REQUIREMENTS.md",
    "docs/IMPLEMENTATION_CHECKLIST.md",
    "windows/install_task.ps1",
    "windows/run_once.ps1",
    "windows/uninstall_task.ps1",
    "rust-core/Cargo.toml",
    "python/edu_workflow/monitoring.py",
)
PENDING_GATES = (
    ("IT_ENDPOINT_APPROVAL", "Approved endpoint and script execution policy"),
    ("SCHEDULED_15_MIN", "15-minute task observed under organization policy"),
    ("OUTLOOK_READ_ONLY", "Institution-authorized real read-only Outlook smoke"),
    ("NOTIFICATION_TEST", "Approved synthetic recipient delivery observed"),
    ("IDENTITY_PRIVACY", "SSO/MFA, source access, retention, signing, and privacy review"),
    ("PILOTS", "Three operator-observed and documented pilot sign-offs"),
)


def _check(key, status, explanation):
    return {"id": key, "status": status, "explanation": explanation}


def _probe_windows():
    """Read-only facts; never execute a .ps1 file or modify ExecutionPolicy."""
    result = {"platform": os.name, "session_id": None,
              "execution_policy": "UNAVAILABLE", "task_exists": None}
    if os.name != "nt":
        return result
    try:
        import ctypes
        current = ctypes.windll.kernel32.GetCurrentProcessId()
        session = ctypes.c_ulong()
        ok = ctypes.windll.kernel32.ProcessIdToSessionId(current, ctypes.byref(session))
        if ok:
            result["session_id"] = int(session.value)
    except (OSError, AttributeError, ValueError):
        pass
    # -Command asks only the effective policy: NOT -ExecutionPolicy Bypass.
    try:
        p = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command",
             "(Get-ExecutionPolicy).ToString()"],
            capture_output=True, text=True, timeout=8, check=False,
        )
        if p.returncode == 0:
            policy = p.stdout.strip()
            if policy in {"Restricted", "AllSigned", "RemoteSigned",
                          "Unrestricted", "Bypass", "Undefined", "Default"}:
                result["execution_policy"] = policy
    except (OSError, subprocess.TimeoutExpired, UnicodeError):
        pass
    # Only probe this known task. Do not read the task command, user, XML or secrets.
    try:
        p = subprocess.run(
            ["schtasks.exe", "/Query", "/TN", "EducationAIWorkflow"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=8,
            check=False,
        )
        result["task_exists"] = (p.returncode == 0)
    except (OSError, subprocess.TimeoutExpired):
        pass
    return result


def preflight(root, *, mode="plan", authorized=False, evidence=None):
    """Fail closed and distinguish code presence from real user acceptance."""
    if mode not in {"plan", "machine-readonly"}:
        raise ValueError("Unknown preflight mode")
    if type(authorized) is not bool:
        raise ValueError("authorized must be boolean")
    if mode == "machine-readonly" and not authorized:
        raise PermissionError("IT authorization must be confirmed before machine inspection")
    root = Path(root)
    checks = []
    for rel in PROJECT_FILES:
        file = root / rel
        ok = file.is_file() and not file.is_symlink()
        checks.append(_check("FILE_" + rel.replace("/", "_").replace(".", "_"),
                             "PASS" if ok else "BLOCKED",
                             "project source file present" if ok else "missing or symlinked file"))
    if mode == "machine-readonly":
        info = evidence if evidence is not None else _probe_windows()
        if not isinstance(info, dict) or set(info) != {
            "platform", "session_id", "execution_policy", "task_exists"
        }:
            raise ValueError("Malformed machine observation")
        platform = info["platform"]
        if platform not in {"nt", "posix"}:
            raise ValueError("Invalid platform label")
        if platform == "nt":
            session = info["session_id"]
            if session is None:
                session_status = "UNVERIFIED"
            elif type(session) is not int or session < 0:
                raise ValueError("Invalid Windows session")
            elif session == 0:
                session_status = "BLOCKED_FOR_GUI"
            else:
                session_status = "OBSERVED_NOT_HUMAN_UAT"
            checks.append(_check("WINDOWS_SESSION", session_status,
                                 "Nonzero session cannot prove signed-in operator acceptance"))
            policy = info["execution_policy"]
            if policy not in {"Restricted", "AllSigned", "RemoteSigned",
                              "Unrestricted", "Bypass", "Undefined", "Default", "UNAVAILABLE"}:
                raise ValueError("Unexpected execution-policy observation")
            policy_status = ("BLOCKED_NEEDS_IT" if policy in {"Restricted", "AllSigned"}
                             else "UNVERIFIED" if policy in {"Undefined", "Default", "UNAVAILABLE"}
                             else "IT_REVIEW_REQUIRED")
            checks.append(_check("POWERSHELL_POLICY", policy_status,
                                 "Effective policy is " + policy + "; never bypass enterprise policy"))
            if info["task_exists"] is not None and type(info["task_exists"]) is not bool:
                raise ValueError("Invalid task existence observation")
            checks.append(_check(
                "TASK_EXISTS",
                "EXISTS_NOT_VALIDATED" if info["task_exists"] is True
                else "MISSING" if info["task_exists"] is False else "UNVERIFIED",
                "Existence is not proof of 15-minute cadence, safe action or successful execution",
            ))
        else:
            if info["session_id"] is not None or info["task_exists"] is not None:
                raise ValueError("POSIX observation may not claim Windows session or task")
            checks.append(_check("WINDOWS_ENDPOINT", "NOT_APPLICABLE",
                                 "No Windows endpoint inspected"))
    else:
        checks.append(_check("MACHINE_INSPECTION", "NOT_REQUESTED",
                             "Default is static plan only; no host process inspection"))
    for gate, explanation in PENDING_GATES:
        checks.append(_check(gate, "PENDING_AUTHORIZED_EVIDENCE", explanation))
    blocked = any(x["status"] == "BLOCKED" for x in checks)
    return {
        "schema_version": 1,
        "phase": "W13",
        "mode": mode,
        "status": "SOURCE_BLOCKED" if blocked else "PLAN_REVIEW_ONLY",
        "checks": checks,
        "production_accepted": False,
        "human_pilot_accepted": False,
        "real_outlook_accessed": False,
        "smtp_used": False,
        "task_created_or_changed": False,
        "execution_policy_changed": False,
        "database_opened_or_modified": False,
        "machine_changes_performed": False,
    }


def save_report(report, output):
    """Only explicit, exclusive JSON output, never overwrite approval evidence."""
    target = Path(output)
    if target.is_symlink() or not target.parent.is_dir():
        raise ValueError("Output parent must exist; symlink targets forbidden")
    with target.open("x", encoding="utf-8") as out:
        json.dump(report, out, ensure_ascii=True, indent=2)
        out.write("\n")


def main(argv=None):
    p = argparse.ArgumentParser(description="IT staging checklist; no deployment")
    p.add_argument("--project", default=str(Path(__file__).resolve().parents[2]))
    p.add_argument("--mode", choices=["plan", "machine-readonly"], default="plan")
    p.add_argument("--ack-it-authorized", action="store_true",
                   help="Confirms local IT permission for read-only machine inspection")
    p.add_argument("--output", help="New JSON evidence file, exclusive creation")
    args = p.parse_args(argv)
    report = preflight(args.project, mode=args.mode, authorized=args.ack_it_authorized)
    if args.output:
        save_report(report, args.output)
    print(json.dumps(report, ensure_ascii=True, indent=2))
    # A preflight report is NEVER a production GO decision; exit 3 marks blockers.
    return 3 if report["status"] == "SOURCE_BLOCKED" else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, PermissionError) as exc:
        print("W13 PREFLIGHT ERROR: " + type(exc).__name__, file=sys.stderr)
        sys.exit(2)
