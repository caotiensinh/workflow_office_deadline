"""Real Tk widget smoke with synthetic data in an isolated Xvfb display.

Runs on Linux with xvfb-run. Tests a true Tk window, Treeview, buttons and
WM_DELETE_WINDOW cleanup. Never accesses a user's screen, Outlook or network.
This does not assert visual GUI acceptance on interactive Windows.
"""
from __future__ import annotations
import sqlite3
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

from edu_workflow import desktop_app


class FakeConnection:
    closed = False
    def close(self):
        self.closed = True


def children(widget):
    yield widget
    for child in widget.winfo_children():
        yield from children(child)


def main():
    import tkinter as tk
    from tkinter import ttk

    if sys.platform == 'win32':
        raise RuntimeError('This virtual-X11 display test is for Linux; Windows requires interactive QA')

    with tempfile.TemporaryDirectory(prefix='w5-tk-smoke-') as folder:
        db = Path(folder) / 'synthetic.sqlite3'
        with sqlite3.connect(db) as sqlite:
            sqlite.execute('CREATE TABLE synthetic_scope(value TEXT)')

        fake = FakeConnection()
        pending = [{
            'alert_id': 'f' * 64, 'case_id': 'SYNTH-ONLY',
            'severity': 'WARNING', 'summary': '期限の確認が必要',
            'code': 'VERIFY_DEADLINE', 'delivery_state': 'SENT',
            'day': '2026-10-20'
        }]
        actions = []
        real_tk = tk.Tk
        windows = []

        def create_test_window(*args, **kwargs):
            root = real_tk(*args, **kwargs)
            windows.append(root)
            hooks = {}
            real_protocol = root.protocol

            def protocol(name, callback=None):
                if callback is not None:
                    hooks[name] = callback
                return real_protocol(name, callback)

            root.protocol = protocol

            def exercise():
                widgets = list(children(root))
                trees = [w for w in widgets if isinstance(w, ttk.Treeview)]
                buttons = {w.cget('text'): w for w in widgets if isinstance(w, ttk.Button)}
                assert len(trees) == 1
                tree = trees[0]
                assert len(tree.get_children()) == 1, 'Expected one synthetic notification'
                assert '通知センター' in root.title()
                assert '確認済み' in buttons and '30分後に再表示' in buttons
                assert root.winfo_width() >= 580 and root.winfo_height() >= 350
                tree.selection_set(pending[0]['alert_id'])
                buttons['確認済み'].invoke()
                assert actions == [('f' * 64, 'ACK')], actions
                assert len(tree.get_children()) == 0, 'ACK did not clear visible notice'
                root.after(50, hooks['WM_DELETE_WINDOW'])

            root.after(350, exercise)
            return root

        def acknowledge(conn, alert_id, actor, choice):
            actions.append((alert_id, choice))
            pending.clear()
            return True

        with (patch.object(tk, 'Tk', new=create_test_window),
              patch.object(desktop_app, 'open_store', return_value=fake),
              patch.object(desktop_app, 'list_notifications', side_effect=lambda *_: list(pending)),
              patch.object(desktop_app, 'mark_notification', side_effect=acknowledge)):
            desktop_app.launch(db, poll_seconds=5)

        assert len(windows) == 1 and fake.closed and actions
        print('W5_REAL_TK_SMOKE_PASS: window, Japanese labels, Treeview, ACK and close verified')


if __name__ == '__main__':
    main()
