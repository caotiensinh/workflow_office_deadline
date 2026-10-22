"""W36: read-only local Ollama token-progress heartbeat for isolated workers.

Only localhost /api/generate. Tokens are never logged or written to the
heartbeat: it carries pid/count/stage, and is confined to a private temp dir.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import urllib.request

from .autopilot_worker_w27 import LOCAL_URL, NoRedirect, no_duplicates

MAX_LINE_BYTES = 32768
MAX_TOTAL_BYTES = 128 * 1024
MAX_TEXT_BYTES = 65536
MAX_CHUNKS = 2000


def stream_generate(payload, *, progress=None, opener=None):
    """Return Ollama's normal {'response': str} adapter from its NDJSON stream.

    progress is invoked only on a non-empty response fragment received from
    Ollama, not on clock ticks or synthetic heartbeats. Never stream the
    content to CI/logs. No redirects, extra domains or model downloads.
    """
    if not isinstance(payload, dict) or not isinstance(payload.get("model"), str):
        raise ValueError("Unsafe model stream request")
    if payload.get("stream") is not True or payload.get("keep_alive") != 0:
        raise ValueError("Stream + disabled resident model are mandatory")
    if payload.get("options", {}).get("num_gpu") != 0:
        raise ValueError("CPU-only policy violation")
    req = urllib.request.Request(
        LOCAL_URL + "/api/generate",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    client = opener or urllib.request.build_opener(NoRedirect)
    parts, seen_bytes, total_text, chunks, done = [], 0, 0, 0, False
    with client.open(req, timeout=180) as response:
        if response.status != 200:
            raise ValueError("Ollama returned HTTP error")
        while True:
            line = response.readline(MAX_LINE_BYTES + 1)
            if not line:
                break
            seen_bytes += len(line)
            if len(line) > MAX_LINE_BYTES or seen_bytes > MAX_TOTAL_BYTES:
                raise ValueError("Model stream budget exceeded")
            item = json.loads(line.decode("utf-8"), object_pairs_hook=no_duplicates)
            if not isinstance(item, dict) or type(item.get("done")) is not bool:
                raise ValueError("Missing streaming terminal marker")
            if item.get("error"):
                raise ValueError("Model streaming error")
            fragment = item.get("response", "")
            if not isinstance(fragment, str):
                raise ValueError("Non-string model response fragment")
            if fragment:
                total_text += len(fragment.encode("utf-8"))
                chunks += 1
                if total_text > MAX_TEXT_BYTES or chunks > MAX_CHUNKS:
                    raise ValueError("Model text/chunk limit exceeded")
                parts.append(fragment)
                if progress is not None:
                    progress(chunks)
            if item["done"]:
                done = True
                break
    if not done or not parts:
        raise ValueError("Incomplete/empty Ollama streaming result")
    return {"response": "".join(parts)}


class Heartbeat:
    """Private numeric-only atomic JSON receipts, never model text or paths."""
    def __init__(self, file):
        dest = Path(file)
        if not dest.is_absolute() or dest.suffix != ".json":
            raise ValueError("Unsafe heartbeat file")
        base = dest.parent
        if (not base.is_dir() or base.is_symlink() or dest.is_symlink()
                or dest.exists()):
            raise ValueError("Unsafe/existing heartbeat destination")
        self.path = dest
        self.count = 0
        self._write("started")

    def _write(self, status):
        data = json.dumps({"pid": os.getpid(), "chunks": self.count, "state": status})
        tmp = self.path.with_suffix(".tmp")
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            with os.fdopen(fd, "w", encoding="ascii") as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(tmp, self.path)
        finally:
            if tmp.exists():
                tmp.unlink()

    def progress(self, chunks):
        if type(chunks) is not int or chunks <= self.count or chunks > MAX_CHUNKS:
            raise ValueError("Non-monotonic heartbeat")
        self.count = chunks
        self._write("streaming")

    def completed(self):
        if self.count < 1:
            raise ValueError("No actual streamed model progress")
        self._write("complete")


def read_progress(file, expected_pid):
    """Parent trusts only its own ephemeral path and matching process ID."""
    if not file:
        return 0
    path = Path(file)
    if not path.is_file() or path.is_symlink() or path.stat().st_size > 256:
        return 0
    try:
        d = json.loads(path.read_text(encoding="ascii"), object_pairs_hook=no_duplicates)
        if (not isinstance(d, dict) or set(d) != {"pid", "chunks", "state"}
                or d["pid"] != expected_pid or type(d["chunks"]) is not int
                or not 0 <= d["chunks"] <= MAX_CHUNKS
                or d["state"] not in ("started", "streaming", "complete")):
            return 0
        return d["chunks"]
    except (OSError, UnicodeError, ValueError, TypeError):
        return 0
