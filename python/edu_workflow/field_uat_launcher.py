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
from .field_uat import run_manual


def _require_interactive_windows():
    if sys.platform != "win32" or not desktop_app._interactive_desktop_available():
        raise RuntimeError("BLOCKED_SESSION_0_OR_NON_WINDOWS: signed-in Windows user required")


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
    path = _report_path()
    try:
        result = run_manual(path)
    except Exception:
        # A --windowed executable has no visible console. Fail visibly without
        # disclosing potentially sensitive path or exception arguments.
        _show_result("テストを完了できませんでした。\nUAT failed. No production operation was performed.",
                     error=True)
        raise

    passed = result["status"] == "DESKTOP_ACTIONS_AND_HUMAN_REPORT_COMPLETE"
    _show_result(
        ("架空データのGUI確認が完了しました。" if passed else
         "確認項目が未完了です。テスト結果を確認してください。") +
        "\n\nReport: " + str(path) +
        "\n\nNot a production or login-Startup acceptance."
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
        "session_interactive": bool(
            sys.platform == "win32" and desktop_app._interactive_desktop_available()
        ),
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


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="One-click Windows field UAT using entirely fictional local notifications"
    )
    parser.add_argument("--preflight-file",
                        help="Noninteractive JSON preflight; does not launch GUI")
    args = parser.parse_args(argv)
    if args.preflight_file:
        preflight(args.preflight_file)
        return
    one_click()


if __name__ == "__main__":
    main()
