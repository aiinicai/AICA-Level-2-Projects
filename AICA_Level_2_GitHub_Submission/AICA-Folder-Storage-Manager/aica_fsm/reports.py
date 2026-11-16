"""Read-only queries. Every function takes a ProjectDB (one project) and a snapshot id that must
belong to that project."""
from __future__ import annotations

import os
from collections import defaultdict

from .paths import category_of
from .store import ProjectDB

ACTED_OUTCOMES = ("Recycled", "Deleted permanently", "Moved")


def check_snapshot(db: ProjectDB, scan_id: str):
    s = db.scan(scan_id)
    if s is None or s["project_id"] != db.project_id:
        raise ValueError("Snapshot does not belong to the active project.")
    return s


def acted_paths(db: ProjectDB, scan_id: str) -> set[str]:
    """Files moved/deleted by the app after this snapshot was taken (so they are hidden until re-scan)."""
    s = check_snapshot(db, scan_id)
    since = s["finished"] or s["started"]
    root = db.project.root_path
    out = set()
    for r in db.con.execute(
        "SELECT source FROM actions WHERE ts>=? AND outcome IN (?,?,?)", (since, *ACTED_OUTCOMES)):
        src = r[0] or ""
        try:
            out.add(os.path.relpath(src, root).lower())
        except ValueError:
            pass
    return out


def overview(db: ProjectDB, scan_id: str) -> dict:
    s = check_snapshot(db, scan_id)
    c = db.con
    count, total = c.execute("SELECT COUNT(*), COALESCE(SUM(size),0) FROM files WHERE scan_id=?", (scan_id,)).fetchone()
    by_folder = defaultdict(lambda: [0, 0])
    by_type = defaultdict(lambda: [0, 0])
    by_cat = defaultdict(lambda: [0, 0])
    for r in c.execute("SELECT folder, ext, size FROM files WHERE scan_id=?", (scan_id,)):
        top = r[0].split("\\", 1)[0] if r[0] else "(project folder)"
        by_folder[top][0] += 1
        by_folder[top][1] += r[2]
        e = r[1] or "(none)"
        by_type[e][0] += 1
        by_type[e][1] += r[2]
        cat = category_of(r[1])
        by_cat[cat][0] += 1
        by_cat[cat][1] += r[2]
    largest = c.execute(
        "SELECT rel_path, size, mtime FROM files WHERE scan_id=? ORDER BY size DESC LIMIT 25", (scan_id,)).fetchall()
    groups, recoverable, dup_files = dup_summary(db, scan_id)
    return {
        "scan": s, "count": count, "total": total,
        "by_folder": sorted(((k, v[0], v[1]) for k, v in by_folder.items()), key=lambda x: -x[2]),
        "by_type": sorted(((k, v[0], v[1]) for k, v in by_type.items()), key=lambda x: -x[2]),
        "by_category": sorted(((k, v[0], v[1]) for k, v in by_cat.items()), key=lambda x: -x[2]),
        "largest": largest, "dup_groups": groups, "dup_files": dup_files, "recoverable": recoverable,
        "issues": db.con.execute(
            "SELECT COUNT(*) FROM scan_issues WHERE scan_id=? AND kind IN ('folder','file','root')", (scan_id,)
        ).fetchone()[0],
    }


def dup_summary(db: ProjectDB, scan_id: str):
    r = db.con.execute(
        "SELECT COUNT(*), COALESCE(SUM((n-1)*size),0), COALESCE(SUM(n),0) FROM ("
        " SELECT sha256, size, COUNT(*) n FROM files WHERE scan_id=? AND sha256 IS NOT NULL AND size>0"
        " GROUP BY sha256, size HAVING n>1)", (scan_id,)).fetchone()
    return r[0], r[1], r[2]


FILE_SORTS = {"name": "name COLLATE NOCASE", "path": "rel_path COLLATE NOCASE", "size": "size",
              "type": "ext", "modified": "mtime"}


def _file_where(scan_id, search="", ext="", min_size=None, max_size=None, mod_from=None, mod_to=None, folder=""):
    where = ["scan_id=?"]
    args: list = [scan_id]
    if search:
        for term in search.split():
            where.append("rel_path LIKE ? ESCAPE '\\'")
            t = term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            args.append(f"%{t}%")
    if ext:
        exts = [e.strip().lower().lstrip(".") for e in ext.split(",") if e.strip()]
        if exts:
            where.append(f"ext IN ({','.join('?' * len(exts))})")
            args += exts
    if min_size is not None:
        where.append("size>=?")
        args.append(min_size)
    if max_size is not None:
        where.append("size<=?")
        args.append(max_size)
    if mod_from is not None:
        where.append("mtime>=?")
        args.append(mod_from)
    if mod_to is not None:
        where.append("mtime<=?")
        args.append(mod_to)
    if folder:
        f = folder.strip("\\")
        where.append("(folder=? COLLATE NOCASE OR folder LIKE ? ESCAPE '\\')")
        args += [f, f.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "\\\\%"]
    return " AND ".join(where), args


def files_count(db: ProjectDB, scan_id: str, **flt) -> tuple[int, int]:
    check_snapshot(db, scan_id)
    w, a = _file_where(scan_id, **flt)
    r = db.con.execute(f"SELECT COUNT(*), COALESCE(SUM(size),0) FROM files WHERE {w}", a).fetchone()
    return r[0], r[1]


def files_page(db: ProjectDB, scan_id: str, offset: int, limit: int, sort="path", desc=False, **flt):
    check_snapshot(db, scan_id)
    w, a = _file_where(scan_id, **flt)
    order = FILE_SORTS.get(sort, "rel_path")
    return db.con.execute(
        f"SELECT rel_path,name,folder,ext,size,mtime,sha256,hash_error FROM files WHERE {w} "
        f"ORDER BY {order} {'DESC' if desc else 'ASC'}, rel_path LIMIT ? OFFSET ?", a + [limit, offset]).fetchall()


def duplicate_groups(db: ProjectDB, scan_id: str, hide_acted=True) -> list[dict]:
    check_snapshot(db, scan_id)
    acted = acted_paths(db, scan_id) if hide_acted else set()
    rows = db.con.execute(
        "SELECT f.sha256, f.size, f.rel_path, f.mtime, f.file_id FROM files f JOIN ("
        " SELECT sha256, size FROM files WHERE scan_id=? AND sha256 IS NOT NULL AND size>0"
        " GROUP BY sha256, size HAVING COUNT(*)>1) g ON f.sha256=g.sha256 AND f.size=g.size"
        " WHERE f.scan_id=? ORDER BY f.size DESC, f.sha256, f.rel_path", (scan_id, scan_id)).fetchall()
    groups: dict[str, dict] = {}
    for r in rows:
        if r["rel_path"].lower() in acted:
            continue
        g = groups.setdefault(r["sha256"], {"sha256": r["sha256"], "size": r["size"], "files": []})
        g["files"].append(dict(rel_path=r["rel_path"], mtime=r["mtime"], file_id=r["file_id"]))
    out = [g for g in groups.values() if len(g["files"]) > 1]
    for g in out:
        g["savings"] = (len(g["files"]) - 1) * g["size"]
    return out


def unverified_duplicate_candidates(db: ProjectDB, scan_id: str):
    """Files that share a size with other files but could not be fully read -> cannot be verified."""
    return db.con.execute(
        "SELECT f.rel_path, f.size, f.mtime, f.hash_error FROM files f WHERE f.scan_id=? AND f.hash_error IS NOT NULL"
        " AND (SELECT COUNT(*) FROM files g WHERE g.scan_id=f.scan_id AND g.size=f.size)>1 ORDER BY f.size DESC",
        (scan_id,)).fetchall()


def change_rows(db: ProjectDB, scan_id: str):
    return db.con.execute("SELECT * FROM changes WHERE scan_id=? ORDER BY kind, COALESCE(new_path,old_path)",
                          (scan_id,)).fetchall()


def timeline(db: ProjectDB, search: str = "", kinds: tuple = ("scan", "change", "action"), limit=20000):
    """Unified history: scans, detected changes, user actions."""
    out = []
    s = search.lower().strip()
    seqmap = {r["scan_id"]: r["seq"] for r in db.scans()}
    if "scan" in kinds:
        for r in db.scans():
            text = f"Scan #{r['seq']} {r['status']} - {r['files_found']} files, {r['inaccessible_count']} unreadable"
            out.append({"time": r["finished"] or r["started"], "type": "Scan", "action": f"Scan #{r['seq']}",
                        "source": r["root_path"], "destination": "", "outcome": r["status"],
                        "detail": (r["message"] or "") + f" [snapshot {r['scan_id']}]", "text": text})
    if "change" in kinds:
        for r in db.con.execute("SELECT * FROM changes ORDER BY id"):
            out.append({"time": r["detected"], "type": "Change", "action": r["kind"],
                        "source": r["old_path"] or "", "destination": r["new_path"] or "",
                        "outcome": f"Scan #{seqmap.get(r['scan_id'], '?')}", "detail": r["method"] or "", "text": ""})
    if "action" in kinds:
        for r in db.con.execute("SELECT * FROM actions ORDER BY id"):
            out.append({"time": r["ts"], "type": "Action", "action": r["action"], "source": r["source"] or "",
                        "destination": r["destination"] or "", "outcome": r["outcome"],
                        "detail": " ".join(x for x in (r["error"] or "", r["detail"] or "") if x), "text": ""})
    if s:
        out = [e for e in out if s in " ".join(str(v) for v in e.values()).lower()]
    out.sort(key=lambda e: e["time"] or "", reverse=True)
    return out[:limit]
