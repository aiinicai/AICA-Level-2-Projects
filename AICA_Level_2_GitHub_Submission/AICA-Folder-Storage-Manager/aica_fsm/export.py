"""Exports (.xlsx / .csv) of the ACTIVE project only. Each export starts with a header block that
names the project, its scan path and the snapshot(s) it was calculated from."""
from __future__ import annotations

import csv
import os

from . import reports
from .paths import now_iso, ts_to_iso
from .scanner import compare_snapshots
from .store import ProjectDB

FORMULA_START = ("=", "+", "-", "@", "\t", "\r")


def _safe(v):
    if isinstance(v, str) and v.startswith(FORMULA_START):
        return "'" + v
    return v


def _write(path: str, title: str, meta: list[tuple[str, str]], headers: list[str], rows) -> int:
    ext = os.path.splitext(path)[1].lower()
    n = 0
    if ext == ".csv":
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow([title])
            for k, v in meta:
                w.writerow([k, v])
            w.writerow([])
            w.writerow(headers)
            for r in rows:
                w.writerow([_safe(x) for x in r])
                n += 1
        return n
    from openpyxl import Workbook
    from openpyxl.styles import Font
    wb = Workbook(write_only=True)
    ws = wb.create_sheet(title[:31])
    from openpyxl.cell import WriteOnlyCell
    c = WriteOnlyCell(ws, value=title)
    c.font = Font(bold=True, size=13)
    ws.append([c])
    for k, v in meta:
        ws.append([k, v])
    ws.append([])
    hdr = []
    for h in headers:
        hc = WriteOnlyCell(ws, value=h)
        hc.font = Font(bold=True)
        hdr.append(hc)
    ws.append(hdr)
    for r in rows:
        if n >= 1_048_000:
            ws.append(["Excel row limit reached - export as CSV for the full list"])
            break
        ws.append([_safe(x) for x in r])
        n += 1
    wb.save(path)
    return n


def _meta(db: ProjectDB, scan=None, extra=None):
    m = [("Project", db.project.name), ("Project ID", db.project.project_id), ("Scan path", db.project.root_path)]
    if scan is not None:
        m += [("Snapshot", f"#{scan['seq']} ({scan['scan_id']})"), ("Snapshot status", scan["status"]),
              ("Scan started", scan["started"]), ("Scan finished", scan["finished"] or "")]
    m += list(extra or [])
    m.append(("Exported", now_iso()))
    return m


def export_inventory(db: ProjectDB, scan_id: str, path: str) -> int:
    s = reports.check_snapshot(db, scan_id)
    cur = db.con.execute("SELECT rel_path,name,folder,ext,size,mtime,sha256,hash_error FROM files WHERE scan_id=? "
                         "ORDER BY rel_path", (scan_id,))
    rows = ((r["name"], r["rel_path"], r["folder"], r["ext"], r["size"], ts_to_iso(r["mtime"]),
             r["sha256"] or "", r["hash_error"] or "") for r in cur)
    n = _write(path, "File inventory", _meta(db, s, [("Files in snapshot", str(s["files_found"]))]),
               ["File name", "Relative path", "Folder", "Type", "Size (bytes)", "Modified", "SHA-256", "Read error"], rows)
    db.log_action("Export file inventory", "Exported", destination=path, scan_id=scan_id, detail=f"{n} rows")
    return n


def export_changes(db: ProjectDB, old_scan_id: str, new_scan_id: str, path: str) -> int:
    a = reports.check_snapshot(db, old_scan_id)
    b = reports.check_snapshot(db, new_scan_id)
    res = compare_snapshots(db, old_scan_id, new_scan_id)
    detected = b["finished"] or b["started"]
    rows = []
    for c in sorted(res.changes, key=lambda c: (c.kind, (c.new or c.old).rel_path)):
        o, n = c.old, c.new
        rows.append((c.kind, o.rel_path if o else "", n.rel_path if n else "", o.size if o else "", n.size if n else "",
                     ts_to_iso(o.mtime) if o else "", ts_to_iso(n.mtime) if n else "", c.method, detected))
    meta = _meta(db, None, [("Compared from", f"Snapshot #{a['seq']} ({a['scan_id']}) {a['finished'] or a['started']}"),
                            ("Compared to", f"Snapshot #{b['seq']} ({b['scan_id']}) {b['finished'] or b['started']}"),
                            ("Newer snapshot status", b["status"])])
    n = _write(path, "Change report", meta, ["Change", "Old path", "New path", "Old size", "New size", "Old modified",
                                             "New modified", "How detected", "Detected (scan date)"], rows)
    db.log_action("Export change report", "Exported", destination=path, scan_id=new_scan_id, detail=f"{n} rows")
    return n


def export_duplicates(db: ProjectDB, scan_id: str, path: str) -> int:
    s = reports.check_snapshot(db, scan_id)
    rows = []
    for gi, g in enumerate(reports.duplicate_groups(db, scan_id), 1):
        for f in g["files"]:
            rows.append((gi, g["sha256"], g["size"], f["rel_path"], ts_to_iso(f["mtime"]), len(g["files"]),
                         g["savings"], "Verified (full SHA-256)"))
    for r in reports.unverified_duplicate_candidates(db, scan_id):
        rows.append(("", "", r["size"], r["rel_path"], ts_to_iso(r["mtime"]), "", "", f"Not verified: {r['hash_error']}"))
    n = _write(path, "Duplicate report", _meta(db, s), ["Group", "SHA-256", "Size (bytes)", "Path", "Modified",
                                                        "Copies in group", "Recoverable (bytes)", "Verification"], rows)
    db.log_action("Export duplicate report", "Exported", destination=path, scan_id=scan_id, detail=f"{n} rows")
    return n


def export_actions(db: ProjectDB, path: str) -> int:
    rows = [(r["ts"], r["action"], r["source"] or "", r["destination"] or "", r["outcome"], r["error"] or "",
             r["scan_id"] or "", r["detail"] or "")
            for r in db.con.execute("SELECT * FROM actions WHERE project_id=? ORDER BY id", (db.project_id,))]
    n = _write(path, "Action log", _meta(db), ["Time", "Action", "Source", "Destination", "Outcome", "Error",
                                               "Snapshot ID", "Detail"], rows)
    db.log_action("Export action log", "Exported", destination=path, detail=f"{n} rows")
    return n


def export_history(db: ProjectDB, items: list[dict], path: str) -> int:
    rows = [(e["time"], e["type"], e["action"], e["source"], e["destination"], e["outcome"], e["detail"]) for e in items]
    n = _write(path, "History", _meta(db), ["Time", "Type", "Action", "Source", "Destination", "Outcome", "Detail"], rows)
    db.log_action("Export history", "Exported", destination=path, detail=f"{n} rows")
    return n
