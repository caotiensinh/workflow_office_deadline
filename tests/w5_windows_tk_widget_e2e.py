"""Real Windows Tk widget E2E with a disposable, entirely synthetic SQLite DB.

Run only on a Windows *interactive test runner*. Uses genuine Tk widgets,
list_notifications and mark_notification (no backend mocks), without looking
at other windows, grabbing desktop screenshots or touching real Startup/mail.
It does not certify that an institutional user can see the window on MRCAO.
"""
from __future__ import annotations

import argparse
import ctypes
from ctypes import wintypes
import getpass
import json
import sqlite3
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from edu_workflow import desktop_app
from edu_workflow.desktop_center import list_notifications
from edu_workflow.store import add_case, open_store


def windows_session_id():
    if sys.platform != "win32":
        raise RuntimeError("Windows required for this E2E")
    session = wintypes.DWORD()
    if not ctypes.windll.kernel32.ProcessIdToSessionId(
        ctypes.windll.kernel32.GetCurrentProcessId(), ctypes.byref(session)
    ):
        raise RuntimeError("Unable to establish Windows session ID")
    return int(session.value)


def walk(widget):
    yield widget
    for child in widget.winfo_children():
        yield from walk(child)


def seed(db_path):
    conn = open_store(db_path)
    for n, aid in enumerate(("a" * 64, "b" * 64), 1):
        cid = f"W5B-SYNTH-{n}"
        case = {
            "case_id": cid,
            "kind": "EMAIL",
            "data_class": "RESTRICTED",
            "safe_title": "PRIVATE_SYNTHETIC_INTERNAL_VALUE",
            "owner": "noreply@example.invalid",
            "status": "IN_PROGRESS",
            "approval_status": "NOT_REQUIRED",
            "due_at": "2026-10-22T17:00:00+09:00",
            "due_verified": True,
            "evidence_ref": None,
        }
        assert add_case(conn, case), "Synthetic case insertion failed"
        with conn:
            conn.execute(
                """INSERT INTO alerts
                   (alert_id,case_id,revision,code,severity,day,message,
                    state,created_at,delivered_at)
                   VALUES(?,?,?,?,?,?,?,?,?,?)""",
                (aid,cid,1,"D_MINUS_3","WARNING","2026-10-19",
                 "PRIVATE_SYNTHETIC_MESSAGE","SENT",
                 "2026-10-19T00:00:00+00:00","2026-10-19T00:01:00+00:00"),
            )
    conn.close()


def exercise_window(db_path, *, report_path):
    import tkinter as tk
    from tkinter import ttk

    sid = windows_session_id()
    if sid == 0 or not desktop_app._interactive_desktop_available():
        raise RuntimeError("BLOCKED_SESSION_0: cannot assert visible Tk GUI in service runner")
    real_tk = tk.Tk
    result = {
        "scope": "synthetic-only",
        "os": "Windows",
        "windows_session_id": sid,
        "runner": "github-hosted-windows-interactive-test",
        "gui_window_mapped": False,
        "japanese_title": False,
        "initial_notices": 0,
        "initial_bell_calls": 0,
        "snooze_removed": False,
        "snooze_expiry_realerted": False,
        "realert_only_once": False,
        "ack_removed": False,
        "audit_events": 0,
        "approvals": 0,
        "db_closed": False,
        "status": "FAILED",
    }
    captured = {"error": None, "closed": False}
    expected_ids = {"a" * 64, "b" * 64}

    def create_window(*args, **kwargs):
        root = real_tk(*args, **kwargs)
        original_bell = root.bell
        bell_calls = {"count": 0}

        def measured_bell(*args, **kwargs):
            bell_calls["count"] += 1
            return original_bell(*args, **kwargs)

        root.bell = measured_bell
        original_protocol = root.protocol
        hooks = {}

        def protocol(name, callback=None):
            if callback is not None:
                hooks[name] = callback
            return original_protocol(name, callback)

        root.protocol = protocol

        def perform():
            try:
                root.update_idletasks()
                result["japanese_title"] = "通知センター" in root.title()
                result["gui_window_mapped"] = bool(root.winfo_viewable())
                elements = list(walk(root))
                trees = [x for x in elements if isinstance(x, ttk.Treeview)]
                controls = {x.cget("text"): x for x in elements if isinstance(x, ttk.Button)}
                assert len(trees) == 1, "Expected exactly one notification Treeview"
                assert all(k in controls for k in ("確認済み","30分後に再表示","更新"))
                assert result["japanese_title"] and result["gui_window_mapped"], "Windows test desktop could not render Tk"
                view=trees[0]
                items=set(view.get_children())
                result["initial_notices"]=len(items)
                assert items == expected_ids, "Wrong number of actual SQLite-backed notifications"
                result["initial_bell_calls"] = bell_calls["count"]
                assert bell_calls["count"] == 1, "Initial alert should ring only once"
                assert all("PRIVATE_SYNTHETIC" not in str(view.item(aid, "values"))
                           for aid in items), "Private synthetic text leaked into Treeview"
                labels=" ".join(x.cget("text") for x in elements if isinstance(x, ttk.Label))
                assert "PRIVATE_SYNTHETIC" not in labels, "Private data escaped into Tk label"
                assert root.winfo_width() >= 580 and root.winfo_height() >= 350

                view.selection_set("a" * 64)
                controls["30分後に再表示"].invoke()
                assert set(view.get_children()) == {"b" * 64}, "Snoozed notice remains visible"
                result["snooze_removed"]=True

                view.selection_set("b" * 64)
                controls["確認済み"].invoke()
                assert not view.get_children(), "Acknowledged notice remains visible"
                result["ack_removed"]=True

                # Simulate elapsed time ONLY in this isolated synthetic DB.
                # Use the real Refresh button, Tk widget and SQL receipt model.
                with sqlite3.connect(db_path) as writer:
                    writer.execute(
                        "UPDATE desktop_receipts SET snoozed_until=? WHERE alert_id=?",
                        ("2000-01-01T00:00:00+00:00", "a" * 64),
                    )
                controls["更新"].invoke()
                result["snooze_expiry_realerted"] = (
                    set(view.get_children()) == {"a" * 64}
                    and bell_calls["count"] == 2
                )
                assert result["snooze_expiry_realerted"], "Expired Snooze did not re-alert"
                controls["更新"].invoke()
                result["realert_only_once"] = bell_calls["count"] == 2
                assert result["realert_only_once"], "Unchanged alert rang more than once"
            except BaseException as exc:
                captured["error"] = f"{type(exc).__name__}: {exc}"
            finally:
                callback=hooks.get("WM_DELETE_WINDOW")
                if callback is not None:
                    root.after(50,callback)
                else:
                    root.after(50,root.destroy)

        def timeout():
            if not captured["closed"]:
                captured["error"] = captured["error"] or "Tk timeout (15 seconds)"
                try:
                    callback=hooks.get("WM_DELETE_WINDOW")
                    if callback:
                        callback()
                    else:
                        root.destroy()
                except Exception:
                    root.destroy()
        root.after(450,perform)
        root.after(15000,timeout)
        return root

    with patch.object(tk, "Tk", new=create_window):
        desktop_app.launch(db_path, poll_seconds=5)
    captured["closed"] = True
    result["db_closed"]=True

    conn = open_store(db_path)
    try:
        receipts = conn.execute(
            "SELECT disposition, COUNT(*) AS n FROM desktop_receipts GROUP BY disposition"
        ).fetchall()
        assert {x["disposition"]: x["n"] for x in receipts} == {"ACK":1,"SNOOZE":1}
        result["audit_events"] = conn.execute(
            "SELECT COUNT(*) FROM audit WHERE event IN ('DESKTOP_ACK','DESKTOP_SNOOZE')"
        ).fetchone()[0]
        result["approvals"]=conn.execute("SELECT COUNT(*) FROM decisions").fetchone()[0]
        assert len(list_notifications(conn,"another-synthetic-account")) == 2
    finally:
        conn.close()

    if captured["error"]:
        result["error"] = captured["error"]
    else:
        assert result["audit_events"] == 2 and result["approvals"] == 0
        assert result["japanese_title"] and result["gui_window_mapped"]
        assert result["snooze_removed"] and result["ack_removed"]
        assert result["initial_bell_calls"] == 1
        assert result["snooze_expiry_realerted"] and result["realert_only_once"]
        result["status"]="PASS_WINDOWS_TK_WIDGET_E2E"

    report_path.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    print("W5B_WINDOWS_TK_E2E " + json.dumps(result,ensure_ascii=False))
    if result["status"] != "PASS_WINDOWS_TK_WIDGET_E2E":
        raise AssertionError(result.get("error","Windows Tk E2E failed"))


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--report",required=True)
    opt=ap.parse_args()
    report=Path(opt.report).resolve()
    report.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="workflow-w5b-") as temp:
        db_path=Path(temp)/"isolated-synthetic.sqlite3"
        seed(db_path)
        exercise_window(db_path,report_path=report)


if __name__=="__main__":
    main()
