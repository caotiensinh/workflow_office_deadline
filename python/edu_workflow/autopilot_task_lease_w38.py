"""W38 durable SQLite task leases for bounded unattended proposal workers.

- Persisted local state survives process/host restart when placed on persistent
  filesystem. Hosted GitHub runner ephemeral disks do not satisfy this.
- BEGIN IMMEDIATE + owner fencing token prevent two workers from claiming the
  same task or an expired owner from completing a reclaimed task.
- A lease renews ONLY when genuine token fragment count increases, and cannot
  exceed the absolute task budget; never use an idle clock tick as progress.
- DB stores approved task ID, canonical task digest, lease metadata and output
  SHA256 only; no model output, prompts, secrets, production or employee data.
- This is local execution control, NOT approval or model-authored code merge.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import sqlite3

from .autopilot_worker_w27 import safe_tasks

MIN_TTL = 30
MAX_TTL = 180
MAX_LIFETIME = 600
MAX_ATTEMPTS = 2
ID_PATTERN = re.compile(r"W27-[A-Z0-9]{2,8}\Z")
OWNER_PATTERN = re.compile(r"[A-Za-z0-9_-]{4,80}\Z")
DIGEST_PATTERN = re.compile(r"[0-9a-f]{64}\Z")


def task_digest(task):
    if (not isinstance(task, dict) or task.get("kind") != "AUTO_PROPOSAL"
            or task.get("approval_required") is not False
            or not isinstance(task.get("id"), str)
            or not ID_PATTERN.fullmatch(task["id"])):
        raise ValueError("Unapproved or unsafe task")
    raw = json.dumps(task, sort_keys=True, ensure_ascii=True,
                     separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _time(value):
    if type(value) is not int or value < 0:
        raise ValueError("Invalid clock")
    return value


class LeaseStore:
    def __init__(self, db_path):
        path = Path(db_path)
        if (not path.is_absolute() or path.suffix != ".sqlite3"
                or path.is_symlink() or not path.parent.is_dir()
                or path.parent.is_symlink()
                or (path.exists() and not path.is_file())):
            raise ValueError("Unsafe state database path")
        self.path = path
        with self._connect() as con:
            con.execute("""CREATE TABLE IF NOT EXISTS lease_tasks (
                task_id TEXT PRIMARY KEY,
                task_digest TEXT NOT NULL,
                state TEXT NOT NULL CHECK(state IN ('PENDING','LEASED','DONE','FAILED')),
                owner TEXT, token TEXT, started INTEGER, deadline INTEGER,
                attempts INTEGER NOT NULL DEFAULT 0,
                chunks INTEGER NOT NULL DEFAULT 0,
                result_digest TEXT,
                finished INTEGER
            )""")
            con.execute("PRAGMA user_version")
            cols = {row[1] for row in con.execute("PRAGMA table_info(lease_tasks)")}
            if cols != {"task_id", "task_digest", "state", "owner", "token",
                        "started", "deadline", "attempts", "chunks",
                        "result_digest", "finished"}:
                raise ValueError("Unknown lease schema")

    def _connect(self):
        # No callback executes arbitrary SQL; only trusted schema and params.
        con = sqlite3.connect(str(self.path), timeout=8)
        con.execute("PRAGMA busy_timeout=8000")
        con.execute("PRAGMA journal_mode=WAL")
        con.execute("PRAGMA synchronous=FULL")
        return con

    def seed(self, backlog):
        tasks = [t for t in safe_tasks(backlog) if t["kind"] == "AUTO_PROPOSAL"]
        if not tasks:
            raise ValueError("No approved proposal tasks")
        with self._connect() as con:
            con.execute("BEGIN IMMEDIATE")
            for task in tasks:
                name, digest = task["id"], task_digest(task)
                row = con.execute(
                    "SELECT task_digest FROM lease_tasks WHERE task_id=?", (name,)
                ).fetchone()
                if row and row[0] != digest:
                    raise ValueError("Backlog task changed after lease registration")
                con.execute("""INSERT OR IGNORE INTO lease_tasks
                    (task_id,task_digest,state,attempts,chunks)
                    VALUES (?,?,'PENDING',0,0)""", (name, digest))
        return len(tasks)

    def claim(self, task, owner, *, now, ttl=165):
        now = _time(now)
        if type(ttl) is not int or not MIN_TTL <= ttl <= MAX_TTL:
            raise ValueError("Unsafe lease duration")
        if not isinstance(owner, str) or not OWNER_PATTERN.fullmatch(owner):
            raise ValueError("Unsafe lease owner")
        ident, digest = task["id"], task_digest(task)
        with self._connect() as con:
            con.execute("BEGIN IMMEDIATE")
            row = con.execute("""SELECT task_digest,state,attempts,deadline
                                FROM lease_tasks WHERE task_id=?""",
                              (ident,)).fetchone()
            if row is None or row[0] != digest:
                raise ValueError("Task not registered in authoritative backlog")
            state, attempts, deadline = row[1:]
            if state in ("DONE", "FAILED") or (state == "LEASED" and
                    (type(deadline) is not int or deadline > now)):
                return None
            if attempts >= MAX_ATTEMPTS:
                con.execute("""UPDATE lease_tasks
                    SET state='FAILED',owner=NULL,token=NULL,deadline=NULL
                    WHERE task_id=?""", (ident,))
                return None
            token = secrets.token_hex(16)
            con.execute("""UPDATE lease_tasks SET
                state='LEASED', owner=?, token=?, started=?, deadline=?,
                attempts=?, chunks=0 WHERE task_id=?""",
                (owner, token, now, now + ttl, attempts + 1, ident))
            return {"task_id": ident, "owner": owner, "token": token,
                    "attempt": attempts+1, "expires_at": now+ttl}

    def _active(self, con, lease, now):
        now = _time(now)
        if (not isinstance(lease, dict)
                or set(lease) != {"task_id", "owner", "token", "attempt", "expires_at"}
                or type(lease["attempt"]) is not int
                or not isinstance(lease["token"], str)):
            raise ValueError("Malformed owner lease")
        row = con.execute("""SELECT state,owner,token,started,deadline,
                                attempts,chunks FROM lease_tasks WHERE task_id=?""",
                          (lease["task_id"],)).fetchone()
        if (not row or row[0] != "LEASED" or row[1] != lease["owner"]
                or row[2] != lease["token"] or row[5] != lease["attempt"]
                or row[4] is None or row[4] <= now
                or row[3] is None or now < row[3]
                or now >= row[3] + MAX_LIFETIME):
            raise ValueError("Expired or fenced worker lease")
        return row

    def renew_progress(self, lease, *, chunks, now, ttl=90):
        now = _time(now)
        if (type(chunks) is not int or chunks < 1 or chunks > 2000
                or type(ttl) is not int or not MIN_TTL <= ttl <= MAX_TTL):
            raise ValueError("Invalid stream progress")
        with self._connect() as con:
            con.execute("BEGIN IMMEDIATE")
            row = self._active(con, lease, now)
            if chunks <= row[6]:
                raise ValueError("No actual new model token chunks")
            deadline = min(now+ttl, row[3]+MAX_LIFETIME)
            con.execute("""UPDATE lease_tasks SET chunks=?,deadline=?
                           WHERE task_id=?""",
                        (chunks, deadline, lease["task_id"]))
            return deadline

    def complete(self, lease, *, result_digest, now):
        now = _time(now)
        if (not isinstance(result_digest, str)
                or not DIGEST_PATTERN.fullmatch(result_digest)):
            raise ValueError("Invalid model output identity")
        with self._connect() as con:
            con.execute("BEGIN IMMEDIATE")
            self._active(con, lease, now)
            con.execute("""UPDATE lease_tasks SET state='DONE',
                owner=NULL,token=NULL,deadline=NULL,result_digest=?,finished=?
                WHERE task_id=?""", (result_digest, now, lease["task_id"]))
        return {"task_id": lease["task_id"], "state": "DONE"}

    def fail(self, lease, *, now):
        now = _time(now)
        with self._connect() as con:
            con.execute("BEGIN IMMEDIATE")
            row = self._active(con, lease, now)
            state = "FAILED" if row[5] >= MAX_ATTEMPTS else "PENDING"
            con.execute("""UPDATE lease_tasks SET state=?,
                owner=NULL,token=NULL,deadline=NULL WHERE task_id=?""",
                (state, lease["task_id"]))
        return state

    def inspect(self):
        """Read-only, token-free public summary; no task text or model data."""
        with self._connect() as con:
            records = con.execute("""SELECT task_id,state,attempts,chunks
                FROM lease_tasks ORDER BY task_id""").fetchall()
        return [{"task_id": r[0], "state": r[1],
                 "attempts": r[2], "chunks": r[3]} for r in records]


def authorized_state_db(value):
    """Require explicit persistent directory. Never write in Git checkout."""
    if os.environ.get("EDU_W38_PERSISTENT_LEASES") != "1":
        raise ValueError("Persistent worker state requires operator opt-in")
    root = Path(value)
    cwd = Path.cwd().resolve()
    if (not root.is_absolute() or not root.is_dir() or root.is_symlink()
            or root.resolve() == cwd or cwd in root.resolve().parents
            or root.resolve() in cwd.parents):
        raise ValueError("State directory must be separate from repository")
    return root / "autopilot-proposals.sqlite3"
