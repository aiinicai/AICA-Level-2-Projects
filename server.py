import csv
import io
import os
import re
import secrets
import sqlite3
import statistics
from datetime import datetime
from functools import wraps

import openpyxl
from flask import Flask, Response, g, jsonify, request, send_from_directory
from openpyxl.styles import Alignment, Font, PatternFill
from werkzeug.security import check_password_hash, generate_password_hash

import sys
if getattr(sys, "frozen", False):  # running as DuneCount.exe
    BASE = sys._MEIPASS  # bundled front-end files
    DATA = os.path.dirname(sys.executable)  # database lives next to the exe
else:
    BASE = DATA = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(DATA, "dune_count.db")
LOCATIONS = {"SHW1": "Showroom 1", "SHW2": "Showroom 2", "SHW3": "Showroom 3", "WHS4": "Warehouse 4"}

app = Flask(__name__, static_folder=None)
app.config["MAX_CONTENT_LENGTH"] = 25 * 1024 * 1024

SCHEMA = """
create table if not exists users(
  id integer primary key, email text unique not null, name text, role text not null,
  pwd_hash text, active integer default 1, created text);
create table if not exists sessions(token text primary key, user_id integer, created text);
create table if not exists counts(
  id integer primary key, location text not null, name text, status text not null,
  created_by text, created_at text, requested_by text, requested_at text,
  confirmed_by text, confirmed_at text, submitted_by text, closed_at text, stickers_declared integer);
create table if not exists book(
  id integer primary key, count_id integer, barcode text, description text,
  unique(count_id, barcode));
create index if not exists ix_book on book(count_id, barcode);
create table if not exists entries(
  id integer primary key, count_id integer, barcode text, sticker_no text, in_book integer,
  user_id integer, user_name text, ts text,
  unique(count_id, barcode), unique(count_id, sticker_no));
create table if not exists booklets(
  id integer primary key, count_id integer, user_id integer, user_name text, start_no text,
  ts text, used integer default 0, is_first integer default 1);
create table if not exists missing_stickers(
  id integer primary key, count_id integer, sticker_no text, user_name text, ts text, unique(count_id, sticker_no));
create table if not exists audit(
  id integer primary key, ts text, user_email text, user_name text, count_id integer,
  location text, action text, detail text);
"""


def init_db():
    c = sqlite3.connect(DB)
    c.execute("pragma journal_mode=wal")
    c.executescript(SCHEMA)
    for col in ("sticker_flag text default ''", "flag_detail text default ''"):
        try:
            c.execute("alter table entries add column " + col)
        except sqlite3.OperationalError:
            pass  # already migrated
    c.commit()
    c.close()


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def db():
    if "db" not in g:
        g.db = sqlite3.connect(DB)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def _close(_):
    d = g.pop("db", None)
    if d is not None:
        d.close()


def rows(sql, a=()):
    return [dict(r) for r in db().execute(sql, a).fetchall()]


def one(sql, a=()):
    r = db().execute(sql, a).fetchone()
    return dict(r) if r else None


def run(sql, a=()):
    c = db().execute(sql, a)
    db().commit()
    return c


def err(msg, code=400):
    return jsonify(error=msg), code


def log(action, detail="", count=None, user=None):
    u = user or getattr(g, "user", None) or {}
    run("insert into audit(ts,user_email,user_name,count_id,location,action,detail) values(?,?,?,?,?,?,?)",
        (now(), u.get("email"), u.get("name"), count["id"] if count else None,
         count["location"] if count else None, action, detail))


def auth(role=None):
    def deco(f):
        @wraps(f)
        def w(*a, **k):
            t = request.headers.get("Authorization", "").replace("Bearer ", "")
            u = one("select u.* from sessions s join users u on u.id=s.user_id where s.token=?", (t,))
            if not u or not u["active"]:
                return err("Please sign in again.", 401)
            if role and u["role"] != role:
                return err("Admin access only.", 403)
            g.user = u
            return f(*a, **k)
        return w
    return deco


def norm_email(e):
    return (e or "").strip().lower()


def public_user(u):
    return {"id": u["id"], "email": u["email"], "name": u["name"], "role": u["role"]}


def start_session(u):
    t = secrets.token_hex(24)
    run("insert into sessions(token,user_id,created) values(?,?,?)", (t, u["id"], now()))
    return jsonify(token=t, user=public_user(u))


PORTAL_ROLE = {"admin": "admin", "counter": "counter"}


@app.post("/api/signup")
def signup():
    d = request.get_json(silent=True) or {}
    email, pw, portal = norm_email(d.get("email")), d.get("password") or "", d.get("portal")
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        return err("Enter a valid email id.")
    if len(pw) < 6:
        return err("Password must be at least 6 characters.")
    total = one("select count(*) n from users")["n"]
    if total == 0:
        if portal != "admin":
            return err("The first account must be created from the Count Admin portal.", 403)
        cur = run("insert into users(email,name,role,pwd_hash,created) values(?,?,?,?,?)",
                  (email, (d.get("name") or "Admin").strip(), "admin", generate_password_hash(pw), now()))
        u = one("select * from users where id=?", (cur.lastrowid,))
        log("signup", "First user - registered as admin", user=u)
        return start_session(u)
    u = one("select * from users where email=?", (email,))
    if not u:
        return err("This email id has not been authorised by the admin. Sign-up is not allowed.", 403)
    if u["pwd_hash"]:
        return err("Account already registered. Please sign in.")
    if PORTAL_ROLE.get(portal) != u["role"]:
        return err("This email belongs to the %s portal." % ("Count Admin" if u["role"] == "admin" else "Count Persons"), 403)
    run("update users set pwd_hash=? where id=?", (generate_password_hash(pw), u["id"]))
    log("signup", "Employee registered", user=u)
    return start_session(u)


@app.post("/api/login")
def login():
    d = request.get_json(silent=True) or {}
    u = one("select * from users where email=?", (norm_email(d.get("email")),))
    if not u or not u["pwd_hash"] or not check_password_hash(u["pwd_hash"], d.get("password") or ""):
        return err("Invalid email id or password. New employees must sign up first.")
    if not u["active"]:
        return err("Account disabled.", 403)
    if PORTAL_ROLE.get(d.get("portal")) != u["role"]:
        return err("This account belongs to the %s portal." % ("Count Admin" if u["role"] == "admin" else "Count Persons"), 403)
    log("login", "", user=u)
    return start_session(u)


@app.get("/api/setup-state")
def setup_state():
    return jsonify(first_user=one("select count(*) n from users")["n"] == 0)


@app.get("/api/me")
@auth()
def me():
    return jsonify(user=public_user(g.user), locations=LOCATIONS)


@app.post("/api/logout")
@auth()
def logout():
    log("logout")
    run("delete from sessions where token=?", (request.headers.get("Authorization", "").replace("Bearer ", ""),))
    return jsonify(ok=True)


# ---------------- employees ----------------
@app.get("/api/employees")
@auth("admin")
def employees():
    return jsonify(rows("""select u.id,u.email,u.name,u.role,u.active,u.created,
        (u.pwd_hash is not null) registered,
        (select count(*) from entries e where e.user_id=u.id) scans from users u order by u.id"""))


@app.post("/api/employees")
@auth("admin")
def add_employee():
    d = request.get_json(silent=True) or {}
    email, name = norm_email(d.get("email")), (d.get("name") or "").strip()
    role = d.get("role") if d.get("role") in ("admin", "counter") else "counter"
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email) or not name:
        return err("Name and a valid email id are required.")
    if one("select 1 from users where email=?", (email,)):
        return err("This email id already exists.")
    run("insert into users(email,name,role,created) values(?,?,?,?)", (email, name, role, now()))
    log("employee_added", "%s <%s> as %s" % (name, email, role))
    return jsonify(ok=True)


@app.delete("/api/employees/<int:uid>")
@auth("admin")
def del_employee(uid):
    u = one("select * from users where id=?", (uid,))
    if not u or u["id"] == g.user["id"]:
        return err("Cannot remove this user.")
    run("delete from sessions where user_id=?", (uid,))
    run("delete from users where id=?", (uid,))
    log("employee_removed", u["email"])
    return jsonify(ok=True)


# ---------------- counts ----------------
def stats(c):
    cid = c["id"]
    book = one("select count(*) n from book where count_id=?", (cid,))["n"]
    e = one("select count(*) n, coalesce(sum(in_book),0) m from entries where count_id=?", (cid,))
    pct = round(100.0 * e["m"] / book, 1) if book else 0
    miss = one("select count(*) n from missing_stickers where count_id=?", (cid,))["n"]
    flags = one("select count(*) n from entries where count_id=? and sticker_flag not in ('','MISSING')", (cid,))["n"] + \
        one("select count(*) n from booklets where count_id=? and is_first=0", (cid,))["n"] + miss
    return {**c, "sticker_flags": flags, "book": book, "counted": e["n"], "matched": e["m"], "unlisted": e["n"] - e["m"],
            "pct": pct, "missing_stickers": miss, "stickers_used": e["n"] + miss, "location_name": LOCATIONS.get(c["location"])}


@app.get("/api/counts")
@auth()
def list_counts():
    cs = rows("select * from counts order by id desc")
    if g.user["role"] != "admin":
        cs = [c for c in cs if c["status"] != "submitted"]
    return jsonify([stats(c) for c in cs])


def get_count(cid):
    return one("select * from counts where id=?", (cid,))


@app.get("/api/counts/<int:cid>")
@auth()
def count_detail(cid):
    c = get_count(cid)
    if not c:
        return err("Count not found.", 404)
    s = stats(c)
    s["mine"] = one("select count(*) n from entries where count_id=? and user_id=?", (cid, g.user["id"]))["n"]
    s["needs_booklet"] = not one("select 1 from booklets where count_id=? and user_id=?", (cid, g.user["id"]))
    s["next_sticker"] = expected_sticker(cid, g.user["id"])
    return jsonify(s)


SER = re.compile(r"^(.*?)(\d+)$")


def split_serial(s):
    m = SER.match(s or "")
    return (m.group(1), int(m.group(2)), len(m.group(2))) if m else (None, None, 0)


def make_serial(prefix, n, width):
    return prefix + str(n).zfill(width)


def next_serial(s):
    p, n, w = split_serial(s)
    return make_serial(p, n + 1, w) if p is not None else ""


def expected_sticker(cid, uid):
    """Next sticker this counter should use: a freshly declared booklet start, else last used + 1."""
    b = one("select * from booklets where count_id=? and user_id=? and used=0 order by id desc limit 1", (cid, uid))
    if b:
        return b["start_no"]
    e = one("select sticker_no from entries where count_id=? and user_id=? order by id desc limit 1", (cid, uid))
    return next_serial(e["sticker_no"]) if e else ""


@app.post("/api/counts/<int:cid>/booklet")
@auth()
def set_booklet(cid):
    c = get_count(cid)
    if not c or c["status"] != "counting":
        return err("Count is not open for entry.")
    start = ((request.get_json(silent=True) or {}).get("start") or "").strip().upper()
    if not re.fullmatch(r"\d{6}", start):
        return err("Sticker serial number must be exactly 6 digits (e.g. 100245).")
    first = 0 if one("select 1 from booklets where count_id=? and user_id=?", (cid, g.user["id"])) else 1
    run("update booklets set used=1 where count_id=? and user_id=? and used=0", (cid, g.user["id"]))
    run("insert into booklets(count_id,user_id,user_name,start_no,ts,used,is_first) values(?,?,?,?,?,0,?)",
        (cid, g.user["id"], g.user["name"], start, now(), first))
    log("booklet_started" if first else "NEW_BOOKLET_STARTED", "Sticker booklet starts at %s" % start, c)
    return jsonify(ok=True, next_sticker=start)


def sticker_check(cid, uid, sticker):
    """Return (flag, detail, skipped) comparing the entered sticker with the expected next serial."""
    exp = expected_sticker(cid, uid)
    if not exp or exp == sticker:
        return "", "", []
    ep, en, ew = split_serial(exp)
    sp, sn, _ = split_serial(sticker)
    if sp is not None and sp == ep and en < sn <= en + 50:  # a bigger jump is treated as a new booklet
        used = {r["sticker_no"] for r in rows("select sticker_no from entries where count_id=? union select sticker_no from missing_stickers where count_id=?", (cid, cid))}
        missing = [make_serial(ep, k, ew) for k in range(en, sn) if make_serial(ep, k, ew) not in used]
        if missing:
            lst = missing[0] if len(missing) == 1 else "%s to %s" % (missing[0], missing[-1])
            return "MISSING", "%d sticker(s) skipped: %s (expected %s, got %s)" % (len(missing), lst, exp, sticker), missing
        return "", "", []
    return "NEW_SERIES", "Serial changed: expected %s, got %s - new booklet?" % (exp, sticker), []


def parse_book(f):
    name = (f.filename or "").lower()
    if name.endswith(".csv"):
        data = list(csv.reader(io.StringIO(f.read().decode("utf-8-sig", "ignore"))))
    else:
        wb = openpyxl.load_workbook(f, read_only=True, data_only=True)
        data = [list(r) for r in wb.active.iter_rows(values_only=True)]
    if len(data) < 2:
        raise ValueError("The file has no data rows. Row 1 must be the header.")
    head = [str(h or "").strip().lower() for h in data[0]]

    def find(keys, default):
        for i, h in enumerate(head):
            if any(k in h for k in keys):
                return i
        return default
    bi = find(["barcode", "bar code", "vin", "chassis", "vehicle id", "unit id", "serial"], 0)
    di = find(["desc", "model", "name", "make", "item"], 1 if len(head) > 1 and bi != 1 else (0 if bi != 0 else None))
    out, seen, dups = [], set(), 0
    for r in data[1:]:
        if bi >= len(r) or r[bi] in (None, ""):
            continue
        v = r[bi]
        code = str(int(v)) if isinstance(v, float) and v == int(v) else str(v)
        code = code.strip().upper()
        if not code:
            continue
        if code in seen:
            dups += 1
            continue
        seen.add(code)
        desc = ""
        if di is not None and di < len(r) and r[di] is not None:
            desc = str(r[di]).strip()
        out.append((code, desc))
    if not out:
        raise ValueError("No barcodes found. Make sure a 'Barcode' column exists.")
    return out, dups


@app.post("/api/counts")
@auth("admin")
def create_count():
    loc = request.form.get("location")
    f = request.files.get("file")
    if loc not in LOCATIONS:
        return err("Select a valid location.")
    if not f:
        return err("Upload the book quantity Excel file to start the count.")
    if one("select 1 from counts where location=? and status!='submitted'", (loc,)):
        return err("%s already has a count in progress. Submit it before starting a new one." % loc)
    try:
        items, dups = parse_book(f)
    except Exception as ex:
        return err("Could not read file: %s" % ex)
    name = (request.form.get("name") or "").strip() or "%s count %s" % (loc, datetime.now().strftime("%d %b %Y"))
    cur = run("insert into counts(location,name,status,created_by,created_at) values(?,?,?,?,?)",
              (loc, name, "counting", g.user["name"], now()))
    cid = cur.lastrowid
    db().executemany("insert into book(count_id,barcode,description) values(?,?,?)", [(cid, b, d) for b, d in items])
    db().commit()
    log("count_started", "Book uploaded: %d units%s" % (len(items), (", %d duplicate rows ignored" % dups) if dups else ""), get_count(cid))
    return jsonify(id=cid, units=len(items), duplicates=dups)


@app.get("/api/counts/<int:cid>/suggest")
@auth()
def suggest(cid):
    q = re.sub(r"[^A-Za-z0-9]", "", request.args.get("q", "")).upper()
    if not q:
        return jsonify([])
    r = rows("""select b.barcode, b.description from book b where b.count_id=? and b.barcode like ?
        and not exists(select 1 from entries e where e.count_id=b.count_id and e.barcode=b.barcode)
        order by b.barcode limit 25""", (cid, "%" + q))
    return jsonify(r)


@app.get("/api/counts/<int:cid>/entries")
@auth()
def entries(cid):
    sql = "select e.*, b.description from entries e left join book b on b.count_id=e.count_id and b.barcode=e.barcode where e.count_id=?"
    a = [cid]
    if g.user["role"] != "admin" or request.args.get("mine"):
        sql += " and e.user_id=?"
        a.append(g.user["id"])
    sql += " order by e.id desc"
    if request.args.get("limit"):
        sql += " limit %d" % int(request.args["limit"])
    return jsonify(rows(sql, a))


def record_missing_sticker(c, sticker):
    """Sticker consumed with no unit (missing sequence): counts as a sticker, not as a unit (bar code NULL)."""
    cid, uid = c["id"], g.user["id"]
    if not sticker:
        return err("Enter the sticker number that is missing.")
    if not re.fullmatch(r"\d{6}", sticker):
        return err("Sticker serial number must be exactly 6 digits.")
    if not one("select 1 from booklets where count_id=? and user_id=?", (cid, uid)):
        return err("Enter the starting sticker number of your booklet first.")
    if one("select 1 from entries where count_id=? and sticker_no=?", (cid, sticker)) or \
            one("select 1 from missing_stickers where count_id=? and sticker_no=?", (cid, sticker)):
        return err("Sticker %s is already used in this count." % sticker)
    _, _, skipped = sticker_check(cid, uid, sticker)  # numbers skipped before this sticker are missing too
    for s in skipped + [sticker]:
        run("insert or ignore into missing_stickers(count_id,sticker_no,user_name,ts) values(?,?,?,?)", (cid, s, g.user["name"], now()))
    nxt = next_serial(sticker)
    run("update booklets set used=1 where count_id=? and user_id=? and used=0", (cid, uid))
    run("insert into booklets(count_id,user_id,user_name,start_no,ts,used,is_first) values(?,?,?,?,?,0,1)",
        (cid, uid, g.user["name"], nxt, now()))
    log("STICKER_MISSING", "Sticker(s) used with no bar code: %s" % ", ".join(skipped + [sticker]), c)
    return jsonify(ok=True, missing=True, flag="MISSING", next_sticker=nxt,
                   **{k: v for k, v in stats(c).items() if k in ("counted", "pct", "book", "matched", "stickers_used", "missing_stickers")})


@app.post("/api/counts/<int:cid>/entries")
@auth()
def add_entry(cid):
    c = get_count(cid)
    if not c:
        return err("Count not found.", 404)
    if c["status"] != "counting":
        return err("This count is closed for entry (status: %s)." % c["status"].replace("_", " "))
    d = request.get_json(silent=True) or {}
    code = (d.get("barcode") or "").strip().upper()
    sticker = (d.get("sticker") or "").strip().upper()
    if (d.get("reason") or "") == "missing" and not code:
        return record_missing_sticker(c, sticker)
    if not code or not sticker:
        return err("Select a unit and enter the sticker number.")
    if not re.fullmatch(r"\d{6}", sticker):
        return err("Sticker serial number must be exactly 6 digits.")
    inb = 1 if one("select 1 from book where count_id=? and barcode=?", (cid, code)) else 0
    if not inb and not d.get("unlisted"):
        return err("This barcode is not in the book stock. Use 'Unit not in book list' to record it as excess.")
    if one("select 1 from entries where count_id=? and barcode=?", (cid, code)):
        return err("Unit %s is already counted." % code)
    if one("select 1 from entries where count_id=? and sticker_no=?", (cid, sticker)):
        return err("Sticker %s is already used in this count." % sticker)
    if not one("select 1 from booklets where count_id=? and user_id=?", (cid, g.user["id"])):
        return err("Enter the starting sticker number of your booklet first.")
    if one("select 1 from missing_stickers where count_id=? and sticker_no=?", (cid, sticker)):
        return err("Sticker %s was recorded as a missing sequence - no bar code can be entered against it." % sticker)
    flag, detail, skipped = sticker_check(cid, g.user["id"], sticker)
    reason = d.get("reason") or ""
    if flag:
        if reason not in ("new_booklet", "missing"):
            return err("Sticker serial changed (%s). Select a reason: start of new booklet or missing sequence." % detail)
        flag = "NEW_BOOKLET" if reason == "new_booklet" else "MISSING"
        if flag != "MISSING" or not skipped:
            skipped = []
        detail = ("Reason: %s. " % ("Start of new booklet" if reason == "new_booklet" else "Missing sequence")) + detail
    run("insert into entries(count_id,barcode,sticker_no,in_book,user_id,user_name,ts,sticker_flag,flag_detail) values(?,?,?,?,?,?,?,?,?)",
        (cid, code, sticker, inb, g.user["id"], g.user["name"], now(), flag, detail))
    for s in skipped:
        run("insert or ignore into missing_stickers(count_id,sticker_no,user_name,ts) values(?,?,?,?)", (cid, s, g.user["name"], now()))
    run("update booklets set used=1 where count_id=? and user_id=? and used=0", (cid, g.user["id"]))
    log("unit_counted", "%s | sticker %s%s" % (code, sticker, "" if inb else " | NOT IN BOOK (excess)"), c)
    if flag:
        log("STICKER_" + flag, detail, c)
    return jsonify(ok=True, next_sticker=next_serial(sticker), flag=flag,
                   **{k: v for k, v in stats(c).items() if k in ("counted", "pct", "book", "matched")})


@app.get("/api/counts/<int:cid>/flags")
@auth("admin")
def sticker_flags(cid):
    out = []
    for e in rows("select ts,user_name,barcode,sticker_no,sticker_flag,flag_detail from entries where count_id=? and sticker_flag not in ('','MISSING') order by id", (cid,)):
        out.append({"ts": e["ts"], "user": e["user_name"], "type": e["sticker_flag"], "sticker": e["sticker_no"], "barcode": e["barcode"], "detail": e["flag_detail"]})
    for m in rows("select * from missing_stickers where count_id=? order by id", (cid,)):
        out.append({"ts": m["ts"], "user": m["user_name"], "type": "MISSING", "sticker": m["sticker_no"], "barcode": "",
                    "detail": "Missing sequence: sticker %s used with no bar code (counts as sticker, not unit)" % m["sticker_no"]})
    for b in rows("select * from booklets where count_id=? and is_first=0 order by id", (cid,)):
        out.append({"ts": b["ts"], "user": b["user_name"], "type": "NEW_BOOKLET", "sticker": b["start_no"], "barcode": "",
                    "detail": "New booklet started at %s" % b["start_no"]})
    out.sort(key=lambda x: x["ts"])
    return jsonify(out)


@app.delete("/api/counts/<int:cid>/entries/<int:eid>")
@auth("admin")
def del_entry(cid, eid):
    c = get_count(cid)
    e = one("select * from entries where id=? and count_id=?", (eid, cid))
    if not e or not c or c["status"] == "submitted":
        return err("Entry cannot be removed.")
    run("delete from entries where id=?", (eid,))
    log("unit_removed", "%s | sticker %s" % (e["barcode"], e["sticker_no"]), c)
    return jsonify(ok=True)


@app.post("/api/counts/<int:cid>/request-completion")
@auth()
def req_completion(cid):
    c = get_count(cid)
    if not c or c["status"] != "counting":
        return err("Count is not in counting stage.")
    run("update counts set status='completion_requested', requested_by=?, requested_at=? where id=?",
        (g.user["name"], now(), cid))
    log("completion_requested", "Counter confirmed completion", c)
    return jsonify(ok=True)


@app.post("/api/counts/<int:cid>/confirm-completion")
@auth("admin")
def confirm_completion(cid):
    c = get_count(cid)
    if not c or c["status"] not in ("completion_requested", "counting"):
        return err("Count cannot be confirmed in its current status.")
    run("update counts set status='sticker_check', confirmed_by=?, confirmed_at=? where id=?", (g.user["name"], now(), cid))
    log("completion_confirmed", "Count admin confirmed completion", c)
    return jsonify(ok=True)


@app.post("/api/counts/<int:cid>/reopen")
@auth("admin")
def reopen(cid):
    c = get_count(cid)
    if not c or c["status"] in ("counting", "submitted"):
        return err("Cannot reopen.")
    run("update counts set status='counting', requested_by=null, requested_at=null, confirmed_by=null, confirmed_at=null where id=?", (cid,))
    log("count_reopened", "Returned to counting", c)
    return jsonify(ok=True)


@app.get("/api/counts/<int:cid>/recon")
@auth("admin")
def recon(cid):
    c = get_count(cid)
    if not c:
        return err("Not found", 404)
    units = one("select count(*) n from entries where count_id=?", (cid,))["n"]
    miss = rows("select sticker_no, user_name, ts from missing_stickers where count_id=? order by id", (cid,))
    return jsonify(units=units, missing=miss, missing_count=len(miss), total_used=units + len(miss),
                   declared=c["stickers_declared"])


@app.get("/api/counts/<int:cid>/recon-full")
@auth("admin")
def recon_full(cid):
    c = get_count(cid)
    if not c:
        return err("Not found", 404)
    r, s = report(cid)
    miss = rows("select sticker_no, user_name, ts from missing_stickers where count_id=? order by id", (cid,))
    units = s["counted"]
    return jsonify(
        count=stats(c),
        sticker={"units": units, "missing": len(miss), "total_used": units + len(miss), "declared": c["stickers_declared"],
                 "missing_list": miss},
        book={"book": s["book"], "physical": units, "matched": s["zero"], "not_found": s["minus"], "excess": s["plus"],
              "net_variance": units - s["book"]},
        excess=[{"barcode": x["barcode"], "sticker_no": x["sticker_no"], "counted_by": x["counted_by"], "counted_at": x["counted_at"]}
                for x in r if x["difference"] == 1],
        not_found=[{"barcode": x["barcode"], "description": x["description"]} for x in r if x["difference"] == -1])


@app.post("/api/counts/<int:cid>/submit")
@auth("admin")
def submit(cid):
    c = get_count(cid)
    if not c or c["status"] != "sticker_check":
        return err("Confirm count completion first.")
    try:
        declared = int((request.get_json(silent=True) or {}).get("stickers"))
    except (TypeError, ValueError):
        return err("Enter the number of stickers used as a whole number.")
    units = one("select count(*) n from entries where count_id=?", (cid,))["n"]
    miss = one("select count(*) n from missing_stickers where count_id=?", (cid,))["n"]
    if declared != units + miss:
        log("sticker_mismatch", "Declared %d stickers vs %d units + %d missing stickers = %d - submission blocked" % (declared, units, miss, units + miss), c)
        return err("Mismatch: %d stickers declared but %d units counted + %d missing stickers = %d. Reconcile before submitting." % (declared, units, miss, units + miss))
    run("update counts set status='submitted', stickers_declared=?, submitted_by=?, closed_at=? where id=?",
        (declared, g.user["name"], now(), cid))
    log("count_submitted", "Stickers %d = units %d + missing stickers %d. Report generated." % (declared, units, miss), c)
    return jsonify(ok=True)


# ---------------- report / exports ----------------
def report(cid):
    book = rows("select barcode, description from book where count_id=? order by barcode", (cid,))
    ent = {e["barcode"]: e for e in rows("select * from entries where count_id=?", (cid,))}
    out, seen = [], set()
    for b in book:
        e = ent.get(b["barcode"])
        seen.add(b["barcode"])
        out.append({"barcode": b["barcode"], "description": b["description"], "sticker_no": e["sticker_no"] if e else "",
                    "book_qty": 1, "counted_qty": 1 if e else 0, "difference": 0 if e else -1,
                    "counted_by": e["user_name"] if e else "", "counted_at": e["ts"] if e else ""})
    for code, e in ent.items():
        if code not in seen:
            out.append({"barcode": code, "description": "(not in book list)", "sticker_no": e["sticker_no"], "book_qty": 0,
                        "counted_qty": 1, "difference": 1, "counted_by": e["user_name"], "counted_at": e["ts"]})
    summ = {"book": len(book), "counted": len(ent),
            "zero": sum(1 for r in out if r["difference"] == 0),
            "minus": sum(1 for r in out if r["difference"] == -1),
            "plus": sum(1 for r in out if r["difference"] == 1)}
    return out, summ


@app.get("/api/counts/<int:cid>/report")
@auth("admin")
def report_json(cid):
    c = get_count(cid)
    if not c:
        return err("Not found", 404)
    r, s = report(cid)
    return jsonify(count=stats(c), rows=r, summary=s)


def csv_response(name, header, data):
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(header)
    w.writerows(data)
    return Response("﻿" + buf.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": "attachment; filename=%s" % name})


@app.get("/api/counts/<int:cid>/export/<kind>")
@auth("admin")
def export(cid, kind):
    c = get_count(cid)
    if not c:
        return err("Not found", 404)
    tag = "%s_%s" % (c["location"], cid)
    if kind == "entries":
        r = rows("""select e.ts, e.barcode, b.description, e.sticker_no, case e.in_book when 1 then 'In book' else 'Excess' end st,
                 e.user_name, e.sticker_flag, e.flag_detail from entries e left join book b on b.count_id=e.count_id and b.barcode=e.barcode
                 where e.count_id=? order by e.id""", (cid,))
        return csv_response("count_table_%s.csv" % tag, ["Time", "Barcode", "Description", "Sticker No", "Status", "Counted By", "Sticker Flag", "Flag Detail"],
                            [list(x.values()) for x in r])
    if kind == "results":
        r, s = report(cid)
        return csv_response("count_results_%s.csv" % tag,
                            ["Barcode", "Description", "Sticker No", "Book Qty", "Counted Qty", "Difference", "Counted By", "Counted At"],
                            [[x["barcode"], x["description"], x["sticker_no"], x["book_qty"], x["counted_qty"], x["difference"],
                              x["counted_by"], x["counted_at"]] for x in r])
    if kind == "audit":
        r = rows("select ts,user_name,user_email,location,action,detail from audit where count_id=? order by id", (cid,))
        return csv_response("audit_trail_%s.csv" % tag, ["Time", "User", "Email", "Location", "Action", "Detail"], [list(x.values()) for x in r])
    if kind == "xlsx":
        return xlsx_response(c)
    return err("Unknown export", 404)


@app.get("/api/export/audit")
@auth("admin")
def export_audit_all():
    r = rows("select ts,user_name,user_email,location,action,detail from audit order by id")
    return csv_response("audit_trail_all.csv", ["Time", "User", "Email", "Location", "Action", "Detail"], [list(x.values()) for x in r])


def style_header(ws, ncol):
    for i in range(1, ncol + 1):
        c = ws.cell(row=1, column=i)
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor="0B1F41")
        c.alignment = Alignment(horizontal="center")


def xlsx_response(c):
    r, s = report(c["id"])
    missing = rows("select sticker_no, user_name, ts from missing_stickers where count_id=? order by id", (c["id"],))
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Count vs Book"
    head = ["Barcode", "Description", "Sticker No", "Book Qty", "Counted Qty", "Difference", "Counted By", "Counted At"]
    ws.append(head)
    for x in r:
        ws.append([x["barcode"], x["description"], x["sticker_no"], x["book_qty"], x["counted_qty"], x["difference"], x["counted_by"], x["counted_at"]])
    style_header(ws, len(head))
    last = len(r) + 1
    ws.append(["TOTAL", "", "", "=SUM(D2:D%d)" % last, "=SUM(E2:E%d)" % last, "=SUM(F2:F%d)" % last])
    for cell in ws[ws.max_row]:
        cell.font = Font(bold=True)
    red, green, amber = (PatternFill("solid", fgColor=x) for x in ("F8C9C9", "CDEFD8", "FFE7A8"))
    for row in ws.iter_rows(min_row=2, max_row=last):
        d = row[5].value
        row[5].fill = green if d == 0 else (red if d == -1 else amber)
    for col, w in zip("ABCDEFGH", (24, 32, 14, 11, 13, 12, 20, 20)):
        ws.column_dimensions[col].width = w
    ws.freeze_panes = "A2"
    sm = wb.create_sheet("Summary")
    for line in [("Location", "%s - %s" % (c["location"], LOCATIONS.get(c["location"]))), ("Count", c["name"]),
                 ("Status", c["status"] + ("" if c["status"] == "submitted" else "  (PROVISIONAL)")),
                 ("Book units", s["book"]), ("Units counted", s["counted"]), ("Stickers used (units + missing)", s["counted"] + len(missing)), ("Missing stickers (used, no bar code)", len(missing)),
                 ("Matched (0)", s["zero"]), ("Missing (-1)", s["minus"]), ("Excess (+1)", s["plus"]),
                 ("Stickers declared by admin", c["stickers_declared"] if c["stickers_declared"] is not None else "-"),
                 ("Generated", now())]:
        sm.append(line)
    sm.column_dimensions["A"].width = 28
    sm.column_dimensions["B"].width = 36
    for cell in sm["A"]:
        cell.font = Font(bold=True)
    ms = wb.create_sheet("Missing Stickers")
    ms.append(["Sticker No", "Recorded By", "Recorded At", "Note"])
    for m in missing:
        ms.append([m["sticker_no"], m["user_name"], m["ts"], "Sticker used - no bar code (missing sequence)"])
    style_header(ms, 4)
    for col, w in zip("ABCD", (16, 20, 20, 46)):
        ms.column_dimensions[col].width = w
    buf = io.BytesIO()
    wb.save(buf)
    return Response(buf.getvalue(), mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": "attachment; filename=count_vs_book_%s_%s.xlsx" % (c["location"], c["id"])})


@app.get("/api/template.xlsx")
def template():
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Barcode", "Description"])
    for i in range(1, 6):
        ws.append(["EXC2024%05d" % (1000 + i * 37), "Excavator model sample %d" % i])
    style_header(ws, 2)
    ws.column_dimensions["A"].width = 24
    ws.column_dimensions["B"].width = 34
    buf = io.BytesIO()
    wb.save(buf)
    return Response(buf.getvalue(), mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": "attachment; filename=book_quantity_template.xlsx"})


# ---------------- dashboards ----------------
@app.get("/api/dashboard")
@auth("admin")
def dashboard():
    cs = [stats(c) for c in rows("select * from counts order by id desc")]
    latest = {}
    for c in cs:
        latest.setdefault(c["location"], c)
    locs = [{"location": k, "name": v, **({kk: latest[k][kk] for kk in ("id", "status", "book", "counted", "pct", "unlisted")} if k in latest else {"status": "none", "book": 0, "counted": 0, "pct": 0, "unlisted": 0})}
            for k, v in LOCATIONS.items()]
    members = rows("""select user_id, user_name, count(*) n, min(ts) first_ts, max(ts) last_ts, count(distinct count_id) counts_n,
                      sum(1-in_book) excess from entries group by user_id order by n desc""")
    for m in members:
        a, b = datetime.strptime(m["first_ts"], "%Y-%m-%d %H:%M:%S"), datetime.strptime(m["last_ts"], "%Y-%m-%d %H:%M:%S")
        mins = max((b - a).total_seconds() / 60.0, 1.0)
        m["rate_per_hour"] = round(m["n"] / mins * 60, 1) if m["n"] > 1 else 0
    total_entries = sum(c["counted"] for c in cs)
    kpi = {"active": sum(1 for c in cs if c["status"] != "submitted"), "submitted": sum(1 for c in cs if c["status"] == "submitted"),
           "book": sum(c["book"] for c in cs if c["status"] != "submitted"),
           "counted": sum(c["counted"] for c in cs if c["status"] != "submitted"),
           "total_counted": total_entries, "stickers": total_entries + one("select count(*) n from missing_stickers")["n"],
           "pct": round(100.0 * sum(c["matched"] for c in cs if c["status"] != "submitted") /
                        max(1, sum(c["book"] for c in cs if c["status"] != "submitted")), 1),
           "team": len(members), "flags": sum(c["sticker_flags"] for c in cs if c["status"] != "submitted")}
    tl = rows("select substr(ts,1,16) t, count(*) n from entries group by t order by t desc limit 60")[::-1]
    cum = 0
    base = one("select count(*) n from entries")["n"] - sum(x["n"] for x in tl)
    cum = base
    for x in tl:
        cum += x["n"]
        x["cum"] = cum
    # task-wise: members per count
    for c in cs:
        c["members"] = rows("select user_name, count(*) n from entries where count_id=? group by user_id order by n desc", (c["id"],))
    status_dist = {}
    for c in cs:
        status_dist[c["status"]] = status_dist.get(c["status"], 0) + 1
    recent_flags = []
    for c in cs:
        if c["sticker_flags"]:
            for f in sticker_flags(c["id"]).get_json():
                recent_flags.append({**f, "location": c["location"], "count_id": c["id"]})
    recent_flags.sort(key=lambda x: x["ts"], reverse=True)
    return jsonify(recent_flags=recent_flags[:15], kpi=kpi, locations=locs, members=members, counts=cs, timeline=tl, status_dist=status_dist)


@app.get("/api/analytics")
@auth("admin")
def analytics():
    hourly = rows("select substr(ts,1,13)||':00' h, count(*) n from entries group by substr(ts,1,13) order by h desc limit 24")[::-1]
    gaps = {}
    prev = {}
    for e in rows("select user_name, count_id, ts from entries order by id"):
        t = datetime.strptime(e["ts"], "%Y-%m-%d %H:%M:%S")
        key = (e["user_name"], e["count_id"])
        if key in prev:
            sec = (t - prev[key]).total_seconds()
            if 0 <= sec <= 600:
                gaps.setdefault(e["user_name"], []).append(sec)
        prev[key] = t
    speed = [{"name": k, "median_sec": round(statistics.median(v), 1), "avg_sec": round(sum(v) / len(v), 1), "n": len(v)} for k, v in gaps.items()]
    speed.sort(key=lambda x: x["median_sec"])
    var = {"zero": 0, "minus": 0, "plus": 0}
    acc = []
    for c in rows("select * from counts where status='submitted'"):
        r, s = report(c["id"])
        var["zero"] += s["zero"]; var["minus"] += s["minus"]; var["plus"] += s["plus"]
        acc.append({"location": c["location"], "name": c["name"], "accuracy": round(100.0 * s["zero"] / max(1, s["book"] + s["plus"]), 1),
                    "zero": s["zero"], "minus": s["minus"], "plus": s["plus"]})
    ex = one("select count(*) n, coalesce(sum(1-in_book),0) x from entries")
    dur = []
    for c in rows("select * from counts where closed_at is not null"):
        a = datetime.strptime(c["created_at"], "%Y-%m-%d %H:%M:%S"); b = datetime.strptime(c["closed_at"], "%Y-%m-%d %H:%M:%S")
        dur.append({"location": c["location"], "minutes": round((b - a).total_seconds() / 60, 1)})
    by_loc = rows("select c.location l, count(*) n from entries e join counts c on c.id=e.count_id group by c.location")
    return jsonify(hourly=hourly, speed=speed, variance=var, accuracy=acc, excess_rate=round(100.0 * ex["x"] / max(1, ex["n"]), 1),
                   durations=dur, by_location=by_loc)


@app.get("/api/audit")
@auth("admin")
def audit_list():
    sql, a = "select * from audit", []
    if request.args.get("count_id"):
        sql += " where count_id=?"
        a.append(int(request.args["count_id"]))
    return jsonify(rows(sql + " order by id desc limit 1000", a))


# ---------------- static front ends ----------------
@app.get("/")
def home():
    return Response("""<!doctype html><meta name=viewport content="width=device-width,initial-scale=1"><title>Dune Count</title>
<body style="margin:0;min-height:100vh;display:grid;place-items:center;background:#0B1F41;color:#fff;font-family:Segoe UI,sans-serif">
<div style="text-align:center"><h1 style="letter-spacing:.3em;color:#00AEEF">DUNE COUNT</h1>
<p><a style="color:#fff;margin:12px;padding:14px 28px;border:1px solid #00AEEF;border-radius:10px;text-decoration:none" href="/admin/">Count Admin</a>
<a style="color:#fff;margin:12px;padding:14px 28px;border:1px solid #00AEEF;border-radius:10px;text-decoration:none" href="/counter/">Count Persons</a></p></div>""", mimetype="text/html")


@app.get("/admin/")
def admin_page():
    return send_from_directory(os.path.join(BASE, "admin"), "index.html")


@app.get("/counter/")
def counter_page():
    return send_from_directory(os.path.join(BASE, "counter"), "index.html")


@app.get("/<folder>/<path:fn>")
def assets(folder, fn):
    if folder not in ("admin", "counter", "shared"):
        return err("Not found", 404)
    return send_from_directory(os.path.join(BASE, folder), fn)


init_db()
