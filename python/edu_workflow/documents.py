"""Structural DOCX checker. No semantic, regulatory or pedagogic compliance claims."""
import hashlib
import json
import zipfile
from pathlib import Path
from xml.etree import ElementTree

W_NS='{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'

def validate_docx(path, criteria):
    path=Path(path)
    if path.stat().st_size>10_000_000: raise ValueError('document too large')
    with zipfile.ZipFile(path) as z:
        contents=z.namelist()
        if len(contents)>2500: raise ValueError('too many DOCX archive members')
        meta=z.getinfo('word/document.xml')
        if meta.file_size>10_000_000: raise ValueError('expanded document too large')
        xml=z.read(meta)
    root=ElementTree.fromstring(xml)
    text=' '.join((el.text or '') for el in root.iter(W_NS+'t'))
    required=criteria['required_phrases']
    if not isinstance(required,list) or not required or not all(isinstance(x,str) and x for x in required):
        raise ValueError('required_phrases must be nonempty strings')
    return {'document_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
            'check_type':'structure_only','passed':all(x in text for x in required),
            'found':[x for x in required if x in text], 'missing':[x for x in required if x not in text],
            'warning':'Does NOT verify factual claims, personnel decisions or legal validity.'}
