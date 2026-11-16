"""Headless self-test of the packaged app (for a clean Windows machine).

AICA Folder Storage Manager.exe --selftest <empty work folder>

Creates test files inside the work folder only, then checks: scanning, project isolation, re-scan change
detection, duplicates, OCR + name detection, confirm-name (no move), move with conflict handling, Excel/CSV
exports, history, and reopening the saved projects. Writes selftest_report.txt into the work folder.
"""
from __future__ import annotations

import csv
import os
import platform
import sys
import time
import traceback


def run(work: str) -> int:
    os.makedirs(work, exist_ok=True)
    os.environ["AICA_FSM_DATA"] = os.path.join(work, "appdata")
    lines: list[str] = []
    ok_all = True

    def check(name, cond, detail=""):
        nonlocal ok_all
        ok_all &= bool(cond)
        lines.append(f"[{'PASS' if cond else 'FAIL'}] {name}" + (f" - {detail}" if detail else ""))

    t0 = time.time()
    try:
        from . import actions, export, organize, reports
        from .scanner import Scanner
        from .store import Catalog, ProjectDB
        from .testdata import make_bulk, make_docs
        from .textextract import ocr_available

        lines.append(f"Windows {platform.version()}  Python {sys.version.split()[0]}  frozen={getattr(sys, 'frozen', False)}")
        check("Windows OCR engine available", ocr_available())
        a_dir, b_dir, c_dir = (os.path.join(work, n) for n in ("ProjectA", "ProjectB", "ProjectC"))
        make_bulk(a_dir, 530, seed=1)
        make_bulk(b_dir, 100, seed=2)
        files = make_docs(c_dir)
        cat = Catalog()
        a = cat.create("Selftest A", a_dir)
        b = cat.create("Selftest B", b_dir)
        c = cat.create("Selftest C", c_dir)
        sa, sb, sc = Scanner(a).run(), Scanner(b).run(), Scanner(c).run()
        da, db, dc = ProjectDB.open(a), ProjectDB.open(b), ProjectDB.open(c)
        check("Scan A completed with 530 files", reports.overview(da, sa)["count"] == 530)
        check("Scan B completed with 100 files", reports.overview(db, sb)["count"] == 100)
        check("B database holds no A snapshot", db.scan(sa) is None)
        inv = os.path.join(work, "B_inventory.csv")
        n = export.export_inventory(db, sb, inv)
        with open(inv, encoding="utf-8-sig") as f:
            rows = list(csv.reader(f))
        hdr = next(i for i, r in enumerate(rows) if r and r[0] == "File name")
        data = rows[hdr + 1:]
        check("B CSV export has exactly 100 rows, all inside B",
              n == 100 and len(data) == 100 and all(os.path.isfile(os.path.join(b_dir, r[1])) for r in data))
        n = export.export_inventory(db, sb, os.path.join(work, "B_inventory.xlsx"))
        check("B Excel export has 100 rows", n == 100)
        # change detection in B
        some = sorted(os.path.join(dp, fn) for dp, _, fns in os.walk(b_dir) for fn in fns
                      if fn.startswith("file_") and os.path.getsize(os.path.join(dp, fn)) > 100)[:3]
        with open(os.path.join(b_dir, "added.txt"), "w") as f:
            f.write("added")
        with open(some[0], "ab") as f:
            f.write(b"edited")
        os.remove(some[1])
        os.rename(some[2], os.path.join(b_dir, "renamed_" + os.path.basename(some[2])))
        sb2 = Scanner(b).run()
        kinds = sorted(r["kind"] for r in reports.change_rows(db, sb2))
        check("Re-scan B detects New/Modified/Deleted/Moved", kinds == ["Deleted", "Modified", "Moved", "New"], str(kinds))
        # duplicates
        g = reports.duplicate_groups(db, sb2)
        check("Exact duplicate groups found in B", len(g) > 0, f"{len(g)} groups")
        g0 = g[0]
        keep = g0["files"][0]["rel_path"]
        rep = actions.delete_duplicates(db, sb2, [actions.DeletePlanGroup(
            g0["sha256"], g0["size"], keep, [f["rel_path"] for f in g0["files"][1:]])], allow_permanent=False)
        check("Selected copies sent to Recycle Bin, kept copy survives",
              rep.count("Recycled") == len(g0["files"]) - 1 and os.path.isfile(os.path.join(b_dir, keep)),
              "; ".join(f"{r.outcome} {r.error}" for r in rep.results))
        # OCR + organize
        dest = os.path.join(work, "Clients")
        organize.save_name(dc, "Sharma Textiles", "Sharma Textiles Pvt Ltd", os.path.join(dest, "Sharma"))
        organize.save_name(dc, "Mehta Exports", "", os.path.join(dest, "Mehta"))
        organize.save_name(dc, "Gupta Agro Industries", "", os.path.join(dest, "Gupta"))
        organize.build_queue(dc, sc)
        q = {r["rel_path"]: r for r in organize.queue(dc)}
        check("Text PDF name detected", q["Invoice_2025_001.pdf"]["detected_name"] == "Sharma Textiles")
        check("Scanned PDF name detected via OCR", q["Scan_0007.pdf"]["detected_name"] == "Mehta Exports",
              q["Scan_0007.pdf"]["page_ref"] or "")
        check("Word document name detected", q["Engagement letter.docx"]["detected_name"] == "Gupta Agro Industries")
        check("Image name detected via OCR", q["receipt_photo.png"]["detected_name"] == "Sharma Textiles")
        qid = q["Invoice_2025_001.pdf"]["id"]
        organize.confirm_name(dc, qid, "Sharma Textiles")
        check("Confirm Name leaves the file in place", os.path.isfile(files["text_pdf"]))
        os.makedirs(os.path.join(dest, "Sharma"), exist_ok=True)
        with open(os.path.join(dest, "Sharma", "receipt_photo.png"), "w") as f:
            f.write("existing")
        organize.confirm_name(dc, q["receipt_photo.png"]["id"], "Sharma Textiles")
        items = [actions.MovePlanItem("Invoice_2025_001.pdf", os.path.join(dest, "Sharma"), "Invoice_2025_001.pdf", "ask", qid),
                 actions.MovePlanItem("receipt_photo.png", os.path.join(dest, "Sharma"), "receipt_photo.png", "ask",
                                      q["receipt_photo.png"]["id"])]
        pre = actions.preflight_moves(c_dir, items)
        check("Destination conflict detected before moving", pre[1]["conflict"] and not pre[0]["conflict"])
        rep = actions.move_files(dc, sc, [items[0]])
        check("Move Selected Files moved the confirmed file",
              rep.count("Moved") == 1 and os.path.isfile(os.path.join(dest, "Sharma", "Invoice_2025_001.pdf"))
              and not os.path.exists(files["text_pdf"]))
        with open(os.path.join(dest, "Sharma", "receipt_photo.png")) as f:
            check("Existing destination file not overwritten", f.read() == "existing")
        log = [r for r in dc.con.execute("SELECT * FROM actions WHERE action='Move file'")]
        check("Audit entry for the move", any(r["outcome"] == "Moved" for r in log))
        export.export_actions(dc, os.path.join(work, "C_actions.xlsx"))
        export.export_duplicates(db, sb2, os.path.join(work, "B_duplicates.csv"))
        export.export_changes(db, sb, sb2, os.path.join(work, "B_changes.xlsx"))
        check("History timeline has entries", len(reports.timeline(dc)) > 0)
        for d in (da, db, dc):
            d.close()
        cat.close()
        # "restart": reopen everything from disk
        cat2 = Catalog()
        projs = {p.name: p for p in cat2.list()}
        da2, db2 = ProjectDB.open(projs["Selftest A"]), ProjectDB.open(projs["Selftest B"])
        check("After reopening: A still 530 files", da2.baseline()["files_found"] == 530)
        check("After reopening: B scan history restored", len(db2.scans()) == 2)
        da2.close()
        db2.close()
        cat2.close()
    except Exception:
        ok_all = False
        lines.append("[FAIL] Exception:\n" + traceback.format_exc())
    lines.append(f"RESULT: {'ALL PASSED' if ok_all else 'FAILURES'} in {time.time() - t0:.1f}s")
    with open(os.path.join(work, "selftest_report.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return 0 if ok_all else 1
