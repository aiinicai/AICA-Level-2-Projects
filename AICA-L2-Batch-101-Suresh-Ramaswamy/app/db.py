"""SQLite storage: clients, projects, files, lines, document register, audit trail, backup."""
import datetime as dt
import json
import shutil
import sqlite3
import zipfile
from pathlib import Path
from typing import List, Optional

from . import config
from .config import DB_PATH, DEFAULT_SETTINGS
from .models import Line, DocSeries

SCHEMA = """
CREATE TABLE IF NOT EXISTS clients(
  id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, gstin TEXT UNIQUE NOT NULL,
  legal_name TEXT, trade_name TEXT, state_code TEXT, reg_type TEXT, return_type TEXT);
CREATE TABLE IF NOT EXISTS projects(
  id INTEGER PRIMARY KEY AUTOINCREMENT, client_id INTEGER NOT NULL, fy TEXT, month INTEGER,
  year INTEGER, frequency TEXT, schema_version TEXT, status TEXT DEFAULT 'Open',
  csv_status TEXT DEFAULT 'Not generated', created TEXT, UNIQUE(client_id, month, year));
CREATE TABLE IF NOT EXISTS files(
  id INTEGER PRIMARY KEY AUTOINCREMENT, project_id INTEGER, filename TEXT, stored_path TEXT,
  sha256 TEXT, ftype TEXT, status TEXT, records INTEGER DEFAULT 0, review_count INTEGER DEFAULT 0,
  message TEXT, processed_at TEXT);
CREATE TABLE IF NOT EXISTS lines(id INTEGER PRIMARY KEY AUTOINCREMENT, project_id INTEGER, data TEXT);
CREATE TABLE IF NOT EXISTS docs(id INTEGER PRIMARY KEY AUTOINCREMENT, project_id INTEGER, data TEXT);
CREATE TABLE IF NOT EXISTS audit(
  id INTEGER PRIMARY KEY AUTOINCREMENT, project_id INTEGER, ts TEXT, operator TEXT,
  action TEXT, detail TEXT);
CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS datasets(
  id INTEGER PRIMARY KEY AUTOINCREMENT, project_id INTEGER, filename TEXT, sha256 TEXT, uploaded TEXT, data TEXT);
CREATE TABLE IF NOT EXISTS hsn_master(
  client_id INTEGER, hsn TEXT, description TEXT, uqc TEXT, rate TEXT, updated TEXT, PRIMARY KEY(client_id, hsn));
"""


def now() -> str:
    return dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class Database:
    def __init__(self, path: Path = None):
        config.ensure_dirs()
        self.path = Path(path or DB_PATH)
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    # ---------- generic ----------
    def q(self, sql, args=()):
        return [dict(r) for r in self.conn.execute(sql, args).fetchall()]

    def x(self, sql, args=()):
        cur = self.conn.execute(sql, args)
        self.conn.commit()
        return cur.lastrowid

    # ---------- settings ----------
    def get_settings(self) -> dict:
        s = dict(DEFAULT_SETTINGS)
        for r in self.q("SELECT key,value FROM settings"):
            s[r["key"]] = r["value"]
        return s

    def set_setting(self, key, value):
        self.x("INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
               (key, str(value)))

    # ---------- clients ----------
    def clients(self):
        return self.q("SELECT * FROM clients ORDER BY name")

    def save_client(self, c: dict) -> int:
        if c.get("id"):
            self.x("UPDATE clients SET name=?,gstin=?,legal_name=?,trade_name=?,state_code=?,reg_type=?,"
                   "return_type=? WHERE id=?",
                   (c["name"], c["gstin"], c["legal_name"], c["trade_name"], c["state_code"],
                    c["reg_type"], c["return_type"], c["id"]))
            return c["id"]
        return self.x("INSERT INTO clients(name,gstin,legal_name,trade_name,state_code,reg_type,return_type)"
                      " VALUES(?,?,?,?,?,?,?)",
                      (c["name"], c["gstin"], c["legal_name"], c["trade_name"], c["state_code"],
                       c["reg_type"], c["return_type"]))

    def delete_client_data(self, client_id: int):
        for p in self.q("SELECT id FROM projects WHERE client_id=?", (client_id,)):
            self.delete_project_data(p["id"], keep_project=False)
        self.x("DELETE FROM hsn_master WHERE client_id=?", (client_id,))
        self.x("DELETE FROM clients WHERE id=?", (client_id,))

    # ---------- projects ----------
    def projects(self, client_id: int):
        return self.q("SELECT * FROM projects WHERE client_id=? ORDER BY year DESC, month DESC", (client_id,))

    def get_project(self, pid: int) -> Optional[dict]:
        r = self.q("SELECT * FROM projects WHERE id=?", (pid,))
        return r[0] if r else None

    def create_project(self, client_id, fy, month, year, frequency, schema_version) -> int:
        ex = self.q("SELECT id FROM projects WHERE client_id=? AND month=? AND year=?", (client_id, month, year))
        if ex:
            return ex[0]["id"]
        pid = self.x("INSERT INTO projects(client_id,fy,month,year,frequency,schema_version,created)"
                     " VALUES(?,?,?,?,?,?,?)", (client_id, fy, month, year, frequency, schema_version, now()))
        self.audit(pid, "Project created", f"{month:02d}/{year}")
        return pid

    def set_csv_status(self, pid, status):
        self.x("UPDATE projects SET csv_status=? WHERE id=?", (status, pid))

    def delete_project_data(self, pid: int, keep_project=True):
        for t in ("files", "lines", "docs", "datasets"):
            self.x(f"DELETE FROM {t} WHERE project_id=?", (pid,))
        if not keep_project:
            self.x("DELETE FROM audit WHERE project_id=?", (pid,))
            self.x("DELETE FROM projects WHERE id=?", (pid,))

    # ---------- files ----------
    def files(self, pid):
        return self.q("SELECT * FROM files WHERE project_id=? ORDER BY id", (pid,))

    def file_by_hash(self, pid, sha):
        r = self.q("SELECT * FROM files WHERE project_id=? AND sha256=?", (pid, sha))
        return r[0] if r else None

    def add_file(self, pid, filename, stored_path, sha, ftype) -> int:
        return self.x("INSERT INTO files(project_id,filename,stored_path,sha256,ftype,status) VALUES(?,?,?,?,?,?)",
                      (pid, filename, str(stored_path), sha, ftype, "Queued"))

    def update_file(self, fid, **kw):
        cols = ",".join(f"{k}=?" for k in kw)
        self.x(f"UPDATE files SET {cols} WHERE id=?", (*kw.values(), fid))

    # ---------- lines ----------
    def load_lines(self, pid) -> List[Line]:
        out = []
        for r in self.q("SELECT id,data FROM lines WHERE project_id=? ORDER BY id", (pid,)):
            l = Line.from_dict(json.loads(r["data"]))
            out.append(l)
        return out

    def save_lines(self, pid, lines: List[Line]):
        self.conn.execute("DELETE FROM lines WHERE project_id=?", (pid,))
        self.conn.executemany("INSERT INTO lines(project_id,data) VALUES(?,?)",
                              [(pid, json.dumps(l.to_dict())) for l in lines])
        self.conn.commit()

    # ---------- document register ----------
    def load_docs(self, pid) -> List[DocSeries]:
        return [DocSeries.from_dict(json.loads(r["data"]))
                for r in self.q("SELECT data FROM docs WHERE project_id=? ORDER BY id", (pid,))]

    def save_docs(self, pid, docs: List[DocSeries]):
        self.conn.execute("DELETE FROM docs WHERE project_id=?", (pid,))
        self.conn.executemany("INSERT INTO docs(project_id,data) VALUES(?,?)",
                              [(pid, json.dumps(d.to_dict())) for d in docs])
        self.conn.commit()

    # ---------- master-template datasets ----------
    def datasets(self, pid) -> List[dict]:
        """[{id, filename, sha256, uploaded, tables:{key:[rows]}}]"""
        out = []
        for r in self.q("SELECT * FROM datasets WHERE project_id=? ORDER BY id", (pid,)):
            out.append({"id": r["id"], "filename": r["filename"], "sha256": r["sha256"], "uploaded": r["uploaded"],
                        "tables": json.loads(r["data"])})
        return out

    def add_dataset(self, pid, filename, sha, tables: dict) -> int:
        return self.x("INSERT INTO datasets(project_id,filename,sha256,uploaded,data) VALUES(?,?,?,?,?)",
                      (pid, filename, sha, now(), json.dumps(tables)))

    def update_dataset(self, ds_id: int, tables: dict):
        self.x("UPDATE datasets SET data=? WHERE id=?", (json.dumps(tables), ds_id))

    def delete_dataset(self, ds_id: int):
        self.x("DELETE FROM datasets WHERE id=?", (ds_id,))

    def dataset_by_hash(self, pid, sha):
        r = self.q("SELECT id, filename FROM datasets WHERE project_id=? AND sha256=?", (pid, sha))
        return r[0] if r else None

    # ---------- HSN memory (per client) ----------
    def hsn_master(self, client_id) -> dict:
        return {r["hsn"]: {"description": r["description"], "uqc": r["uqc"], "rate": r["rate"]}
                for r in self.q("SELECT * FROM hsn_master WHERE client_id=?", (client_id,))}

    def remember_hsn(self, client_id, hsn, description="", uqc="", rate=""):
        old = self.hsn_master(client_id).get(hsn, {})
        self.x("INSERT OR REPLACE INTO hsn_master(client_id,hsn,description,uqc,rate,updated) VALUES(?,?,?,?,?,?)",
               (client_id, hsn, description or old.get("description", ""), uqc or old.get("uqc", ""),
                str(rate) if rate not in (None, "") else old.get("rate", ""), now()))

    # ---------- audit ----------
    def audit(self, pid, action, detail=""):
        self.x("INSERT INTO audit(project_id,ts,operator,action,detail) VALUES(?,?,?,?,?)",
               (pid, now(), self.get_settings().get("operator", ""), action, detail))

    def audit_log(self, pid):
        return self.q("SELECT ts,operator,action,detail FROM audit WHERE project_id=? ORDER BY id DESC", (pid,))

    # ---------- backup / restore ----------
    def backup(self, dest_zip: Path) -> Path:
        dest_zip = Path(dest_zip)
        tmp = config.BACKUP_DIR / "_db_snapshot.db"
        config.BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        snap = sqlite3.connect(tmp)
        with snap:
            self.conn.backup(snap)
        snap.close()
        with zipfile.ZipFile(dest_zip, "w", zipfile.ZIP_DEFLATED) as z:
            z.write(tmp, "app_data.db")
            if config.CLIENTS_DIR.exists():
                for p in config.CLIENTS_DIR.rglob("*"):
                    if p.is_file():
                        z.write(p, str(Path("clients") / p.relative_to(config.CLIENTS_DIR)))
        tmp.unlink(missing_ok=True)
        return dest_zip

    def restore(self, src_zip: Path):
        """Restore a backup zip over the data folder. Restart the app afterwards."""
        self.conn.close()
        with zipfile.ZipFile(src_zip) as z:
            for name in z.namelist():
                target = (config.DATA_ROOT / name).resolve()
                if config.DATA_ROOT.resolve() not in target.parents and target != config.DATA_ROOT.resolve():
                    raise ValueError("Unsafe path in backup file")
            z.extractall(config.DATA_ROOT)
