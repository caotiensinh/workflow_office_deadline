"""Optional, read-only Outlook Classic adapter (COM, logged-in Windows).

Not compatible with New Outlook. Nothing is marked as read or modified.
Only anonymous hashes of StoreID + EntryID persist; after an Outlook move
EntryID can change, so cross-folder de-duplication is NOT guaranteed.
"""
from email.message import EmailMessage

from .intake import email_to_case, case_id_for_source


def unread_cases(limit=50, owner='LOCAL_REVIEWER', existing_ids=(), scan_limit=5000):
    if not 1 <= limit <= 200:
        raise ValueError('limit must be 1..200')
    if not limit <= scan_limit <= 10000:
        raise ValueError('scan_limit must cover limit and be <= 10000')
    try:
        import win32com.client
    except ImportError as exc:
        raise RuntimeError('Classic Outlook adapter requires approved pywin32 installation') from exc

    try:
        namespace = win32com.client.Dispatch('Outlook.Application').GetNamespace('MAPI')
        inbox = namespace.GetDefaultFolder(6)
        store_id = str(inbox.StoreID)
        items = inbox.Items
        items.Sort('[ReceivedTime]', True)
        seen = set(existing_ids)
        found = 0
        # Skip previously imported unread emails. Without this, a full batch
        # of 50 old unread emails permanently starves every new import.
        for index in range(1, min(items.Count, scan_limit) + 1):
            if found >= limit:
                break
            item = items.Item(index)
            if item.Class != 43 or not bool(item.UnRead):
                continue
            entry_id = str(item.EntryID or '')
            if not entry_id:
                continue
            source_key = store_id + ':' + entry_id
            opaque_id = case_id_for_source('outlook-classic:' + source_key)
            if opaque_id in seen:
                continue

            message = EmailMessage()
            message['Subject'] = str(item.Subject or '')
            # Outlook EntryID is never stored as a plaintext header.
            message.set_content(str(item.Body or '')[:150_000])
            case = email_to_case(message.as_bytes(), owner=owner, source_key=source_key)
            seen.add(case['case_id'])
            yield case
            found += 1
    except Exception as exc:
        raise RuntimeError('Outlook read failed; no mailbox content logged') from exc
