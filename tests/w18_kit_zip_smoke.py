"""W18 Windows CI final-bundle smoke: inspect a real ZIP, never launch GUI."""
import argparse
import hashlib
import sys
import tempfile
import zipfile
from pathlib import Path

from edu_workflow.kit_integrity_w18 import verify


def run(archive):
    source = Path(archive)
    before = source.read_bytes()
    result = verify(source)
    if result['archive_members'] != 3 or result['signed_release_verified'] or result['actual_physical_gui_uat_verified']:
        raise AssertionError('Unsafe positive result')
    with zipfile.ZipFile(source) as inp:
        members = {name: inp.read(name) for name in inp.namelist()}
    if len(members) != 3:
        raise AssertionError('Archive has unexpected entries')
    with tempfile.TemporaryDirectory() as td:
        for kind in ('exe', 'launcher', 'extra'):
            case = dict(members)
            if kind == 'exe':
                case['EDUFieldUAT.exe'] += b'W18_INTENTIONAL_FINAL_ZIP_TAMPER'
            elif kind == 'launcher':
                case['00_START_UAT.cmd'] += b'\nrem W18_INTENTIONAL_FINAL_ZIP_TAMPER\n'
            else:
                case['W18_EXTRA_UNEXPECTED.txt'] = b'x'
            modified = Path(td) / (kind + '.zip')
            with zipfile.ZipFile(modified, 'w', compression=zipfile.ZIP_DEFLATED) as out:
                for name, value in case.items():
                    out.writestr(name, value)
            try:
                verify(modified)
            except ValueError:
                continue
            raise AssertionError('W18 final ZIP tamper was not rejected: ' + kind)
    if hashlib.sha256(source.read_bytes()).digest() != hashlib.sha256(before).digest():
        raise AssertionError('Original signed-in kit mutated')
    print('W18_FINAL_ZIP_INTEGRITY_AND_3_NEGATIVE_TAMPERS_PASS_NOT_SIGNED_OR_GUI_UAT')
    print('W18_FINAL_ZIP_SHA256=' + result['zip_sha256'])


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--zip', required=True)
    args = parser.parse_args(argv)
    run(args.zip)
    return 0


if __name__ == '__main__':
    sys.exit(main())
