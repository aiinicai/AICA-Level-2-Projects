"""Name detection and the organize review queue.

Detection order:
 1. Names from the project's client list (and aliases), matched as whole words, case-insensitive.
 2. If none: label-based suggestions such as 'Client: ...', 'Name: ...', 'M/s ...' (marked unconfirmed).
Every detection carries a short source excerpt and a page/paragraph reference.
Statuses: Detected | Several names | Suggestion | Manual review | Name confirmed | Skipped | Moved | Move failed
"""
from __future__ import annotations

import json
import os
import re

from .paths import now_iso
from .store import ProjectDB
from .textextract import IMAGE_EXTS, cached_extract

ORGANIZE_EXTS = {"pdf", "docx"} | IMAGE_EXTS

LABEL_RE = re.compile(
    r"(?:\b(?:Client|Customer|Party|Assessee|Name of (?:the )?(?:Client|Assessee|Party)|Bill(?:ed)? To|Name)\s*[:\-]\s*"
    r"|\bM/[sS]\.?\s+|\bMessrs\.?\s+)"
    r"([A-Z][A-Za-z0-9&.,'()\- ]{2,70})")


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def excerpt(text: str, start: int, end: int, width: int = 60) -> str:
    a = max(0, start - width)
    b = min(len(text), end + width)
    s = _norm(text[a:b])
    return ("..." if a > 0 else "") + s + ("..." if b < len(text) else "")


def name_patterns(db: ProjectDB):
    out = []
    for r in db.con.execute("SELECT name, aliases, folder FROM client_names ORDER BY name"):
        variants = [r["name"]] + [a.strip() for a in (r["aliases"] or "").split(";") if a.strip()]
        for v in variants:
            words = [re.escape(w) for w in v.split()]
            if not words:
                continue
            pat = re.compile(r"(?<![\w])" + r"\s+".join(words) + r"(?![\w])", re.IGNORECASE)
            out.append((r["name"], pat, r["folder"]))
    return out


def detect(pages: list[tuple[str, str]], patterns) -> dict:
    found: dict[str, dict] = {}
    for ref, text in pages:
        for canon, pat, folder in patterns:
            if canon in found:
                found[canon]["hits"] += len(pat.findall(text))
                continue
            m = pat.search(text)
            if m:
                found[canon] = {"name": canon, "page": ref, "excerpt": excerpt(text, m.start(), m.end()),
                                "folder": folder, "hits": len(pat.findall(text))}
    if found:
        return {"source": "Client list", "matches": sorted(found.values(), key=lambda d: -d["hits"])}
    sugg = []
    seen = set()
    for ref, text in pages:
        for m in LABEL_RE.finditer(text):
            cand = _norm(m.group(1)).split("  ")[0]
            cand = re.split(r"\s{2,}|\n| (?:Date|Address|PAN|GSTIN|Phone|Email|Invoice|Ref)\b", cand)[0].strip(" ,.-")
            if len(cand) < 3 or cand.lower() in seen:
                continue
            seen.add(cand.lower())
            sugg.append({"name": cand, "page": ref, "excerpt": excerpt(text, m.start(), m.end()), "folder": "", "hits": 1})
            if len(sugg) >= 5:
                break
    return {"source": "Label in document (unconfirmed)", "matches": sugg}


def build_queue(db: ProjectDB, scan_id: str, folder_filter: str = "", progress=None, cancel=None) -> dict:
    """Extract text for documents/images in the snapshot and (re)build pending queue entries.
    Entries already confirmed, skipped or moved are left untouched."""
    patterns = name_patterns(db)
    rows = db.con.execute("SELECT rel_path, ext FROM files WHERE scan_id=? ORDER BY rel_path", (scan_id,)).fetchall()
    rows = [r for r in rows if r["ext"] in ORGANIZE_EXTS]
    if folder_filter:
        ff = folder_filter.strip("\\").lower()
        rows = [r for r in rows if r["rel_path"].lower().startswith(ff + "\\")]
    stats = {"files": len(rows), "detected": 0, "review": 0, "suggested": 0, "kept": 0}
    keep_status = ("Name confirmed", "Skipped", "Moved")
    for i, r in enumerate(rows):
        if cancel is not None and cancel.is_set():
            break
        if progress:
            progress(i, len(rows), r["rel_path"])
        rel = r["rel_path"]
        ex_row = db.con.execute("SELECT status FROM organize_queue WHERE rel_path=?", (rel,)).fetchone()
        if ex_row and ex_row["status"] in keep_status:
            stats["kept"] += 1
            continue
        if not os.path.isfile(os.path.join(db.project.root_path, rel)):
            continue
        try:
            ex = cached_extract(db, rel)
        except OSError as e:
            _upsert(db, scan_id, rel, None, [], "", "", "", "Manual review", f"Unreadable: {e}")
            stats["review"] += 1
            continue
        if ex.status in ("error", "empty", "unsupported"):
            _upsert(db, scan_id, rel, None, [], "", "", ex.method, "Manual review",
                    ex.error or "No readable text found")
            stats["review"] += 1
            continue
        det = detect(ex.pages, patterns)
        ms = det["matches"]
        if det["source"] == "Client list" and len(ms) == 1:
            m = ms[0]
            _upsert(db, scan_id, rel, m["name"], ms, m["excerpt"], m["page"], det["source"] + f" / {ex.method}",
                    "Detected", "", m["folder"])
            stats["detected"] += 1
        elif det["source"] == "Client list":
            m = ms[0]
            _upsert(db, scan_id, rel, None, ms, m["excerpt"], m["page"], det["source"] + f" / {ex.method}",
                    "Several names", f"{len(ms)} client names found - choose one")
            stats["review"] += 1
        elif ms:
            m = ms[0]
            _upsert(db, scan_id, rel, m["name"], ms, m["excerpt"], m["page"], det["source"] + f" / {ex.method}",
                    "Suggestion", "Not in client list - check before confirming")
            stats["suggested"] += 1
        else:
            _upsert(db, scan_id, rel, None, [], "", "", ex.method, "Manual review", "No name detected")
            stats["review"] += 1
    return stats


def _upsert(db, scan_id, rel, name, cands, exc, page, source, status, note, dest=""):
    with db._write_lock:
        db.con.execute(
            "INSERT INTO organize_queue(scan_id,rel_path,detected_name,candidates,excerpt,page_ref,source,status,"
            "confirmed_name,destination,selected,note,updated) VALUES(?,?,?,?,?,?,?,?,NULL,?,0,?,?) "
            "ON CONFLICT(rel_path) DO UPDATE SET scan_id=excluded.scan_id, detected_name=excluded.detected_name,"
            " candidates=excluded.candidates, excerpt=excluded.excerpt, page_ref=excluded.page_ref,"
            " source=excluded.source, status=excluded.status, note=excluded.note, updated=excluded.updated,"
            " destination=CASE WHEN organize_queue.destination IS NULL OR organize_queue.destination='' "
            "   THEN excluded.destination ELSE organize_queue.destination END",
            (scan_id, rel, name, json.dumps(cands), exc, page, source, status, dest, note, now_iso()))
        db.con.commit()


def folder_for(db: ProjectDB, name: str) -> str:
    r = db.con.execute("SELECT folder FROM client_names WHERE name=? COLLATE NOCASE", (name,)).fetchone()
    return r["folder"] if r else ""


def confirm_name(db: ProjectDB, qid: int, name: str, destination: str | None = None) -> None:
    """Accepts the identification ONLY. Does not touch the file."""
    name = name.strip()
    if not name:
        raise ValueError("Name is empty.")
    r = db.con.execute("SELECT * FROM organize_queue WHERE id=?", (qid,)).fetchone()
    if r is None:
        raise ValueError("Queue entry not found.")
    if r["status"] == "Moved":
        raise ValueError("File was already moved.")
    dest = destination if destination is not None else (r["destination"] or folder_for(db, name))
    with db._write_lock:
        db.con.execute("UPDATE organize_queue SET status='Name confirmed', confirmed_name=?, destination=?, selected=1, "
                       "updated=? WHERE id=?", (name, dest, now_iso(), qid))
        db.con.commit()
    db.log_action("Confirm name", "Confirmed", source=os.path.join(db.project.root_path, r["rel_path"]),
                  destination=dest or "", scan_id=r["scan_id"],
                  detail=f"Name: {name} (detected: {r['detected_name'] or '-'}; {r['page_ref'] or ''}) - file not moved")


def set_destination(db: ProjectDB, qid: int, dest: str) -> None:
    with db._write_lock:
        db.con.execute("UPDATE organize_queue SET destination=?, updated=? WHERE id=?", (dest, now_iso(), qid))
        db.con.commit()


def skip(db: ProjectDB, qid: int) -> None:
    r = db.con.execute("SELECT * FROM organize_queue WHERE id=?", (qid,)).fetchone()
    with db._write_lock:
        db.con.execute("UPDATE organize_queue SET status='Skipped', selected=0, updated=? WHERE id=?", (now_iso(), qid))
        db.con.commit()
    if r:
        db.log_action("Skip file (organize)", "Skipped", source=os.path.join(db.project.root_path, r["rel_path"]),
                      scan_id=r["scan_id"])


def reopen(db: ProjectDB, qid: int) -> None:
    with db._write_lock:
        db.con.execute("UPDATE organize_queue SET status=CASE WHEN detected_name IS NULL THEN 'Manual review' "
                       "ELSE 'Detected' END, confirmed_name=NULL, updated=? WHERE id=? AND status<>'Moved'",
                       (now_iso(), qid))
        db.con.commit()


def set_selected(db: ProjectDB, qid: int, selected: bool) -> None:
    with db._write_lock:
        db.con.execute("UPDATE organize_queue SET selected=? WHERE id=? AND status<>'Moved'",
                       (1 if selected else 0, qid))
        db.con.commit()


def queue(db: ProjectDB, status: str = "", search: str = ""):
    sql = "SELECT * FROM organize_queue WHERE 1=1"
    args = []
    if status:
        sql += " AND status=?"
        args.append(status)
    if search:
        sql += " AND (rel_path LIKE ? OR COALESCE(detected_name,'') LIKE ? OR COALESCE(confirmed_name,'') LIKE ?)"
        args += [f"%{search}%"] * 3
    return db.con.execute(sql + " ORDER BY status, rel_path", args).fetchall()


# ---- client list
def list_names(db):
    return db.con.execute("SELECT * FROM client_names ORDER BY name COLLATE NOCASE").fetchall()


def save_name(db, name: str, aliases: str, folder: str, name_id: int | None = None):
    name = name.strip()
    if not name:
        raise ValueError("Name is required.")
    with db._write_lock:
        if name_id:
            db.con.execute("UPDATE client_names SET name=?, aliases=?, folder=? WHERE id=?", (name, aliases, folder, name_id))
        else:
            db.con.execute("INSERT INTO client_names(name,aliases,folder) VALUES(?,?,?)", (name, aliases, folder))
        db.con.commit()
    db.log_action("Save client name mapping", "Saved", destination=folder, detail=f"{name}; aliases: {aliases}")


def delete_name(db, name_id: int):
    r = db.con.execute("SELECT name FROM client_names WHERE id=?", (name_id,)).fetchone()
    with db._write_lock:
        db.con.execute("DELETE FROM client_names WHERE id=?", (name_id,))
        db.con.commit()
    if r:
        db.log_action("Remove client name mapping", "Removed", detail=r["name"])
