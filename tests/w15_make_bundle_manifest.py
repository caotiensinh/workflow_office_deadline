"""Create a SHA-256 manifest for a sealed, temporary Windows W15 portable bundle.

Run only on the GitHub-hosted Windows build job, never on an organization
workstation. The self-hosted test verifies every member before any CLI launch.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
from pathlib import Path

GIT_SHA = re.compile(r"^[0-9a-f]{40}$")


def build_manifest(folder, commit):
    folder = Path(folder)
    if not folder.is_dir() or folder.is_symlink():
        raise ValueError("Bundle root must be a regular directory")
    if not isinstance(commit, str) or not GIT_SHA.fullmatch(commit):
        raise ValueError("Explicit 40-hex commit required")
    manifest = folder / "w15_manifest.json"
    if manifest.exists() or manifest.is_symlink():
        raise FileExistsError("Manifest already present")
    members = sorted(p for p in folder.rglob("*") if p.is_file())
    if not 6 <= len(members) <= 250:
        raise ValueError("Unexpected bundle file count")
    files = {}
    for p in members:
        if p.is_symlink():
            raise ValueError("Symlinked bundle source is forbidden")
        rel = p.relative_to(folder).as_posix()
        if ":" in rel or "\\" in rel or ".." in rel.split("/"):
            raise ValueError("Unsafe bundle file name")
        files[rel] = hashlib.sha256(p.read_bytes()).hexdigest()
    for needed in ("python.exe", "python312._pth", "edu_rules.exe",
                   "cases.json", "w15_e2e.py", "edu_workflow/cli.py"):
        if needed not in files:
            raise ValueError("Missing W15 component: " + needed)
    manifest.write_text(json.dumps({"source_commit": commit, "files": files},
                                   ensure_ascii=True, sort_keys=True, indent=2),
                        encoding="utf-8")
    return len(files)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--bundle", required=True)
    ap.add_argument("--commit", required=True)
    args = ap.parse_args()
    print("W15_MANIFEST_FILES:", build_manifest(args.bundle, args.commit))
