"""GUI acceptance tests against the PACKAGED exe, driven through Windows UI Automation.

python tools/acceptance.py "<path to exe>" <work folder on D:>

Writes <work>/acceptance_report.txt. Verification reads exported files, the disk, and (read-only)
the app's per-project databases.
"""
from __future__ import annotations

import csv
import os
import shutil
import sqlite3
import subprocess
import sys
import time
import traceback

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from aica_fsm.testdata import make_bulk, make_docs  # noqa: E402

from pywinauto import Desktop  # noqa: E402
from pywinauto.controls.uiawrapper import UIAWrapper  # noqa: E402
from pywinauto.uia_defines import IUIA  # noqa: E402
from pywinauto.uia_element_info import UIAElementInfo  # noqa: E402

EXE = os.path.abspath(sys.argv[1])
WORK = os.path.abspath(sys.argv[2])
DATA = os.path.join(WORK, "appdata")
OUT = os.path.join(WORK, "exports")
UNC_PREFIX = "\\\\localhost\\" + WORK[0] + "$" + WORK[2:]   # D:\x -> \\localhost\D$\x
D = Desktop(backend="uia")
U = IUIA()
REPORT: list[str] = []
proc = None


def log(s):
    print(s, flush=True)
    REPORT.append(s)


RESULTS = []


def check(name, cond, detail=""):
    RESULTS.append(bool(cond))
    log(f"  [{'PASS' if cond else 'FAIL'}] {name}" + (f"  ({detail})" if detail else ""))
    return cond


# ------------------------------------------------------------------ UIA helpers
def _cond(name=None, ctype=None, help_=None):
    conds = []
    if name is not None:
        conds.append(U.iuia.CreatePropertyCondition(U.UIA_dll.UIA_NamePropertyId, name))
    if ctype is not None:
        conds.append(U.iuia.CreatePropertyCondition(U.UIA_dll.UIA_ControlTypePropertyId, U.known_control_types[ctype]))
    if help_ is not None:
        conds.append(U.iuia.CreatePropertyCondition(30159, help_))  # UIA FullDescription = Qt accessibleDescription
    c = conds[0]
    for x in conds[1:]:
        c = U.iuia.CreateAndCondition(c, x)
    return c


def find(parent, name=None, ctype=None, help_=None, timeout=20, startswith=None):
    end = time.time() + timeout
    pel = parent.element_info.element
    while True:
        try:
            if startswith is not None:
                arr = pel.FindAll(U.tree_scope["descendants"], _cond(ctype=ctype))
                for i in range(arr.Length):
                    e = arr.GetElement(i)
                    if (e.CurrentName or "").startswith(startswith):
                        return UIAWrapper(UIAElementInfo(e))
            else:
                e = pel.FindFirst(U.tree_scope["descendants"], _cond(name, ctype, help_))
                if e:
                    return UIAWrapper(UIAElementInfo(e))
        except Exception:  # element tree changing while the page refreshes
            pass
        if time.time() > end:
            raise LookupError(f"not found: name={name} type={ctype} help={help_} startswith={startswith}")
        time.sleep(0.2)


def exists(parent, **kw):
    try:
        find(parent, timeout=0, **kw)
        return True
    except LookupError:
        return False


def mw(timeout=60):
    """The main window of the app process under test (the one with the Navigation list)."""
    end = time.time() + timeout
    while True:
        for w in D.windows(control_type="Window"):
            try:
                if (w.element_info.name or "").endswith("AICA Folder Storage Manager") and \
                        w.element_info.element.FindFirst(U.tree_scope["descendants"],
                                                         _cond(name="Navigation", ctype="List")):
                    return w
            except Exception:
                pass
        if time.time() > end:
            raise LookupError("main window not found")
        time.sleep(0.3)


def window(title, timeout=60, regex=False):
    """Dialogs may be top-level or nested under the main window in the UIA tree."""
    import re
    end = time.time() + timeout
    while True:
        for w in D.windows(control_type="Window"):
            n = w.element_info.name or ""
            if (re.fullmatch(title, n) if regex else n == title):
                return w
        try:
            m = mw(timeout=0)
            arr = m.element_info.element.FindAll(U.tree_scope["descendants"], _cond(ctype="Window"))
            for i in range(arr.Length):
                e = arr.GetElement(i)
                n = e.CurrentName or ""
                if (re.fullmatch(title, n) if regex else n == title):
                    return UIAWrapper(UIAElementInfo(e))
        except Exception:
            pass
        if time.time() > end:
            raise LookupError(f"window not found: {title}")
        time.sleep(0.25)


def text(help_):
    for _ in range(20):
        try:
            return find(mw(), help_=help_).element_info.name
        except Exception:
            time.sleep(0.5)
    return find(mw(), help_=help_).element_info.name


def press(parent, name, timeout=20):
    b = find(parent, name=name, ctype="Button", timeout=timeout)
    b.invoke()
    time.sleep(0.3)


def set_edit(parent, name, value):
    e = find(parent, name=name, ctype="Edit")
    e.iface_value.SetValue(value)
    time.sleep(0.1)


def nav(page):
    find(mw(), name=page, ctype="ListItem").select()
    time.sleep(0.6)


def ok_box(title, button="OK", timeout=120):
    w = window(title, timeout=timeout)
    msg = " ".join(e.element_info.name for e in w.descendants(control_type="Text"))
    press(w, button)
    return msg


def save_dialog(title, path):
    w = window(title)
    fn = find(w, name="File name:", ctype="Edit")
    fn.set_focus()
    time.sleep(0.2)
    esc = "".join("{%s}" % ch if ch in "+^%~(){}[]" else ch for ch in path)
    fn.type_keys("^a{BACKSPACE}", set_foreground=True)
    fn.type_keys(esc, with_spaces=True, pause=0.01)
    time.sleep(0.3)
    fn.type_keys("{ENTER}")


# ------------------------------------------------------------------ app + db
def launch():
    global proc
    env = dict(os.environ)
    env["TEMP"] = env["TMP"] = os.path.join(WORK, "tmp")
    os.makedirs(env["TEMP"], exist_ok=True)
    proc = subprocess.Popen([EXE, "--data", DATA], env=env)
    mw(timeout=120)
    time.sleep(2)


def quit_app():
    w = mw()
    w.close()
    try:
        proc.wait(60)
    except subprocess.TimeoutExpired:
        log("  app did not exit in 60s")


def catalog():
    con = sqlite3.connect(f"file:{os.path.join(DATA, 'catalog.db')}?mode=ro", uri=True)
    rows = {r[0]: r[1] for r in con.execute("SELECT name, project_id FROM projects")}
    con.close()
    return rows


def pdb(name):
    pid = catalog()[name]
    con = sqlite3.connect(f"file:{os.path.join(DATA, 'projects', pid, 'project.db')}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    return con


def latest_scan(name):
    con = pdb(name)
    r = con.execute("SELECT * FROM scans ORDER BY seq DESC LIMIT 1").fetchone()
    con.close()
    return r


def toggle(el):
    el.iface_toggle.Toggle()
    time.sleep(0.2)


def combo_value(el):
    try:
        return el.iface_value.CurrentValue
    except Exception:
        return el.window_text()


def rescan(name):
    prev = latest_scan(name)["seq"]
    press(mw(), "Re-scan project")
    return wait_scan(name, prev + 1)


def wait_scan(name, min_seq=1, timeout=900):
    end = time.time() + timeout
    while time.time() < end:
        try:
            r = latest_scan(name)
            if r and r["seq"] >= min_seq and r["status"] != "Running":
                time.sleep(1.5)
                return r
        except Exception:
            pass
        time.sleep(0.5)
    raise TimeoutError(f"scan of {name} did not finish")


def create_project(name, path):
    nav("Projects")
    press(mw(), "New Project...")
    d = window("New Project")
    set_edit(d, "Project name", name)
    set_edit(d, "Project folder path", path)
    press(d, "Create Project")
    return wait_scan(name)


def open_project(name):
    nav("Projects")
    t = find(mw(), name="Projects table", ctype="Table")
    cell = find(t, ctype="DataItem", startswith=name)
    cell.select()
    time.sleep(0.2)
    press(mw(), "Open")
    time.sleep(1.5)


def overview_count():
    nav("Overview")
    return text("Overview file count")


def export_from(page, button, dialog_title, path):
    nav(page)
    press(mw(), button)
    save_dialog(dialog_title, path)
    msg = ok_box("Export")
    if not os.path.isfile(path):
        log(f"    export box said: {msg!r}; expected file {path} missing")
    return msg


def read_csv_table(path):
    with open(path, encoding="utf-8-sig") as f:
        rows = list(csv.reader(f))
    meta = {r[0]: r[1] for r in rows[1:] if len(r) >= 2 and r[0] and r[0] not in ("",)}
    hi = next(i for i, r in enumerate(rows) if len(r) > 2)
    hdr = rows[hi]
    return meta, [dict(zip(hdr, r)) for r in rows[hi + 1:]]


# ------------------------------------------------------------------ setup
def setup():
    if os.path.exists(WORK):
        subprocess.run(["icacls", WORK, "/reset", "/T", "/C", "/Q"], capture_output=True)
        shutil.rmtree(WORK, ignore_errors=True)
    os.makedirs(OUT)
    log(f"Work folder {WORK}; exe {EXE} ({os.path.getsize(EXE)/1e6:.1f} MB)")
    make_bulk(os.path.join(WORK, "A"), 5298, seed=11)
    make_bulk(os.path.join(WORK, "B"), 1000, seed=22)
    for i in range(1500):  # many folders so listing over SMB takes a while
        dd = os.path.join(WORK, "N", f"F{i // 100:02d}", f"S{i:04d}")
        os.makedirs(dd)
        for j in range(2):
            with open(os.path.join(dd, f"n{j}.txt"), "w") as f:
                f.write(f"{i}-{j}")
    make_docs(os.path.join(WORK, "C"))
    log("Test data: A=5,298 files (local), B=1,000 files (opened via UNC "
        f"{UNC_PREFIX}\\B), N=3,000 files in 1,500 folders (UNC), C=documents")


# ------------------------------------------------------------------ tests
def t1_check_b(tag):
    check(f"{tag}: B overview shows 1,000", overview_count() == "1,000", overview_count())
    nav("Files")
    fc = text("Files count")
    check(f"{tag}: B Files page shows 1,000", fc.startswith("1,000 files"), fc)
    p = os.path.join(OUT, f"B_inventory_{tag}.csv")
    export_from("Files", "Export inventory...", "Export file inventory", p)
    meta, rows = read_csv_table(p)
    bdir = os.path.join(WORK, "B")
    check(f"{tag}: B inventory export has exactly 1,000 rows", len(rows) == 1000, f"{len(rows)} rows")
    check(f"{tag}: every exported row exists under B", all(os.path.isfile(os.path.join(bdir, r["Relative path"])) for r in rows))
    check(f"{tag}: export header names project B and its path",
          meta.get("Project") == "Project B" and meta.get("Scan path", "").endswith("\\B"), str(meta.get("Scan path")))
    p = os.path.join(OUT, f"B_duplicates_{tag}.csv")
    export_from("Duplicates", "Export duplicate report...", "Export duplicate report", p)
    _, rows = read_csv_table(p)
    check(f"{tag}: B duplicate report only has B files ({len(rows)} rows)",
          rows and all(os.path.isfile(os.path.join(bdir, r["Path"])) for r in rows))
    p = os.path.join(OUT, f"B_history_{tag}.csv")
    export_from("History", "Export this view...", "Export history", p)
    with open(p, encoding="utf-8-sig") as f:
        h = f.read()
    check(f"{tag}: B history contains no Project A data", os.path.join(WORK, "A") + "\\" not in h
          and (os.path.join(WORK, "A") + ",") not in h and "Project A" not in h)
    con = pdb("Project B")
    n_scans = con.execute("SELECT COUNT(*) FROM scans").fetchone()[0]
    con.close()
    check(f"{tag}: B scan history only B scans", n_scans >= 1 and all(
        r[0].endswith("\\B") for r in pdb("Project B").execute("SELECT root_path FROM scans")))


def t1():
    log("\nTEST 1 - two projects, isolation, restart")
    s = create_project("Project A", os.path.join(WORK, "A"))
    check("A first scan Completed", s["status"] == "Completed", s["status"])
    check("A overview shows 5,298", overview_count() == "5,298", overview_count())
    s = create_project("Project B", UNC_PREFIX + "\\B")
    check("B first scan Completed", s["status"] == "Completed", s["status"])
    t1_check_b("before restart")
    open_project("Project A")
    check("Switch back: A overview shows 5,298", overview_count() == "5,298", overview_count())
    nav("Files")
    check("Switch back: A Files page 5,298", text("Files count").startswith("5,298 files"), text("Files count"))
    quit_app()
    launch()
    open_project("Project B")
    t1_check_b("after restart")
    open_project("Project A")
    check("After restart: A overview shows 5,298", overview_count() == "5,298", overview_count())
    nav("History")
    check("After restart: A history restored", "entries for project 'Project A'" in text("History count"),
          text("History count"))


def t2():
    log("\nTEST 2 - A scan finishing while B is on screen")
    open_project("Project A")
    adir = os.path.join(WORK, "A")
    now = time.time()
    for dp, _, fns in os.walk(adir):  # force full re-fingerprinting so the scan takes a while
        for fn in fns:
            os.utime(os.path.join(dp, fn), (now, now))
    before = latest_scan("Project A")["seq"]
    press(mw(), "Re-scan project")
    open_project("Project B")
    r = latest_scan("Project A")
    check("A scan still running when B was opened", r["status"] == "Running" and r["seq"] == before + 1, r["status"])
    nav("Overview")
    snap_before = combo_value(find(mw(), name="Snapshot selector", ctype="ComboBox"))
    r = wait_scan("Project A", before + 1)
    time.sleep(2)
    check("A re-scan completed in background", r["status"] == "Completed", r["status"])
    ap = text("Active project")
    check("Screen still shows Project B", ap == "Project: Project B", ap)
    snap_after = combo_value(find(mw(), name="Snapshot selector", ctype="ComboBox"))
    check("B snapshot selector unchanged", snap_after == snap_before, snap_after)
    check("B overview still 1,000", overview_count() == "1,000", overview_count())
    nav("Files")
    check("B Files page still 1,000", text("Files count").startswith("1,000 files"))
    check("No scan progress panel shown for B", not exists(mw(), help_="Scan progress") or
          not find(mw(), help_="Scan progress").is_visible())
    open_project("Project A")
    snap = combo_value(find(mw(), name="Snapshot selector", ctype="ComboBox"))
    check("A now shows its new snapshot #2 with 5,298 files", snap.startswith(f"#{before + 1}") and "5,298" in snap, snap)


def known_b_files():
    out = []
    for dp, _, fns in os.walk(os.path.join(WORK, "B")):
        for fn in sorted(fns):
            if fn.startswith("file_") and os.path.getsize(os.path.join(dp, fn)) > 100:
                out.append(os.path.join(dp, fn))
    return sorted(out)


def latest_changes_csv(tag):
    p = os.path.join(OUT, f"B_changes_{tag}.csv")
    time.sleep(0.5)
    export_from("Changes", "Export change report...", "Export change report", p)
    return read_csv_table(p)


def t3():
    log("\nTEST 3 - changes in B, unreadable folder, network location going offline")
    bdir = os.path.join(WORK, "B")
    rel = lambda p: os.path.relpath(p, bdir)  # noqa
    k = known_b_files()
    edit, delete, rename, move = k[0], k[1], k[2], k[3]
    added = os.path.join(bdir, "T3_added.txt")
    with open(added, "w") as f:
        f.write("new file for test 3")
    with open(edit, "ab") as f:
        f.write(b"EDITED")
    os.remove(delete)
    renamed = os.path.join(os.path.dirname(rename), "T3_renamed.dat")
    os.rename(rename, renamed)
    os.makedirs(os.path.join(bdir, "T3_moved_here"), exist_ok=True)
    moved = os.path.join(bdir, "T3_moved_here", os.path.basename(move))
    os.rename(move, moved)
    open_project("Project B")
    prev = latest_scan("Project B")
    s = rescan("Project B")
    check("B re-scan Completed", s["status"] == "Completed", s["status"])
    meta, rows = latest_changes_csv("t3")
    got = sorted((r["Change"], r["Old path"], r["New path"]) for r in rows)
    exp = sorted([("New", "", rel(added)), ("Modified", rel(edit), rel(edit)), ("Deleted", rel(delete), ""),
                  ("Moved", rel(rename), rel(renamed)), ("Moved", rel(move), rel(moved))])
    check("Change report compares with B's previous scan", f"#{prev['seq']}" in meta.get("Compared from", ""),
          meta.get("Compared from"))
    check("Exactly the 5 expected changes (New, Modified, Deleted, 2x Moved)", got == exp,
          "; ".join(f"{a}:{b}->{c}" for a, b, c in got))
    log("    how detected: " + "; ".join(f"{r['Change']}={r['How detected']}" for r in rows))

    # unreadable subfolder
    locked = os.path.join(bdir, "Dept03")
    n_locked = sum(len(f) for _, _, f in os.walk(locked))
    base_before = s["scan_id"]
    # qualified name: an unqualified one is ambiguous when the PC and the user share a name
    user = f"{os.environ.get('USERDOMAIN')}\\{os.environ.get('USERNAME')}"
    subprocess.run(["icacls", locked, "/deny", f"{user}:(OI)(CI)(RX)"], capture_output=True, check=True)
    try:
        s2 = rescan("Project B")
        try:
            ok_box("Scan incomplete", timeout=15)
        except Exception:
            pass
    finally:
        subprocess.run(["icacls", locked, "/remove:d", user, "/T", "/C", "/Q"], capture_output=True)
    check("Scan with unreadable folder labelled Incomplete", s2["status"] == "Incomplete", s2["status"])
    meta, rows = latest_changes_csv("t3_locked")
    kinds = {}
    for r in rows:
        kinds[r["Change"]] = kinds.get(r["Change"], 0) + 1
    check("No files reported Deleted; files in unreadable folder are Unverified",
          kinds.get("Deleted", 0) == 0 and kinds.get("Unverified", 0) == n_locked, str(kinds))
    con = pdb("Project B")
    bl = con.execute("SELECT scan_id FROM scans WHERE is_baseline=1 ORDER BY seq DESC LIMIT 1").fetchone()[0]
    iss = con.execute("SELECT rel_path, reason FROM scan_issues WHERE scan_id=? AND kind='folder'", (s2["scan_id"],)).fetchall()
    con.close()
    check("Previous completed scan kept as baseline", bl == base_before)
    check("Unreadable location listed", any(r[0] == "Dept03" for r in iss), "; ".join(f"{a}: {b}" for a, b in iss))

    # network location going offline mid-scan
    s = create_project("Project N (network)", UNC_PREFIX + "\\N")
    check("N (UNC) first scan Completed with 3,000 files", s["status"] == "Completed" and s["files_found"] == 3000,
          f"{s['status']} {s['files_found']}")
    ndir = os.path.join(WORK, "N")
    off = ndir + "_offline"
    prev_n = latest_scan("Project N (network)")["seq"]
    press(mw(), "Re-scan project")
    t_start = time.time()
    renamed_ok = False
    while time.time() - t_start < 60:
        r = latest_scan("Project N (network)")
        if r["status"] != "Running" and r["seq"] > s["seq"]:
            break
        try:
            if time.time() - t_start > 0.8:
                os.rename(ndir, off)
                renamed_ok = True
                log(f"    share folder taken offline {time.time() - t_start:.1f}s after scan start")
                break
        except OSError:
            time.sleep(0.05)
    s3 = wait_scan("Project N (network)", prev_n + 1)
    try:
        ok_box("Scan incomplete", timeout=10)
    except Exception:
        try:
            ok_box("Scan failed", timeout=3)
        except Exception:
            pass
    if renamed_ok:
        for _ in range(100):
            try:
                os.rename(off, ndir)
                break
            except OSError:
                time.sleep(0.2)
    con = pdb("Project N (network)")
    ch = con.execute("SELECT kind, COUNT(*) FROM changes WHERE scan_id=? GROUP BY kind", (s3["scan_id"],)).fetchall()
    bl = con.execute("SELECT seq FROM scans WHERE is_baseline=1 ORDER BY seq DESC LIMIT 1").fetchone()[0]
    con.close()
    kinds = dict(ch)
    log(f"    offline scan: status={s3['status']} files_found={s3['files_found']} unreadable={s3['inaccessible_count']} changes={kinds}")
    check("Location went offline during the scan (test valid)", renamed_ok and s3["files_found"] < 3000,
          f"files found {s3['files_found']}")
    check("Offline scan labelled Incomplete/Failed, not Completed", s3["status"] in ("Incomplete", "Failed"), s3["status"])
    check("No files reported as Deleted", kinds.get("Deleted", 0) == 0, str(kinds))
    check("Baseline still the last successful scan", bl == s["seq"], f"baseline #{bl}")


def t4():
    log("\nTEST 4 - exact copies vs similar files, delete selected copies")
    t4 = os.path.join(WORK, "B", "T4")
    os.makedirs(t4)
    payload = b"T4 exact duplicate payload " * 4000
    copies = [os.path.join(t4, n) for n in ("copy_a.bin", "copy_b.bin", "copy_c.bin")]
    for i, p in enumerate(copies):
        with open(p, "wb") as f:
            f.write(payload)
        os.utime(p, (time.time() - 1000 + i * 100,) * 2)  # copy_a is the oldest -> default KEEP
    text1 = "\n".join(f"Line {i}: the quarterly review of storage usage for the audit team." for i in range(80))
    with open(os.path.join(t4, "T4 report v1.txt"), "w") as f:
        f.write(text1)
    with open(os.path.join(t4, "T4 report v2.txt"), "w") as f:
        f.write(text1.replace("Line 40:", "Line 40 (revised):"))
    open_project("Project B")
    rescan("Project B")
    p = os.path.join(OUT, "B_duplicates_t4.csv")
    export_from("Duplicates", "Export duplicate report...", "Export duplicate report", p)
    _, rows = read_csv_table(p)
    t4rows = [r for r in rows if r["Path"].startswith("T4\\")]
    check("The 3 exact copies form one verified group",
          sorted(r["Path"] for r in t4rows) == ["T4\\copy_a.bin", "T4\\copy_b.bin", "T4\\copy_c.bin"]
          and len({r["Group"] for r in t4rows}) == 1, str([r["Path"] for r in t4rows]))
    check("Similar files (different hashes) are not in the duplicates", not any("report" in r["Path"] for r in t4rows))
    nav("Duplicates")
    set_edit(mw(), "Duplicate filter", "T4\\")
    time.sleep(0.5)
    press(mw(), "Tick extra copies (shown groups)")
    find(mw(), ctype="Button", startswith="Review").invoke()
    d = window(r"Review deletion - Project B", regex=False)
    rows_txt = [e.element_info.name for e in find(d, name="Deletion review table", ctype="Table").descendants(control_type="DataItem")]
    check("Review screen lists full paths", any(x == os.path.join(UNC_PREFIX, "B", "T4", "copy_b.bin") for x in rows_txt)
          and any(x == os.path.join(UNC_PREFIX, "B", "T4", "copy_a.bin") for x in rows_txt))
    perm_note = any("PERMANENT" in x for x in rows_txt)
    press(d, "Delete Selected Copies")
    if perm_note:
        log("    location is a network share -> separate permanent-deletion confirmation shown")
        pdlg = window("Permanent deletion")
        toggle(find(pdlg, ctype="CheckBox", startswith="I understand"))
        find(pdlg, ctype="Button", startswith="Permanently delete").invoke()
    res = window("Deletion results", timeout=120)
    summary = " ".join(e.element_info.name for e in res.descendants(control_type="Text"))
    seq_b = latest_scan("Project B")["seq"]
    press(res, "Close")
    log("    " + summary[:200])
    check("Kept copy survives", os.path.isfile(copies[0]))
    check("Selected copies removed", not os.path.exists(copies[1]) and not os.path.exists(copies[2]))
    check("Similar files untouched", os.path.isfile(os.path.join(t4, "T4 report v1.txt"))
          and os.path.isfile(os.path.join(t4, "T4 report v2.txt")))
    con = pdb("Project B")
    acts = con.execute("SELECT source, outcome FROM actions WHERE action='Delete duplicate copy'").fetchall()
    con.close()
    check("Each deleted file has an audit entry", sum(1 for a in acts if a[0].endswith(("copy_b.bin", "copy_c.bin"))) == 2,
          "; ".join(f"{os.path.basename(a[0])}={a[1]}" for a in acts))
    wait_scan("Project B", seq_b + 1)  # automatic refresh re-scan after the action
    # same workflow on a LOCAL project -> Recycle Bin
    open_project("Project A")
    adir = os.path.join(WORK, "A")
    con = pdb("Project A")
    grp = [r[0] for r in con.execute("SELECT rel_path FROM files WHERE scan_id=(SELECT scan_id FROM scans WHERE "
                                     "is_baseline=1 ORDER BY seq DESC LIMIT 1) AND name LIKE 'dup_000_copy%'")]
    con.close()
    nav("Duplicates")
    set_edit(mw(), "Duplicate filter", "dup_000_")
    time.sleep(0.5)
    press(mw(), "Tick extra copies (shown groups)")
    find(mw(), ctype="Button", startswith="Review").invoke()
    d = window("Review deletion - Project A")
    cells = [e.element_info.name for e in find(d, name="Deletion review table", ctype="Table").descendants(control_type="DataItem")]
    check("Local project: deletion method is Recycle Bin", "Recycle Bin" in cells and "PERMANENT deletion" not in cells)
    press(d, "Delete Selected Copies")
    res = window("Deletion results", timeout=120)
    seq_a = latest_scan("Project A")["seq"]
    press(res, "Close")
    left = [g for g in grp if os.path.isfile(os.path.join(adir, g))]
    con = pdb("Project A")
    outs = [r[0] for r in con.execute("SELECT outcome FROM actions WHERE action='Delete duplicate copy'")]
    con.close()
    check("Local: exactly one copy kept, 2 sent to Recycle Bin", len(grp) == 3 and len(left) == 1
          and outs.count("Recycled") == 2, f"left={left} outcomes={outs}")
    wait_scan("Project A", seq_a + 1)
    open_project("Project B")
    nav("Compare Versions")
    press(mw(), "Analyse this snapshot")
    time.sleep(1)
    for _ in range(300):
        if "candidate pair" in text("Versions summary"):
            break
        time.sleep(0.5)
    con = pdb("Project B")
    snap = con.execute("SELECT scan_id FROM scans WHERE is_baseline=1 ORDER BY seq DESC LIMIT 1").fetchone()[0]
    vp = con.execute("SELECT * FROM version_pairs WHERE scan_id=? AND path_a LIKE 'T4%'", (snap,)).fetchall()
    con.close()
    check("Similar pair appears in Compare Versions with reasons",
          any(r["path_a"] == "T4\\T4 report v1.txt" and r["path_b"] == "T4\\T4 report v2.txt" for r in vp),
          "; ".join(f"{r['path_a']}|{r['path_b']}|{r['reasons']}|older={r['older']}" for r in vp))


def queue_rows():
    t = find(mw(), name="Organize queue", ctype="Table")
    cells = [e.element_info.name for e in t.descendants(control_type="DataItem")]
    return t, cells


def t5():
    log("\nTEST 5 - text PDF, scanned PDF, Word, image; confirm name; move; conflict")
    cdir = os.path.join(WORK, "C")
    dest = os.path.join(WORK, "Clients")
    create_project("Project C", cdir)
    nav("Organize")
    find(mw(), name="Client names & folders", ctype="TabItem").select()
    for name, alias, folder in (("Sharma Textiles", "Sharma Textiles Pvt Ltd", os.path.join(dest, "Sharma")),
                                ("Mehta Exports", "", os.path.join(dest, "Mehta")),
                                ("Gupta Agro Industries", "", os.path.join(dest, "Gupta"))):
        press(mw(), "Add...")
        d = window("Client name and folder")
        set_edit(d, "Client name", name)
        set_edit(d, "Client aliases", alias)
        set_edit(d, "Client folder", folder)
        press(d, "OK")
    find(mw(), name="Review queue", ctype="TabItem").select()
    press(mw(), "Read documents (text, Word, OCR)")
    msg = ok_box("Read documents", timeout=300)
    log("    " + msg.replace("\n", " ")[:200])
    con = pdb("Project C")
    q = {r["rel_path"]: r for r in con.execute("SELECT * FROM organize_queue")}
    con.close()
    for f, exp in (("Invoice_2025_001.pdf", "Sharma Textiles"), ("Scan_0007.pdf", "Mehta Exports"),
                   ("Engagement letter.docx", "Gupta Agro Industries"), ("receipt_photo.png", "Sharma Textiles")):
        r = q.get(f)
        check(f"{f}: detected '{exp}' with evidence", r is not None and r["detected_name"] == exp and r["excerpt"],
              f"{r['page_ref']}: {r['excerpt'][:70]}" if r else "missing")
    t, cells = queue_rows()
    check("Queue table shows detected names", "Mehta Exports" in cells and "Gupta Agro Industries" in cells)
    # confirm invoice + receipt
    os.makedirs(os.path.join(dest, "Sharma"), exist_ok=True)
    with open(os.path.join(dest, "Sharma", "receipt_photo.png"), "w") as f:
        f.write("existing file - must not be overwritten")
    for fname in ("Invoice_2025_001.pdf", "receipt_photo.png"):
        t, _ = queue_rows()
        find(t, name=fname, ctype="DataItem").select()
        time.sleep(0.4)
        press(mw(), "Confirm Name")
        time.sleep(0.6)
    check("Confirm Name leaves the files in place", os.path.isfile(os.path.join(cdir, "Invoice_2025_001.pdf"))
          and os.path.isfile(os.path.join(cdir, "receipt_photo.png")))
    con = pdb("Project C")
    st = {r[0]: r[1] for r in con.execute("SELECT rel_path, status FROM organize_queue")}
    con.close()
    check("Both entries are 'Name confirmed'", st["Invoice_2025_001.pdf"] == "Name confirmed"
          and st["receipt_photo.png"] == "Name confirmed", str(st))
    # tick the Select checkbox of both rows
    t, _ = queue_rows()
    items = t.descendants(control_type="DataItem")
    ncols = 9
    names = [e.element_info.name for e in items]
    for fname in ("Invoice_2025_001.pdf", "receipt_photo.png"):
        i = names.index(fname)
        chk = items[i - 1]
        r = chk.rectangle()
        chk.click_input(coords=(10, (r.bottom - r.top) // 2))  # real click on the tick-box indicator
        time.sleep(0.5)
    con = pdb("Project C")
    ticked = [r[0] for r in con.execute("SELECT rel_path FROM organize_queue WHERE selected=1")]
    con.close()
    log(f"    ticked in queue: {ticked}")
    press(mw(), "Move Selected Files")
    d = window("Review moves - Project C")
    cells = [e.element_info.name for e in find(d, name="Move review table", ctype="Table").descendants(control_type="DataItem")]
    inv_dst = os.path.join(dest, "Sharma", "Invoice_2025_001.pdf")
    check("Review shows exact source and destination paths",
          os.path.join(cdir, "Invoice_2025_001.pdf") in cells and inv_dst in cells, "")
    check("Review flags the destination conflict", any(c.startswith("CONFLICT") for c in cells))
    press(d, "Move Selected Files")
    res = window("Move results", timeout=120)
    seq_c = latest_scan("Project C")["seq"]
    press(res, "Close")
    wait_scan("Project C", seq_c + 1)
    check("Invoice moved to the client folder", os.path.isfile(inv_dst) and not os.path.exists(os.path.join(cdir, "Invoice_2025_001.pdf")))
    with open(os.path.join(dest, "Sharma", "receipt_photo.png")) as f:
        check("Conflicting file not overwritten; source stays", f.read().startswith("existing")
              and os.path.isfile(os.path.join(cdir, "receipt_photo.png")))
    p = os.path.join(OUT, "C_action_log.csv")
    export_from("History", "Export action log...", "Export action log", p)
    _, rows = read_csv_table(p)
    mv = [r for r in rows if r["Action"] == "Move file"]
    check("Audit log: move recorded with destination", any(r["Outcome"] == "Moved" and r["Destination"] == inv_dst for r in mv))
    check("Audit log: conflict skip recorded", any(r["Outcome"] == "Skipped" and r["Source"].endswith("receipt_photo.png") for r in mv))
    check("Audit log: Confirm Name recorded", sum(1 for r in rows if r["Action"] == "Confirm name") == 2)


def main():
    setup()
    launch()
    for t in (t1, t2, t3, t4, t5):
        try:
            t()
        except Exception:
            RESULTS.append(False)
            log("  [FAIL] exception:\n" + traceback.format_exc())
            try:
                for title in ("Export", "Scan incomplete", "Scan failed"):
                    if D.window(title=title).exists(timeout=0):
                        D.window(title=title).close()
            except Exception:
                pass
    try:
        quit_app()
    except Exception:
        pass
    log(f"\nRESULT: {sum(RESULTS)}/{len(RESULTS)} checks passed")
    with open(os.path.join(WORK, "acceptance_report.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(REPORT) + "\n")


if __name__ == "__main__":
    main()
