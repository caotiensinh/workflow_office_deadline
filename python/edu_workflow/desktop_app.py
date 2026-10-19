"""Interactive Windows notification center (Python standard-library Tk).

Run ONLY in the signed-in user's desktop session; do not launch from the
noninteractive Task Scheduler worker. Uses SQLite read/write for local receipts,
never approves/denies a case or invokes network actions.
"""
from __future__ import annotations
import getpass
from datetime import datetime, timezone
from pathlib import Path
from .store import open_store
from .desktop_center import list_notifications, mark_notification


def _interactive_desktop_available():
    """Fail closed on Windows Session 0; never present a fake UI PASS."""
    import sys
    if sys.platform != 'win32':
        return True
    import ctypes
    from ctypes import wintypes
    sid=wintypes.DWORD()
    if not ctypes.windll.kernel32.ProcessIdToSessionId(
        ctypes.windll.kernel32.GetCurrentProcessId(), ctypes.byref(sid)
    ):
        return False
    return sid.value != 0


def launch(db_path, poll_seconds=15):
    if not 5 <= poll_seconds <= 3600:
        raise ValueError('poll_seconds must be in 5..3600')
    if not _interactive_desktop_available():
        raise RuntimeError('No interactive Windows user session (Session 0 is service-only)')
    try:
        import tkinter as tk
        from tkinter import ttk, messagebox
    except ImportError as exc:
        raise RuntimeError('Python Tkinter desktop component not installed') from exc
    try:
        window=tk.Tk()
    except tk.TclError as exc:
        raise RuntimeError('No interactive Windows desktop session; cannot show notifications') from exc
    window.title('学校業務 - 通知センター（ローカル）')
    window.geometry('790x460')
    window.minsize(580,350)
    root=ttk.Frame(window,padding=12)
    root.pack(fill='both',expand=True)
    ttk.Label(root,text='期限・要確認のお知らせ',font=('Yu Gothic UI',14,'bold')).pack(anchor='w')
    ttk.Label(root,text='確認済み = 通知を読んだだけ。人事・業務の承認にはなりません。').pack(anchor='w',pady=(2,8))
    cols=('priority','category','case','delivery','day')
    grid=ttk.Treeview(root,columns=cols,show='headings',selectmode='browse')
    for col,title,width in (
        ('priority','重要度',85),('category','確認内容',250),('case','案件ID',190),
        ('delivery','配信',80),('day','発生日',100)):
        grid.heading(col,text=title)
        grid.column(col,width=width,anchor='w')
    grid.pack(fill='both',expand=True)
    caption=tk.StringVar(value='通知を確認中')
    ttk.Label(root,textvariable=caption).pack(anchor='w',pady=(8,4))
    controls=ttk.Frame(root)
    controls.pack(fill='x')
    conn=open_store(Path(db_path))
    account=getpass.getuser()
    cache={}
    surfaced=set()
    alive=[True]

    def refresh(schedule=False):
        if not alive[0]:
            return
        try:
            alerts=list_notifications(conn,account)
            cache.clear()
            cache.update({a['alert_id']:a for a in alerts})
            previous=set(grid.get_children())
            current=set(cache)
            # A snoozed notice leaves the visible list. Once it expires,
            # treat it as newly visible again so the bell fires once.
            surfaced.intersection_update(current)
            for item in previous-current:
                grid.delete(item)
            for alert in alerts:
                aid=alert['alert_id']
                vals=(alert['severity'],alert['summary'],alert['case_id'],
                      '要調査' if alert['delivery_state']=='UNKNOWN' else '保存済',
                      alert['day'])
                if aid in previous:
                    grid.item(aid,values=vals)
                else:
                    grid.insert('','end',iid=aid,values=vals)
            new = current-surfaced
            if new:
                # Never use an always-on-top window that could obscure the
                # operator's work. Bell and lift the local notification center.
                window.bell()
                window.deiconify()
                window.lift()
            surfaced.update(current)
            caption.set(f'未確認 {len(alerts)} 件 / 配信 UNKNOWN は手動照合が必要')
        except Exception:
            caption.set('通知の読込でエラー。DBと権限を確認してください。')
            # No raw email/title or case content is displayed in exceptions.
        finally:
            if alive[0] and schedule:
                window.after(poll_seconds*1000,lambda:refresh(schedule=True))

    def action(choice):
        selected=grid.selection()
        if not selected:
            messagebox.showinfo('選択してください','通知を1件選択してください。')
            return
        alert_id=selected[0]
        alert=cache.get(alert_id)
        if not alert:
            refresh()
            return
        if alert['delivery_state']=='UNKNOWN' and choice=='ACK':
            messagebox.showwarning('配信状態 UNKNOWN','送信結果は未確定です。担当者による照合が必要なため、確認済みにできません。')
            return
        try:
            mark_notification(conn,alert_id,account,choice)
            refresh()
        except (ValueError,RuntimeError) as exc:
            messagebox.showerror('処理できません','通知が更新された可能性があります。再表示して確認してください。')
            refresh()

    ttk.Button(controls,text='確認済み',command=lambda:action('ACK')).pack(side='left',padx=(0,8))
    ttk.Button(controls,text='30分後に再表示',command=lambda:action('SNOOZE')).pack(side='left',padx=(0,8))
    ttk.Button(controls,text='更新',command=refresh).pack(side='left')
    ttk.Label(controls,text='承認・期限確定: 管理職用CLIで実施').pack(side='right')
    def close():
        alive[0]=False
        conn.close()
        window.destroy()
    window.protocol('WM_DELETE_WINDOW',close)
    refresh(schedule=True)
    window.mainloop()


def main():
    import argparse
    parser=argparse.ArgumentParser(description='Windows local notification center; no network or automatic approval')
    parser.add_argument('--db',required=True)
    parser.add_argument('--poll-seconds',type=int,default=15)
    options=parser.parse_args()
    launch(options.db,options.poll_seconds)


if __name__=='__main__':
    main()
