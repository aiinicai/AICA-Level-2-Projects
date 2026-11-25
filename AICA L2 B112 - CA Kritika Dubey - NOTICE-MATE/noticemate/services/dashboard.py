"""Dashboard KPIs, alerts and activity — computed only from live application data."""
from __future__ import annotations

import json
import re
from datetime import date, timedelta

from ..core.db import ro
from . import cases

CLOSED_STATUSES = {"SUBMITTED", "CLOSED"}
UPCOMING_DAYS = 15
_ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _deadline_of(notice_row) -> tuple[str | None, bool]:
    if notice_row["deadline_verified"] and notice_row["deadline_value"]:
        return notice_row["deadline_value"], True
    try:
        p = json.loads(notice_row["particulars_json"])
        v = (p.get("compliance_deadline") or {}).get("value")
    except (ValueError, TypeError):
        v = None
    return (v if v and _ISO.match(v) else None), False


def summary(user: dict, today: date | None = None) -> dict:
    today = today or date.today()
    cl = cases.list_cases(user)
    ids = [c["id"] for c in cl]
    by_id = {c["id"]: c for c in cl}
    active_ids = {c["id"] for c in cl if c["status"] not in CLOSED_STATUSES}
    status_dist: dict[str, int] = {}
    for c in cl:
        status_dist[c["status"]] = status_dist.get(c["status"], 0) + 1
    out = {"as_of": today.isoformat(), "total_cases": len(cl), "active_cases": len(active_ids),
           "status_distribution": status_dist, "pending_notices": 0, "upcoming_deadlines": [], "overdue": [],
           "awaiting_review": [], "recent_activity": [], "alerts": [], "deadline_timeline": []}
    if not ids:
        out["alerts"].append({"level": "info", "text": "No cases yet. Create a case to begin."})
        return out
    q = ",".join("?" * len(ids))
    with ro() as conn:
        notices = conn.execute(f"SELECT * FROM notices WHERE case_id IN ({q})", ids).fetchall()
        docs_bad = conn.execute(f"SELECT case_id, original_name, extraction_status FROM documents WHERE case_id IN ({q}) "
                                "AND extraction_status IN ('FAILED','PARTIAL')", ids).fetchall()
        ai_bad = conn.execute(f"SELECT case_id, id, status FROM ai_submissions WHERE case_id IN ({q}) AND status IN ('BLOCKED','FAILED') "
                              "AND created_at >= ?", (*ids, (today - timedelta(days=30)).isoformat())).fetchall()
        drafts = conn.execute(f"SELECT d.case_id, d.id, d.version, d.content_hash FROM drafts d JOIN "
                              f"(SELECT case_id, MAX(version) v FROM drafts WHERE case_id IN ({q}) GROUP BY case_id) m "
                              "ON m.case_id=d.case_id AND m.v=d.version", ids).fetchall()
        approvals = {r["draft_id"]: r["content_hash"] for r in conn.execute(
            "SELECT draft_id, content_hash FROM approvals WHERE revoked=0").fetchall()}
        rejected = {r["draft_id"] for r in conn.execute(
            "SELECT draft_id FROM draft_reviews WHERE decision IN ('REJECTED','CHANGES_REQUESTED')").fetchall()}
        open_comments = conn.execute(f"SELECT case_id, COUNT(*) n FROM draft_comments WHERE status='OPEN' AND case_id IN ({q}) "
                                     "GROUP BY case_id", ids).fetchall()
        activity = conn.execute(f"SELECT a.ts, a.event, a.case_id, u.full_name FROM audit_log a LEFT JOIN users u ON u.id=a.user_id "
                                f"WHERE a.case_id IN ({q}) ORDER BY a.id DESC LIMIT 25", ids).fetchall()

    for n in notices:
        if n["case_id"] not in active_ids:
            continue
        out["pending_notices"] += 1
        dl, verified = _deadline_of(n)
        c = by_id[n["case_id"]]
        item = {"case_id": c["id"], "case_ref": c["case_ref"], "assessee": c["assessee_name"], "notice_id": n["id"],
                "deadline": dl, "verified": verified}
        if dl:
            d = date.fromisoformat(dl)
            item["days_left"] = (d - today).days
            out["deadline_timeline"].append(item)
            if d < today:
                out["overdue"].append(item)
                out["alerts"].append({"level": "critical", "case_id": c["id"],
                                      "text": f"{c['case_ref']}: deadline {dl} has passed ({-item['days_left']} days overdue)."})
            elif d <= today + timedelta(days=UPCOMING_DAYS):
                out["upcoming_deadlines"].append(item)
                if item["days_left"] <= 3:
                    out["alerts"].append({"level": "high", "case_id": c["id"],
                                          "text": f"{c['case_ref']}: deadline in {item['days_left']} day(s) ({dl})."})
        if not verified:
            out["alerts"].append({"level": "high", "case_id": c["id"],
                                  "text": f"{c['case_ref']}: compliance deadline for notice #{n['id']} NOT VERIFIED"
                                          + ("" if dl else " (no date extracted)") + "."})
    out["upcoming_deadlines"].sort(key=lambda x: x["deadline"])
    out["overdue"].sort(key=lambda x: x["deadline"])
    out["deadline_timeline"].sort(key=lambda x: x["deadline"])

    for d in drafts:
        if d["case_id"] not in active_ids:
            continue
        approved = approvals.get(d["id"]) == d["content_hash"]
        if not approved:
            c = by_id[d["case_id"]]
            out["awaiting_review"].append({"case_id": c["id"], "case_ref": c["case_ref"], "draft_id": d["id"], "version": d["version"],
                                           "state": "CHANGES REQUESTED" if d["id"] in rejected else "AWAITING CA REVIEW"})
    for c in cl:
        if c["status"] == "UNDER_REVIEW" and c["id"] in active_ids and not any(a["case_id"] == c["id"] for a in out["awaiting_review"]):
            out["awaiting_review"].append({"case_id": c["id"], "case_ref": c["case_ref"], "draft_id": None, "version": None,
                                           "state": "UNDER REVIEW (no draft yet)"})
    for r in docs_bad:
        out["alerts"].append({"level": "medium", "case_id": r["case_id"],
                              "text": f"{by_id[r['case_id']]['case_ref']}: '{r['original_name']}' extraction {r['extraction_status']} — check original."})
    for r in ai_bad:
        out["alerts"].append({"level": "medium", "case_id": r["case_id"],
                              "text": f"{by_id[r['case_id']]['case_ref']}: AI submission #{r['id']} {r['status']}."})
    for r in open_comments:
        out["alerts"].append({"level": "medium", "case_id": r["case_id"],
                              "text": f"{by_id[r['case_id']]['case_ref']}: {r['n']} open reviewer comment(s)."})
    order = {"critical": 0, "high": 1, "medium": 2, "info": 3}
    out["alerts"].sort(key=lambda a: order.get(a["level"], 9))
    out["recent_activity"] = [{"ts": a["ts"], "event": a["event"], "case_ref": by_id.get(a["case_id"], {}).get("case_ref"),
                               "user": a["full_name"]} for a in activity]
    return out
