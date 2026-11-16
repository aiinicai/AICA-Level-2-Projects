import os
import threading

import pytest

from make_test_data import make_bulk, make_docs
from aica_fsm import actions, export, organize, reports, versions
from aica_fsm.scanner import Scanner, accept_incomplete_as_baseline
from aica_fsm.store import IsolationError, ProjectDB


def scan(p):
    return Scanner(p).run()


def test_isolation_counts_and_exports(env):
    tmp, cat = env
    make_bulk(str(tmp / "A"), 530, seed=1)
    make_bulk(str(tmp / "B"), 100, seed=2)
    a = cat.create("Project A", str(tmp / "A"))
    b = cat.create("Project B", str(tmp / "B"))
    sa = scan(a)
    sb = scan(b)
    da, dbb = ProjectDB.open(a), ProjectDB.open(b)
    assert da.scan(sa)["status"] == "Completed"
    assert reports.overview(da, sa)["count"] == 530
    assert reports.overview(dbb, sb)["count"] == 100
    # B's db has no trace of A
    assert dbb.scan(sa) is None
    with pytest.raises(ValueError):
        reports.overview(dbb, sa)
    for g in reports.duplicate_groups(dbb, sb):
        for f in g["files"]:
            assert os.path.isfile(os.path.join(str(tmp / "B"), f["rel_path"]))
    out = tmp / "b.csv"
    assert export.export_inventory(dbb, sb, str(out)) == 100
    xl = tmp / "b.xlsx"
    assert export.export_inventory(dbb, sb, str(xl)) == 100
    # opening a project db under the wrong project id fails
    from aica_fsm.store import Project
    fake = Project(b.project_id, "x", a.root_path, b.created)
    with pytest.raises(IsolationError):
        ProjectDB.open(fake)


def test_missing_root_fails_without_fallback(env):
    tmp, cat = env
    (tmp / "gone").mkdir()
    p = cat.create("Gone", str(tmp / "gone"))
    (tmp / "gone").rmdir()
    sid = scan(p)
    db = ProjectDB.open(p)
    s = db.scan(sid)
    assert s["status"] == "Failed" and s["files_found"] == 0 and db.baseline() is None


def test_changes_and_unverified(env):
    tmp, cat = env
    root = tmp / "C"
    (root / "sub").mkdir(parents=True)
    (root / "locked").mkdir()
    for n in ("keep.txt", "edit.txt", "del.txt", "ren.txt"):
        (root / n).write_text(f"content of {n}" * 10)
    (root / "locked" / "inside.txt").write_text("inside")
    p = cat.create("C", str(root))
    s1 = scan(p)
    (root / "new.txt").write_text("brand new")
    (root / "edit.txt").write_text("edited content, longer than before " * 5)
    os.remove(root / "del.txt")
    os.rename(root / "ren.txt", root / "sub" / "renamed.txt")
    s2 = scan(p)
    db = ProjectDB.open(p)
    kinds = {(r["kind"], r["old_path"], r["new_path"]) for r in reports.change_rows(db, s2)}
    assert ("New", None, "new.txt") in kinds
    assert ("Modified", "edit.txt", "edit.txt") in kinds
    assert ("Deleted", "del.txt", None) in kinds
    assert ("Moved", "ren.txt", "sub\\renamed.txt") in kinds
    assert db.baseline()["scan_id"] == s2


def test_unreadable_folder_not_deleted(env, monkeypatch):
    tmp, cat = env
    root = tmp / "D"
    (root / "share").mkdir(parents=True)
    (root / "share" / "a.txt").write_text("a")
    (root / "b.txt").write_text("b")
    p = cat.create("D", str(root))
    s1 = scan(p)
    real = os.scandir

    def fake(path):
        if str(path).endswith("share"):
            raise PermissionError(13, "Access is denied")
        return real(path)
    monkeypatch.setattr(os, "scandir", fake)
    s2 = scan(p)
    db = ProjectDB.open(p)
    assert db.scan(s2)["status"] == "Incomplete"
    rows = reports.change_rows(db, s2)
    assert [r["kind"] for r in rows] == ["Unverified"]
    assert db.baseline()["scan_id"] == s1  # baseline kept
    accept_incomplete_as_baseline(db, s2)
    assert db.baseline()["scan_id"] == s2


def test_duplicate_delete_keeps_copy_and_excludes_similar(env):
    tmp, cat = env
    root = tmp / "E"
    root.mkdir()
    for n in ("one.dat", "two.dat", "three.dat"):
        (root / n).write_bytes(b"same bytes" * 1000)
    (root / "similar.dat").write_bytes(b"same bytes" * 999 + b"different!")
    p = cat.create("E", str(root))
    sid = scan(p)
    db = ProjectDB.open(p)
    groups = reports.duplicate_groups(db, sid)
    assert len(groups) == 1 and {f["rel_path"] for f in groups[0]["files"]} == {"one.dat", "two.dat", "three.dat"}
    g = groups[0]
    plan = [actions.DeletePlanGroup(g["sha256"], g["size"], "one.dat", ["two.dat", "three.dat"])]
    rep = actions.delete_duplicates(db, sid, plan, allow_permanent=False)
    assert rep.count("Recycled") == 2, rep.results
    assert (root / "one.dat").exists() and not (root / "two.dat").exists()
    assert (root / "similar.dat").exists()
    assert reports.duplicate_groups(db, sid) == []


def test_delete_skips_if_kept_copy_changed(env):
    tmp, cat = env
    root = tmp / "F"
    root.mkdir()
    for n in ("a.dat", "b.dat"):
        (root / n).write_bytes(b"x" * 5000)
    p = cat.create("F", str(root))
    sid = scan(p)
    db = ProjectDB.open(p)
    g = reports.duplicate_groups(db, sid)[0]
    (root / "a.dat").write_bytes(b"y" * 5000)
    rep = actions.delete_duplicates(db, sid, [actions.DeletePlanGroup(g["sha256"], g["size"], "a.dat", ["b.dat"])], False)
    assert rep.count("Skipped") == 1 and (root / "b.dat").exists()


def test_organize_confirm_then_move_and_conflict(env):
    tmp, cat = env
    root = tmp / "G"
    files = make_docs(str(root))
    p = cat.create("G", str(root))
    sid = scan(p)
    db = ProjectDB.open(p)
    dest = tmp / "Clients"
    organize.save_name(db, "Sharma Textiles", "Sharma Textiles Pvt Ltd", str(dest / "Sharma"))
    organize.save_name(db, "Mehta Exports", "", str(dest / "Mehta"))
    organize.save_name(db, "Gupta Agro Industries", "", str(dest / "Gupta"))
    organize.build_queue(db, sid)
    q = {r["rel_path"]: r for r in organize.queue(db)}
    assert q["Invoice_2025_001.pdf"]["detected_name"] == "Sharma Textiles"
    assert q["Scan_0007.pdf"]["detected_name"] == "Mehta Exports", dict(q["Scan_0007.pdf"])
    assert "OCR" in q["Scan_0007.pdf"]["page_ref"]
    assert q["Engagement letter.docx"]["detected_name"] == "Gupta Agro Industries"
    assert q["receipt_photo.png"]["detected_name"] == "Sharma Textiles"
    assert "notes.txt" not in q  # organize reads PDF, Word and images only
    qid = q["Invoice_2025_001.pdf"]["id"]
    organize.confirm_name(db, qid, "Sharma Textiles")
    assert os.path.exists(files["text_pdf"])  # confirm does not move
    # conflict
    os.makedirs(dest / "Sharma")
    (dest / "Sharma" / "Invoice_2025_001.pdf").write_text("existing")
    item = actions.MovePlanItem("Invoice_2025_001.pdf", str(dest / "Sharma"), "Invoice_2025_001.pdf", "ask", qid)
    pre = actions.preflight_moves(str(root), [item])
    assert pre[0]["conflict"]
    rep = actions.move_files(db, sid, [item])
    assert rep.count("Failed") == 1 and os.path.exists(files["text_pdf"])
    assert (dest / "Sharma" / "Invoice_2025_001.pdf").read_text() == "existing"
    item.on_conflict = "keep_both"
    rep = actions.move_files(db, sid, [item])
    assert rep.count("Moved") == 1
    assert not os.path.exists(files["text_pdf"]) and (dest / "Sharma" / "Invoice_2025_001 (2).pdf").exists()
    log = [r for r in db.con.execute("SELECT * FROM actions WHERE action='Move file' AND outcome='Moved'")]
    assert log and log[0]["destination"].endswith("Invoice_2025_001 (2).pdf")


def test_versions_separate_from_duplicates(env):
    tmp, cat = env
    root = tmp / "H"
    make_docs(str(root))
    p = cat.create("H", str(root))
    sid = scan(p)
    db = ProjectDB.open(p)
    versions.analyse(db, sid)
    pairs = versions.pairs_for(db, sid)
    keys = {(r["path_a"], r["path_b"]) for r in pairs}
    assert ("Audit report v1.docx", "Audit report v2.docx") in keys
    pr = [r for r in pairs if r["path_a"] == "Audit report v1.docx"][0]
    assert pr["older"] == "Audit report v1.docx" and pr["order_certain"] == 1
    assert reports.duplicate_groups(db, sid) == []


def test_links_skipped(env):
    tmp, cat = env
    root = tmp / "L"
    root.mkdir()
    (root / "f.txt").write_text("x")
    outside = tmp / "outside"
    outside.mkdir()
    (outside / "secret.txt").write_text("s")
    import subprocess
    r = subprocess.run(["cmd", "/c", "mklink", "/J", str(root / "jn"), str(outside)], capture_output=True)
    if r.returncode != 0:
        pytest.skip("cannot create junction")
    p = cat.create("L", str(root))
    sid = scan(p)
    db = ProjectDB.open(p)
    assert reports.overview(db, sid)["count"] == 1
    assert db.scan(sid)["links_skipped"] == 1 and db.scan(sid)["status"] == "Completed"


def test_cancel_keeps_baseline(env):
    tmp, cat = env
    make_bulk(str(tmp / "K"), 300, seed=4)
    p = cat.create("K", str(tmp / "K"))
    s1 = scan(p)
    ev = threading.Event()
    ev.set()
    s2 = Scanner(p, cancel=ev).run()
    db = ProjectDB.open(p)
    assert db.scan(s2)["status"] == "Cancelled"
    assert db.baseline()["scan_id"] == s1
