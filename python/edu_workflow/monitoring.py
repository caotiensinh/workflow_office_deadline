"""WF-08 read-only local health snapshot and Japanese HTML incident dashboard.

Never call open_store(): doing so would create SQLite files, WAL and/or schema.
Never dispatch, resend, mark delivered, acknowledge or modify a decision.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from html import escape
from pathlib import Path

STATES = ("QUEUED", "SENDING", "SENT", "UNKNOWN", "STALE")
TABLES = frozenset({"cases", "alerts", "decisions", "audit"})
ALERT_COLUMNS = frozenset({"state", "created_at"})
UTC = timezone.utc
JST = timezone(timedelta(hours=9))
RISK = {
    "UNKNOWN_DELIVERY": ("CRITICAL", "送信結果が不明", "送信先とサーバーログを人が照合してください。自動再送は禁止です。"),
    "SENDING_RECONCILIATION": ("CRITICAL", "送信処理の状態確認", "送信処理が残っています。外部送信の有無を確認し、自動再送しないでください。"),
    "OVERDUE_QUEUED": ("WARNING", "通知の滞留", "出力先・実行スケジュール・権限を管理者が調査してください。"),
    "INVALID_TIME_METADATA": ("WARNING", "時刻情報が不正", "監査ログと通知メタデータを確認してください。"),
    "DATABASE_MISSING": ("CRITICAL", "データベース未検出", "設定されたファイルと権限を確認してください。新規作成は行いません。"),
    "DATABASE_READ_FAILED": ("CRITICAL", "データベース読取不能", "破損・権限・ロックを安全に調査してください。自動修復はしません。"),
    "SCHEMA_MISMATCH": ("CRITICAL", "スキーマ不一致", "使用中のアプリ版・マイグレーション履歴を確認してください。"),
    "INTEGRITY_CHECK_FAILED": ("CRITICAL", "DB整合性エラー", "読み取り専用のバックアップを確保し、専門管理者が修復を判断してください。"),
}
SEVERITIES = {"HEALTHY", "WARNING", "CRITICAL"}
MAX_AGE_MINUTES = 10080


def _check_time(instant):
    if instant is None:
        return datetime.now(UTC)
    if isinstance(instant, str):
        try:
            instant = datetime.fromisoformat(instant)
        except ValueError as exc:
            raise ValueError("A valid timezone-aware ISO datetime is required") from exc
    if not isinstance(instant, datetime) or instant.tzinfo is None or instant.utcoffset() is None:
        raise ValueError("A timezone-aware datetime is required")
    return instant.astimezone(UTC)


def _age(instant, now):
    if not isinstance(instant, str) or len(instant) > 60:
        return None
    try:
        dt = datetime.fromisoformat(instant)
    except ValueError:
        return None
    if dt.tzinfo is None or dt.utcoffset() is None:
        return None
    # Negative age is invalid future metadata; do not silently treat it as healthy.
    delta = (now - dt.astimezone(UTC)).total_seconds()
    if delta < 0:
        return None
    return int(delta // 60)


def _issue(code):
    severity, title, action = RISK[code]
    return {"code": code, "severity": severity, "title_ja": title,
            "action_ja": action, "requires_human": True,
            "automated_retry_allowed": False}


def _empty_report(now, status, code):
    return {
        "schema_version": 1,
        "status": status,
        "checked_at": now.astimezone(JST).isoformat(timespec="seconds"),
        "db_integrity": "NOT_VERIFIED",
        "counts": {state: 0 for state in STATES},
        "cases_count": None,
        "decisions_count": None,
        "audit_count": None,
        "oldest_queued_age_minutes": None,
        "oldest_sending_age_minutes": None,
        "incidents": [_issue(code)],
        "requires_human": True,
        "read_only": True,
        "external_actions_performed": False,
        "database_created": False,
        "messages_resent": False,
        "production_accepted": False,
    }


def snapshot(db_path, *, at=None, queue_max_minutes=30, quick_check=True):
    """Read only aggregates, no raw email, people, payload, case IDs or message text.

    SENDING age is counted from created_at, a lower-bound/alert age, NOT
    a true sending-start duration (schema has no sending_started_at).
    """
    now = _check_time(at)
    if type(queue_max_minutes) is not int or not 1 <= queue_max_minutes <= MAX_AGE_MINUTES:
        raise ValueError("queue_max_minutes must be an integer 1..10080")
    if type(quick_check) is not bool:
        raise ValueError("quick_check must be bool")
    p = Path(db_path)
    if p.is_symlink() or not p.is_file():
        return _empty_report(now, "CRITICAL", "DATABASE_MISSING")
    conn = None
    try:
        # Use SQLite URI mode=ro, never open_store(): absent DB must stay absent.
        conn = sqlite3.connect(p.resolve().as_uri() + "?mode=ro", uri=True, timeout=2)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA query_only=ON")
        conn.execute("PRAGMA busy_timeout=2000")
        names = {x["name"] for x in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
        if not TABLES.issubset(names):
            return _empty_report(now, "CRITICAL", "SCHEMA_MISMATCH")
        cols = {x["name"] for x in conn.execute("PRAGMA table_info(alerts)")}
        if not ALERT_COLUMNS.issubset(cols):
            return _empty_report(now, "CRITICAL", "SCHEMA_MISMATCH")
        if quick_check:
            verified = conn.execute("PRAGMA quick_check(1)").fetchone()
            if verified is None or verified[0] != "ok":
                return _empty_report(now, "CRITICAL", "INTEGRITY_CHECK_FAILED")
        counts = {x: 0 for x in STATES}
        for r in conn.execute("SELECT state, COUNT(*) AS n FROM alerts GROUP BY state"):
            if r["state"] not in counts:
                return _empty_report(now, "CRITICAL", "SCHEMA_MISMATCH")
            counts[r["state"]] = r["n"]
        # We need earliest chronological date. The data store always writes UTC
        # created_at; inspect only grouped timestamps, never alert content.
        ages = {"QUEUED": None, "SENDING": None}
        issues = []
        for state in ages:
            dates = conn.execute("SELECT created_at FROM alerts WHERE state=?", (state,))
            oldest = 0
            for row in dates:
                age = _age(row["created_at"], now)
                if age is None:
                    if "INVALID_TIME_METADATA" not in issues:
                        issues.append("INVALID_TIME_METADATA")
                else:
                    oldest = max(oldest, age)
            if counts[state]:
                ages[state] = oldest
        if counts["UNKNOWN"]:
            issues.append("UNKNOWN_DELIVERY")
        if counts["SENDING"]:
            issues.append("SENDING_RECONCILIATION")
        if counts["QUEUED"] and ages["QUEUED"] is not None and ages["QUEUED"] >= queue_max_minutes:
            issues.append("OVERDUE_QUEUED")
        cases_count = conn.execute("SELECT COUNT(*) FROM cases").fetchone()[0]
        decision_count = conn.execute("SELECT COUNT(*) FROM decisions").fetchone()[0]
        audit_count = conn.execute("SELECT COUNT(*) FROM audit").fetchone()[0]
    except (sqlite3.Error, OSError, ValueError):
        return _empty_report(now, "CRITICAL", "DATABASE_READ_FAILED")
    finally:
        if conn is not None:
            conn.close()
    incidents = [_issue(k) for k in sorted(set(issues))]
    status = ("CRITICAL" if any(i["severity"] == "CRITICAL" for i in incidents)
              else "WARNING" if incidents else "HEALTHY")
    return {
        "schema_version": 1, "status": status,
        "checked_at": now.astimezone(JST).isoformat(timespec="seconds"),
        "db_integrity": "PASS" if quick_check else "NOT_CHECKED",
        "counts": counts, "cases_count": cases_count,
        "decisions_count": decision_count, "audit_count": audit_count,
        "oldest_queued_age_minutes": ages["QUEUED"],
        "oldest_sending_age_minutes": ages["SENDING"],
        "incidents": incidents, "requires_human": bool(incidents),
        "read_only": True, "external_actions_performed": False,
        "database_created": False, "messages_resent": False,
        "production_accepted": False,
    }


def html_dashboard(report):
    """Static offline HTML; no remote assets, scripts, input actions or PII."""
    if not isinstance(report, dict) or report.get("status") not in SEVERITIES:
        raise ValueError("Invalid monitor report")
    counts = report["counts"]
    incident_rows = "".join(
        "<tr><td>" + escape(item["severity"]) + "</td><td>" +
        escape(item["title_ja"]) + "</td><td>" + escape(item["action_ja"]) +
        "</td></tr>" for item in report["incidents"])
    ) or "<tr><td colspan='3'>異常なし</td></tr>"
    tiles = "".join(
        "<article class='tile'><div>" + escape(state) + "</div><strong>" +
        str(int(counts[state])) + "</strong></article>" for state in STATES
    )
    metric = "".join(
        "<article class='tile'><div>" + label + "</div><strong>" +
        str(int(report[key]) if report[key] is not None else "—") +
        "</strong></article>"
        for label, key in (("案件", "cases_count"), ("承認記録", "decisions_count"),
                           ("監査記録", "audit_count"))
    )
    status = escape(report["status"])
    checked = escape(report["checked_at"])
    # No JavaScript, forms, remote requests, CDN, meta refresh or linked assets.
    return """<!doctype html><html lang="ja"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none';style-src 'unsafe-inline';base-uri 'none';form-action 'none'">
<title>WF08 ローカル監視</title><style>
:root{font-family:system-ui,'Meiryo',sans-serif;background:#f4f6fa;color:#172238}
body{max-width:1050px;margin:36px auto;padding:0 18px}
h1{font-size:1.7rem} .lead{color:#4d596b}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(155px,1fr));gap:12px}
.tile{background:white;border:1px solid #d9dfeb;border-radius:12px;padding:17px}
.tile div{font-size:.85rem;color:#56657a}.tile strong{font-size:2rem}
table{width:100%;background:white;border-collapse:collapse;border-radius:10px;overflow:hidden}
th,td{padding:14px;text-align:left;border-bottom:1px solid #e4e8f0;vertical-align:top}
th{background:#e9edf6} .stamp{font-size:.85rem}
.warning{border-left:4px solid #a36a00;padding:10px;background:#fff7e8}
</style></head><body><h1>WF-08 ローカル監視 / Recovery</h1>
<p class="lead">読み取り専用・個人情報非表示・自動復旧／SMTP再送なし</p>
<h2>総合状態: """ + status + """</h2><p class="stamp">確認時刻（JST）: """ + checked + """</p>
<h2>通知状態</h2><section class="tiles">""" + tiles + """</section>
<h2>監査の集計</h2><section class="tiles">""" + metric + """</section>
<h2>確認を要する事象</h2>
<table><thead><tr><th>重要度</th><th>事象</th><th>人が行う対応</th></tr></thead>
<tbody>""" + incident_rows + """</tbody></table>
<p class="warning">UNKNOWN は送信済み・未送信を確定できません。自動再送は禁止です。
SENDINGの時間は通知作成からの経過時間であり、送信開始時刻ではありません。</p>
<p class="lead">CI・ローカル診断は本番環境の安全性や承認を保証しません。</p></body></html>"""


def save_html_new(report, output_path):
    """Explicit output only; exclusive create avoids clobbering old evidence."""
    file = Path(output_path)
    if not file.parent.is_dir() or file.is_symlink():
        raise ValueError("Output parent must exist and output must not be a symlink")
    with file.open("x", encoding="utf-8") as f:
        f.write(html_dashboard(report))
    return file
