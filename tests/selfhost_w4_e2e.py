"""Self-hosted Windows E2E using synthetic data ONLY.

No Outlook, SMTP, Windows Task Scheduler, production SQLite or external services.
Uses a disposable directory within RUNNER_TEMP and reports hardware/session
status without reading addresses, camera streams or user files.
"""
from __future__ import annotations

import getpass
import json
import os
import platform
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

from edu_workflow.desktop_center import list_notifications, mark_notification
from edu_workflow.store import audit_list, get_case, get_cases, open_store


ROOT = Path(__file__).resolve().parents[1]
NOW = "2026-10-19T09:00:00+09:00"
UTC = timezone.utc


def invoke(argv, *, env=None, typed=None, timeout=90):
    result = subprocess.run(
        [str(x) for x in argv], cwd=ROOT,
        env=(dict(os.environ, PYTHONPATH=str(ROOT / "python")) if env is None else env),
        input=typed, capture_output=True, encoding="utf-8", errors="replace",
        timeout=timeout, check=False,
    )
    if result.returncode:
        raise AssertionError(
            f"Command failed rc={result.returncode}, executable={Path(str(argv[0])).name}, "
            f"stdout_tail={result.stdout[-450:]!r}, stderr_tail={result.stderr[-450:]!r}"
        )
    return result.stdout.strip()


def cli(db, *args, env=None, typed=None):
    return invoke([sys.executable, "-m", "edu_workflow.cli", "--db", db, *args],
                  env=env, typed=typed)


def session_id():
    try:
        import ctypes
        from ctypes import wintypes
        ident = wintypes.DWORD()
        ok = ctypes.windll.kernel32.ProcessIdToSessionId(os.getpid(), ctypes.byref(ident))
        return int(ident.value) if ok else None
    except (ImportError, AttributeError, OSError):
        return None


def execute(dest: Path):
    assert sys.platform == "win32", "This E2E specifically requires the Windows self-hosted runner"
    dest.mkdir(parents=True, exist_ok=True)
    # No data outside dest: all tests are fictional, and target is RUNNER_TEMP.
    db = dest / "selfhost-w4.sqlite3"
    notices = dest / "notifications"
    if db.exists():
        raise AssertionError("Disposable test database already exists; refusing to modify it")
    env = dict(os.environ, PYTHONPATH=str(ROOT / "python"))
    entry = ROOT / "windows" / "run_once.ps1"
    inbox = ROOT / "examples" / "w2_inbox"
    for loop in (1, 2):
        out = invoke([
            "powershell.exe", "-NoProfile", "-NonInteractive",
            "-ExecutionPolicy", "Bypass", "-File", entry,
            "-ImportEmlDir", inbox,
            "-DbPath", db, "-OutDir", notices, "-At", NOW,
        ], env=env, timeout=120)
        print(f"background_cycle_{loop}: {out[-500:]}")

    conn = open_store(db)
    try:
        all_cases = get_cases(conn)
        assert len(all_cases) == 3, f"expected 3 synthetic EML cases, got {len(all_cases)}"
        assert all(not case["due_verified"] for case, _ in all_cases)
        alerts = conn.execute("SELECT COUNT(*) FROM alerts").fetchone()[0]
        assert alerts == 3, f"duplicate notifications: {alerts}"
        assert len(list(notices.glob("*.json"))) == 3

        viewer = getpass.getuser()
        initial = list_notifications(conn, viewer)
        assert len(initial) == 3
        assert all(item["delivery_state"] == "SENT" for item in initial)
        assert all("example.invalid" not in json.dumps(x) for x in initial)

        # ACK means viewed; snooze must expire and persist without human approval.
        first, second = initial[0]["alert_id"], initial[1]["alert_id"]
        at = datetime(2026, 10, 19, 12, tzinfo=timezone(timedelta(hours=9)))
        assert mark_notification(conn, first, viewer, "ACK", at=at)
        assert mark_notification(conn, second, viewer, "SNOOZE", at=at, snooze_minutes=30)
        assert conn.execute("SELECT COUNT(*) FROM decisions").fetchone()[0] == 0
    finally:
        conn.close()

    conn = open_store(db)
    try:
        assert len(list_notifications(conn, viewer, at=at + timedelta(minutes=1))) == 1
        assert len(list_notifications(conn, viewer, at=at + timedelta(minutes=31))) == 2
        assert len(list_notifications(conn, "another-synthetic-user", at=at)) == 3

        # Human confirmation must require the exact timestamp and case revision.
        selected_case, version = next((c, rev) for c, rev in get_cases(conn) if c.get("due_at"))
        assert version == 1
        case_id, due = selected_case["case_id"], selected_case["due_at"]
    finally:
        conn.close()

    env["EDU_VERIFIER_USERS"] = viewer
    command = (
        "confirm-deadline", "--case-id", case_id, "--due", due,
        "--revision", "1", "--method", "source-reviewed",
    )
    bad = subprocess.run(
        [sys.executable, "-m", "edu_workflow.cli", "--db", str(db), *command],
        input="WRONG\n", cwd=ROOT, env=env, capture_output=True, encoding="utf-8"
    )
    assert bad.returncode != 0
    out = cli(db, *command, env=env, typed=f"CONFIRM {case_id} {due}\n")
    assert json.loads(out)["revision"] == 2
    # User confirmation is not automatically a management approval.
    conn = open_store(db)
    try:
        actual, version = get_case(conn, case_id)
        assert version == 2 and actual["due_verified"]
        assert conn.execute("SELECT COUNT(*) FROM decisions").fetchone()[0] == 0
        assert len([r for r in audit_list(conn) if r["event"] == "HUMAN_VERIFIED_DEADLINE"]) == 1
    finally:
        conn.close()

    # Re-run compiled Rust engine after confirmation, then materialize next reminder.
    rust_bin = ROOT / "rust-core" / "target" / "release" / "edu_rules.exe"
    assert rust_bin.is_file(), "Rust native binary not found; cargo release build required"
    out = cli(db, "tick", "--backend", "rust", "--rust-bin", rust_bin, "--at", NOW, env=env)
    assert json.loads(out)["alerts_added"] == 1
    delivery = json.loads(cli(db, "deliver", "--channel", "file", "--out-dir", notices, env=env))
    assert delivery["sent"] == 1

    conn = open_store(db)
    try:
        codes = [row["code"] for row in conn.execute(
            "SELECT code FROM alerts WHERE case_id=? AND revision=2", (case_id,)
        )]
        assert codes == ["D_MINUS_3"], codes
        current_notices = list_notifications(conn, "another-synthetic-user", at=at)
        # The old "VERIFY_DEADLINE" alert is excluded by revision match.
        assert len(current_notices) == 3
        assert any(x["code"] == "D_MINUS_3" and x["case_id"] == case_id for x in current_notices)
    finally:
        conn.close()

    # Do not force GUI in Session 0: Windows service runners cannot present
    # a window to the user's interactive desktop.
    sid = session_id()
    ui = "BLOCKED_NONINTERACTIVE_SESSION" if sid in (None, 0) else "SESSION_AVAILABLE_FOR_UI_PROBE"
    report = {
        "status": "PASS_CORE_E2E", "runner_type": "github-self-hosted-Windows",
        "os": platform.system(), "runner_session_id": sid,
        "python": platform.python_version(), "synthetic_eml": 3,
        "initial_alerts": 3, "duplicates_after_repeat": 0,
        "viewed_ack": True, "snooze_survives_restart": True,
        "confirm_due_human_token": True, "rust_d_minus_3": True,
        "business_approvals_issued": 0, "gui_session": ui,
        "outlook_accessed": False, "smtp_sent": False,
        "task_scheduler_changed": False,
    }
    (dest / "result.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("SELFHOST_W4_CORE_E2E_PASS " + json.dumps(report, ensure_ascii=False))
    return report


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: selfhost_w4_e2e.py <disposable output folder>")
    execute(Path(sys.argv[1]).resolve())
