"""Probe only OUR OWN Tkinter window on a signed-in Windows desktop.

Does not capture desktop/screenshots, read other applications, click other windows,
touch Outlook, or modify system settings. Service Session 0 is a documented blocker.
"""
from __future__ import annotations
import ctypes
from ctypes import wintypes
import json
import os
import subprocess
import sys
import time
from pathlib import Path


def session_id():
    sid=wintypes.DWORD()
    ok=ctypes.windll.kernel32.ProcessIdToSessionId(os.getpid(),ctypes.byref(sid))
    return int(sid.value) if ok else None


def own_window(pid):
    user32=ctypes.windll.user32
    def callback(hwnd, unused):
        current=wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd,ctypes.byref(current))
        if current.value != pid or not user32.IsWindowVisible(hwnd):
            return True
        buf=ctypes.create_unicode_buffer(256)
        user32.GetWindowTextW(hwnd,buf,256)
        if "通知センター" in buf.value:
            found.append((hwnd,buf.value))
            return False
        return True
    found=[]
    callback_type=ctypes.WINFUNCTYPE(wintypes.BOOL,wintypes.HWND,wintypes.LPARAM)
    enum=callback_type(callback)
    user32.EnumWindows(enum,0)
    return found[0] if found else None


def execute(dest):
    dest=Path(dest)
    dest.mkdir(parents=True,exist_ok=True)
    result={"run_scope":"selfhost-UI", "real_school_mail":False}
    sid=session_id()
    result["process_session_id"]=sid
    if sid in (None,0):
        result["status"]="BLOCKED_SESSION_0_NONINTERACTIVE"
    else:
        try:
            import tkinter
        except ImportError:
            result["status"]="BLOCKED_TKINTER_MISSING"
        else:
            db=dest/"selfhost-w4.sqlite3"
            if not db.is_file():
                raise RuntimeError("No isolated synthetic DB; refusing to probe production data")
            env=dict(os.environ,PYTHONPATH=str(Path(__file__).resolve().parents[1]/"python"))
            process=subprocess.Popen([sys.executable,"-m","edu_workflow.desktop_app",
                                      "--db",str(db),"--poll-seconds","5"],
                                      cwd=Path(__file__).resolve().parents[1],
                                      env=env,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
            try:
                matched=None
                deadline=time.monotonic()+12
                while time.monotonic()<deadline:
                    if process.poll() is not None:
                        break
                    matched=own_window(process.pid)
                    if matched:
                        break
                    time.sleep(.4)
                if matched:
                    handle,title=matched
                    # ONLY close this process-owned Tk window, not another app.
                    ctypes.windll.user32.PostMessageW(handle,0x0010,0,0)
                    result["status"]="PASS_OWN_TK_WINDOW_FOUND"
                    result["visible_window_title"]="通知センター"
                    result["window_process_id_matches"]=True
                else:
                    result["status"]="FAILED_NO_OWN_TK_WINDOW"
                    result["details"]="No visible window belonging to the spawned test process found in 12s"
            finally:
                try:
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    process.terminate()
                    try:process.wait(timeout=3)
                    except subprocess.TimeoutExpired:process.kill()
    (dest/"gui_result.json").write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding="utf-8")
    print("SELFHOST_W4_GUI_PROBE "+json.dumps(result,ensure_ascii=False))
    # Missing interactive session is a limitation, not a false code pass.
    return 1 if result["status"].startswith("FAILED") else 0


if __name__=="__main__":
    if sys.platform!="win32":
        raise SystemExit("Windows required")
    if len(sys.argv)!=2:raise SystemExit("usage: selfhost_w4_gui_probe.py <isolated result dir>")
    sys.exit(execute(sys.argv[1]))
