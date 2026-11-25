"""V3 — legal authorities, propositions and the reasoning trace.

Design rules (Project Instructions §2, §6, §12):
* Nothing here invents law. Sources are entered by a user, imported from the
  existing registry (always unverified), or recorded from an AI reply (always
  labelled AI_SUGGESTION and never verifiable as authority).
* Primary law, secondary commentary and AI suggestions are separate classes.
* A source is VERIFIED only by a CA who records the URL they opened, the
  paragraph/provision they checked and that applicability (AY/Tax Year, Act,
  transition) was confirmed. Every decision is kept in an append-only log.
* Any later change to a verified source or proposition drops it back to
  NEEDS_CA_REVIEW automatically (hash comparison), and a source whose
  effective_to date has passed or that is superseded is shown as OUTDATED.
* A proposition can be VERIFIED only when a verified, current PRIMARY source
  supports it; differing authority must be addressed in the CA note.
* A document quote linked as a fact must actually occur in that document.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import date
from urllib.parse import urlparse

from ..core import audit
from ..core.db import ro, row_to_dict, tx, utcnow
from ..core.errors import NotFound, PermissionDenied, ValidationError
from . import cases

SOURCE_CLASSES = ("PRIMARY", "SECONDARY", "AI_SUGGESTION")
SOURCE_TYPES = ("ACT_SECTION", "RULE", "NOTIFICATION", "CIRCULAR", "INSTRUCTION", "CASE_LAW",
                "COMMENTARY", "ARTICLE", "AI_OUTPUT", "OTHER")
COURT_LEVELS = ("SUPREME_COURT", "HIGH_COURT", "ITAT", "AAR_BAR", "OTHER")
ACTS = ("IT_ACT_1961", "IT_ACT_2025", "IT_RULES_1962", "IT_RULES_2026", "OTHER")
STANCES = ("SUPPORTS", "DIFFERS", "DISTINGUISHABLE", "CONTEXT")
SOURCE_DECISIONS = ("VERIFIED", "UNVERIFIED", "OUTDATED", "NEEDS_CA_REVIEW")
PROP_DECISIONS = ("VERIFIED", "UNVERIFIED", "NEEDS_CA_REVIEW", "REJECTED")
FACT_TYPES = ("NOTICE_TEXT", "DOCUMENT_SPAN", "EVIDENCE_ITEM", "RECON_RUN", "CLIENT_EXPLANATION", "ASSUMPTION")
BASES = ("ESTABLISHED", "DOCUMENT_AVAILABLE", "CLIENT_EXPLANATION", "ASSUMPTION", "UNRESOLVED")

# Government domains. Being on one of these shows the link is an official
# publication channel; it does not by itself make a proposition correct.
OFFICIAL_SUFFIXES = (".gov.in", ".nic.in")
OFFICIAL_HOSTS = {"gov.in", "nic.in"}

# Where a CA can look things up. These are portal home pages, not citations.
OFFICIAL_PORTALS = [
    {"name": "Income Tax Department — Acts, Rules, Circulars, Notifications", "url": "https://incometaxindia.gov.in"},
    {"name": "e-Filing portal (notices, responses)", "url": "https://www.incometax.gov.in"},
    {"name": "India Code (central Acts)", "url": "https://www.indiacode.nic.in"},
    {"name": "e-Gazette of India", "url": "https://egazette.gov.in"},
    {"name": "Supreme Court of India — judgments", "url": "https://www.sci.gov.in"},
    {"name": "Income Tax Appellate Tribunal — orders", "url": "https://itat.gov.in"},
]

_EDITABLE = ("source_class", "source_type", "title", "citation", "issuing_body", "court_level", "document_number",
             "date_issued", "effective_from", "effective_to", "act", "provision", "pinpoint", "excerpt", "summary",
             "applicability_note", "ay_from", "ay_to", "official_url", "superseded_by")
_HASHED = ("source_class", "source_type", "title", "citation", "issuing_body", "court_level", "document_number",
           "date_issued", "effective_from", "effective_to", "act", "provision", "pinpoint", "excerpt",
           "applicability_note", "ay_from", "ay_to", "official_url", "superseded_by")

UNVERIFIED_LAW_NOTICE = ("Legal sources shown here are a research aid. Only items marked VERIFIED have been checked by a CA "
                         "against the primary source for this assessment year. Everything else must not be relied on.")


# ------------------------------------------------------------------ helpers
def is_official_url(url: str | None) -> bool:
    if not url:
        return False
    try:
        u = urlparse(url.strip())
    except ValueError:
        return False
    host = (u.hostname or "").lower()
    return u.scheme == "https" and (host in OFFICIAL_HOSTS or host.endswith(OFFICIAL_SUFFIXES))


def _valid_url(url: str | None) -> None:
    if url is None or url == "":
        return
    u = urlparse(url.strip())
    if u.scheme not in ("https", "http") or not u.hostname:
        raise ValidationError("Source link must be a full web address starting with https://")


def _valid_date(v: str | None, label: str) -> None:
    if v and not re.match(r"^\d{4}-\d{2}-\d{2}$", v):
        raise ValidationError(f"{label} must be in YYYY-MM-DD format.")


def _source_hash(src: dict) -> str:
    payload = json.dumps({k: src.get(k) for k in _HASHED}, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip().lower()


def _require_ca(user: dict, what: str) -> None:
    if user["role"] not in ("CA", "ADMIN"):
        raise PermissionDenied(f"Only a CA can {what}.")


# ------------------------------------------------------------------ sources
def effective_source_status(src: dict, today: date | None = None) -> str:
    """Status the UI should show. A stored VERIFIED can decay to OUTDATED / NEEDS_CA_REVIEW."""
    today = today or date.today()
    st = src["status"]
    if src.get("source_class") == "AI_SUGGESTION" and st == "VERIFIED":
        return "NEEDS_CA_REVIEW"
    if src.get("superseded_by") or (src.get("effective_to") and src["effective_to"] < today.isoformat()):
        return "OUTDATED"
    if st == "VERIFIED" and src.get("verified_hash") != src.get("content_hash"):
        return "NEEDS_CA_REVIEW"
    return st


def _view(src: dict) -> dict:
    src = dict(src)
    src["effective_status"] = effective_source_status(src)
    src["url_is_official"] = bool(src.get("url_is_official"))
    src["class_label"] = {"PRIMARY": "Primary source", "SECONDARY": "Secondary commentary",
                          "AI_SUGGESTION": "AI suggestion — not an authority"}[src["source_class"]]
    return src


def _validate_source(f: dict) -> None:
    if f.get("source_class") not in SOURCE_CLASSES:
        raise ValidationError(f"source_class must be one of {SOURCE_CLASSES}.")
    if f.get("source_type") not in SOURCE_TYPES:
        raise ValidationError(f"source_type must be one of {SOURCE_TYPES}.")
    if f["source_class"] == "AI_SUGGESTION" and f["source_type"] != "AI_OUTPUT":
        raise ValidationError("An AI suggestion must use source_type AI_OUTPUT.")
    if f["source_type"] == "AI_OUTPUT" and f["source_class"] != "AI_SUGGESTION":
        raise ValidationError("AI_OUTPUT can only be recorded as an AI_SUGGESTION.")
    if f["source_class"] == "PRIMARY" and f["source_type"] in ("COMMENTARY", "ARTICLE"):
        raise ValidationError("Commentary and articles are secondary sources.")
    if not (f.get("title") or "").strip():
        raise ValidationError("Title is required.")
    if f.get("court_level") and f["court_level"] not in COURT_LEVELS:
        raise ValidationError(f"court_level must be one of {COURT_LEVELS}.")
    if f.get("act") and f["act"] not in ACTS:
        raise ValidationError(f"act must be one of {ACTS}.")
    for k in ("date_issued", "effective_from", "effective_to"):
        _valid_date(f.get(k), k)
    _valid_url(f.get("official_url"))
    if f.get("excerpt") and len(f["excerpt"]) > 2000:
        raise ValidationError("Keep the excerpt to the relevant paragraph (2,000 characters max).")


def get_source(source_id: int) -> dict:
    with ro() as conn:
        r = conn.execute("SELECT * FROM legal_sources WHERE id=?", (source_id,)).fetchone()
        if not r:
            raise NotFound("Legal source not found.")
        hist = conn.execute(
            "SELECT v.*, u.full_name AS decided_by_name FROM verification_log v JOIN users u ON u.id=v.decided_by "
            "WHERE entity_type='SOURCE' AND entity_id=? ORDER BY v.id DESC", (source_id,)).fetchall()
    d = _view(row_to_dict(r))
    d["verification_history"] = [row_to_dict(h) for h in hist]
    return d


def list_sources(*, source_class: str | None = None, status: str | None = None, q: str | None = None) -> list[dict]:
    sql, args = "SELECT * FROM legal_sources WHERE 1=1", []
    if source_class:
        sql += " AND source_class=?"
        args.append(source_class)
    if q:
        sql += " AND (title LIKE ? OR citation LIKE ? OR provision LIKE ?)"
        args += [f"%{q}%"] * 3
    with ro() as conn:
        rows = [_view(row_to_dict(r)) for r in conn.execute(sql + " ORDER BY source_class, title", args)]
    if status:
        rows = [r for r in rows if r["effective_status"] == status]
    return rows


def add_source(user: dict, **f) -> dict:
    f = {k: (v.strip() if isinstance(v, str) else v) or None for k, v in f.items() if k in _EDITABLE + ("source_key", "origin")}
    _validate_source(f)
    f.setdefault("origin", "USER")
    if f["origin"] not in ("USER", "AI", "SEED", "IMPORTED_REGISTRY"):
        raise ValidationError("Invalid origin.")
    key = f.get("source_key") or f"SRC-{hashlib.sha1((f['title'] + utcnow()).encode()).hexdigest()[:10].upper()}"
    now = utcnow()
    f["url_is_official"] = int(is_official_url(f.get("official_url")))
    f["content_hash"] = _source_hash(f)
    cols = [k for k in _EDITABLE if k in f] + ["source_key", "origin", "url_is_official", "content_hash", "status",
                                               "created_by", "created_at", "updated_at"]
    vals = [f[k] for k in _EDITABLE if k in f] + [key, f["origin"], f["url_is_official"], f["content_hash"], "UNVERIFIED",
                                                  user["id"], now, now]
    with tx() as conn:
        if conn.execute("SELECT 1 FROM legal_sources WHERE source_key=?", (key,)).fetchone():
            raise ValidationError("A source with this key already exists.")
        sid = conn.execute(f"INSERT INTO legal_sources({','.join(cols)}) VALUES ({','.join('?' * len(cols))})", vals).lastrowid
        audit.log_event(conn, "LEGAL_SOURCE_ADDED", user_id=user["id"],
                        meta={"source_id": sid, "class": f["source_class"], "type": f["source_type"], "origin": f["origin"]})
    return get_source(sid)


def update_source(user: dict, source_id: int, updates: dict) -> dict:
    cur = get_source(source_id)
    bad = set(updates) - set(_EDITABLE)
    if bad:
        raise ValidationError(f"Fields cannot be edited: {sorted(bad)}")
    merged = {k: cur.get(k) for k in _EDITABLE}
    merged.update({k: (v.strip() if isinstance(v, str) else v) or None for k, v in updates.items()})
    _validate_source(merged)
    new_hash = _source_hash(merged)
    if new_hash == cur["content_hash"]:
        return cur
    with tx() as conn:
        sets = ", ".join(f"{k}=?" for k in _EDITABLE)
        conn.execute(f"UPDATE legal_sources SET {sets}, url_is_official=?, content_hash=?, updated_at=?"
                     + (", status='NEEDS_CA_REVIEW'" if cur["status"] == "VERIFIED" else "") + " WHERE id=?",
                     [merged[k] for k in _EDITABLE] + [int(is_official_url(merged.get("official_url"))), new_hash, utcnow(), source_id])
        audit.log_event(conn, "LEGAL_SOURCE_EDITED", user_id=user["id"],
                        meta={"source_id": source_id, "fields": sorted(updates), "was_verified": cur["status"] == "VERIFIED"})
    return get_source(source_id)


def decide_source(user: dict, source_id: int, *, decision: str, checked_url: str | None = None,
                  checked_pinpoint: str | None = None, applicability_confirmed: bool = False, note: str = "") -> dict:
    if decision not in SOURCE_DECISIONS:
        raise ValidationError(f"decision must be one of {SOURCE_DECISIONS}.")
    src = get_source(source_id)
    if decision in ("VERIFIED", "OUTDATED"):
        _require_ca(user, "verify or retire a legal source")
    if decision == "VERIFIED":
        problems = []
        if src["source_class"] == "AI_SUGGESTION":
            problems.append("An AI suggestion cannot be verified as an authority. Add the primary source it points to and verify that instead.")
        if not src.get("official_url"):
            problems.append("Add the link to the source you checked.")
        if src["source_class"] == "PRIMARY" and not src.get("url_is_official"):
            problems.append("A primary source must be verified from an official government link (https, .gov.in / .nic.in).")
        if (checked_url or "").strip() != (src.get("official_url") or ""):
            problems.append("Open the source link and confirm it by entering the same URL as 'checked URL'.")
        if not (checked_pinpoint or src.get("pinpoint")):
            problems.append("Record the exact paragraph, section or sub-rule you checked.")
        if not applicability_confirmed:
            problems.append("Confirm applicability (Act, AY/Tax Year, effective dates, transition provisions).")
        if src["source_type"] == "CASE_LAW" and not (src.get("citation") and src.get("court_level") and src.get("date_issued")):
            problems.append("A judgment needs its full citation, court and date of decision.")
        if src["source_type"] in ("CIRCULAR", "NOTIFICATION", "INSTRUCTION") and not (src.get("document_number") and src.get("date_issued")):
            problems.append("A circular/notification needs its number and date.")
        if src["source_type"] in ("ACT_SECTION", "RULE") and not (src.get("act") and src.get("provision")):
            problems.append("A statutory provision needs the Act/Rules and the section/rule number.")
        if effective_source_status({**src, "status": "UNVERIFIED"}) == "OUTDATED":
            problems.append("This source is outdated (effective_to has passed or it is superseded). Mark it OUTDATED instead.")
        if problems:
            raise ValidationError("Cannot mark VERIFIED yet.", details={"problems": problems})
    now = utcnow()
    with tx() as conn:
        conn.execute("UPDATE legal_sources SET status=?, verified_hash=?, pinpoint=COALESCE(pinpoint, ?), updated_at=? WHERE id=?",
                     (decision, src["content_hash"] if decision == "VERIFIED" else None, checked_pinpoint, now, source_id))
        if decision == "VERIFIED" and not src.get("pinpoint") and checked_pinpoint:
            # pinpoint became part of the record, so re-hash and re-bind the verification to it
            fresh = row_to_dict(conn.execute("SELECT * FROM legal_sources WHERE id=?", (source_id,)).fetchone())
            h = _source_hash(fresh)
            conn.execute("UPDATE legal_sources SET content_hash=?, verified_hash=? WHERE id=?", (h, h, source_id))
        conn.execute(
            "INSERT INTO verification_log(entity_type,entity_id,decision,checked_url,checked_pinpoint,applicability_confirmed,"
            "note,content_hash,decided_by,decided_at) VALUES ('SOURCE',?,?,?,?,?,?,?,?,?)",
            (source_id, decision, checked_url, checked_pinpoint, int(applicability_confirmed), note, src["content_hash"], user["id"], now))
        audit.log_event(conn, "LEGAL_SOURCE_DECISION", user_id=user["id"],
                        meta={"source_id": source_id, "decision": decision, "content_hash": src["content_hash"]})
    return get_source(source_id)


_REGTYPE = {"STATUTE": "ACT_SECTION", "RULE": "RULE", "CIRCULAR": "CIRCULAR", "NOTIFICATION": "NOTIFICATION",
            "JUDGMENT": "CASE_LAW", "PRACTICE_NOTE": "COMMENTARY"}


def import_registry(system_user_id: int | None = None) -> int:
    """Copy V2 registry entries into legal_sources once. Never marks anything verified."""
    n = 0
    now = utcnow()
    with tx() as conn:
        refs = [row_to_dict(r) for r in conn.execute("SELECT * FROM legal_refs")]
        for r in refs:
            key = f"REG:{r['ref_key']}"
            existing = conn.execute("SELECT * FROM legal_sources WHERE source_key=?", (key,)).fetchone()
            if existing:
                # back-fill an official link into an untouched, unverified imported entry (never a verified one)
                ex = row_to_dict(existing)
                if (ex["origin"] == "IMPORTED_REGISTRY" and ex["status"] == "UNVERIFIED" and not ex.get("official_url")
                        and r.get("source_url")):
                    ex["official_url"] = r["source_url"]
                    conn.execute("UPDATE legal_sources SET official_url=?, url_is_official=?, content_hash=?, updated_at=? WHERE id=?",
                                 (r["source_url"], int(is_official_url(r["source_url"])), _source_hash(ex), now, ex["id"]))
                continue
            stype = _REGTYPE.get(r.get("ref_type") or "STATUTE", "OTHER")
            act_txt = (r.get("act") or "")
            act = "IT_ACT_1961" if "1961" in act_txt else "IT_ACT_2025" if "2025" in act_txt else "OTHER"
            is_case = stype == "CASE_LAW"
            f = {"source_class": "SECONDARY" if stype == "COMMENTARY" else "PRIMARY", "source_type": stype,
                 "title": (f"{r['provision']} — {r['title']}" if is_case else f"{r['act']} — {r['provision']}: {r['title']}"),
                 "act": None if is_case else act, "provision": None if is_case else r["provision"],
                 "citation": r["provision"] if is_case else None,
                 "court_level": "SUPREME_COURT" if is_case and "supreme" in (r.get("act") or "").lower() else None,
                 "summary": r["summary"], "official_url": r.get("source_url"), "effective_from": r.get("effective_from"),
                 "effective_to": r.get("effective_to"), "applicability_note": r.get("applies_to")}
            for k in ("effective_from", "effective_to"):
                if f[k] and not re.match(r"^\d{4}-\d{2}-\d{2}$", f[k]):
                    f[k] = None
            f["content_hash"] = _source_hash(f)
            # A V2 'VERIFIED' lacked pinpoint/applicability evidence, so it comes across as NEEDS_CA_REVIEW.
            status = "NEEDS_CA_REVIEW" if r["status"] == "VERIFIED" else "UNVERIFIED"
            conn.execute(
                "INSERT INTO legal_sources(source_key,source_class,source_type,title,act,provision,summary,official_url,"
                "url_is_official,effective_from,effective_to,applicability_note,status,origin,content_hash,created_by,created_at,updated_at,"
                "citation,court_level)"
                " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,'IMPORTED_REGISTRY',?,?,?,?,?,?)",
                (key, f["source_class"], stype, f["title"], f["act"], f["provision"], f["summary"], f["official_url"],
                 int(is_official_url(f["official_url"])), f["effective_from"], f["effective_to"], f["applicability_note"],
                 status, f["content_hash"], system_user_id, now, now, f["citation"], f["court_level"]))
            n += 1
    return n


def _source_id_for_ref(conn, ref_key: str) -> int | None:
    r = conn.execute("SELECT id FROM legal_sources WHERE source_key=?", (f"REG:{ref_key}",)).fetchone()
    return r["id"] if r else None


# ------------------------------------------------------------- propositions
def _prop_hash(conn, prop_id: int) -> str:
    p = conn.execute("SELECT text, kind FROM propositions WHERE id=?", (prop_id,)).fetchone()
    links = conn.execute("SELECT source_id, stance, COALESCE(pinpoint,'') FROM proposition_sources WHERE proposition_id=? "
                         "ORDER BY source_id", (prop_id,)).fetchall()
    facts = conn.execute("SELECT fact_type, basis, COALESCE(document_id,0), COALESCE(quote,''), COALESCE(evidence_item_id,0), "
                         "COALESCE(recon_run_id,0) FROM proposition_facts WHERE proposition_id=? ORDER BY id", (prop_id,)).fetchall()
    payload = json.dumps([p["text"], p["kind"], [list(x) for x in links], [list(x) for x in facts]], ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _get_prop_row(prop_id: int) -> dict:
    with ro() as conn:
        r = conn.execute("SELECT * FROM propositions WHERE id=?", (prop_id,)).fetchone()
    if not r:
        raise NotFound("Proposition not found.")
    return row_to_dict(r)


def add_proposition(user: dict, case_id: int, text: str, *, issue_id: int | None = None, kind: str = "LEGAL",
                    origin: str = "USER") -> dict:
    cases.check_access(user, case_id)
    if kind not in ("LEGAL", "FACTUAL", "MIXED") or origin not in ("SYSTEM", "USER", "AI"):
        raise ValidationError("Invalid kind or origin.")
    if not (text or "").strip():
        raise ValidationError("Proposition text is required.")
    now = utcnow()
    with tx() as conn:
        if issue_id is not None:
            r = conn.execute("SELECT case_id FROM issues WHERE id=?", (issue_id,)).fetchone()
            if not r or r["case_id"] != case_id:
                raise ValidationError("Issue does not belong to this case.")
        pid = conn.execute("INSERT INTO propositions(case_id,issue_id,text,kind,origin,status,created_by,created_at,updated_at)"
                           " VALUES (?,?,?,?,?,'UNVERIFIED',?,?,?)",
                           (case_id, issue_id, text.strip(), kind, origin, user["id"], now, now)).lastrowid
        audit.log_event(conn, "PROPOSITION_ADDED", user_id=user["id"], case_id=case_id,
                        meta={"proposition_id": pid, "issue_id": issue_id, "origin": origin})
    return proposition_view(user, pid)


def _touch_prop(conn, prop_id: int) -> None:
    conn.execute("UPDATE propositions SET updated_at=?, status=CASE WHEN status='VERIFIED' THEN 'NEEDS_CA_REVIEW' ELSE status END "
                 "WHERE id=?", (utcnow(), prop_id))


def edit_proposition(user: dict, prop_id: int, text: str) -> dict:
    p = _get_prop_row(prop_id)
    cases.check_access(user, p["case_id"])
    if not text.strip():
        raise ValidationError("Proposition text is required.")
    with tx() as conn:
        conn.execute("UPDATE propositions SET text=? WHERE id=?", (text.strip(), prop_id))
        _touch_prop(conn, prop_id)
        audit.log_event(conn, "PROPOSITION_EDITED", user_id=user["id"], case_id=p["case_id"], meta={"proposition_id": prop_id})
    return proposition_view(user, prop_id)


def link_source(user: dict, prop_id: int, source_id: int, *, stance: str, relevance_note: str = "", pinpoint: str | None = None) -> dict:
    p = _get_prop_row(prop_id)
    cases.check_access(user, p["case_id"])
    if stance not in STANCES:
        raise ValidationError(f"stance must be one of {STANCES}.")
    get_source(source_id)
    with tx() as conn:
        conn.execute("INSERT OR REPLACE INTO proposition_sources(proposition_id,source_id,stance,relevance_note,pinpoint,added_by,added_at)"
                     " VALUES (?,?,?,?,?,?,?)", (prop_id, source_id, stance, relevance_note, pinpoint, user["id"], utcnow()))
        _touch_prop(conn, prop_id)
        audit.log_event(conn, "PROPOSITION_SOURCE_LINKED", user_id=user["id"], case_id=p["case_id"],
                        meta={"proposition_id": prop_id, "source_id": source_id, "stance": stance})
    return proposition_view(user, prop_id)


def unlink_source(user: dict, prop_id: int, source_id: int) -> dict:
    p = _get_prop_row(prop_id)
    cases.check_access(user, p["case_id"])
    with tx() as conn:
        conn.execute("DELETE FROM proposition_sources WHERE proposition_id=? AND source_id=?", (prop_id, source_id))
        _touch_prop(conn, prop_id)
        audit.log_event(conn, "PROPOSITION_SOURCE_UNLINKED", user_id=user["id"], case_id=p["case_id"],
                        meta={"proposition_id": prop_id, "source_id": source_id})
    return proposition_view(user, prop_id)


def add_fact(user: dict, prop_id: int, *, fact_type: str, basis: str, document_id: int | None = None, page: int | None = None,
             quote: str | None = None, evidence_item_id: int | None = None, recon_run_id: int | None = None, note: str = "") -> dict:
    p = _get_prop_row(prop_id)
    cases.check_access(user, p["case_id"])
    if fact_type not in FACT_TYPES or basis not in BASES:
        raise ValidationError("Invalid fact type or basis.")
    quote = (quote or "").strip() or None
    if quote and len(quote) > 600:
        raise ValidationError("Keep the quoted passage short (600 characters max).")
    with ro() as conn:
        if fact_type in ("NOTICE_TEXT", "DOCUMENT_SPAN"):
            if not document_id or not quote:
                raise ValidationError("A document fact needs the document and the exact quoted words.")
            d = conn.execute("SELECT d.case_id, t.text FROM documents d LEFT JOIN doc_text t ON t.document_id=d.id WHERE d.id=?",
                             (document_id,)).fetchone()
            if not d or d["case_id"] != p["case_id"]:
                raise ValidationError("Document does not belong to this case.")
            if _norm(quote) not in _norm(d["text"] or ""):
                raise ValidationError("The quoted words were not found in that document. Copy them exactly from the extracted text.")
        if fact_type == "EVIDENCE_ITEM":
            e = conn.execute("SELECT case_id FROM evidence_items WHERE id=?", (evidence_item_id or 0,)).fetchone()
            if not e or e["case_id"] != p["case_id"]:
                raise ValidationError("Evidence item does not belong to this case.")
        if fact_type == "RECON_RUN":
            rr = conn.execute("SELECT case_id FROM recon_runs WHERE id=?", (recon_run_id or 0,)).fetchone()
            if not rr or rr["case_id"] != p["case_id"]:
                raise ValidationError("Reconciliation run does not belong to this case.")
        if fact_type == "CLIENT_EXPLANATION" and basis not in ("CLIENT_EXPLANATION", "UNRESOLVED"):
            raise ValidationError("A client explanation stays a client explanation until supported by evidence.")
        if fact_type == "ASSUMPTION" and basis != "ASSUMPTION":
            raise ValidationError("An assumption must be labelled as an assumption.")
    with tx() as conn:
        fid = conn.execute(
            "INSERT INTO proposition_facts(proposition_id,fact_type,basis,document_id,page,quote,evidence_item_id,recon_run_id,note,"
            "added_by,added_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (prop_id, fact_type, basis, document_id, page, quote, evidence_item_id, recon_run_id, note, user["id"], utcnow())).lastrowid
        _touch_prop(conn, prop_id)
        audit.log_event(conn, "PROPOSITION_FACT_ADDED", user_id=user["id"], case_id=p["case_id"],
                        meta={"proposition_id": prop_id, "fact_id": fid, "fact_type": fact_type, "basis": basis})
    return proposition_view(user, prop_id)


def remove_fact(user: dict, fact_id: int) -> dict:
    with ro() as conn:
        r = conn.execute("SELECT proposition_id FROM proposition_facts WHERE id=?", (fact_id,)).fetchone()
    if not r:
        raise NotFound("Fact link not found.")
    p = _get_prop_row(r["proposition_id"])
    cases.check_access(user, p["case_id"])
    with tx() as conn:
        conn.execute("DELETE FROM proposition_facts WHERE id=?", (fact_id,))
        _touch_prop(conn, p["id"])
        audit.log_event(conn, "PROPOSITION_FACT_REMOVED", user_id=user["id"], case_id=p["case_id"],
                        meta={"proposition_id": p["id"], "fact_id": fact_id})
    return proposition_view(user, p["id"])


def _prop_checks(pv: dict) -> list[str]:
    """Reasons why a proposition cannot (yet) be VERIFIED. Empty list = eligible."""
    problems = []
    support = [s for s in pv["sources"] if s["stance"] == "SUPPORTS"]
    good = [s for s in support if s["source_class"] == "PRIMARY" and s["effective_status"] == "VERIFIED"]
    if pv["kind"] in ("LEGAL", "MIXED") and not good:
        problems.append("No verified, current primary source supports this proposition.")
    if pv["kind"] in ("FACTUAL", "MIXED") and not any(f["basis"] in ("ESTABLISHED", "DOCUMENT_AVAILABLE") for f in pv["facts"]):
        problems.append("No fact established by a document is linked.")
    if any(f["basis"] in ("ASSUMPTION", "CLIENT_EXPLANATION", "UNRESOLVED") for f in pv["facts"]):
        problems.append("Some linked facts are assumptions, unconfirmed client explanations or unresolved — "
                        "the CA note must say how they are handled.")
    return problems


def proposition_view(user: dict, prop_id: int) -> dict:
    p = _get_prop_row(prop_id)
    cases.check_access(user, p["case_id"])
    with ro() as conn:
        srcs = conn.execute("SELECT ls.*, ps.stance, ps.relevance_note, ps.pinpoint AS link_pinpoint FROM proposition_sources ps "
                            "JOIN legal_sources ls ON ls.id=ps.source_id WHERE ps.proposition_id=? ORDER BY ps.stance, ls.title",
                            (prop_id,)).fetchall()
        facts = conn.execute(
            "SELECT f.*, d.original_name AS document_name, e.requirement AS evidence_requirement, e.status AS evidence_status, "
            "r.recon_type FROM proposition_facts f LEFT JOIN documents d ON d.id=f.document_id "
            "LEFT JOIN evidence_items e ON e.id=f.evidence_item_id LEFT JOIN recon_runs r ON r.id=f.recon_run_id "
            "WHERE f.proposition_id=? ORDER BY f.id", (prop_id,)).fetchall()
        current_hash = _prop_hash(conn, prop_id)
        hist = conn.execute("SELECT v.decision, v.note, v.decided_at, u.full_name AS decided_by_name FROM verification_log v "
                            "JOIN users u ON u.id=v.decided_by WHERE entity_type='PROPOSITION' AND entity_id=? ORDER BY v.id DESC",
                            (prop_id,)).fetchall()
    pv = dict(p)
    pv["sources"] = [_view(row_to_dict(s)) for s in srcs]
    pv["facts"] = [row_to_dict(f) for f in facts]
    pv["verification_history"] = [row_to_dict(h) for h in hist]
    checks = _prop_checks(pv)
    hard = [x for x in checks if not x.startswith("Some linked facts")]
    status = p["status"]
    if status == "VERIFIED" and (p.get("verified_hash") != current_hash or hard):
        status = "NEEDS_CA_REVIEW"
    pv["effective_status"] = status
    pv["blocking_reasons"] = checks
    pv["differing_authorities"] = [s for s in pv["sources"] if s["stance"] in ("DIFFERS", "DISTINGUISHABLE")]
    pv["origin_label"] = {"SYSTEM": "System-generated starting point", "USER": "Entered by user",
                          "AI": "AI suggestion — not a professional opinion"}[p["origin"]]
    return pv


def decide_proposition(user: dict, prop_id: int, *, decision: str, note: str = "") -> dict:
    if decision not in PROP_DECISIONS:
        raise ValidationError(f"decision must be one of {PROP_DECISIONS}.")
    pv = proposition_view(user, prop_id)
    if decision in ("VERIFIED", "REJECTED"):
        _require_ca(user, "accept or reject a proposition")
    if decision == "VERIFIED":
        problems = [x for x in pv["blocking_reasons"] if not x.startswith("Some linked facts")]
        if problems:
            raise ValidationError("Cannot mark VERIFIED yet.", details={"problems": problems})
        if (pv["differing_authorities"] or any(x.startswith("Some linked facts") for x in pv["blocking_reasons"])) and len(note.strip()) < 20:
            raise ValidationError("Explain in the CA note how the differing authorities / unconfirmed facts are dealt with.",
                                  details={"problems": ["CA note required (at least 20 characters)."]})
    now = utcnow()
    with tx() as conn:
        h = _prop_hash(conn, prop_id)
        conn.execute("UPDATE propositions SET status=?, ca_note=?, verified_hash=?, decided_by=?, decided_at=?, updated_at=? WHERE id=?",
                     (decision, note or None, h if decision == "VERIFIED" else None, user["id"], now, now, prop_id))
        conn.execute("INSERT INTO verification_log(entity_type,entity_id,case_id,decision,note,content_hash,decided_by,decided_at)"
                     " VALUES ('PROPOSITION',?,?,?,?,?,?,?)", (prop_id, pv["case_id"], decision, note, h, user["id"], now))
        audit.log_event(conn, "PROPOSITION_DECISION", user_id=user["id"], case_id=pv["case_id"],
                        meta={"proposition_id": prop_id, "decision": decision, "content_hash": h})
    return proposition_view(user, prop_id)


def seed_issue_propositions(user: dict, issue_id: int) -> list[dict]:
    """Create one SYSTEM starting-point proposition per issue (idempotent).

    It carries the rule-based balanced view as text, the notice query as its
    first fact (quoted from the notice), and the candidate provisions as
    CONTEXT links. It starts UNVERIFIED and states no conclusion."""
    with ro() as conn:
        iss = conn.execute("SELECT i.*, n.document_id FROM issues i LEFT JOIN notices n ON n.id=i.notice_id WHERE i.id=?",
                           (issue_id,)).fetchone()
        if not iss:
            raise NotFound("Issue not found.")
        iss = row_to_dict(iss, ("analysis_json",))
        exists = conn.execute("SELECT id FROM propositions WHERE issue_id=? AND origin='SYSTEM'", (issue_id,)).fetchone()
    cases.check_access(user, iss["case_id"])
    if exists:
        return [proposition_view(user, exists["id"])]
    import_registry(user["id"])
    a = iss["analysis_json"] or {}
    balanced = (a.get("perspectives") or {}).get("balanced") or "[CA to state the proposed view]"
    text = f"Proposed view for CA review (no conclusion yet): {balanced}"
    pv = add_proposition(user, iss["case_id"], text, issue_id=issue_id, kind="MIXED", origin="SYSTEM")
    if iss.get("document_id"):
        q = iss["query_text"].strip()
        with ro() as conn:
            t = conn.execute("SELECT text FROM doc_text WHERE document_id=?", (iss["document_id"],)).fetchone()
        if t and _norm(q[:300]) in _norm(t["text"]):
            add_fact(user, pv["id"], fact_type="NOTICE_TEXT", basis="ESTABLISHED", document_id=iss["document_id"],
                     quote=q[:300], note="The Department's question as it appears in the notice.")
    with ro() as conn:
        ids = [_source_id_for_ref(conn, k) for k in a.get("candidate_provisions_to_examine", [])]
    for sid in [i for i in ids if i]:
        link_source(user, pv["id"], sid, stance="CONTEXT", relevance_note="Candidate provision to examine — applicability not decided.")
    return [proposition_view(user, pv["id"])]


def record_ai_suggestion(user: dict, case_id: int, *, issue_id: int | None, proposition_text: str,
                         claimed_citation: str | None, claimed_url: str | None, submission_id: int | None = None) -> dict:
    """Store an AI reply as an AI_SUGGESTION source + AI proposition. Never verifiable as is."""
    cases.check_access(user, case_id)
    src = add_source(user, source_class="AI_SUGGESTION", source_type="AI_OUTPUT",
                     title=f"AI suggestion{f' (submission {submission_id})' if submission_id else ''}",
                     citation=(f"AS CLAIMED BY AI — NOT CHECKED: {claimed_citation}" if claimed_citation else None),
                     official_url=claimed_url if claimed_url and urlparse(claimed_url).scheme in ("http", "https") else None,
                     summary="Recorded from an AI reply. Find and verify the primary source before relying on it.", origin="AI")
    pv = add_proposition(user, case_id, proposition_text, issue_id=issue_id, kind="LEGAL", origin="AI")
    return link_source(user, pv["id"], src["id"], stance="SUPPORTS", relevance_note="AI-claimed support; unverified.")


# ------------------------------------------------------------------- trace
def issue_trace(user: dict, issue_id: int) -> dict:
    """Everything behind an issue, for the side panel: notice → facts → evidence → propositions → sources."""
    with ro() as conn:
        iss = conn.execute("SELECT i.*, n.document_id AS notice_document_id FROM issues i LEFT JOIN notices n ON n.id=i.notice_id "
                           "WHERE i.id=?", (issue_id,)).fetchone()
        if not iss:
            raise NotFound("Issue not found.")
        iss = row_to_dict(iss, ("analysis_json",))
        cases.check_access(user, iss["case_id"])
        ev = conn.execute("SELECT e.*, d.original_name AS document_name, d.extraction_status FROM evidence_items e "
                          "LEFT JOIN documents d ON d.id=e.document_id WHERE e.issue_id=? ORDER BY e.id", (issue_id,)).fetchall()
        recon = conn.execute("SELECT id, recon_type, created_at, result_json FROM recon_runs WHERE case_id=? ORDER BY id DESC LIMIT 10",
                             (iss["case_id"],)).fetchall()
        pids = [r["id"] for r in conn.execute("SELECT id FROM propositions WHERE issue_id=? ORDER BY origin='SYSTEM' DESC, id",
                                              (issue_id,))]
        notice_doc = None
        if iss.get("notice_document_id"):
            nd = conn.execute("SELECT id, original_name, extraction_status FROM documents WHERE id=?",
                              (iss["notice_document_id"],)).fetchone()
            notice_doc = row_to_dict(nd)
    props = [proposition_view(user, pid) for pid in pids]
    recon_runs = []
    for r in recon:
        try:
            res = json.loads(r["result_json"])
        except Exception:
            res = {}
        recon_runs.append({"id": r["id"], "recon_type": r["recon_type"], "created_at": r["created_at"],
                           "status": res.get("status") if isinstance(res, dict) else None,
                           "note": "A reconciliation PASS shows internal consistency only, not source or genuineness."})
    warnings = []
    if notice_doc and notice_doc.get("extraction_status") in ("PARTIAL", "OCR"):
        warnings.append("The notice was read by OCR or only partly read — check the quoted question against the original.")
    if not props:
        warnings.append("No proposition has been recorded for this issue yet.")
    for p in props:
        if p["effective_status"] != "VERIFIED":
            warnings.append(f"Proposition #{p['id']} is {p['effective_status'].replace('_', ' ').lower()} — do not rely on it in the reply yet.")
        for s in p["sources"]:
            if s["effective_status"] == "OUTDATED":
                warnings.append(f"Source '{s['title']}' is outdated.")
            if s["source_class"] == "AI_SUGGESTION":
                warnings.append(f"Proposition #{p['id']} relies on an AI suggestion; find the primary source.")
        if p["differing_authorities"]:
            warnings.append(f"Proposition #{p['id']} has differing authority — the CA must address it.")
    missing = [row_to_dict(e) for e in ev if e["status"] in ("NOT_PROVIDED", "INSUFFICIENT", "CONTRADICTORY")]
    if missing:
        warnings.append(f"{len(missing)} evidence requirement(s) are missing, insufficient or contradictory.")
    try:
        from .issues import _requirements

        labels = {r["key"]: r["label"] for r in _requirements().get(iss["category"], {}).get("requirements", [])}
    except Exception:
        labels = {}
    evidence = [dict(row_to_dict(e), requirement_label=labels.get(e["requirement"], e["requirement"].replace("_", " "))) for e in ev]
    return {
        "issue": {k: iss[k] for k in ("id", "case_id", "seq", "query_text", "category", "amount", "strategy", "strategy_reason")},
        "analysis": iss["analysis_json"],
        "notice_document": notice_doc,
        "evidence": evidence,
        "reconciliations": recon_runs,
        "propositions": props,
        "warnings": list(dict.fromkeys(warnings)),
        "portals": OFFICIAL_PORTALS,
        "disclaimer": UNVERIFIED_LAW_NOTICE,
    }
