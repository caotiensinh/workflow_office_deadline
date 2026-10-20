"""W5 Tk controller tests without requiring a real logged-in desktop.

These tests exercise *our* UI callbacks against synthetic notifications.
They are NOT visual/window-placement acceptance.
"""
from __future__ import annotations
import sys
import types
import unittest
from unittest.mock import patch
from edu_workflow import desktop_app


class FakeConn:
    def __init__(self):
        self.closed = False
    def close(self):
        self.closed = True


class Widget:
    def __init__(self,*args,**kwargs):
        self.text=kwargs.get("text","")
    def pack(self,*args,**kwargs):
        return None
    def heading(self,*args,**kwargs):
        return None
    def column(self,*args,**kwargs):
        return None


class FakeStringVar:
    latest = None
    def __init__(self,*args,**kwargs):
        self.value=kwargs.get("value","")
        FakeStringVar.latest = self
    def set(self,value):
        self.value=value


class FakeTree(Widget):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.items={}
        self.chosen=()
    def get_children(self):
        return tuple(self.items)
    def delete(self,key):
        self.items.pop(key,None)
    def item(self,key,**kwargs):
        self.items[key]=kwargs["values"]
    def insert(self,parent,index,*,iid,values):
        self.items[iid]=values
    def selection(self):
        return self.chosen


class FakeButton(Widget):
    all={}
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.command=kwargs["command"]
        self.all[self.text]=self


class FakeWindow:
    def __init__(self):
        self.bells=0
        self.after_calls=[]
        self.protocols={}
        self.actions=None
        self.closed=False
    def title(self,*args): pass
    def geometry(self,*args): pass
    def minsize(self,*args): pass
    def bell(self): self.bells+=1
    def deiconify(self): pass
    def lift(self): pass
    def after(self,delay,callback): self.after_calls.append((delay,callback))
    def protocol(self,label,callback): self.protocols[label]=callback
    def mainloop(self):
        assert self.actions is not None
        self.actions()
    def destroy(self): self.closed=True


def notification(code="VERIFY_DEADLINE",state="SENT",id="a"*64):
    return {"alert_id":id,"case_id":"SYNTH-ONLY","severity":"INFO","code":code,
            "summary":"期限の確認が必要","day":"2026-10-19",
            "delivery_state":state,"snoozed_until":None}


class W5UIControllerTests(unittest.TestCase):
    def test_missing_database_rejected_before_starting_gui(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as folder:
            missing=Path(folder)/"absent.sqlite3"
            with (patch.object(desktop_app,"_interactive_desktop_available",return_value=True),
                  patch.object(desktop_app,"open_store") as store):
                with self.assertRaises(FileNotFoundError):
                    desktop_app.launch(missing)
                store.assert_not_called()
            self.assertFalse(missing.exists())

    def test_invalid_database_rejected_without_modifying_file(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as folder:
            broken=Path(folder)/"invalid.sqlite3"
            broken.write_bytes(b"Not SQLite")
            with (patch.object(desktop_app,"_interactive_desktop_available",return_value=True),
                  patch.object(desktop_app,"open_store") as store):
                with self.assertRaisesRegex(ValueError,"not a valid SQLite"):
                    desktop_app.launch(broken)
                store.assert_not_called()
            self.assertEqual(broken.read_bytes(),b"Not SQLite")

    def test_session_zero_must_refuse_gui(self):
        with patch.object(desktop_app,"_interactive_desktop_available",return_value=False):
            with self.assertRaisesRegex(RuntimeError,"Session 0"):
                desktop_app.launch("nonexistent.sqlite3")

    def _run_ui(self,action,rows,*,bell_failure=False):
        FakeButton.all={}
        window=FakeWindow()
        if bell_failure:
            def no_audio():
                raise OSError("Synthetic audio device unavailable")
            window.bell=no_audio
        fakeconn=FakeConn()
        events=[]
        module=types.ModuleType("tkinter")
        module.Tk=lambda:window
        module.StringVar=FakeStringVar
        module.TclError=RuntimeError
        ttk=types.ModuleType("tkinter.ttk")
        ttk.Frame=Widget
        ttk.Label=Widget
        ttk.Treeview=FakeTree
        ttk.Button=FakeButton
        boxes=types.ModuleType("tkinter.messagebox")
        boxes.showwarning=lambda *a,**kw:events.append(("warning",a))
        boxes.showinfo=lambda *a,**kw:events.append(("info",a))
        boxes.showerror=lambda *a,**kw:events.append(("error",a))
        module.ttk=ttk
        module.messagebox=boxes
        with (patch.dict(sys.modules,{"tkinter":module,"tkinter.ttk":ttk,
                                      "tkinter.messagebox":boxes}),
              patch.object(desktop_app,"_interactive_desktop_available",return_value=True),
              patch.object(desktop_app,"_require_existing_workflow_db",return_value="synthetic.sqlite3"),
              patch.object(desktop_app,"open_store",return_value=fakeconn),
              patch.object(desktop_app,"getpass") as getpass,
              patch.object(desktop_app,"list_notifications",side_effect=lambda *_:list(rows)),
              patch.object(desktop_app,"mark_notification") as mark):
            getpass.getuser.return_value="test-user"
            def run():
                tree=next(x for x in FakeTreeInstances.instances)
                action(window,tree,rows,events,mark)
                window.protocols["WM_DELETE_WINDOW"]()
            window.actions=run
            FakeTreeInstances.instances=[]
            original_init=FakeTree.__init__
            def capture(self,*args,**kwargs):
                original_init(self,*args,**kwargs)
                FakeTreeInstances.instances.append(self)
            with patch.object(FakeTree,"__init__",capture):
                desktop_app.launch("synthetic.sqlite3",poll_seconds=5)
        self.assertTrue(fakeconn.closed)
        self.assertTrue(window.closed)
        return events

    def test_refresh_after_snooze_expiry_bells_once_again(self):
        rows=[notification()]
        def actions(window,tree,visible,events,mark):
            self.assertEqual(window.bells,1)
            self.assertEqual(len(tree.items),1)
            # Refresh unchanged: no extra bell.
            FakeButton.all["更新"].command()
            self.assertEqual(window.bells,1)
            visible.clear()
            FakeButton.all["更新"].command()
            self.assertEqual(window.bells,1)
            visible.append(notification())  # Snooze expired, visible again.
            FakeButton.all["更新"].command()
            self.assertEqual(window.bells,2)
            self.assertEqual(len(tree.items),1)
            FakeButton.all["更新"].command()
            self.assertEqual(window.bells,2)
            mark.assert_not_called()
        self._run_ui(actions,rows)

    def test_missing_sound_device_keeps_inbox_visible(self):
        rows=[notification()]
        def actions(window,tree,visible,events,mark):
            self.assertEqual(set(tree.items), {"a"*64})
            self.assertIn("未確認 1 件", FakeStringVar.latest.value)
            FakeButton.all["更新"].command()
            self.assertEqual(set(tree.items), {"a"*64})
            self.assertIn("未確認 1 件", FakeStringVar.latest.value)
            self.assertEqual(events, [])
            mark.assert_not_called()
        self._run_ui(actions,rows,bell_failure=True)

    def test_ack_never_calls_approve(self):
        rows=[notification()]
        def actions(window,tree,visible,events,mark):
            tree.chosen=(rows[0]["alert_id"],)
            FakeButton.all["確認済み"].command()
            mark.assert_called_once()
            args=mark.call_args.args
            self.assertEqual(args[3],"ACK")
            self.assertEqual(len(args),4)
        self._run_ui(actions,rows)

    def test_unknown_cannot_ack_from_tk(self):
        rows=[notification(state="UNKNOWN")]
        def actions(window,tree,visible,events,mark):
            tree.chosen=(rows[0]["alert_id"],)
            FakeButton.all["確認済み"].command()
            mark.assert_not_called()
            self.assertEqual(events[0][0],"warning")
        self._run_ui(actions,rows)


    def test_snooze_button_is_visibility_only(self):
        rows=[notification()]
        def actions(window,tree,visible,events,mark):
            tree.chosen=(rows[0]["alert_id"],)
            FakeButton.all["30分後に再表示"].command()
            mark.assert_called_once()
            self.assertEqual(mark.call_args.args[3],"SNOOZE")
        self._run_ui(actions,rows)

    def test_ack_requires_selected_notice(self):
        rows=[notification()]
        def actions(window,tree,visible,events,mark):
            FakeButton.all["確認済み"].command()
            mark.assert_not_called()
            self.assertEqual(events[0][0],"info")
        self._run_ui(actions,rows)

    def test_gui_bundle_preflight_writes_file_without_opening_window(self):
        import json
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as temp:
            dest=Path(temp)/"result.json"
            with (patch.object(sys,"argv",["EDUNotifications","--db","synthetic.sqlite",
                                           "--preflight-file",str(dest)]),
                  patch.object(desktop_app,"_interactive_desktop_available",return_value=False),
                  patch.dict(sys.modules,{"tkinter":types.ModuleType("tkinter")})):
                desktop_app.main()
            report=json.loads(dest.read_text(encoding="utf-8"))
            self.assertEqual(report["packaged_entrypoint"],"OK")
            self.assertTrue(report["tk_importable"])
            self.assertFalse(report["interactive_user_session"])


class FakeTreeInstances:
    instances=[]


if __name__=="__main__":
    unittest.main()
