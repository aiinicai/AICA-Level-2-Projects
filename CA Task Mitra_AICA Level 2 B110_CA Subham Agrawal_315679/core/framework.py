"""Core framework: database, router, events, settings, auth helpers, module registry."""
import sqlite3, re, hashlib, secrets, datetime as dt
from . import paths


class HttpError(Exception):
    def __init__(self, code, msg):
        self.code, self.msg = code, msg


class Response:
    def __init__(self, body, ctype="text/plain", filename=None):
        self.body = body if isinstance(body, bytes) else body.encode("utf-8")
        self.ctype, self.filename = ctype, filename


class DB:
    def __init__(self, path=None):
        self.c = sqlite3.connect(path or paths.DBFILE, timeout=30, check_same_thread=False)
        self.c.row_factory = sqlite3.Row
        self.c.execute("PRAGMA foreign_keys=ON")

    def q(self, sql, a=()):
        return [dict(r) for r in self.c.execute(sql, a).fetchall()]

    def one(self, sql, a=()):
        r = self.c.execute(sql, a).fetchone()
        return dict(r) if r else None

    def x(self, sql, a=()):
        return self.c.execute(sql, a).lastrowid

    def script(self, s):
        self.c.executescript(s)

    def commit(self):
        self.c.commit()

    def close(self):
        self.c.close()


CORE_SCHEMA = """
create table if not exists settings(key text primary key, value text);
create table if not exists users(id integer primary key, username text unique not null, name text,
  role text not null default 'employee', email text, phone text, designation text, pw text not null,
  active int default 1, demo int default 0, created text default (datetime('now')));
create table if not exists sessions(token text primary key, user_id int not null, expires real);
create table if not exists module_state(key text primary key, enabled int default 1);
create table if not exists sub_state(mod text, key text, enabled int default 1, primary key(mod,key));
create table if not exists audit_log(id integer primary key, ts text default (datetime('now')), user text, action text, detail text);
"""

# ---------- passwords / settings / helpers ----------
def hash_pw(p, salt=None):
    salt = salt or secrets.token_hex(8)
    return salt + "$" + hashlib.pbkdf2_hmac("sha256", p.encode(), salt.encode(), 100000).hex()


def check_pw(p, stored):
    return secrets.compare_digest(hash_pw(p, stored.split("$", 1)[0]), stored)


def get_setting(db, k, d=""):
    r = db.one("select value from settings where key=?", (k,))
    return r["value"] if r and r["value"] is not None else d


def set_setting(db, k, v):
    db.x("insert into settings(key,value) values(?,?) on conflict(key) do update set value=excluded.value", (k, str(v)))


def today():
    return dt.date.today().isoformat()


def log(db, user, action, detail=""):
    db.x("insert into audit_log(user,action,detail) values(?,?,?)", (user, action, (detail or "")[:500]))


def mod_on(db, key):
    r = db.one("select enabled from module_state where key=?", (key,))
    return bool(r and r["enabled"])


def sub_on(db, mod, sub):
    r = db.one("select enabled from sub_state where mod=? and key=?", (mod, sub))
    return bool(r and r["enabled"])


# ---------- router ----------
class Router:
    def __init__(self):
        self.routes = []

    def add(self, method, path, roles=None, sub=None):
        rx = re.compile("^" + re.sub(r"<(\w+)>", r"(?P<\1>[^/]+)", path) + "$")

        def deco(fn):
            self.routes.append((method, rx, fn, roles, sub))
            return fn
        return deco

    def get(self, p, **k): return self.add("GET", p, **k)
    def post(self, p, **k): return self.add("POST", p, **k)
    def put(self, p, **k): return self.add("PUT", p, **k)
    def delete(self, p, **k): return self.add("DELETE", p, **k)


class Ctx:
    def __init__(self, db, user, body, query, params):
        self.db, self.user, self.body, self.query, self.params = db, user, body, query, params

    def need(self, *keys):
        miss = [k for k in keys if self.body.get(k) in (None, "")]
        if miss:
            raise HttpError(400, "Required: " + ", ".join(miss))
        return [self.body[k] for k in keys]

    @property
    def is_boss(self):
        return self.user["role"] in ("ca", "manager")


CA = ["ca"]
BOSS = ["ca", "manager"]

# ---------- events (loose coupling between modules) ----------
SUBS = {}


def subscribe(evt, mod):
    def deco(fn):
        SUBS.setdefault(evt, []).append((mod, fn))
        return fn
    return deco


def emit(db, evt, payload):
    for mod, fn in SUBS.get(evt, []):
        if mod_on(db, mod):
            try:
                fn(db, payload)
            except Exception as e:  # a failing add-on must never break core work
                print("event error", evt, mod, e)


# ---------- registry ----------
def load(db):
    from modules import ALL
    db.script(CORE_SCHEMA)
    for m in ALL:
        if m.SCHEMA:
            db.script(m.SCHEMA)
        for stmt in getattr(m, "MIGRATE", []):  # additive upgrades for databases created by older versions
            try:
                db.x(stmt)
            except Exception:
                pass
        man = m.MANIFEST
        ready = man["status"] == "ready"
        db.x("insert or ignore into module_state(key,enabled) values(?,?)", (man["key"], 1 if ready else 0))
        for s in man["subs"]:
            db.x("insert or ignore into sub_state(mod,key,enabled) values(?,?,?)",
                 (man["key"], s[0], 1 if (ready and s[2] == "ready") else 0))
    db.commit()
