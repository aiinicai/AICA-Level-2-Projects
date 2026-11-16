"""Scan engine. Runs in a worker thread; writes ONLY to the project database it was given.

Rules:
* Scans exactly project.root_path and its subfolders. If the root cannot be read the scan fails;
  there is no fallback to a parent folder, drive root or another project's location.
* Junctions and symbolic links are skipped (recorded as 'link' issues).
* Unreadable folders/files are recorded; a scan with unreadable locations is 'Incomplete' and does
  not become the baseline (unless the user later accepts it explicitly).
* Cancelled scans are labelled 'Cancelled' and never become the baseline.
"""
from __future__ import annotations

import hashlib
import os
import threading
import time
import uuid
from dataclasses import dataclass
from typing import Callable

from .changes import FileRec, diff
from .paths import is_within, now_iso
from .store import Project, ProjectDB

SYSTEM_DIRS = {"system volume information", "$recycle.bin", "$windows.~bt", "$windows.~ws", "recovery"}
HASH_CHUNK = 1024 * 1024


class Cancelled(Exception):
    pass


@dataclass
class Progress:
    project_id: str
    scan_id: str
    phase: str
    files: int = 0
    bytes: int = 0
    dirs: int = 0
    issues: int = 0
    hashed: int = 0
    to_hash: int = 0
    current: str = ""


def sha256_file(path: str, cancel: threading.Event | None = None) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            if cancel is not None and cancel.is_set():
                raise Cancelled()
            b = f.read(HASH_CHUNK)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def _file_id(st) -> str | None:
    ino = getattr(st, "st_ino", 0)
    dev = getattr(st, "st_dev", 0)
    if not ino:
        return None
    return f"{dev:x}:{ino:x}"


def load_snapshot(db: ProjectDB, scan_id: str) -> dict[str, FileRec]:
    out = {}
    for r in db.con.execute(
        "SELECT rel_path,name,size,mtime,file_id,sha256 FROM files WHERE scan_id=?", (scan_id,)
    ):
        out[r["rel_path"].lower()] = FileRec(r["rel_path"], r["size"], r["mtime"], r["file_id"], r["sha256"], r["name"])
    return out


def unverified_locations(db: ProjectDB, scan_id: str) -> list[str]:
    return [r["rel_path"] for r in db.con.execute(
        "SELECT rel_path FROM scan_issues WHERE scan_id=? AND kind IN ('folder','file','root')", (scan_id,))]


def compare_snapshots(db: ProjectDB, old_scan_id: str, new_scan_id: str):
    a = db.scan(old_scan_id)
    b = db.scan(new_scan_id)
    if a is None or b is None:
        raise ValueError("Snapshot not found in this project.")
    if a["project_id"] != db.project_id or b["project_id"] != db.project_id:
        raise ValueError("Snapshots belong to a different project.")
    return diff(load_snapshot(db, old_scan_id), load_snapshot(db, new_scan_id), unverified_locations(db, new_scan_id))


class Scanner:
    def __init__(self, project: Project, cancel: threading.Event | None = None,
                 progress: Callable[[Progress], None] | None = None, scan_id: str | None = None):
        self.project = project
        self.cancel = cancel or threading.Event()
        self.progress_cb = progress or (lambda p: None)
        self.scan_id = scan_id or str(uuid.uuid4())
        self._last_emit = 0.0

    def _emit(self, p: Progress, force=False):
        t = time.monotonic()
        if force or t - self._last_emit > 0.15:
            self._last_emit = t
            self.progress_cb(p)

    def run(self) -> str:
        db = ProjectDB.open(self.project)
        try:
            return self._run(db)
        finally:
            db.close()

    def _run(self, db: ProjectDB) -> str:
        root = self.project.root_path
        sid = self.scan_id
        seq = (db.con.execute("SELECT COALESCE(MAX(seq),0) FROM scans").fetchone()[0] or 0) + 1
        base = db.baseline()
        with db._write_lock:
            db.con.execute(
                "INSERT INTO scans(scan_id,seq,project_id,root_path,started,status,base_scan_id) "
                "VALUES(?,?,?,?,?,'Running',?)",
                (sid, seq, db.project_id, root, now_iso(), base["scan_id"] if base else None),
            )
            db.con.commit()
        db.log_action("Scan started", "Running", source=root, scan_id=sid)
        prog = Progress(db.project_id, sid, "Listing files")
        self._emit(prog, True)

        issues: list[tuple[str, str, str]] = []

        def add_issue(rel, kind, reason):
            issues.append((rel, kind, reason))
            if kind in ("folder", "file", "root"):
                prog.issues += 1

        # ---- root must be reachable; never fall back anywhere else
        try:
            if not os.path.isdir(root):
                raise FileNotFoundError("Folder not found or not reachable")
            with os.scandir(root) as it:
                next(iter(it), None)
        except OSError as e:
            add_issue("", "root", f"{type(e).__name__}: {e.strerror or e}")
            self._finish(db, sid, "Failed", prog, issues, [], message=f"Location unavailable: {root}")
            return sid

        rows: list[tuple] = []
        stack = [""]
        cancelled = False
        while stack:
            if self.cancel.is_set():
                cancelled = True
                break
            rel_dir = stack.pop()
            full_dir = os.path.join(root, rel_dir) if rel_dir else root
            prog.current = rel_dir or "(project folder)"
            try:
                with os.scandir(full_dir) as it:
                    entries = list(it)
            except OSError as e:
                add_issue(rel_dir, "folder", f"{type(e).__name__}: {e.strerror or e}")
                self._emit(prog)
                continue
            prog.dirs += 1
            for entry in entries:
                if self.cancel.is_set():
                    cancelled = True
                    break
                rel = os.path.join(rel_dir, entry.name) if rel_dir else entry.name
                try:
                    is_junction = getattr(entry, "is_junction", lambda: False)()
                    if entry.is_symlink() or is_junction:
                        add_issue(rel, "link", "Junction / symbolic link skipped")
                        continue
                    if entry.is_dir(follow_symlinks=False):
                        if not rel_dir and entry.name.lower() in SYSTEM_DIRS or entry.name.lower() in (
                                "system volume information", "$recycle.bin"):
                            add_issue(rel, "system", "Windows system folder skipped")
                            continue
                        stack.append(rel)
                        continue
                    if not entry.is_file(follow_symlinks=False):
                        continue
                    full = entry.path
                    if not is_within(root, full):  # defensive: never index outside the project
                        add_issue(rel, "link", "Outside project folder - skipped")
                        continue
                    st = os.stat(full, follow_symlinks=False)
                    name = entry.name
                    ext = os.path.splitext(name)[1].lower().lstrip(".")
                    rows.append((sid, rel, name, rel_dir, ext, st.st_size, st.st_mtime, st.st_ctime, _file_id(st)))
                    prog.files += 1
                    prog.bytes += st.st_size
                except OSError as e:
                    add_issue(rel, "file", f"{type(e).__name__}: {e.strerror or e}")
            self._emit(prog)
            if len(rows) >= 5000:
                self._insert_files(db, rows)
                rows = []
        if rows:
            self._insert_files(db, rows)
            rows = []

        if not cancelled:
            # root can disappear mid-scan (share offline)
            try:
                if not os.path.isdir(root):
                    add_issue("", "root", "Location went offline during the scan")
            except OSError as e:
                add_issue("", "root", f"Location went offline during the scan: {e}")

        if cancelled:
            self._finish(db, sid, "Cancelled", prog, issues, [], message="Cancelled by user")
            return sid

        # ---- fingerprints
        prog.phase = "Fingerprinting (SHA-256)"
        try:
            self._hash_phase(db, sid, base, prog)
        except Cancelled:
            self._finish(db, sid, "Cancelled", prog, issues, [], message="Cancelled by user during fingerprinting")
            return sid

        blocking = [i for i in issues if i[1] in ("folder", "file", "root")]
        status = "Incomplete" if blocking else "Completed"
        msg = (f"{len(blocking)} location(s) could not be checked" if blocking else "")
        self._finish(db, sid, status, prog, issues, [], message=msg, base=base)
        return sid

    def _insert_files(self, db: ProjectDB, rows):
        with db._write_lock:
            db.con.executemany(
                "INSERT OR REPLACE INTO files(scan_id,rel_path,name,folder,ext,size,mtime,ctime,file_id) "
                "VALUES(?,?,?,?,?,?,?,?,?)", rows)
            db.con.commit()

    def _hash_phase(self, db: ProjectDB, sid: str, base, prog: Progress):
        mode = db.get_setting("hash_mode", "all")
        max_mb = db.get_setting("hash_max_mb", 0) or 0
        cur = db.con.execute("SELECT rel_path,size,mtime,file_id FROM files WHERE scan_id=?", (sid,)).fetchall()
        prev = {}
        if base is not None:
            for r in db.con.execute(
                "SELECT rel_path,size,mtime,file_id,sha256 FROM files WHERE scan_id=? AND sha256 IS NOT NULL",
                (base["scan_id"],)):
                prev[r["rel_path"].lower()] = r
        size_count: dict[int, int] = {}
        for r in cur:
            size_count[r["size"]] = size_count.get(r["size"], 0) + 1
        base_sizes = set()
        if base is not None and mode != "all":
            base_sizes = {r[0] for r in db.con.execute("SELECT DISTINCT size FROM files WHERE scan_id=?", (base["scan_id"],))}

        reuse, todo = [], []
        for r in cur:
            p = prev.get(r["rel_path"].lower())
            if p is not None and p["size"] == r["size"] and p["mtime"] == r["mtime"] and (
                    not p["file_id"] or not r["file_id"] or p["file_id"] == r["file_id"]):
                reuse.append((p["sha256"], sid, r["rel_path"]))
                continue
            if r["size"] == 0:
                reuse.append((hashlib.sha256(b"").hexdigest(), sid, r["rel_path"]))
                continue
            dup_candidate = size_count.get(r["size"], 0) > 1
            if dup_candidate or r["size"] in base_sizes:
                todo.append(r)  # duplicates/moves always need a full fingerprint
            elif mode == "all" and not (max_mb and r["size"] > max_mb * 1024 * 1024):
                todo.append(r)
        with db._write_lock:
            db.con.executemany("UPDATE files SET sha256=? WHERE scan_id=? AND rel_path=?", reuse)
            db.con.commit()
        prog.to_hash = len(todo)
        prog.hashed = 0
        root = self.project.root_path
        batch = []
        for r in todo:
            if self.cancel.is_set():
                raise Cancelled()
            prog.current = r["rel_path"]
            full = os.path.join(root, r["rel_path"])
            try:
                h = sha256_file(full, self.cancel)
                batch.append((h, None, sid, r["rel_path"]))
            except Cancelled:
                raise
            except OSError as e:
                batch.append((None, f"{type(e).__name__}: {e.strerror or e}", sid, r["rel_path"]))
            prog.hashed += 1
            self._emit(prog)
            if len(batch) >= 500:
                self._write_hashes(db, batch)
                batch = []
        if batch:
            self._write_hashes(db, batch)

    def _write_hashes(self, db, batch):
        with db._write_lock:
            db.con.executemany("UPDATE files SET sha256=?, hash_error=? WHERE scan_id=? AND rel_path=?", batch)
            db.con.commit()

    def _finish(self, db: ProjectDB, sid: str, status: str, prog: Progress, issues, _unused, message="", base=None):
        with db._write_lock:
            if issues:
                db.con.executemany(
                    "INSERT INTO scan_issues(scan_id,rel_path,kind,reason) VALUES(?,?,?,?)",
                    [(sid, rel, kind, reason) for rel, kind, reason in issues])
            agg = db.con.execute(
                "SELECT COUNT(*), COALESCE(SUM(size),0), SUM(sha256 IS NOT NULL) FROM files WHERE scan_id=?", (sid,)
            ).fetchone()
            blocking = sum(1 for i in issues if i[1] in ("folder", "file", "root"))
            links = sum(1 for i in issues if i[1] == "link")
            db.con.execute(
                "UPDATE scans SET finished=?, status=?, is_baseline=?, files_found=?, total_bytes=?, "
                "dirs_scanned=?, inaccessible_count=?, links_skipped=?, hashed_files=?, message=? WHERE scan_id=?",
                (now_iso(), status, 1 if status == "Completed" else 0, agg[0], agg[1], prog.dirs, blocking,
                 links, agg[2] or 0, message, sid))
            db.con.commit()
        prog.phase = status
        if base is not None and status in ("Completed", "Incomplete"):
            prog.phase = "Detecting changes"
            self._emit(prog, True)
            store_changes(db, base["scan_id"], sid)
        db.log_action("Scan finished", status, source=self.project.root_path, scan_id=sid,
                      detail=f"{agg[0]} files, {blocking} unreadable location(s), {links} link(s) skipped"
                             + (f"; {message}" if message else ""))
        prog.phase = status
        self._emit(prog, True)


def store_changes(db: ProjectDB, base_id: str, new_id: str) -> int:
    res = compare_snapshots(db, base_id, new_id)
    t = now_iso()
    rows = []
    for c in res.changes:
        o, n = c.old, c.new
        rows.append((new_id, base_id, c.kind, o.rel_path if o else None, n.rel_path if n else None,
                     o.size if o else None, n.size if n else None, o.mtime if o else None,
                     n.mtime if n else None, c.method, t))
    with db._write_lock:
        db.con.execute("DELETE FROM changes WHERE scan_id=?", (new_id,))
        db.con.executemany(
            "INSERT INTO changes(scan_id,base_scan_id,kind,old_path,new_path,old_size,new_size,old_mtime,"
            "new_mtime,method,detected) VALUES(?,?,?,?,?,?,?,?,?,?,?)", rows)
        db.con.commit()
    return len(rows)


def accept_incomplete_as_baseline(db: ProjectDB, scan_id: str) -> None:
    s = db.scan(scan_id)
    if s is None or s["status"] != "Incomplete":
        raise ValueError("Only an incomplete scan can be accepted.")
    with db._write_lock:
        db.con.execute("UPDATE scans SET is_baseline=1, accepted_manually=1 WHERE scan_id=?", (scan_id,))
        db.con.commit()
    db.log_action("Accept incomplete scan as baseline", "Done", scan_id=scan_id,
                  detail=f"{s['inaccessible_count']} location(s) were not checked")
