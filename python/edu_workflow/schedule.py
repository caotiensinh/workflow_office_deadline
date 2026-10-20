"""WF-06: deterministic OFFLINE meeting-slot proposals, no calendar writes.

Input is anonymous, structured free/busy data ONLY. Not a live calendar adapter,
not a reservation, not permission to send invites or modify an appointment.
All intervals are half-open [start, end); output is normalized to JST.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

JST = timezone(timedelta(hours=9))
UTC = timezone.utc
WINDOW_LIMIT = timedelta(days=31)
MAX_FILE_BYTES = 256_000


def _integer(obj, key, lower, upper, default=None):
    v = obj.get(key, default)
    if type(v) is not int or not lower <= v <= upper:
        raise ValueError(f"{key} must be an integer in [{lower},{upper}]")
    return v


def _timestamp(value):
    if not isinstance(value, str) or len(value) > 40:
        raise ValueError("Invalid datetime: an ISO timestamp with offset is required")
    try:
        dt = datetime.fromisoformat(value)
    except (ValueError, TypeError) as exc:
        raise ValueError("Invalid datetime: an ISO timestamp with offset is required") from exc
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError("Naive datetime is forbidden; timezone offset required")
    return dt.astimezone(UTC)


def _interval(obj):
    if not isinstance(obj, dict) or set(obj) != {"start", "end"}:
        raise ValueError("Every interval requires only start and end")
    start, end = _timestamp(obj["start"]), _timestamp(obj["end"])
    if end <= start:
        raise ValueError("Interval end must be later than start")
    return (start, end)


def _intervals(value, *, required=False):
    if not isinstance(value, list) or len(value) > 32 or (required and not value):
        raise ValueError("Availability and busy periods must be lists (1..32 available intervals)")
    return [_interval(v) for v in value]


def _merge(pairs):
    combined = []
    for start, end in sorted(pairs):
        if combined and start <= combined[-1][1]:
            last_start, last_end = combined[-1]
            combined[-1] = (last_start, max(end, last_end))
        else:
            combined.append((start, end))
    return combined


def _intersection(left, right):
    result = []
    i = j = 0
    while i < len(left) and j < len(right):
        a, b = left[i]
        c, d = right[j]
        if max(a, c) < min(b, d):
            result.append((max(a, c), min(b, d)))
        if b <= d:
            i += 1
        else:
            j += 1
    return result


def _subtract(available, busy):
    remaining = available
    for block_start, block_end in busy:
        updated = []
        for a, b in remaining:
            if b <= block_start or a >= block_end:
                updated.append((a, b))
            else:
                if a < block_start:
                    updated.append((a, block_start))
                if block_end < b:
                    updated.append((block_end, b))
        remaining = updated
    return remaining


def _next_slot_start(moment, slot_minutes):
    """Round UP to JST midnight + N*slot; never suggest a past partial slot."""
    jst = moment.astimezone(JST)
    midnight = jst.replace(hour=0, minute=0, second=0, microsecond=0)
    step = timedelta(minutes=slot_minutes)
    elapsed = jst - midnight
    n = elapsed // step
    if midnight + n * step < jst:
        n += 1
    return (midnight + n * step).astimezone(UTC)


def propose_slots(request):
    """Return masked, read-only candidate slots; never assert calendar verification."""
    if not isinstance(request, dict) or set(request) - {
        "window", "participants", "duration_minutes", "slot_minutes", "max_proposals"
    }:
        raise ValueError("Unsupported schedule request fields")
    window = _interval(request.get("window"))
    if window[1] - window[0] > WINDOW_LIMIT:
        raise ValueError("Scheduling window cannot exceed 31 days")
    duration = timedelta(minutes=_integer(request, "duration_minutes", 15, 480))
    granularity = _integer(request, "slot_minutes", 5, 60, default=15)
    max_proposals = _integer(request, "max_proposals", 1, 20, default=5)
    participants = request.get("participants")
    if not isinstance(participants, list) or not 2 <= len(participants) <= 20:
        raise ValueError("2..20 anonymous participant schedules are required")
    common = [window]
    for person in participants:
        if not isinstance(person, dict) or set(person) - {"available", "busy"}:
            raise ValueError("Participant must contain only anonymous available/busy intervals")
        periods = _merge(_intervals(person.get("available"), required=True))
        blocks = _merge(_intervals(person.get("busy", [])))
        free = _subtract(periods, blocks)
        common = _intersection(common, free)
        if not common:
            break

    proposals = []
    step = timedelta(minutes=granularity)
    for start, end in common:
        candidate = _next_slot_start(start, granularity)
        while candidate + duration <= end and len(proposals) < max_proposals:
            proposals.append({
                "start": candidate.astimezone(JST).isoformat(timespec="minutes"),
                "end": (candidate + duration).astimezone(JST).isoformat(timespec="minutes"),
            })
            candidate += step
        if len(proposals) == max_proposals:
            break
    return {
        "status": "PROPOSALS" if proposals else "NO_COMMON_AVAILABILITY",
        "participant_count": len(participants),
        "proposals": proposals,
        "requires_human_approval": True,
        "calendar_verified": False,
        "external_actions_performed": False,
        "writes_database": False,
    }


def propose_from_file(path):
    """Read only a bounded, non-symlink regular JSON file; no SQLite opened."""
    file = Path(path)
    if file.is_symlink() or not file.is_file():
        raise ValueError("Scheduling input must be an existing, non-symlink JSON file")
    if file.stat().st_size > MAX_FILE_BYTES:
        raise ValueError("Scheduling input exceeds the 256 KB limit")
    data = json.loads(file.read_text(encoding="utf-8"))
    return propose_slots(data)
