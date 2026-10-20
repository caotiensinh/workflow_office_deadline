"""One-click, strictly synthetic Windows GUI UAT launcher.

This app can record operator observations. It does not certify actual Windows
login autorun, access Outlook, install startup items or approve business cases.
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
import uuid
from pathlib import Path

from . import desktop_app
from . import interactive_session_w19 as session_guard
from .field_uat import run_manual
from .uat_review import review as review_uat_report


def _require_interactive_windows():
    # A non-zero process session is not sufficient: disconnected/RDP/service
    # sessions must not be treated as the active signed-in console.
    return session_guard.require_active_console()


def _ask_consent():
    import tkinter as tk
    from tkinter import messagebox
    root = tk.Tk()
    root.withdraw()
    try:
        return bool(messagebox.askokcancel(
            "学校業務・架空データのテスト",
            "これは架空の通知2件を使うローカル表示テストです。\n"
            "実際のメール、組織データ、Windows Startupは変更しません。\n"
            "続行しますか？\n\n"
            "Synthetic data only. No Outlook, SMTP or production changes. Continue?",
            parent=root,
        ))
    finally:
        root.destroy()


def _show_result(message, *, error=False):
    import tkinter as tk
    from tkinter import messagebox
    root = tk.Tk()
    root.withdraw()
    try:
        if error:
            messagebox.showerror("W8 UAT", message, parent=root)
        else:
            messagebox.showinfo("W8 UAT", message, parent=root)
    finally:
        root.destroy()


def _report_path():
    # Random non-existing user-TEMP path, with exclusive creation in run_manual.
    return Path(tempfile.gettempdir()) / ("EDU_W8_Synthetic_UAT_" + uuid.uuid4().hex + ".json")


def one_click():
    _require_interactive_windows()
    if not _ask_consent():
        return {"status": "CANCELLED", "production_accepted": False}
    # Session may have been disconnected or changed during the consent dialog.
    # Refuse to create a DB/report after an interactive-console mismatch.
    _require_interactive_windows()
    path = _report_path()
    try:
        result = run_manual(path)
        # Verify the *written* evidence, not just the in-memory success flag.
        # This is a consistency review, never independent human/IT acceptance.
        checked = review_uat_report(path)
        if (checked["production_accepted"] or checked["it_approved"] or
                checked["actual_physical_observation_independently_verified"] or
                checked["actual_login_autorun_verified"]):
            raise ValueError("W20A_UNAUTHORIZED_ACCEPTANCE_FLAG")
        if ((result["status"] == "DESKTOP_ACTIONS_AND_HUMAN_REPORT_COMPLETE") !=
                (checked["status"] == "CONSISTENT_SELF_ATTESTATION_NOT_INDEPENDENTLY_VERIFIED")):
            raise ValueError("W20A_REPORT_IN_MEMORY_DISAGREEMENT")
    except Exception:
        # A --windowed executable has no visible console. Fail visibly without
        # disclosing potentially sensitive path or exception arguments.
        _show_result("テストを完了できませんでした。\nUAT failed. No production operation was performed.",
                     error=True)
        raise

    passed = checked["status"] == "CONSISTENT_SELF_ATTESTATION_NOT_INDEPENDENTLY_VERIFIED"
    _show_result(
        ("自己申告レポートの整合性を確認しました。" if passed else
         "自己申告レポートは未完了です。確認項目を見直してください。") +
        "\n\nReport: " + str(path) +
        "\n\nSelf-attestation only; NOT independent GUI, IT or production approval."
    )
    return result


def preflight(output_file):
    """Non-interactive, non-mutating smoke. Never opens the UAT GUI."""
    path = Path(output_file)
    if not path.parent.is_dir():
        raise FileNotFoundError("Preflight output parent must already exist")
    try:
        import tkinter
        tk_ready = True
    except ImportError:
        tk_ready = False
    result = {
        "mode": "one-click-uat-preflight",
        "packaged_entrypoint": "OK",
        "tk_importable": tk_ready,
        "session_interactive": bool(session_guard.inspect()["active_console_match"]),
        "synthetic_only": True,
        "changes_startup": False,
        "opens_outlook": False,
        "sends_smtp": False,
        "actual_login_autorun_verified": False,
        "production_accepted": False,
    }
    # No stale PASS: preserve old reports rather than overwriting evidence.
    with path.open("x", encoding="utf-8") as out:
        json.dump(result, out, ensure_ascii=False)
    return result


def session_check(output_file):
    """W19 non-GUI diagnostic: read only numeric session IDs, new local file."""
    path = Path(output_file)
    if path.is_symlink() or not path.parent.is_dir():
        raise ValueError("W19 diagnostic output must use an existing directory")
    result = session_guard.inspect()
    # Exclusive creation: no replacement of an existing acceptance report.
    with path.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, ensure_ascii=True, sort_keys=True)
    return result


def review_existing_uat(report_file, output_file):
    """W22A offline packaged reviewer; no GUI, Win32 API or mutable source."""
    path = Path(output_file)
    if path.is_symlink() or not path.parent.is_dir():
        raise ValueError("W22A output must be a new regular local file")
    checked = review_uat_report(report_file)
    # Never allow a self-report to become IT approval or production evidence.
    if (checked["production_accepted"] or checked["it_approved"] or
            checked["actual_physical_observation_independently_verified"]):
        raise ValueError("W22A_SELF_REPORT_CANNOT_GRANT_AUTHORITY")
    result = {
        "phase": "W22A",
        "status": checked["status"],
        "ack_receipts": checked["ack_receipts"],
        "snooze_receipts": checked["snooze_receipts"],
        "self_attested_only": True,
        "real_gui_independently_verified": False,
        "windows_login_autorun_verified": False,
        "it_approved": False,
        "production_accepted": False,
        "opens_gui": False,
        "modifies_source": False,
    }
    with path.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, ensure_ascii=True, sort_keys=True)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="One-click Windows field UAT using entirely fictional local notifications"
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--preflight-file",
                       help="Noninteractive JSON preflight; does not launch GUI")
    group.add_argument("--session-check-file",
                       help="W19 read-only Windows session diagnostic, without GUI")
    group.add_argument("--review-report-file",
                       help="W22A offline review of a saved fictional GUI self-report, no GUI")
    parser.add_argument("--review-output-file",
                        help="New JSON summary file required for --review-report-file")
    args = parser.parse_args(argv)
    if bool(args.review_report_file) != bool(args.review_output_file):
        parser.error("W22A requires both review-report and review-output")
    if args.review_report_file:
        try:
            review_existing_uat(args.review_report_file, args.review_output_file)
        except (OSError, ValueError, TypeError, UnicodeError):
            # A windowed EXE must fail without a traceback, private file path,
            # success JSON or messagebox that could hang hosted headless tests.
            raise SystemExit(2) from None
        return
    if args.preflight_file:
        preflight(args.preflight_file)
        return
    if args.session_check_file:
        session_check(args.session_check_file)
        return
    one_click()


if __name__ == "__main__":
    main()
