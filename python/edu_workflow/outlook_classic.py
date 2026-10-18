"""Optional read-only Classic Outlook COM bridge.
Requires Windows, an interactive Outlook profile, pywin32 and organizational permission.
New Outlook has no Outlook Object Model / COM support.
"""
from .intake import email_to_case


def unread_cases(limit=50,owner='LOCAL_REVIEWER'):
    try:
        import win32com.client
    except ImportError as e:
        raise RuntimeError('Classic Outlook adapter requires approved pywin32 installation') from e
    if not 1 <= limit <= 200: raise ValueError('limit must be 1..200')
    ns=win32com.client.Dispatch('Outlook.Application').GetNamespace('MAPI')
    inbox=ns.GetDefaultFolder(6)
    items=inbox.Items
    items.Sort('[ReceivedTime]',True)
    count=0
    for idx in range(1,items.Count+1):
        if count>=limit: break
        obj=items.Item(idx)
        try:
            if obj.Class!=43 or not bool(obj.UnRead): continue
            # Convert fields to an ephemeral RFC822 representation; no raw content on disk.
            from email.message import EmailMessage
            msg=EmailMessage()
            msg['Subject']=str(obj.Subject or '')
            msg['Message-ID']=str(obj.EntryID or '')
            msg.set_content(str(obj.Body or '')[:150_000])
            case=email_to_case(msg.as_bytes(),owner=owner)
            yield case
            count+=1
        except Exception:
            # Bad item never stops all ingestion; error is surfaced via bounded warning.
            raise RuntimeError('Outlook read failed; no mailbox content logged')
