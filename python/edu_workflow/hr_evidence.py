"""WF-05: strictly structured, anonymous-only, source-cited HR *draft*.

Never performs HR appraisal, ranking, employment recommendations or approvals.
All inputs must already be fictional or approved/de-identified by an operator.
A matching digest is integrity evidence, NOT proof that observations are true.
"""
from __future__ import annotations
import hashlib
import json
import re
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

JST = timezone(timedelta(hours=9))
PACKET_LIMIT = 128_000
SOURCE_LIMIT = 1_000_000
ANON = re.compile(r"^ANON-[0-9A-F]{16}$")
CLAIM = re.compile(r"^CL-[0-9A-F]{8}$")
EVIDENCE = re.compile(r"^EV-[0-9A-F]{8}$")
HASH = re.compile(r"^[a-f0-9]{64}$")
BASENAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,100}$")
TEMPLATES = {
    "TRAINING_COMPLETED": "研修受講に関する記録（提出資料に基づく。内容・真正性は未確認）",
    "ATTENDANCE_RECORDED": "出席状況に関する記録（提出資料に基づく。内容・真正性は未確認）",
    "DOCUMENT_SUBMITTED": "文書提出に関する記録（提出資料に基づく。内容・真正性は未確認）",
    "ASSIGNMENT_RECORDED": "担当業務に関する記録（提出資料に基づく。内容・真正性は未確認）",
    "SUPPORT_ACTIVITY": "支援活動に関する記録（提出資料に基づく。内容・真正性は未確認）",
}
PACKET_FIELDS = {"schema_version", "case_ref", "required_codes", "claims", "sources"}
CLAIM_FIELDS = {"claim_id", "fact_code", "observed_on", "evidence_id"}
SOURCE_FIELDS = {"evidence_id", "document", "sha256", "reviewed"}


def _invalid(reason):
    raise ValueError("HR_PACKET_INVALID: " + reason)


def _unique(pairs):
    result = {}
    for key, val in pairs:
        if key in result:
            _invalid("duplicate JSON member")
        result[key] = val
    return result


def _read(path, limit):
    p = Path(path)
    if p.is_symlink() or not p.is_file():
        _invalid("expected local regular non-symlink file")
    if p.stat().st_size > limit:
        _invalid("file exceeds size limit")
    with p.open("rb") as stream:
        content = stream.read(limit + 1)
    if len(content) > limit:
        _invalid("file exceeds size limit")
    return content


def _day(text):
    if not isinstance(text, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        _invalid("date must be YYYY-MM-DD")
    try:
        return date.fromisoformat(text)
    except ValueError:
        _invalid("invalid calendar day")


def _match(value, pattern, label):
    if not isinstance(value, str) or pattern.fullmatch(value) is None:
        _invalid("invalid " + label)


def _schema(data):
    if not isinstance(data, dict) or set(data) != PACKET_FIELDS:
        _invalid("unexpected packet fields")
    if type(data["schema_version"]) is not int or data["schema_version"] != 1:
        _invalid("unsupported schema_version")
    _match(data["case_ref"], ANON, "anonymous case_ref")
    required = data["required_codes"]
    if (not isinstance(required, list) or not 1 <= len(required) <= len(TEMPLATES)
            or any(not isinstance(code, str) or code not in TEMPLATES for code in required)
            or len(set(required)) != len(required)):
        _invalid("required_codes must be a nonempty distinct set of enum values")
    claims = data["claims"]
    sources = data["sources"]
    if not isinstance(claims, list) or not 1 <= len(claims) <= 100:
        _invalid("claims must contain 1..100 structured records")
    if not isinstance(sources, list) or len(sources) > 64:
        _invalid("sources must contain 0..64 structured records")
    seen_claims, seen_sources = set(), set()
    for item in claims:
        if not isinstance(item, dict) or set(item) != CLAIM_FIELDS:
            _invalid("claim must contain only structured fields")
        _match(item["claim_id"], CLAIM, "claim_id")
        if item["claim_id"] in seen_claims:
            _invalid("duplicate claim_id")
        seen_claims.add(item["claim_id"])
        if not isinstance(item["fact_code"], str) or item["fact_code"] not in TEMPLATES:
            _invalid("unknown fact_code")
        _day(item["observed_on"])
        if item["evidence_id"] is not None:
            _match(item["evidence_id"], EVIDENCE, "evidence_id")
    for item in sources:
        if not isinstance(item, dict) or set(item) != SOURCE_FIELDS:
            _invalid("source must contain only structured fields")
        _match(item["evidence_id"], EVIDENCE, "evidence_id")
        if item["evidence_id"] in seen_sources:
            _invalid("duplicate evidence_id")
        seen_sources.add(item["evidence_id"])
        _match(item["document"], BASENAME, "document basename")
        _match(item["sha256"], HASH, "document sha256")
        if type(item["reviewed"]) is not bool:
            _invalid("reviewed must be a boolean")


def read_packet(packet_path):
    raw = _read(packet_path, PACKET_LIMIT)
    try:
        packet = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique)
    except (UnicodeError, json.JSONDecodeError):
        _invalid("expected strict UTF-8 JSON")
    _schema(packet)
    return packet, hashlib.sha256(raw).hexdigest()


def _as_of(value):
    if value is None:
        return datetime.now(JST).date()
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            _invalid("simulation datetime requires an offset")
        return value.astimezone(JST).date()
    if isinstance(value, date):
        return value
    return _day(value)


def draft_from_packet(packet_path, as_of=None):
    """Return Japanese templated reviewer notes with IDs, not personal narratives."""
    packet, manifest_hash = read_packet(packet_path)
    today = _as_of(as_of)
    sources = {s["evidence_id"]: s for s in packet["sources"]}
    checked = {}
    root = Path(packet_path).parent
    for ident, source in sources.items():
        if not source["reviewed"]:
            checked[ident] = "SOURCE_REVIEW_REQUIRED"
            continue
        try:
            digest = hashlib.sha256(_read(root / source["document"], SOURCE_LIMIT)).hexdigest()
        except (OSError, ValueError):
            checked[ident] = "SOURCE_UNAVAILABLE"
            continue
        checked[ident] = "SOURCE_HASH_MATCH" if digest == source["sha256"] else "SOURCE_HASH_MISMATCH"
    gaps = []
    confirmed = defaultdict(list)
    all_codes = set()
    for claim in packet["claims"]:
        code, cid, eid = claim["fact_code"], claim["claim_id"], claim["evidence_id"]
        all_codes.add(code)
        if _day(claim["observed_on"]) > today:
            reason = "FUTURE_OBSERVATION"
        elif eid is None:
            reason = "MISSING_EVIDENCE"
        elif eid not in checked:
            reason = "UNLISTED_EVIDENCE"
        elif checked[eid] != "SOURCE_HASH_MATCH":
            reason = checked[eid]
        else:
            reason = None
        if reason:
            gaps.append({"claim_id": cid, "fact_code": code, "reason": reason})
        else:
            confirmed[code].append((cid, eid))
    for code in packet["required_codes"]:
        if code not in confirmed:
            gaps.append({"fact_code": code, "reason": "REQUIRED_CATEGORY_NOT_SUPPORTED"})
    sections = []
    for code in sorted(confirmed):
        pairs = sorted(confirmed[code])
        sections.append({
            "fact_code": code,
            "draft_ja": TEMPLATES[code],
            "claim_ids": [x for x, _ in pairs],
            "source_ids": sorted({y for _, y in pairs}),
        })
    return {
        "status": "EVIDENCE_GAPS" if gaps else "READY_FOR_HUMAN_REVIEW",
        "case_ref": packet["case_ref"],
        "packet_sha256": manifest_hash,
        "as_of": today.isoformat(),
        "draft_sections": sections,
        "gaps": sorted(gaps, key=lambda x: (x["fact_code"], x.get("claim_id", ""), x["reason"])),
        "source_count": len(sources),
        "claim_count": len(packet["claims"]),
        "human_review_required": True,
        "source_authenticity_verified": False,
        "hr_assessment_performed": False,
        "ranking_performed": False,
        "employment_decision_performed": False,
        "external_actions_performed": False,
        "writes_database": False,
    }


def verify_for_hr_approval(packet_path, case_id, evidence_ref, as_of=None):
    """The existing CLI still needs an authorized human and typed approval.

    READY here only checks local integrity and stated fact categories, not truth,
    fairness, HR-appraisal correctness or employer permission.
    """
    if not packet_path:
        raise ValueError("HR_APPROVAL_BLOCKED: packet not configured")
    report = draft_from_packet(packet_path, as_of=as_of)
    if report["case_ref"] != case_id:
        raise ValueError("HR_APPROVAL_BLOCKED: anonymous case binding mismatch")
    if evidence_ref != "HR-PACKET:" + report["packet_sha256"]:
        raise ValueError("HR_APPROVAL_BLOCKED: stale or missing packet hash binding")
    if report["status"] != "READY_FOR_HUMAN_REVIEW":
        raise ValueError("HR_APPROVAL_BLOCKED: evidence gaps require human investigation")
    return {
        "case_ref": report["case_ref"],
        "packet_sha256": report["packet_sha256"],
        "claim_count": report["claim_count"],
        "source_count": report["source_count"],
        "scope": "structural-source-check-only-no-hr-appraisal",
    }
