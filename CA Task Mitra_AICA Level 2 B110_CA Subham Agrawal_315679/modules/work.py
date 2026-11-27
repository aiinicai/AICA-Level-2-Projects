from core import framework as F
from core.framework import Router, HttpError, BOSS

MANIFEST = dict(key="work", name="Work Management", core=True, status="ready",
    desc="Clients, services, assignments, checklists, review and dashboard.",
    subs=[("client_master", "Client master", "ready"), ("service_master", "Service master", "ready"),
          ("assignments", "Assignments", "ready"), ("checklists", "Checklists", "ready"),
          ("comments", "Task comments", "ready"), ("doc_tracking", "Required documents", "ready"),
          ("review_approval", "Review & approval", "ready"), ("dashboard", "Dashboard", "ready"),
          ("workflow_builder", "Custom workflow builder", "planned"), ("bulk_assign", "Bulk assignments", "planned")])
R = Router()
MIGRATE = ["alter table assignments add column remarks text", "alter table assignments add column fee real", "alter table assignments add column fee_mode text"]
TABLES = ["comments", "req_docs", "checklist", "assignments", "services", "clients"]
SCHEMA = """
create table if not exists clients(id integer primary key, name text not null, pan text, gstin text, email text, phone text,
  ctype text default 'Company', address text, active int default 1, created text default (date('now','localtime')));
create table if not exists services(id integer primary key, name text unique not null, category text, default_fee real default 0);
create table if not exists assignments(id integer primary key, client_id int not null references clients(id), service_id int,
  compliance_id int, title text not null, period text, due_date text, priority text default 'Normal', status text default 'New',
  assigned_to int, created_by int, source text default 'manual', ckey text unique, review_note text, remarks text, fee real, fee_mode text,
  created text default (datetime('now')), updated text default (datetime('now')), closed_at text);
create table if not exists checklist(id integer primary key, assignment_id int not null, item text not null, done int default 0);
create table if not exists comments(id integer primary key, assignment_id int not null, user_id int, body text, created text default (datetime('now')));
create table if not exists req_docs(id integer primary key, assignment_id int not null, name text not null, received int default 0);
"""
STATUSES = ["New", "In Progress", "Awaiting Documents", "In Review", "Approved", "Closed"]
OPEN = "('Approved','Closed')"
BASE = """select a.*, c.name client, s.name service, u.name employee,
  (a.due_date < date('now','localtime') and a.status not in ('Approved','Closed')) overdue
  from assignments a join clients c on c.id=a.client_id left join services s on s.id=a.service_id
  left join users u on u.id=a.assigned_to"""


def seed(db):
    for n, cat, fee in [("GST Return Filing", "GST", 1500), ("TDS Compliance", "TDS", 2000), ("Income Tax Return", "Income Tax", 3000),
                        ("Tax Audit", "Audit", 25000), ("School Audit", "Audit", 15000), ("Accounting", "Accounting", 5000),
                        ("ROC Filing", "ROC", 6000), ("Bank Reconciliation", "Accounting", 1000)]:
        db.x("insert or ignore into services(name,category,default_fee) values(?,?,?)", (n, cat, fee))


def create_assignment(db, **k):
    """Shared helper (also used by Compliance and AI modules). Returns id or None if duplicate."""
    cur = db.c.execute(
        "insert or ignore into assignments(client_id,service_id,compliance_id,title,period,due_date,priority,assigned_to,created_by,source,ckey,status,remarks,fee,fee_mode)"
        " values(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (k["client_id"], k.get("service_id"), k.get("compliance_id"), k["title"], k.get("period"), k.get("due_date"),
         k.get("priority", "Normal"), k.get("assigned_to"), k.get("created_by"), k.get("source", "manual"), k.get("ckey"),
         k.get("status") or "New", k.get("remarks"), k.get("fee"), k.get("fee_mode")))
    return cur.lastrowid if cur.rowcount else None


def resolve_fee(db, client_id, service_id, mode, fee):
    """Fee on an assignment: 'default' = client-specific fee or service fee from the fee master; 'custom' = typed amount."""
    if mode == "custom" and fee not in (None, ""):
        return round(float(fee), 2), "custom"
    if service_id:
        r = db.one("select fee from client_fees where client_id=? and service_id=?", (client_id, service_id))
        if r:
            return r["fee"], "default"
        s = db.one("select default_fee from services where id=?", (service_id,))
        if s:
            return s["default_fee"], "default"
    return None, None


def scope(ctx):
    return ("", ()) if ctx.is_boss else (" and a.assigned_to=?", (ctx.user["id"],))


def mine_or_404(ctx, aid):
    a = ctx.db.one(BASE + " where a.id=?", (aid,))
    if not a or (not ctx.is_boss and a["assigned_to"] != ctx.user["id"]):
        raise HttpError(404, "Assignment not found")
    return a


# ---- clients / services ----
@R.get("/clients", sub="client_master")
def clients(c):
    return c.db.q("select * from clients order by name")


@R.post("/clients", roles=BOSS, sub="client_master")
def client_add(c):
    c.need("name")
    b = c.body
    return {"id": c.db.x("insert into clients(name,pan,gstin,email,phone,ctype,address) values(?,?,?,?,?,?,?)",
            (b["name"], b.get("pan"), b.get("gstin"), b.get("email"), b.get("phone"), b.get("ctype") or "Company", b.get("address")))}


@R.put("/clients/<id>", roles=BOSS, sub="client_master")
def client_upd(c):
    b = c.body
    c.db.x("update clients set name=?,pan=?,gstin=?,email=?,phone=?,ctype=?,address=?,active=? where id=?",
           (b["name"], b.get("pan"), b.get("gstin"), b.get("email"), b.get("phone"), b.get("ctype"), b.get("address"),
            1 if b.get("active", 1) in (1, True, "1") else 0, c.params["id"]))
    return {"ok": True}


@R.get("/services", sub="service_master")
def services(c):
    return c.db.q("select * from services order by category,name")


@R.post("/services", roles=BOSS, sub="service_master")
def service_add(c):
    c.need("name")
    return {"id": c.db.x("insert into services(name,category,default_fee) values(?,?,?)",
                         (c.body["name"], c.body.get("category"), float(c.body.get("default_fee") or 0)))}


@R.put("/services/<id>", roles=BOSS, sub="service_master")
def service_upd(c):
    b = c.body
    c.db.x("update services set name=?,category=?,default_fee=? where id=?", (b["name"], b.get("category"), float(b.get("default_fee") or 0), c.params["id"]))
    return {"ok": True}


# ---- assignments ----
@R.get("/assignments", sub="assignments")
def assignments(c):
    w, a = scope(c)
    sql, args = BASE + " where 1=1" + w, list(a)
    for k, col in (("status", "a.status"), ("client_id", "a.client_id"), ("assigned_to", "a.assigned_to")):
        if c.query.get(k):
            sql += f" and {col}=?"
            args.append(c.query[k])
    if c.query.get("overdue"):
        sql += " and a.due_date < date('now','localtime') and a.status not in " + OPEN
    if c.query.get("pending"):
        sql += " and a.status not in " + OPEN
    g = {"service": "coalesce(s.category,'No service')", "employee": "coalesce(u.name,'Unassigned')", "client": "c.name",
         "month": "coalesce(substr(a.due_date,1,7),'No due date')", "source": "case a.source when 'compliance' then 'Compliance' else 'Manual' end"}
    if c.query.get("by") in g and c.query.get("grp") is not None:
        sql += f" and {g[c.query['by']]}=?"
        args.append(c.query["grp"])
    return c.db.q(sql + " order by (a.status in " + OPEN + "), a.due_date limit 500", args)


@R.post("/assignments", roles=BOSS, sub="assignments")
def assignment_add(c):
    cid, title = c.need("client_id", "title")
    b = c.body
    fee, mode = resolve_fee(c.db, cid, b.get("service_id") or None, b.get("fee_mode"), b.get("fee"))
    aid = create_assignment(c.db, client_id=cid, service_id=b.get("service_id") or None, title=title, due_date=b.get("due_date"),
                            priority=b.get("priority") or "Normal", assigned_to=b.get("assigned_to") or None, created_by=c.user["id"],
                            period=b.get("period"), remarks=b.get("remarks"), fee=fee, fee_mode=mode)
    return {"id": aid}


@R.get("/assignments/<id>", sub="assignments")
def assignment_get(c):
    a = mine_or_404(c, c.params["id"])
    i = a["id"]
    a["checklist"] = c.db.q("select * from checklist where assignment_id=?", (i,)) if F.sub_on(c.db, "work", "checklists") else []
    a["docs"] = c.db.q("select * from req_docs where assignment_id=?", (i,)) if F.sub_on(c.db, "work", "doc_tracking") else []
    a["comments"] = c.db.q("select m.*, u.name uname from comments m left join users u on u.id=m.user_id where assignment_id=? order by m.id", (i,)) \
        if F.sub_on(c.db, "work", "comments") else []
    return a


@R.put("/assignments/<id>", roles=BOSS, sub="assignments")
def assignment_upd(c):
    b = c.body
    a = c.db.one("select client_id,service_id from assignments where id=?", (c.params["id"],))
    fee, mode = resolve_fee(c.db, a["client_id"], a["service_id"], b.get("fee_mode"), b.get("fee"))
    c.db.x("update assignments set title=?,due_date=?,priority=?,remarks=?,fee=?,fee_mode=?,updated=datetime('now') where id=?",
           (b["title"], b.get("due_date"), b.get("priority") or "Normal", b.get("remarks"), fee, mode, c.params["id"]))
    return {"ok": True}


@R.post("/assignments/<id>/assign", roles=BOSS, sub="assignments")
def assign(c):
    uid, = c.need("user_id")
    c.db.x("update assignments set assigned_to=?, updated=datetime('now'), status=case when status='New' then 'In Progress' else status end where id=?",
           (uid, c.params["id"]))
    return {"ok": True}


def change_status(c, a, new, note=None):
    if new not in STATUSES:
        raise HttpError(400, "Unknown status")
    if not c.is_boss and new not in ("In Progress", "Awaiting Documents", "In Review"):
        raise HttpError(403, "Only the CA or manager can approve or close work")
    if new in ("Approved", "Closed") and not F.sub_on(c.db, "work", "review_approval"):
        raise HttpError(403, "Review & approval is switched off")
    c.db.x("update assignments set status=?, review_note=coalesce(?,review_note), updated=datetime('now'), closed_at=case when ? in ('Approved','Closed') then datetime('now') end where id=?",
           (new, note, new, a["id"]))
    if note:
        c.db.x("insert into comments(assignment_id,user_id,body) values(?,?,?)", (a["id"], c.user["id"], f"[{new}] {note}"))
    if new == "Approved":
        F.emit(c.db, "assignment.approved", {"id": a["id"]})
    if new == "Closed":
        F.emit(c.db, "assignment.closed", {"id": a["id"], "by": c.user["id"]})


@R.post("/assignments/<id>/status", sub="assignments")
def set_status(c):
    a = mine_or_404(c, c.params["id"])
    change_status(c, a, c.body.get("status"), c.body.get("note"))
    return {"ok": True}


@R.post("/assignments/bulk-status", sub="assignments")
def bulk_status(c):
    """Move many assignments at once (submit for review / approve / close). Each one is checked individually."""
    ids, new = c.body.get("ids") or [], c.body.get("status")
    done, skipped = 0, []
    for i in ids:
        try:
            a = mine_or_404(c, i)
            ok_from = {"In Review": ("New", "In Progress", "Awaiting Documents"), "Approved": ("In Review",), "Closed": ("Approved", "In Review"),
                       "In Progress": ("New", "Awaiting Documents", "In Review")}.get(new, ())
            if a["status"] not in ok_from:
                skipped.append(f"{a['title']} ({a['status']})")
                continue
            if new == "Closed" and a["status"] == "In Review":  # approve and close in one go
                change_status(c, a, "Approved", c.body.get("note"))
            change_status(c, a, new, c.body.get("note"))
            done += 1
        except HttpError as e:
            if e.code == 403:
                raise
            skipped.append(str(i))
    return {"done": done, "skipped": skipped}


@R.get("/assignments-groups", sub="assignments")
def groups(c):
    """Counts grouped by status / service category / employee / client / compliance, so the list is opened only after drilling in."""
    w, a = scope(c)
    by = c.query.get("by") or "status"
    col = {"status": "a.status", "service": "coalesce(s.category,'No service')", "employee": "coalesce(u.name,'Unassigned')",
           "client": "c.name", "month": "coalesce(substr(a.due_date,1,7),'No due date')", "source": "case a.source when 'compliance' then 'Compliance' else 'Manual' end"}.get(by, "a.status")
    rows = c.db.q(f"""select {col} grp, count(*) total,
      sum(a.status not in {OPEN}) pending, sum(a.status in {OPEN}) done,
      sum(a.status='In Review') in_review, sum(a.status='Awaiting Documents') awaiting,
      sum(a.due_date < date('now','localtime') and a.status not in {OPEN}) overdue
      from assignments a join clients c on c.id=a.client_id left join services s on s.id=a.service_id left join users u on u.id=a.assigned_to
      where 1=1{w} group by 1 order by 2 desc""", a)
    return {"by": by, "groups": rows}


@R.post("/assignments/<id>/checklist", sub="checklists")
def check_add(c):
    mine_or_404(c, c.params["id"])
    items = c.body.get("items") or [c.body.get("item")]
    for it in [i for i in items if i]:
        c.db.x("insert into checklist(assignment_id,item) values(?,?)", (c.params["id"], it))
    return {"ok": True}


@R.post("/checklist/<id>/toggle", sub="checklists")
def check_toggle(c):
    c.db.x("update checklist set done=1-done where id=?", (c.params["id"],))
    return {"ok": True}


@R.post("/assignments/<id>/docs", sub="doc_tracking")
def doc_add(c):
    mine_or_404(c, c.params["id"])
    items = c.body.get("items") or [c.body.get("name")]
    for it in [i for i in items if i]:
        c.db.x("insert into req_docs(assignment_id,name) values(?,?)", (c.params["id"], it))
    return {"ok": True}


@R.post("/docs/<id>/toggle", sub="doc_tracking")
def doc_toggle(c):
    c.db.x("update req_docs set received=1-received where id=?", (c.params["id"],))
    return {"ok": True}


@R.post("/assignments/<id>/comments", sub="comments")
def comment_add(c):
    mine_or_404(c, c.params["id"])
    body, = c.need("body")
    c.db.x("insert into comments(assignment_id,user_id,body) values(?,?,?)", (c.params["id"], c.user["id"], body))
    return {"ok": True}


@R.get("/dashboard", sub="dashboard")
def dashboard(c):
    w, a = scope(c)
    d = c.db
    by = {r["status"]: r["n"] for r in d.q("select status, count(*) n from assignments a where 1=1" + w + " group by status", a)}
    one = lambda extra: d.one("select count(*) n from assignments a where 1=1" + w + extra, a)["n"]
    out = {"by_status": by, "total": sum(by.values()),
           "overdue": one(" and due_date < date('now','localtime') and status not in " + OPEN),
           "due_week": one(" and due_date between date('now','localtime') and date('now','localtime','+7 day') and status not in " + OPEN),
           "in_review": by.get("In Review", 0), "awaiting_docs": by.get("Awaiting Documents", 0),
           "clients": d.one("select count(*) n from clients where active=1")["n"],
           "upcoming": d.q(BASE + " where a.status not in " + OPEN + w + " order by a.due_date limit 8", a)}
    out["pending"] = out["total"] - by.get("Approved", 0) - by.get("Closed", 0)
    out["closed"] = by.get("Approved", 0) + by.get("Closed", 0)
    out["new_orders"] = d.q(BASE + " where a.status='New' and a.created>=datetime('now','-7 day')" + w + " order by a.id desc limit 6", a)
    if c.is_boss:
        out["employees"] = d.one("select count(*) n from users where active=1 and role!='ca'")["n"]
        out["by_employee"] = d.q(f"""select coalesce(u.name,'Unassigned') name, count(*) total, sum(a.status not in {OPEN}) pending,
          sum(a.status in {OPEN}) closed, sum(a.status='In Review') in_review,
          sum(a.due_date < date('now','localtime') and a.status not in {OPEN}) overdue
          from assignments a left join users u on u.id=a.assigned_to group by 1 order by pending desc""")
    return out


def demo(db):
    import random
    random.seed(7)
    names = [("ABC Traders", "Company"), ("Sharma & Sons", "Partnership"), ("Mehta Textiles Pvt Ltd", "Company"),
             ("Kumar Hardware", "Proprietorship"), ("Green Valley School", "Trust"), ("Sunrise Public School", "Trust"),
             ("Patel Pharma", "Company"), ("Singh Logistics", "Partnership"), ("Das Electronics", "Proprietorship"),
             ("Rao Constructions", "Company"), ("Khan Garments", "Proprietorship"), ("Joshi Foods Pvt Ltd", "Company")]
    for i, (n, t) in enumerate(names, 1):
        pan = "ABCDE%04dF" % (1000 + i * 37)
        db.x("insert into clients(name,pan,gstin,email,phone,ctype) values(?,?,?,?,?,?)",
             (n, pan, "21%s1Z%d" % (pan, i % 9), "demo.client%d@example.com" % i, "90000%05d" % i, t))
