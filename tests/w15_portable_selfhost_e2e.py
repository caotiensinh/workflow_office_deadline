"""W15 real Windows self-hosted E2E, deliberately bundled and synthetic-only.

This module is packaged by a GitHub-hosted Windows runner together with portable
CPython, a tested native Rust binary, application modules and fake cases.json.
No Outlook, SMTP, Task Scheduler, GUI, human approval or corporate databases.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

NOW = "2026-10-19T09:00:00+09:00"
MAX_FILES = 250


def _digest(p):
    h = hashlib.sha256()
    with p.open("rb") as fd:
        for block in iter(lambda: fd.read(65536), b""):
            h.update(block)
    return h.hexdigest()


def _ensure(condition, code):
    if not condition:
        raise RuntimeError("W15_E2E_BLOCKED: " + code)


def verify_bundle(base):
    manifest = json.loads((base / "w15_manifest.json").read_text(encoding="utf-8-sig"))
    _ensure(set(manifest) == {"source_commit", "files"}, "MANIFEST_FORMAT")
    _ensure(manifest["source_commit"] == os.environ.get("GITHUB_SHA"), "SHA_NOT_PINNED")
    files = manifest["files"]
    _ensure(isinstance(files, dict) and 6 <= len(files) <= MAX_FILES,
            "MANIFEST_FILE_COUNT")
    _ensure(set(["python.exe", "python312._pth", "edu_rules.exe",
                 "cases.json", "w15_e2e.py", "edu_workflow/cli.py"]) <= set(files),
            "MISSING_RUNTIME_FILES")
    for rel, digest in files.items():
        _ensure(isinstance(rel, str) and not rel.startswith(("/", "\\"))
                and "\\" not in rel and ":" not in rel
                and all(part not in ("", ".", "..") for part in rel.split("/")),
                "UNSAFE_MANIFEST_PATH")
        path = base.joinpath(*rel.split("/"))
        _ensure(not path.is_symlink() and path.is_file(), "BUNDLE_FILE_MISSING")
        _ensure(isinstance(digest, str) and len(digest) == 64
                and _digest(path) == digest.lower(), "BUNDLE_SHA256_MISMATCH")
    # All package source files must be in the signed-by-CI hash manifest.
    for p in (base / "edu_workflow").rglob("*.py"):
        _ensure(p.relative_to(base).as_posix() in files, "SOURCE_NOT_IN_MANIFEST")
    return manifest["source_commit"]


def _invoke(base, db, args):
    # Fixed portable Python and offline-only CLI actions; no shell evaluation.
    cmd = [str(base / "python.exe"), "-m", "edu_workflow.cli",
           "--db", str(db), *map(str, args)]
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    for key in list(env):
        if key.startswith(("EDU_SMTP_", "HTTP_PROXY", "HTTPS_PROXY",
                           "ALL_PROXY", "AWS_", "AZURE_", "GOOGLE_")):
            env.pop(key, None)
    p = subprocess.run(cmd, cwd=str(base), env=env, capture_output=True,
                       text=True, encoding="utf-8", errors="replace",
                       timeout=90, check=False)
    _ensure(p.returncode == 0, "CLI_COMMAND_FAILED")
    try:
        return json.loads(p.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError("W15_E2E_BLOCKED: NON_JSON_CLI_RESULT") from exc


def run(root):
    _ensure(sys.platform == "win32", "WINDOWS_REQUIRED")
    base = Path(__file__).resolve().parent
    _ensure(Path(sys.executable).resolve() == (base / "python.exe").resolve(),
            "PORTABLE_PYTHON_REQUIRED")
    allowed = os.environ.get("RUNNER_TEMP")
    _ensure(bool(allowed), "RUNNER_TEMP_REQUIRED")
    allowed = Path(allowed).resolve()
    root = Path(root).resolve()
    _ensure(root != allowed and allowed in root.parents, "OUTPUT_OUTSIDE_RUNNER_TEMP")
    _ensure(root.parent == base, "OUTPUT_NOT_BUNDLE_CHILD")
    _ensure(not root.exists(), "OUTPUT_ALREADY_EXISTS")
    sha = verify_bundle(base)
    root.mkdir(parents=False, exist_ok=False)
    db = root / "workflow.sqlite3"
    alerts = root / "notifications"
    fixture = base / "cases.json"
    rust = base / "edu_rules.exe"

    imported = _invoke(base, db, ["import-json", "--file", fixture])
    _ensure(imported["imported"] == 5, "IMPORT_COUNT")
    tick1 = _invoke(base, db, ["tick", "--backend", "rust",
                              "--rust-bin", rust, "--at", NOW])
    _ensure(tick1["backend"] == "rust" and tick1["alerts_added"] == 6,
            "RUST_ALERT_COUNT")
    sent1 = _invoke(base, db, ["deliver", "--channel", "file", "--out-dir", alerts])
    _ensure(sent1["sent"] == 6 and sent1["unknown"] == 0, "FILE_DELIVERY")

    file_list = sorted(alerts.glob("*.json"))
    _ensure(len(file_list) == 6, "FILE_SPOOL_COUNT")
    fingerprints = {p.name: _digest(p) for p in file_list}
    for p in file_list:
        notice = json.loads(p.read_text(encoding="utf-8"))
        _ensure(p.stem == notice.get("id"), "OUTBOX_FILE_ID")

    tick2 = _invoke(base, db, ["tick", "--backend", "rust",
                              "--rust-bin", rust, "--at", NOW])
    sent2 = _invoke(base, db, ["deliver", "--channel", "file", "--out-dir", alerts])
    imported2 = _invoke(base, db, ["import-json", "--file", fixture])
    _ensure(tick2["alerts_added"] == 0 and sent2["sent"] == 0
            and sent2["unknown"] == 0 and imported2["imported"] == 0,
            "NON_IDEMPOTENT_REPEAT")
    _ensure(fingerprints == {p.name: _digest(p) for p in alerts.glob("*.json")},
            "SECOND_RUN_MODIFIED_FILES")

    conn = sqlite3.connect(f"file:{db.as_posix()}?mode=ro", uri=True)
    try:
        counts = {
            "cases": conn.execute("SELECT COUNT(*) FROM cases").fetchone()[0],
            "alerts": conn.execute("SELECT COUNT(*) FROM alerts").fetchone()[0],
            "sent": conn.execute(
                "SELECT COUNT(*) FROM alerts WHERE state='SENT'").fetchone()[0],
            "unknown": conn.execute(
                "SELECT COUNT(*) FROM alerts WHERE state='UNKNOWN'").fetchone()[0],
            "decisions": conn.execute("SELECT COUNT(*) FROM decisions").fetchone()[0],
            "audit_imported": conn.execute(
                "SELECT COUNT(*) FROM audit WHERE event='IMPORTED'").fetchone()[0],
        }
    finally:
        conn.close()
    _ensure(counts == {"cases": 5, "alerts": 6, "sent": 6, "unknown": 0,
                       "decisions": 0, "audit_imported": 5},
            "PERSISTED_STATE_MISMATCH")

    # Reports contain only safe counters and cryptographic source identifiers.
    report = {
        "status": "W15_REAL_SELFHOST_CMD_E2E_PASS",
        "source_commit": sha,
        "python_portable": True,
        "native_rust_invoked": True,
        "runner_label_verification": "CHECK_GITHUB_JOB_RUNNER_METADATA",
        "counts": counts,
        "file_notices": len(fingerprints),
        "second_cycle_idempotent": True,
        "no_human_approvals": True,
        "outlook_accessed": False,
        "smtp_used": False,
        "task_scheduler_changed": False,
        "execution_policy_changed": False,
        "gui_accepted": False,
        "production_accepted": False,
    }
    target = root / "result.json"
    with target.open("x", encoding="utf-8") as fd:
        json.dump(report, fd, ensure_ascii=True, sort_keys=True, indent=2)
        fd.write("\n")
    print("W15_REAL_SELFHOST_CMD_E2E_PASS", flush=True)
    print(json.dumps({"cases": counts["cases"], "alerts": counts["alerts"],
                      "sent": counts["sent"], "unknown": counts["unknown"],
                      "decisions": counts["decisions"]}, sort_keys=True), flush=True)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--root", required=True)
    args = p.parse_args()
    try:
        run(args.root)
    except (RuntimeError, OSError, ValueError, sqlite3.Error) as exc:
        # No raw file paths, source payloads, usernames or secrets in logs.
        label = str(exc)
        if not label.startswith("W15_E2E_BLOCKED:"):
            label = "W15_E2E_BLOCKED: UNEXPECTED_RUNTIME_FAILURE"
        print(label, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
