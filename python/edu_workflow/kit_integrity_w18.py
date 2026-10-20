"""W18 read-only integrity inspection of the final fictional Windows UAT ZIP.

The original W17 launcher has a SHA-256 of the EXE. This module checks the
*final archive*, its member layout, the EXE digest and the exact approved
launcher template. No ZIP extraction, execution, Windows probing or approvals.
Neither a content hash nor this inspector establishes publisher identity.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import stat
import sys
import zipfile
from pathlib import Path

MEMBERS = frozenset({"EDUFieldUAT.exe", "00_START_UAT.cmd", "W17_README_JP.txt"})
LIMITS = {"EDUFieldUAT.exe": 150 * 1024 * 1024,
          "00_START_UAT.cmd": 16 * 1024,
          "W17_README_JP.txt": 64 * 1024}
MAX_ARCHIVE = 175 * 1024 * 1024
READ_SIZE = 1024 * 1024
ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = ROOT / "windows" / "W17_START_UAT.cmd.in"


def _digest(fileobj, size_limit):
    digest = hashlib.sha256()
    total = 0
    chunks = []
    while True:
        chunk = fileobj.read(READ_SIZE)
        if not chunk:
            break
        total += len(chunk)
        if total > size_limit:
            raise ValueError("Archive member size exceeds limit")
        digest.update(chunk)
        if size_limit < READ_SIZE:
            chunks.append(chunk)
    return digest.hexdigest().upper(), b"".join(chunks)


def _line_endings(s):
    return s.replace("\r\n", "\n").rstrip("\n")


def verify(archive, template=TEMPLATE, expected_zip_sha256=None):
    """Verify an archive without writing to disk; returns only safe hashes.

    Raises ValueError or OSError on all non-conforming inputs. Caller must
    NEVER present the result as Authenticode, human GUI UAT or IT signoff.
    """
    source = Path(archive)
    if source.is_symlink() or not source.is_file():
        raise ValueError("Archive must be a regular local file")
    if source.stat().st_size == 0 or source.stat().st_size > MAX_ARCHIVE:
        raise ValueError("Archive size outside allowed range")
    if expected_zip_sha256 is not None and not re.fullmatch(r"[a-fA-F0-9]{64}", expected_zip_sha256):
        raise ValueError("Invalid expected checksum")
    with source.open("rb") as inp:
        zip_hash, _ = _digest(inp, MAX_ARCHIVE)
    if expected_zip_sha256 is not None and zip_hash != expected_zip_sha256.upper():
        raise ValueError("ZIP SHA-256 differs from expected build artifact")
    with zipfile.ZipFile(source, "r") as zf:
        entries = zf.infolist()
        names = [entry.filename for entry in entries]
        if len(entries) != len(MEMBERS) or set(names) != MEMBERS:
            raise ValueError("Unexpected, duplicate or missing archive members")
        for entry in entries:
            mode = (entry.external_attr >> 16) & 0xFFFF
            if entry.is_dir() or stat.S_ISLNK(mode) or entry.flag_bits & 1:
                raise ValueError("Directory, symlink or encrypted ZIP member")
            if entry.file_size > LIMITS[entry.filename]:
                raise ValueError("Archive member is too large")
            if entry.compress_size == 0 or entry.file_size > entry.compress_size * 300:
                raise ValueError("Unsafe archive compression ratio")
        digests = {}
        contents = {}
        for member in MEMBERS:
            with zf.open(member, "r") as inp:
                digests[member], contents[member] = _digest(inp, LIMITS[member])
    try:
        launcher = contents["00_START_UAT.cmd"].decode("ascii")
        source_template = Path(template).read_text(encoding="utf-8")
        contents["W17_README_JP.txt"].decode("utf-8")
    except (UnicodeError, OSError) as exc:
        raise ValueError("Launcher, template or README cannot be decoded") from exc
    expected = re.findall(r'^set "EXPECTED=([A-Fa-f0-9]{64})"$',
                          _line_endings(launcher), flags=re.MULTILINE)
    if len(expected) != 1 or expected[0].upper() != digests["EDUFieldUAT.exe"]:
        raise ValueError("Launcher EXE hash mismatch")
    if source_template.count("__EXPECTED_SHA256__") != 1:
        raise ValueError("Unsafe trusted launcher template")
    if _line_endings(launcher) != _line_endings(
            source_template.replace("__EXPECTED_SHA256__", expected[0])):
        raise ValueError("Launcher differs from trusted source template")
    return {
        "status": "W18_ARCHIVE_CONTENT_VERIFIED_NOT_SIGNED",
        "zip_sha256": zip_hash,
        "exe_sha256": digests["EDUFieldUAT.exe"],
        "archive_members": len(entries),
        "signed_release_verified": False,
        "actual_physical_gui_uat_verified": False,
        "it_approved": False,
        "production_accepted": False,
        "modifies_system": False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="Read-only ZIP verifier; NOT a signature or GUI UAT")
    parser.add_argument("--zip", required=True)
    parser.add_argument("--expected-zip-sha256")
    args = parser.parse_args(argv)
    try:
        result = verify(args.zip, expected_zip_sha256=args.expected_zip_sha256)
    except (OSError, ValueError, zipfile.BadZipFile, RuntimeError, EOFError):
        print("W18_ZIP_REJECTED", file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
