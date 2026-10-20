"""W18 final-archive integrity gate. All ZIP fixtures are fictional and local."""
import hashlib
import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
import warnings
import zipfile
from pathlib import Path

from edu_workflow.kit_integrity_w18 import verify

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ('@echo off\nsetlocal DisableDelayedExpansion\n'
            'set "EXPECTED=__EXPECTED_SHA256__"\n'
            'rem W18 fixture: fictional; this file is never executed\n')
EXE = b'MZ' + b'W18 synthetic payload no real executable' * 24
README = '架空GUI UAT - 本番運用不可'.encode('utf-8')


class W18ArchiveIntegrityTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.template = self.root / 'trusted.cmd.in'
        self.template.write_text(TEMPLATE, encoding='utf-8')
        self.path = self.root / 'kit.zip'
        self.exe = EXE
        self.launcher = TEMPLATE.replace('__EXPECTED_SHA256__', hashlib.sha256(EXE).hexdigest().upper()).encode('ascii')

    def members(self):
        return {'EDUFieldUAT.exe': self.exe,
                '00_START_UAT.cmd': self.launcher,
                'W17_README_JP.txt': README}

    def package(self, override=None, extras=None):
        members = self.members()
        members.update(override or {})
        members.update(extras or {})
        with zipfile.ZipFile(self.path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
            for name, content in members.items():
                zf.writestr(name, content)
        return self.path

    def test_valid_archive_does_not_claim_approval(self):
        r = verify(self.package(), self.template)
        self.assertEqual(r['status'], 'W18_ARCHIVE_CONTENT_VERIFIED_NOT_SIGNED')
        self.assertEqual(r['archive_members'], 3)
        for field in ('signed_release_verified', 'actual_physical_gui_uat_verified',
                      'it_approved', 'production_accepted', 'modifies_system'):
            self.assertFalse(r[field])

    def test_checksum_reproducible_without_file_mutation(self):
        self.package()
        before = self.path.read_bytes()
        result = verify(self.path, self.template, hashlib.sha256(before).hexdigest())
        self.assertEqual(result['zip_sha256'], hashlib.sha256(before).hexdigest().upper())
        self.assertEqual(before, self.path.read_bytes())

    def test_expected_sha_mismatch_rejected(self):
        with self.assertRaises(ValueError):
            verify(self.package(), self.template, '0' * 64)

    def test_malformed_expected_sha_rejected(self):
        with self.assertRaises(ValueError):
            verify(self.package(), self.template, 'not-a-sha256')

    def test_executable_modified_after_launcher_built_rejected(self):
        with self.assertRaises(ValueError):
            verify(self.package({'EDUFieldUAT.exe': EXE+b'tamper'}), self.template)

    def test_modified_launcher_after_packaging_rejected(self):
        with self.assertRaises(ValueError):
            verify(self.package({'00_START_UAT.cmd': self.launcher+b'\ncalc.exe\n'}), self.template)

    def test_both_exe_and_launcher_tampered_rejected_by_template(self):
        exe = EXE+b'other'
        new_launcher = self.launcher.replace(hashlib.sha256(EXE).hexdigest().upper().encode('ascii'),
                                             hashlib.sha256(exe).hexdigest().upper().encode('ascii')) + b'\nwhoami\n'
        with self.assertRaises(ValueError):
            verify(self.package({'EDUFieldUAT.exe': exe, '00_START_UAT.cmd': new_launcher}), self.template)

    def test_extra_member_rejected(self):
        with self.assertRaises(ValueError):
            verify(self.package(extras={'surprise.cmd': b'unsafe'}), self.template)

    def test_path_traversal_rejected(self):
        with self.assertRaises(ValueError):
            verify(self.package(extras={'../escape.txt': b'x'}), self.template)

    def test_missing_member_rejected(self):
        with zipfile.ZipFile(self.path, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.writestr('EDUFieldUAT.exe', EXE)
            zf.writestr('00_START_UAT.cmd', self.launcher)
        with self.assertRaises(ValueError):
            verify(self.path, self.template)

    def test_duplicate_member_rejected(self):
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', UserWarning)
            with zipfile.ZipFile(self.package(), 'a') as zf:
                zf.writestr('EDUFieldUAT.exe', EXE)
        with self.assertRaises(ValueError):
            verify(self.path, self.template)

    def test_symlink_rejected(self):
        with zipfile.ZipFile(self.path, 'w') as zf:
            for name, content in self.members().items():
                info = zipfile.ZipInfo(name)
                info.create_system = 3
                info.external_attr = ((stat.S_IFLNK | 0o777) if name == '00_START_UAT.cmd' else (stat.S_IFREG | 0o644)) << 16
                zf.writestr(info, content)
        with self.assertRaises(ValueError):
            verify(self.path, self.template)

    def test_zip_bomb_compression_ratio_rejected(self):
        with self.assertRaises(ValueError):
            verify(self.package({'EDUFieldUAT.exe': b'A' * (2*1024*1024)}), self.template)

    def test_non_utf8_readme_rejected(self):
        with self.assertRaises(ValueError):
            verify(self.package({'W17_README_JP.txt': b'\xff\xfe\xff'}), self.template)

    def test_corrupt_zip_rejected(self):
        self.path.write_bytes(b'not a zip')
        with self.assertRaises(zipfile.BadZipFile):
            verify(self.path, self.template)

    def test_symlink_source_rejected(self):
        self.package()
        link = self.root / 'link.zip'
        try:
            link.symlink_to(self.path)
        except (OSError, NotImplementedError):
            self.skipTest('Symlink forbidden by host')
        with self.assertRaises(ValueError):
            verify(link, self.template)

    def test_cli_invalid_archive_no_path_leak(self):
        self.path.write_bytes(b'wrong')
        proc = subprocess.run([sys.executable, '-m', 'edu_workflow.kit_integrity_w18', '--zip', str(self.path)],
                              cwd=ROOT, env=dict(os.environ, PYTHONPATH=str(ROOT / 'python')),
                              capture_output=True, text=True)
        self.assertEqual(proc.returncode, 2)
        self.assertEqual(proc.stderr.strip(), 'W18_ZIP_REJECTED')
        self.assertNotIn(str(self.path), proc.stderr)


if __name__ == '__main__':
    unittest.main()
