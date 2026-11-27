import datetime as dt
from core import framework as F
from core.framework import Router, BOSS, HttpError
from modules import work

MANIFEST = dict(key="compliance", name="Compliance Management", core=False, status="ready", requires=["work"],
    desc="Statutory compliance master, applicability and automatic assignment generation.",
    subs=[("master", "Compliance master", "ready"), ("applicability", "Client applicability", "ready"),
          ("generator", "Auto-generate assignments", "ready"), ("extension", "Due-date extension", "ready"),
          ("calendar", "Compliance calendar", "ready"), ("notices", "Notice tracker", "ready"),
          ("penalty", "Penalty & late fee tracking", "planned"), ("registrations", "Registration renewals", "planned")])
R = Router()
TABLES = ["notices", "compliance_ext", "applicability", "compliance"]
SCHEMA = """
create table if not exists compliance(id integer primary key, code text unique not null, name text, category text,
  freq text not null, due_day int, due_month int, offset int default 1, service_id int, active int default 1);
create table if not exists applicability(id integer primary key, client_id int not null, compliance_id int not null, default_employee int, unique(client_id,compliance_id));
create table if not exists compliance_ext(id integer primary key, compliance_id int, period text, new_due text, reason text, unique(compliance_id,period));
create table if not exists notices(id integer primary key, client_id int, notice_type text, ref_no text, received_on text, reply_due text, status text default 'Open', note text);
"""
# freq monthly/quarterly: due = (period end month + offset months), day due_day. annual: year offset from FY end, fixed month/day.
MASTER = [("GSTR-1", "GSTR-1 monthly return", "GST", "monthly", 11, None, 1, "GST Return Filing"),
          ("GSTR-3B", "GSTR-3B monthly return", "GST", "monthly", 20, None, 1, "GST Return Filing"),
          ("TDS-PAY", "TDS payment", "TDS", "monthly", 7, None, 1, "TDS Compliance"),
          ("TDS-RET", "TDS quarterly return", "TDS", "quarterly", 31, None, 1, "TDS Compliance"),
          ("ITR", "Income tax return (non-audit)", "Income Tax", "annual", 31, 7, 0, "Income Tax Return"),
          ("TAX-AUDIT", "Tax audit report", "Audit", "annual", 30, 9, 0, "Tax Audit"),
          ("ROC-AOC4", "ROC annual filing AOC-4", "ROC", "annual", 30, 10, 0, "ROC Filing")]


def seed(db):
    for code, name, cat, fr, dd, dm, off, svc in MASTER:
        s = db.one("select id from services where name=?", (svc,))
        db.x("insert or ignore into compliance(code,name,category,freq,due_day,due_month,offset,service_id) values(?,?,?,?,?,?,?,?)",
             (code, name, cat, fr, dd, dm, off, s["id"] if s else None))


def add_months(y, m, n):
    t = y * 12 + (m - 1) + n
    return t // 12, t % 12 + 1


def due_date(comp, period):
    """period: 'YYYY-MM' (monthly), 'YYYY-Qn' (quarterly, calendar quarter), 'YYYY' (annual, FY start year)."""
    f = comp["freq"]
    try:
        if f == "monthly":
            y, m = map(int, period.split("-"))
            y, m = add_months(y, m, comp["offset"])
        elif f == "quarterly":
            y, q = period.split("-Q")
            y, m = add_months(int(y), int(q) * 3, comp["offset"])
        else:
            y, m = int(period) + 1 + comp["offset"], comp["due_month"]
        last = (dt.date(y + (m == 12), m % 12 + 1, 1) - dt.timedelta(days=1)).day
        return dt.date(y, m, min(comp["due_day"], last)).isoformat()
    except Exception:
        raise HttpError(400, "Period format: monthly 2026-10, quarterly 2026-Q2, annual 2025 (FY start year)")


def label(comp, period):
    return f"{comp['code']} – {period}"


@R.get("/master", sub="master")
def master(c):
    return c.db.q("select c.*, s.name service from compliance c left join services s on s.id=c.service_id order by c.category,c.code")


@R.post("/master", roles=BOSS, sub="master")
def master_add(c):
    code, name, freq, dd = c.need("code", "name", "freq", "due_day")
    return {"id": c.db.x("insert into compliance(code,name,category,freq,due_day,due_month,offset,service_id) values(?,?,?,?,?,?,?,?)",
            (code, name, c.body.get("category"), freq, dd, c.body.get("due_month") or None, c.body.get("offset") or (1 if freq != "annual" else 0),
             c.body.get("service_id") or None))}


@R.put("/master/<id>", roles=BOSS, sub="master")
def master_upd(c):
    b = c.body
    c.db.x("update compliance set name=?,category=?,freq=?,due_day=?,due_month=?,offset=?,service_id=?,active=? where id=?",
           (b["name"], b.get("category"), b["freq"], b["due_day"], b.get("due_month") or None, b.get("offset") or 0, b.get("service_id") or None,
            1 if b.get("active", 1) in (1, True, "1") else 0, c.params["id"]))
    return {"ok": True}


@R.get("/applicability", sub="applicability")
def appl(c):
    return c.db.q("""select a.*, cl.name client, co.code, co.freq, u.name employee from applicability a join clients cl on cl.id=a.client_id
      join compliance co on co.id=a.compliance_id left join users u on u.id=a.default_employee order by cl.name, co.code""")


@R.post("/applicability", roles=BOSS, sub="applicability")
def appl_add(c):
    cids = c.body.get("client_ids") or ([c.body["client_id"]] if c.body.get("client_id") else [])
    comp, = c.need("compliance_id")
    if not cids:
        raise HttpError(400, "Choose at least one client")
    for cid in cids:
        c.db.x("insert or ignore into applicability(client_id,compliance_id,default_employee) values(?,?,?)", (cid, comp, c.body.get("default_employee") or None))
    return {"added": len(cids)}


@R.delete("/applicability/<id>", roles=BOSS, sub="applicability")
def appl_del(c):
    c.db.x("delete from applicability where id=?", (c.params["id"],))
    return {"ok": True}


def generate(db, freq, period, user_id=None, only_comp=None):
    created = skipped = 0
    rows = db.q("""select a.client_id, a.default_employee, co.* , co.id cid from applicability a join compliance co on co.id=a.compliance_id
        join clients cl on cl.id=a.client_id where co.freq=? and co.active=1 and cl.active=1""", (freq,))
    for r in rows:
        if only_comp and r["cid"] != only_comp:
            continue
        ext = db.one("select new_due from compliance_ext where compliance_id=? and period=?", (r["cid"], period))
        aid = work.create_assignment(db, client_id=r["client_id"], service_id=r["service_id"], compliance_id=r["cid"],
                                     title=label(r, period), period=period, due_date=ext["new_due"] if ext else due_date(r, period),
                                     assigned_to=r["default_employee"], created_by=user_id, source="compliance",
                                     ckey=f"{r['client_id']}|{r['cid']}|{period}")
        if aid:
            created += 1
            if r["default_employee"]:
                db.x("update assignments set status='In Progress' where id=?", (aid,))
        else:
            skipped += 1
    return created, skipped


@R.post("/generate", roles=BOSS, sub="generator")
def gen(c):
    freq, period = c.need("freq", "period")
    n, s = generate(c.db, freq, period, c.user["id"])
    return {"created": n, "skipped_duplicates": s}


@R.get("/extensions", sub="extension")
def ext_list(c):
    return c.db.q("select e.*, co.code from compliance_ext e join compliance co on co.id=e.compliance_id order by e.id desc")


@R.post("/extensions", roles=BOSS, sub="extension")
def ext_add(c):
    comp, period, new_due = c.need("compliance_id", "period", "new_due")
    c.db.x("insert into compliance_ext(compliance_id,period,new_due,reason) values(?,?,?,?) on conflict(compliance_id,period) do update set new_due=excluded.new_due, reason=excluded.reason",
           (comp, period, new_due, c.body.get("reason")))
    cur = c.db.c.execute("update assignments set due_date=?, updated=datetime('now') where compliance_id=? and period=? and status not in ('Approved','Closed')", (new_due, comp, period))
    return {"assignments_updated": cur.rowcount}


@R.get("/calendar", sub="calendar")
def calendar(c):
    mine, args = ("" if c.is_boss else " and a.assigned_to=?"), []
    if c.query.get("days"):  # short preview for the dashboard: next N days (and anything overdue in the last 7 days)
        where, args = " and a.due_date between date('now','localtime','-7 day') and date('now','localtime',?) and a.status not in ('Approved','Closed')", ["+%d day" % int(c.query["days"])]
    else:
        where, args = " and substr(a.due_date,1,7)=?", [c.query.get("month") or F.today()[:7]]
    if mine:
        args.append(c.user["id"])
    return c.db.q("select a.id, a.due_date, a.title, a.status, cl.name client, u.name employee from assignments a join clients cl on cl.id=a.client_id "
                  "left join users u on u.id=a.assigned_to where a.source='compliance'" + where + mine + " order by a.due_date, cl.name", args)


@R.post("/applicability/import", roles=BOSS, sub="applicability")
def appl_import(c):
    """CSV columns: client, compliance (code e.g. GSTR-3B), employee (optional: username or name)."""
    import csv, io
    text, = c.need("csv")
    ok, bad = 0, []
    for n, r in enumerate(csv.DictReader(io.StringIO(text.lstrip("\ufeff"))), 2):
        r = {(k or "").strip().lower(): (v or "").strip() for k, v in r.items()}
        cl = c.db.one("select id from clients where lower(name)=lower(?)", (r.get("client", ""),))
        co = c.db.one("select id from compliance where upper(code)=upper(?)", (r.get("compliance") or r.get("compliance code") or "",))
        if not cl or not co:
            bad.append(f"row {n}: " + ("client not found" if not cl else "compliance code not found"))
            continue
        emp = r.get("employee")
        u = c.db.one("select id from users where lower(username)=lower(?) or lower(name)=lower(?)", (emp, emp)) if emp else None
        c.db.x("insert into applicability(client_id,compliance_id,default_employee) values(?,?,?) on conflict(client_id,compliance_id) do update set default_employee=excluded.default_employee",
               (cl["id"], co["id"], u["id"] if u else None))
        ok += 1
    return {"imported": ok, "errors": bad[:20]}


@R.get("/notices", sub="notices")
def notices(c):
    return c.db.q("select n.*, cl.name client from notices n left join clients cl on cl.id=n.client_id order by (n.status='Closed'), n.reply_due")


@R.post("/notices", roles=BOSS, sub="notices")
def notice_add(c):
    t, = c.need("notice_type")
    b = c.body
    return {"id": c.db.x("insert into notices(client_id,notice_type,ref_no,received_on,reply_due,note) values(?,?,?,?,?,?)",
                         (b.get("client_id") or None, t, b.get("ref_no"), b.get("received_on"), b.get("reply_due"), b.get("note")))}


@R.put("/notices/<id>", roles=BOSS, sub="notices")
def notice_upd(c):
    b = c.body
    c.db.x("update notices set notice_type=?,ref_no=?,received_on=?,reply_due=?,status=?,note=? where id=?",
           (b["notice_type"], b.get("ref_no"), b.get("received_on"), b.get("reply_due"), b.get("status") or "Open", b.get("note"), c.params["id"]))
    return {"ok": True}


def demo(db):
    clients = db.q("select id from clients")
    emps = [u["id"] for u in db.q("select id from users where demo=1 and role='employee'")]
    comps = {r["code"]: r["id"] for r in db.q("select id,code from compliance")}
    for i, cl in enumerate(clients):
        for code in ("GSTR-1", "GSTR-3B") if i % 3 else ("GSTR-3B",):
            db.x("insert or ignore into applicability(client_id,compliance_id,default_employee) values(?,?,?)", (cl["id"], comps[code], emps[i % len(emps)] if emps else None))
        if i % 2 == 0:
            db.x("insert or ignore into applicability(client_id,compliance_id,default_employee) values(?,?,?)", (cl["id"], comps["TDS-PAY"], emps[(i + 1) % len(emps)] if emps else None))
        if i % 4 == 0:
            db.x("insert or ignore into applicability(client_id,compliance_id,default_employee) values(?,?,?)", (cl["id"], comps["ITR"], emps[(i + 2) % len(emps)] if emps else None))
    t = dt.date.today()
    py, pm = add_months(t.year, t.month, -1)
    generate(db, "monthly", f"{py}-{pm:02d}")
    generate(db, "monthly", f"{t.year}-{t.month:02d}")
    fy = t.year - 1 if t.month < 4 else t.year
    generate(db, "annual", str(fy - 1))
    cl = clients[0]["id"]
    db.x("insert into notices(client_id,notice_type,ref_no,received_on,reply_due,note) values(?,?,?,?,date('now','localtime','+9 day'),?)",
         (cl, "GST – ASMT-10 scrutiny", "DEMO/2026/001", F.today(), "Reply with reconciliation of GSTR-2B vs books"))
