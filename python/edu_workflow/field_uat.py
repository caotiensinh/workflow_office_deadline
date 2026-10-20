"""Opt-in, entirely fictional, signed-in Windows desktop acceptance.

This is human-observed UAT evidence, not automatic production acceptance.
Never reads Outlook, a real workflow database, credentials or Startup.
"""
from __future__ import annotations

import argparse
import getpass
import json
import sqlite3
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

from . import desktop_app
from . import interactive_session_w19 as session_guard
from .store import add_case, open_store, now_iso


ALERT_IDS = ("c" * 64, "d" * 64)


def seed_synthetic(db_path):
    """Populate an isolated database with exactly two fictional delivered notices."""
    path = Path(db_path)
    if path.exists():
        raise FileExistsError("UAT fixture must be a NEW temporary database")
    conn = open_store(path)
    try:
        for number, alert_id in enumerate(ALERT_IDS, 1):
            case_id = f"W7-UAT-SYNTH-{number}"
            case = {
                "case_id": case_id,
                "kind": "EMAIL",
                "data_class": "RESTRICTED",
                "safe_title": "SYNTHETIC_NEVER_REAL_DATA",
                "owner": "noreply@example.invalid",
                "status": "IN_PROGRESS",
                "approval_status": "NOT_REQUIRED",
                "due_at": (datetime.now(timezone.utc) + timedelta(days=3)).isoformat(),
                "due_verified": True,
                "evidence_ref": None,
            }
            if not add_case(conn, case):
                raise RuntimeError("UAT fixture had a duplicate synthetic case")
            with conn:
                conn.execute(
                    """INSERT INTO alerts
                    (alert_id,case_id,revision,code,severity,day,message,state,
                     created_at,delivered_at)
                    VALUES (?,?,?,?,?,?,?,?,?,?)""",
                    (alert_id, case_id, 1, "D_MINUS_3", "WARNING",
                     datetime.now(timezone.utc).date().isoformat(),
                     "SYNTHETIC_ONLY", "SENT", now_iso(), now_iso()),
                )
    finally:
        conn.close()
    return path


def inspect_actions(db_path, actor):
    """Compare real desktop ACK/Snooze receipts to audit; never return case content."""
    conn = sqlite3.connect(db_path)
    try:
        account = actor.strip().casefold()
        receipts = conn.execute(
            "SELECT disposition, COUNT(*) FROM desktop_receipts WHERE actor=? "
            "GROUP BY disposition", (account,),
        ).fetchall() if _table_exists(conn, "desktop_receipts") else []
        counts = dict(receipts)
        audits = conn.execute(
            "SELECT COUNT(*) FROM audit WHERE event IN ('DESKTOP_ACK','DESKTOP_SNOOZE')"
        ).fetchone()[0]
        decisions = conn.execute("SELECT COUNT(*) FROM decisions").fetchone()[0]
        valid = counts.get("ACK") == 1 and counts.get("SNOOZE") == 1 and (
            sum(counts.values()) == 2 and audits == 2 and decisions == 0
        )
        return {
            "ack_receipts": counts.get("ACK", 0),
            "snooze_receipts": counts.get("SNOOZE", 0),
            "desktop_audit_events": audits,
            "business_approvals": decisions,
            "human_buttons_recorded": bool(valid),
        }
    finally:
        conn.close()


def _table_exists(conn, name):
    return conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,),
    ).fetchone() is not None


def run_manual(report_file):
    # Must be the currently active console, not just a nonzero session ID.
    # The W8 launcher separately checks before/after asking consent.
    session_guard.require_active_console()
    from tkinter import Tk, messagebox

    target = Path(report_file).resolve()
    if target.exists():
        raise FileExistsError("Refusing to overwrite a previous field UAT report")
    if not target.parent.is_dir():
        raise FileNotFoundError("UAT report parent directory must already exist")

    with tempfile.TemporaryDirectory(prefix="edu-w7-uat-") as temp:
        db = seed_synthetic(Path(temp) / "fictional-only.sqlite3")
        desktop_app.launch(db, poll_seconds=5)
        observed = inspect_actions(db, getpass.getuser())

    root = Tk()
    root.withdraw()
    try:
        visual = messagebox.askyesno(
            "W7 UAT - 日本語", "日本語の表示を正しく読めましたか？\nWere Japanese labels readable?",
            parent=root,
        )
        audible = messagebox.askyesno(
            "W7 UAT - 通知音", "通知音を実際に聞きましたか？\nWas a notification sound audible?",
            parent=root,
        )
        focus = messagebox.askyesno(
            "W7 UAT - ウィンドウ", "通知センターが画面に表示され、操作できましたか？\nWas the window visible and interactive?",
            parent=root,
        )
    finally:
        root.destroy()

    report = {
        "scope": "fictional-local-data-only",
        "type": "human-self-attested-Windows-field-UAT",
        "session_interactive": True,
        "visual_japanese_self_report": bool(visual),
        "sound_audible_self_report": bool(audible),
        "window_interactive_self_report": bool(focus),
        **observed,
        # A separate, authorized logout/login is required. Never invent it.
        "actual_login_autorun_verified": False,
        "production_accepted": False,
        "status": ("DESKTOP_ACTIONS_AND_HUMAN_REPORT_COMPLETE"
                   if all((visual, audible, focus, observed["human_buttons_recorded"]))
                   else "INCOMPLETE_FIELD_UAT"),
    }
    # The operator might log off/disconnect while using Tk. Do not write
    # a purported human UAT report after the console session changed.
    session_guard.require_active_console()
    with target.open("x", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    print("W7 manual synthetic UAT report written (not production acceptance)")
    return report


def main():
    parser = argparse.ArgumentParser(description="W7 signed-in Windows synthetic UAT; opt-in only")
    choices = parser.add_mutually_exclusive_group(required=True)
    choices.add_argument("--plan-only", action="store_true")
    choices.add_argument("--run-synthetic", action="store_true")
    parser.add_argument("--report", help="new JSON report file (required for --run-synthetic)")
    opts = parser.parse_args()
    if opts.plan_only:
        print(json.dumps({
            "mode": "plan-only", "synthetic_only": True, "touches_outlook": False,
            "touches_smtp": False, "changes_startup": False,
            "requires_signed_in_windows": True,
            "physical_user_confirmation": True,
            "production_accepted": False,
        }))
        return
    if not opts.report:
        parser.error("--report is required for --run-synthetic")
    run_manual(opts.report)


if __name__ == "__main__":
    main()
