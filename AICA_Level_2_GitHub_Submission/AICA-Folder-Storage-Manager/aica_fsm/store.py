"""Storage.

* catalog.db  - list of projects (id, name, root path).
* projects/<project_id>/project.db - everything belonging to ONE project: snapshots, file index,
  changes, review queue, settings, audit log. A project database refuses to open if the project id
  stored inside it does not match the id it was opened for, so data can never cross projects.
"""
from __future__ import annotations

import json
import os
import sqlite3
import threading
import uuid
from dataclasses import dataclass

from .paths import app_data_dir, normalize_root, now_iso


class IsolationError(RuntimeError):
    pass


@dataclass(frozen=True)
class Project:
    project_id: str
    name: str
    root_path: str
    created: str

    @property
    def db_path(self) -> str:
        return os.path.join(projects_dir(), self.project_id, "project.db")


def projects_dir() -> str:
    d = os.path.join(app_data_dir(), "projects")
    os.makedirs(d, exist_ok=True)
    return d


def _connect(path: str) -> sqlite3.Connection:
    con = sqlite3.connect(path, timeout=30, check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA synchronous=NORMAL")
    con.execute("PRAGMA foreign_keys=ON")
    return con


# --------------------------------------------------------------------------------------- catalog
class Catalog:
    def __init__(self, path: str | None = None):
        self.path = path or os.path.join(app_data_dir(), "catalog.db")
        self.con = _connect(self.path)
        self.con.execute(
            """CREATE TABLE IF NOT EXISTS projects(
                project_id TEXT PRIMARY KEY, name TEXT NOT NULL, root_path TEXT NOT NULL,
                created TEXT NOT NULL, last_opened TEXT)"""
        )
        self.con.commit()

    def list(self) -> list[Project]:
        rows = self.con.execute("SELECT * FROM projects ORDER BY lower(name)").fetchall()
        return [Project(r["project_id"], r["name"], r["root_path"], r["created"]) for r in rows]

    def get(self, project_id: str) -> Project | None:
        r = self.con.execute("SELECT * FROM projects WHERE project_id=?", (project_id,)).fetchone()
        return Project(r["project_id"], r["name"], r["root_path"], r["created"]) if r else None

    def create(self, name: str, root_path: str) -> Project:
        name = name.strip()
        if not name:
            raise ValueError("Project name is required.")
        root = normalize_root(root_path)
        if not root:
            raise ValueError("Project folder is required.")
        if self.con.execute("SELECT 1 FROM projects WHERE lower(name)=lower(?)", (name,)).fetchone():
            raise ValueError(f"A project named '{name}' already exists.")
        p = Project(str(uuid.uuid4()), name, root, now_iso())
        os.makedirs(os.path.dirname(p.db_path), exist_ok=True)
        db = ProjectDB.create(p)
        db.close()
        self.con.execute(
            "INSERT INTO projects(project_id,name,root_path,created) VALUES(?,?,?,?)",
            (p.project_id, p.name, p.root_path, p.created),
        )
        self.con.commit()
        return p

    def rename(self, project_id: str, new_name: str) -> None:
        new_name = new_name.strip()
        if not new_name:
            raise ValueError("Name is required.")
        if self.con.execute(
            "SELECT 1 FROM projects WHERE lower(name)=lower(?) AND project_id<>?", (new_name, project_id)
        ).fetchone():
            raise ValueError(f"A project named '{new_name}' already exists.")
        self.con.execute("UPDATE projects SET name=? WHERE project_id=?", (new_name, project_id))
        self.con.commit()
        p = self.get(project_id)
        if p:
            db = ProjectDB.open(p)
            db.set_meta("name", new_name)
            db.close()

    def remove(self, project_id: str, delete_data: bool = True) -> None:
        p = self.get(project_id)
        self.con.execute("DELETE FROM projects WHERE project_id=?", (project_id,))
        self.con.commit()
        if p and delete_data:
            folder = os.path.dirname(p.db_path)
            for fn in os.listdir(folder) if os.path.isdir(folder) else []:
                try:
                    os.remove(os.path.join(folder, fn))
                except OSError:
                    pass
            try:
                os.rmdir(folder)
            except OSError:
                pass

    def touch(self, project_id: str) -> None:
        self.con.execute("UPDATE projects SET last_opened=? WHERE project_id=?", (now_iso(), project_id))
        self.con.commit()

    def close(self):
        self.con.close()


# --------------------------------------------------------------------------------- project db
SCHEMA = """
CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS scans(
    scan_id TEXT PRIMARY KEY, seq INTEGER NOT NULL, project_id TEXT NOT NULL, root_path TEXT NOT NULL,
    started TEXT NOT NULL, finished TEXT, status TEXT NOT NULL, is_baseline INTEGER NOT NULL DEFAULT 0,
    accepted_manually INTEGER NOT NULL DEFAULT 0,
    files_found INTEGER DEFAULT 0, total_bytes INTEGER DEFAULT 0, dirs_scanned INTEGER DEFAULT 0,
    inaccessible_count INTEGER DEFAULT 0, links_skipped INTEGER DEFAULT 0, hashed_files INTEGER DEFAULT 0,
    base_scan_id TEXT, message TEXT);
CREATE TABLE IF NOT EXISTS scan_issues(
    scan_id TEXT NOT NULL REFERENCES scans(scan_id) ON DELETE CASCADE,
    rel_path TEXT NOT NULL, kind TEXT NOT NULL, reason TEXT);
CREATE INDEX IF NOT EXISTS ix_issues ON scan_issues(scan_id);
CREATE TABLE IF NOT EXISTS files(
    scan_id TEXT NOT NULL REFERENCES scans(scan_id) ON DELETE CASCADE,
    rel_path TEXT NOT NULL, name TEXT NOT NULL, folder TEXT NOT NULL, ext TEXT NOT NULL,
    size INTEGER NOT NULL, mtime REAL, ctime REAL, file_id TEXT, sha256 TEXT, hash_error TEXT,
    PRIMARY KEY(scan_id, rel_path));
CREATE INDEX IF NOT EXISTS ix_files_hash ON files(scan_id, sha256);
CREATE INDEX IF NOT EXISTS ix_files_size ON files(scan_id, size);
CREATE TABLE IF NOT EXISTS changes(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scan_id TEXT NOT NULL REFERENCES scans(scan_id) ON DELETE CASCADE,
    base_scan_id TEXT NOT NULL, kind TEXT NOT NULL,
    old_path TEXT, new_path TEXT, old_size INTEGER, new_size INTEGER, old_mtime REAL, new_mtime REAL,
    method TEXT, detected TEXT NOT NULL, review TEXT);
CREATE INDEX IF NOT EXISTS ix_changes ON changes(scan_id);
CREATE TABLE IF NOT EXISTS actions(
    id INTEGER PRIMARY KEY AUTOINCREMENT, project_id TEXT NOT NULL, ts TEXT NOT NULL,
    action TEXT NOT NULL, source TEXT, destination TEXT, outcome TEXT NOT NULL, error TEXT,
    scan_id TEXT, detail TEXT);
CREATE TABLE IF NOT EXISTS client_names(
    id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE COLLATE NOCASE,
    aliases TEXT NOT NULL DEFAULT '', folder TEXT NOT NULL DEFAULT '');
CREATE TABLE IF NOT EXISTS doc_text(
    rel_path TEXT PRIMARY KEY, size INTEGER, mtime REAL, status TEXT, method TEXT,
    pages TEXT, error TEXT, doc_modified TEXT);
CREATE TABLE IF NOT EXISTS organize_queue(
    id INTEGER PRIMARY KEY AUTOINCREMENT, scan_id TEXT NOT NULL, rel_path TEXT NOT NULL UNIQUE,
    detected_name TEXT, candidates TEXT, excerpt TEXT, page_ref TEXT, source TEXT,
    status TEXT NOT NULL, confirmed_name TEXT, destination TEXT, selected INTEGER NOT NULL DEFAULT 0,
    note TEXT, updated TEXT);
CREATE TABLE IF NOT EXISTS version_pairs(
    id INTEGER PRIMARY KEY AUTOINCREMENT, scan_id TEXT NOT NULL, path_a TEXT NOT NULL, path_b TEXT NOT NULL,
    score REAL, reasons TEXT, older TEXT, order_note TEXT, order_certain INTEGER);
CREATE INDEX IF NOT EXISTS ix_vp ON version_pairs(scan_id);
CREATE TABLE IF NOT EXISTS move_reviews(
    old_path TEXT NOT NULL, new_path TEXT NOT NULL, decision TEXT NOT NULL, ts TEXT NOT NULL,
    PRIMARY KEY(old_path, new_path));
"""


class ProjectDB:
    """Connection to ONE project's database. Every instance is bound to a project id."""

    _write_lock = threading.RLock()

    def __init__(self, project: Project, con: sqlite3.Connection):
        self.project = project
        self.con = con

    @property
    def project_id(self) -> str:
        return self.project.project_id

    @classmethod
    def create(cls, project: Project) -> "ProjectDB":
        os.makedirs(os.path.dirname(project.db_path), exist_ok=True)
        if os.path.exists(project.db_path):
            raise IsolationError("Project database already exists.")
        con = _connect(project.db_path)
        con.executescript(SCHEMA)
        con.executemany(
            "INSERT INTO meta(key,value) VALUES(?,?)",
            [("project_id", project.project_id), ("name", project.name),
             ("root_path", project.root_path), ("created", project.created), ("schema", "1")],
        )
        con.commit()
        return cls(project, con)

    @classmethod
    def open(cls, project: Project) -> "ProjectDB":
        if not os.path.exists(project.db_path):
            raise IsolationError(f"Project database missing: {project.db_path}")
        con = _connect(project.db_path)
        con.executescript(SCHEMA)
        r = con.execute("SELECT value FROM meta WHERE key='project_id'").fetchone()
        if not r or r[0] != project.project_id:
            con.close()
            raise IsolationError("Project database belongs to a different project.")
        r = con.execute("SELECT value FROM meta WHERE key='root_path'").fetchone()
        if not r or r[0] != project.root_path:
            con.close()
            raise IsolationError("Project database root path does not match the project.")
        return cls(project, con)

    def close(self):
        try:
            self.con.close()
        except Exception:
            pass

    # ----- meta / settings
    def set_meta(self, key: str, value: str):
        with self._write_lock:
            self.con.execute("INSERT OR REPLACE INTO meta(key,value) VALUES(?,?)", (key, value))
            self.con.commit()

    def get_setting(self, key: str, default=None):
        r = self.con.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        if not r:
            return default
        try:
            return json.loads(r[0])
        except Exception:
            return r[0]

    def set_setting(self, key: str, value):
        with self._write_lock:
            self.con.execute("INSERT OR REPLACE INTO settings(key,value) VALUES(?,?)", (key, json.dumps(value)))
            self.con.commit()

    # ----- scans
    def scans(self) -> list[sqlite3.Row]:
        return self.con.execute("SELECT * FROM scans ORDER BY seq DESC").fetchall()

    def scan(self, scan_id: str) -> sqlite3.Row | None:
        return self.con.execute("SELECT * FROM scans WHERE scan_id=?", (scan_id,)).fetchone()

    def baseline(self) -> sqlite3.Row | None:
        return self.con.execute(
            "SELECT * FROM scans WHERE is_baseline=1 ORDER BY seq DESC LIMIT 1"
        ).fetchone()

    def usable_snapshots(self) -> list[sqlite3.Row]:
        """Snapshots whose results may be shown: completed, or incomplete scans the user accepted."""
        return self.con.execute(
            "SELECT * FROM scans WHERE status='Completed' OR accepted_manually=1 ORDER BY seq DESC"
        ).fetchall()

    def running_scans(self):
        return self.con.execute("SELECT * FROM scans WHERE status='Running'").fetchall()

    def mark_interrupted(self):
        """Scans left 'Running' from a previous app session were interrupted."""
        with self._write_lock:
            self.con.execute(
                "UPDATE scans SET status='Interrupted', finished=COALESCE(finished,?), "
                "message='App closed before the scan finished' WHERE status='Running'",
                (now_iso(),),
            )
            self.con.commit()

    def issues(self, scan_id: str) -> list[sqlite3.Row]:
        return self.con.execute(
            "SELECT * FROM scan_issues WHERE scan_id=? ORDER BY kind, rel_path", (scan_id,)
        ).fetchall()

    # ----- audit
    def log_action(self, action: str, outcome: str, source: str = "", destination: str = "",
                   error: str = "", scan_id: str = "", detail: str = "") -> None:
        with self._write_lock:
            self.con.execute(
                "INSERT INTO actions(project_id,ts,action,source,destination,outcome,error,scan_id,detail) "
                "VALUES(?,?,?,?,?,?,?,?,?)",
                (self.project_id, now_iso(), action, source, destination, outcome, error, scan_id, detail),
            )
            self.con.commit()
