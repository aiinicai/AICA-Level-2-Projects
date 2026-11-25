"""Module 8a — applicable-law determination and verified legal-reference registry.

Rules encoded (all outputs carry `requires_ca_verification`):
* Periods ending on or before 31-03-2026 (AY 2026-27 and earlier under the
  1961 Act's numbering) → substantive law: Income-tax Act, 1961, continuing by
  virtue of the repeal & savings provisions of the Income-tax Act, 2025.
* Tax Year 2026-27 onwards (period beginning 01-04-2026) → Income-tax Act, 2025.
* A notice dated on/after 01-04-2026 for an earlier period raises a transition
  flag: procedure / authority / limitation may be governed differently from the
  substantive charge, and must be checked by the CA.
* The tool never maps 1961 section numbers to 2025 Act sections on its own.
"""
from __future__ import annotations

import json
import re
from datetime import date

from ..core import audit
from ..core.config import STATIC_DATA_DIR
from ..core.db import ro, row_to_dict, tx, utcnow
from ..core.errors import NotFound, ValidationError
from .auth import require_role

NEW_ACT_START = date(2026, 4, 1)
ACT_1961 = "Income-tax Act, 1961"
ACT_2025 = "Income-tax Act, 2025"


def _period_from_year(year_label: str, label_type: str) -> tuple[date, date]:
    m = re.match(r"^(\d{4})-(\d{2})$", year_label or "")
    if not m:
        raise ValidationError("Year must look like 2026-27.")
    y = int(m.group(1))
    if label_type == "AY":  # AY y-(y+1) → previous year (y-1)-y
        return date(y - 1, 4, 1), date(y, 3, 31)
    if label_type == "TAX_YEAR":  # tax year y-(y+1) is the year itself
        return date(y, 4, 1), date(y + 1, 3, 31)
    raise ValidationError("label_type must be AY or TAX_YEAR.")


def determine_applicable_law(year_label: str, label_type: str = "AY", notice_date: str | None = None,
                             proceeding_type: str | None = None) -> dict:
    start, end = _period_from_year(year_label, label_type)
    flags: list[str] = []
    if end < NEW_ACT_START:
        substantive = ACT_1961
        basis = (f"The relevant period ({start:%d-%m-%Y} to {end:%d-%m-%Y}) ends before {NEW_ACT_START:%d-%m-%Y}. "
                 "The charge of tax for this period is governed by the Income-tax Act, 1961, continued for such periods by "
                 "the repeal and savings provisions of the Income-tax Act, 2025.")
        flags.append("Verify the specific savings/transition provision of the Income-tax Act, 2025 that preserves this proceeding.")
    elif start >= NEW_ACT_START:
        substantive = ACT_2025
        basis = (f"The relevant tax year ({start:%d-%m-%Y} to {end:%d-%m-%Y}) begins on/after {NEW_ACT_START:%d-%m-%Y}; "
                 "the Income-tax Act, 2025 applies.")
        flags.append("Use Income-tax Act, 2025 section numbering; do not cite 1961 Act sections for this period.")
    else:  # pragma: no cover — cannot happen with Apr–Mar years
        substantive = "INDETERMINATE"
        basis = "Period straddles commencement date."
        flags.append("Period straddles commencement — CA determination required.")

    procedural_note = None
    if notice_date:
        try:
            nd = date.fromisoformat(notice_date)
        except ValueError:
            raise ValidationError("notice_date must be ISO format YYYY-MM-DD.")
        if nd >= NEW_ACT_START and substantive == ACT_1961:
            flags.append("TRANSITION: notice issued on/after 01-04-2026 for a pre-2026 period. Check whether the notice cites the "
                         "correct statute, whether procedure/limitation is governed by the 1961 Act (saved) or the 2025 Act, and "
                         "whether the issuing authority and section reference are valid.")
            procedural_note = "Procedure and limitation for this proceeding require specific CA verification."
        if nd < NEW_ACT_START and substantive == ACT_2025:
            flags.append("Notice predates the period it relates to — check the year/notice details for errors.")
    if proceeding_type and proceeding_type.upper() in {"REASSESSMENT", "148", "148A"}:
        flags.append("Reassessment: verify time limits and the version of ss.147–151 (1961 Act) applicable on the notice date, "
                     "or the corresponding 2025 Act provisions.")
    return {"relevant_period": {"from": start.isoformat(), "to": end.isoformat(), "label": f"{label_type} {year_label}"},
            "substantive_law": substantive, "basis": basis, "procedural_note": procedural_note, "flags": flags,
            "requires_ca_verification": True}


# ---------------- legal reference registry ----------------

REF_TYPES = ("STATUTE", "RULE", "CIRCULAR", "NOTIFICATION", "JUDGMENT", "PRACTICE_NOTE")


def seed_registry() -> int:
    """Insert missing seed entries; back-fill v2 metadata (type / effective date) on
    untouched seed rows only. Never alters user entries or verified rows."""
    data = json.loads((STATIC_DATA_DIR / "legal_registry.json").read_text(encoding="utf-8"))
    n = 0
    with tx() as conn:
        for e in data["entries"]:
            cur = conn.execute(
                "INSERT OR IGNORE INTO legal_refs(ref_key,act,provision,title,summary,source_url,status,origin) "
                "VALUES (?,?,?,?,?,?,'REQUIRES_VERIFICATION','SEED')",
                (e["ref_key"], e["act"], e["provision"], e["title"], e["summary"], e.get("source_url")),
            )
            n += cur.rowcount
            conn.execute("UPDATE legal_refs SET ref_type=COALESCE(?, ref_type), effective_from=COALESCE(effective_from, ?), "
                         "applies_to=COALESCE(applies_to, ?), source_url=COALESCE(source_url, ?), provision=? "
                         "WHERE ref_key=? AND origin='SEED' AND status='REQUIRES_VERIFICATION'",
                         (e.get("ref_type"), e.get("effective_from"), e.get("applies_to"), e.get("source_url"), e["provision"],
                          e["ref_key"]))
    return n


def list_refs(status: str | None = None) -> list[dict]:
    with ro() as conn:
        if status:
            rows = conn.execute("SELECT * FROM legal_refs WHERE status=? ORDER BY ref_key", (status,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM legal_refs ORDER BY ref_key").fetchall()
    return [row_to_dict(r) for r in rows]


def get_ref(ref_key: str) -> dict:
    with ro() as conn:
        r = conn.execute("SELECT * FROM legal_refs WHERE ref_key=?", (ref_key,)).fetchone()
    if not r:
        raise NotFound(f"Legal reference {ref_key} not found.")
    return row_to_dict(r)


def add_ref(user: dict, *, ref_key: str, act: str, provision: str, title: str, summary: str,
            source_url: str | None, ref_type: str = "STATUTE", effective_from: str | None = None,
            effective_to: str | None = None, applies_to: str | None = None) -> dict:
    """Add a statutory reference or judicial precedent. Always starts as
    REQUIRES_VERIFICATION — must be separately verified by a CA."""
    if not re.match(r"^[A-Z0-9_]{3,60}$", ref_key or ""):
        raise ValidationError("ref_key: 3-60 chars, A-Z, 0-9, _.")
    for f, v in (("act", act), ("provision", provision), ("title", title), ("summary", summary)):
        if not v or len(v) > 2000:
            raise ValidationError(f"{f} is required (max 2000 chars).")
    if source_url and not re.match(r"^https?://", source_url):
        raise ValidationError("source_url must be http(s).")
    if ref_type not in REF_TYPES:
        raise ValidationError(f"ref_type must be one of {REF_TYPES}.")
    for f, v in (("effective_from", effective_from), ("effective_to", effective_to)):
        if v:
            try:
                date.fromisoformat(v)
            except ValueError:
                raise ValidationError(f"{f} must be YYYY-MM-DD.")
    with ro() as conn:
        if conn.execute("SELECT 1 FROM legal_refs WHERE ref_key=?", (ref_key,)).fetchone():
            from ..core.errors import Conflict

            raise Conflict(f"Reference {ref_key} already exists.")
    with tx() as conn:
        conn.execute("INSERT INTO legal_refs(ref_key,act,provision,title,summary,source_url,status,origin,ref_type,effective_from,"
                     "effective_to,applies_to) VALUES (?,?,?,?,?,?,'REQUIRES_VERIFICATION','USER',?,?,?,?)",
                     (ref_key, act, provision, title, summary, source_url, ref_type, effective_from, effective_to,
                      (applies_to or None) and applies_to[:200]))
        audit.log_event(conn, "LEGAL_REF_ADDED", user_id=user["id"], meta={"ref_key": ref_key})
    return get_ref(ref_key)


def verify_ref(user: dict, ref_key: str, source_url: str, effective_from: str | None = None, note: str | None = None) -> dict:
    require_role(user, "CA")
    if not source_url or not re.match(r"^https?://", source_url):
        raise ValidationError("A verifiable source URL (official bare Act, CBDT circular, or judgment) is required to verify.")
    if effective_from:
        try:
            date.fromisoformat(effective_from)
        except ValueError:
            raise ValidationError("effective_from must be YYYY-MM-DD.")
    get_ref(ref_key)
    with tx() as conn:
        conn.execute("UPDATE legal_refs SET status='VERIFIED', source_url=?, verified_by=?, verified_at=?, "
                     "effective_from=COALESCE(?, effective_from), verification_note=COALESCE(?, verification_note) WHERE ref_key=?",
                     (source_url, user["id"], utcnow(), effective_from, (note or None) and note[:1000], ref_key))
        audit.log_event(conn, "LEGAL_REF_VERIFIED", user_id=user["id"], meta={"ref_key": ref_key, "source_url": source_url})
    return get_ref(ref_key)


def unverify_ref(user: dict, ref_key: str) -> dict:
    require_role(user, "CA", "ADMIN")
    with tx() as conn:
        conn.execute("UPDATE legal_refs SET status='REQUIRES_VERIFICATION', verified_by=NULL, verified_at=NULL WHERE ref_key=?", (ref_key,))
        audit.log_event(conn, "LEGAL_REF_UNVERIFIED", user_id=user["id"], meta={"ref_key": ref_key})
    return get_ref(ref_key)


def render_ref(ref_key: str) -> str:
    """Text used in drafts: verified refs render normally; others render as a
    conspicuous placeholder so nothing unverified slips into a reply."""
    try:
        r = get_ref(ref_key)
    except NotFound:
        return f"[LEGAL REFERENCE {ref_key} – NOT IN REGISTRY – REQUIRES CA VERIFICATION]"
    if r["status"] != "VERIFIED":
        return f"[{r['provision']} of the {r['act']} – REQUIRES CA VERIFICATION]"
    if (r.get("ref_type") or "STATUTE") == "JUDGMENT":
        return f"{r['title']} ({r['provision']})"
    return f"{r['provision']} of the {r['act']}"
