"""WF04 offline validation of DECLARED reference metadata, not legal validity."""
from __future__ import annotations
import hashlib
import json
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

_KEY = re.compile(r"^[A-Z0-9][A-Z0-9._-]{0,63}$")
_FILE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,100}$")
_SHA = re.compile(r"^[0-9a-f]{64}$")
_FIELDS = {
    "reference_id", "version", "document", "sha256",
    "citation_id", "authority_code", "effective_from", "effective_until",
    "human_reviewed", "superseded_by",
}

def _invalid(reason):
    raise ValueError("REGULATION_REGISTRY_INVALID: " + reason)

def _no_duplicates(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            _invalid("duplicate JSON field")
        out[key] = value
    return out

def _read(path, limit):
    file = Path(path)
    if file.is_symlink() or not file.is_file():
        _invalid("expected regular non-symlink local file")
    if file.stat().st_size > limit:
        _invalid("input exceeds size limit")
    with file.open("rb") as source:
        result = source.read(limit + 1)
    if len(result) > limit:
        _invalid("input exceeds size limit")
    return result

def _date(value):
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        _invalid("date must be YYYY-MM-DD")
    try:
        return date.fromisoformat(value)
    except ValueError:
        _invalid("invalid date")

def _identifier(value):
    if not isinstance(value, str) or _KEY.fullmatch(value) is None:
        _invalid("invalid opaque identifier")

def _validate(item):
    if not isinstance(item, dict) or set(item) != _FIELDS:
        _invalid("reference schema mismatch")
    for key in ("reference_id", "version", "citation_id", "authority_code"):
        _identifier(item[key])
    if not isinstance(item["document"], str) or _FILE.fullmatch(item["document"]) is None:
        _invalid("document path must be a local basename")
    if not isinstance(item["sha256"], str) or _SHA.fullmatch(item["sha256"]) is None:
        _invalid("invalid sha256")
    if type(item["human_reviewed"]) is not bool:
        _invalid("human_reviewed must be boolean")
    if item["superseded_by"] is not None:
        _identifier(item["superseded_by"])
    if _date(item["effective_until"]) <= _date(item["effective_from"]):
        _invalid("invalid effective window")

def read_registry(path):
    raw = _read(path, 128_000)
    try:
        data = json.loads(raw.decode("utf-8"), object_pairs_hook=_no_duplicates)
    except (UnicodeError, json.JSONDecodeError):
        _invalid("invalid JSON/UTF-8")
    if not isinstance(data, dict) or set(data) != {"schema_version", "references"}:
        _invalid("registry schema mismatch")
    if type(data["schema_version"]) is not int or data["schema_version"] != 1:
        _invalid("unsupported registry schema")
    refs = data["references"]
    if not isinstance(refs, list) or not 1 <= len(refs) <= 128:
        _invalid("expected 1..128 references")
    seen = set()
    for item in refs:
        _validate(item)
        identity = (item["reference_id"], item["version"])
        if identity in seen:
            _invalid("duplicate reference version")
        seen.add(identity)
    return refs, hashlib.sha256(raw).hexdigest()

def _status(reason, **metadata):
    return {
        "status": "SOURCE_SNAPSHOT_PASS" if reason == "DECLARED_SOURCE_MATCH" else "HUMAN_REVIEW_REQUIRED",
        "reason": reason,
        **metadata,
        "official_authenticity_verified": False,
        "legal_applicability_verified": False,
        "human_decision_required": True,
        "external_actions_performed": False,
    }

def verify_reference(registry_path, evidence_ref, as_of=None):
    if not isinstance(evidence_ref, str) or evidence_ref.count("@") != 1:
        return _status("INVALID_REFERENCE")
    ident, version = evidence_ref.split("@")
    if _KEY.fullmatch(ident) is None or _KEY.fullmatch(version) is None:
        return _status("INVALID_REFERENCE")
    if registry_path is None:
        return _status("REGISTRY_NOT_CONFIGURED")
    refs, manifest_sha = read_registry(registry_path)
    if as_of is None:
        as_of = datetime.now(timezone(timedelta(hours=9))).date()
    elif isinstance(as_of, datetime):
        if as_of.tzinfo is None or as_of.utcoffset() is None:
            _invalid("as_of needs timezone")
        as_of = as_of.astimezone(timezone(timedelta(hours=9))).date()
    elif isinstance(as_of, str):
        as_of = _date(as_of)
    elif not isinstance(as_of, date):
        _invalid("invalid as_of")
    selected = next((r for r in refs if r["reference_id"] == ident
                     and r["version"] == version), None)
    if selected is None:
        return _status("UNKNOWN_REFERENCE", manifest_sha256=manifest_sha)
    fields = {
        "reference_id": ident, "version": version,
        "citation_id": selected["citation_id"],
        "authority_code": selected["authority_code"],
        "manifest_sha256": manifest_sha,
    }
    if selected["superseded_by"] is not None:
        return _status("SUPERSEDED_REFERENCE", **fields)
    if not selected["human_reviewed"]:
        return _status("SOURCE_REVIEW_REQUIRED", **fields)
    if not _date(selected["effective_from"]) <= as_of < _date(selected["effective_until"]):
        return _status("OUTSIDE_DECLARED_WINDOW", **fields)
    try:
        actual = hashlib.sha256(_read(Path(registry_path).parent / selected["document"], 1_000_000)).hexdigest()
    except (ValueError, OSError):
        return _status("SOURCE_FILE_MISSING", **fields)
    if actual != selected["sha256"]:
        return _status("DOCUMENT_HASH_MISMATCH", **fields)
    return _status("DECLARED_SOURCE_MATCH", document_sha256=actual, **fields)

def verify_for_approval(registry_path, evidence_ref, as_of=None):
    result = verify_reference(registry_path, evidence_ref, as_of=as_of)
    if result["status"] != "SOURCE_SNAPSHOT_PASS":
        raise ValueError("REGULATION_APPROVAL_BLOCKED: " + result["reason"])
    return {k: result[k] for k in (
        "reference_id", "version", "citation_id", "authority_code",
        "manifest_sha256", "document_sha256"
    )}
