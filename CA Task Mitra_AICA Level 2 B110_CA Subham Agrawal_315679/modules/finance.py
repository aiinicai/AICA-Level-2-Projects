from core import framework as F
from core.framework import Router, BOSS, HttpError

MANIFEST = dict(key="finance", name="Finance & Billing", core=False, status="ready", requires=["work"],
    desc="Fee master, invoices, receipts and outstanding fees.",
    subs=[("fee_master", "Fee master", "ready"), ("invoices", "Invoices", "ready"), ("receipts", "Receipts", "ready"), ("auto_billing", "Auto-bill when an assignment is closed", "ready"),
          ("outstanding", "Outstanding & ageing", "ready"), ("expenses", "Firm expenses", "planned"),
          ("profitability", "Assignment profitability", "planned"), ("quotation", "Quotations", "planned")])
R = Router()
TABLES = ["receipts", "invoices", "client_fees"]
SCHEMA = """
create table if not exists client_fees(id integer primary key, client_id int not null, service_id int not null, fee real, unique(client_id,service_id));
create table if not exists invoices(id integer primary key, no text unique, client_id int not null, assignment_id int, inv_date text default (date('now','localtime')),
  descr text, amount real not null, gst_rate real default 18, gst real, total real, paid real default 0, status text default 'Unpaid', created_by int);
create table if not exists receipts(id integer primary key, invoice_id int not null, rcpt_date text default (date('now','localtime')), amount real not null, mode text, ref text, created_by int);
"""


def make_invoice(db, client_id, amount, descr, assignment_id=None, user=None, rate=None):
    amount = round(float(amount), 2)
    rate = float(rate if rate not in (None, "") else F.get_setting(db, "gst_rate", "18"))
    gst = round(amount * rate / 100, 2)
    n = (db.one("select coalesce(max(id),0) n from invoices")["n"]) + 1
    no = "INV-%04d" % n
    iid = db.x("insert into invoices(no,client_id,assignment_id,descr,amount,gst_rate,gst,total,created_by) values(?,?,?,?,?,?,?,?,?)",
               (no, client_id, assignment_id, descr, amount, rate, gst, round(amount + gst, 2), user))
    F.emit(db, "invoice.created", {"id": iid})
    return iid, no


@F.subscribe("assignment.closed", "finance")
def auto_bill(db, p):
    """Closed assignment -> invoice automatically (fee from the assignment). No fee set -> it waits in Billing queue."""
    if not F.sub_on(db, "finance", "auto_billing"):
        return
    a = db.one("select * from assignments where id=?", (p["id"],))
    if not a or db.one("select 1 from invoices where assignment_id=?", (a["id"],)):
        return
    fee = a["fee"] if a["fee"] else (fee_for(db, a["client_id"], a["service_id"]) if a["service_id"] else 0)
    if not fee or fee <= 0:
        return
    make_invoice(db, a["client_id"], fee, "Professional fees for " + a["title"], a["id"], p.get("by"))


@R.get("/billing-queue", roles=BOSS, sub="invoices")
def billing_queue(c):
    """Closed work that has no invoice yet (fee missing, or auto-billing is switched off)."""
    return c.db.q("""select a.id, a.title, a.closed_at, cl.name client, a.fee, a.fee_mode, a.service_id from assignments a join clients cl on cl.id=a.client_id
        where a.status='Closed' and not exists(select 1 from invoices i where i.assignment_id=a.id) order by a.closed_at desc limit 200""")


def fee_for(db, client_id, service_id):
    r = db.one("select fee from client_fees where client_id=? and service_id=?", (client_id, service_id))
    if r:
        return r["fee"]
    s = db.one("select default_fee from services where id=?", (service_id,))
    return s["default_fee"] if s else 0


@R.get("/fees", sub="fee_master")
def fees(c):
    return {"services": c.db.q("select id,name,category,default_fee from services order by category,name"),
            "client_fees": c.db.q("select f.*, cl.name client, s.name service from client_fees f join clients cl on cl.id=f.client_id join services s on s.id=f.service_id order by cl.name")}


@R.put("/fees/service/<id>", roles=BOSS, sub="fee_master")
def fee_service(c):
    c.db.x("update services set default_fee=? where id=?", (float(c.body.get("fee") or 0), c.params["id"]))
    return {"ok": True}


@R.post("/fees/client", roles=BOSS, sub="fee_master")
def fee_client(c):
    cid, sid, fee = c.need("client_id", "service_id", "fee")
    c.db.x("insert into client_fees(client_id,service_id,fee) values(?,?,?) on conflict(client_id,service_id) do update set fee=excluded.fee", (cid, sid, float(fee)))
    return {"ok": True}


@R.get("/fee-suggest", sub="fee_master")
def fee_suggest(c):
    return {"fee": fee_for(c.db, c.query.get("client_id"), c.query.get("service_id"))}


@R.get("/invoices", roles=BOSS, sub="invoices")
def invoices(c):
    return c.db.q("select i.*, cl.name client, round(i.total-i.paid,2) balance from invoices i join clients cl on cl.id=i.client_id order by i.id desc limit 300")


@R.get("/invoices/<id>", roles=BOSS, sub="invoices")
def invoice_get(c):
    i = c.db.one("select i.*, cl.name client, cl.gstin, cl.address from invoices i join clients cl on cl.id=i.client_id where i.id=?", (c.params["id"],))
    if not i:
        raise HttpError(404, "Not found")
    i["firm"] = F.get_setting(c.db, "firm_name")
    i["receipts"] = c.db.q("select * from receipts where invoice_id=? order by id", (i["id"],))
    return i


@R.post("/invoices", roles=BOSS, sub="invoices")
def invoice_add(c):
    cid, = c.need("client_id")
    db, b = c.db, c.body
    amount = b.get("amount")
    descr = b.get("descr")
    if b.get("assignment_id"):
        a = db.one("select * from assignments where id=?", (b["assignment_id"],))
        if a:
            cid = a["client_id"]
            descr = descr or "Professional fees for " + a["title"]
            if not amount:
                amount = a["fee"] or (fee_for(db, cid, a["service_id"]) if a["service_id"] else 0)
    if not amount or float(amount) <= 0:
        raise HttpError(400, "Enter an amount (or set a fee in the fee master)")
    descr = (descr or "Professional fees").strip()
    if not descr.lower().startswith("professional fees"):
        descr = "Professional fees – " + descr
    iid, no = make_invoice(db, cid, amount, descr, b.get("assignment_id") or None, c.user["id"], b.get("gst_rate"))
    return {"id": iid, "no": no}


@R.post("/receipts", roles=BOSS, sub="receipts")
def receipt_add(c):
    iid, amt = c.need("invoice_id", "amount")
    db = c.db
    inv = db.one("select * from invoices where id=?", (iid,))
    amt = round(float(amt), 2)
    if not inv or amt <= 0 or amt > round(inv["total"] - inv["paid"], 2) + 0.001:
        raise HttpError(400, "Amount must be between 0 and the invoice balance")
    rid = db.x("insert into receipts(invoice_id,amount,mode,ref,created_by) values(?,?,?,?,?)", (iid, amt, c.body.get("mode") or "Bank", c.body.get("ref"), c.user["id"]))
    paid = round(inv["paid"] + amt, 2)
    db.x("update invoices set paid=?, status=? where id=?", (paid, "Paid" if paid >= inv["total"] - 0.001 else "Partial", iid))
    F.emit(db, "receipt.created", {"id": rid})
    return {"id": rid}


@R.get("/outstanding", roles=BOSS, sub="outstanding")
def outstanding(c):
    rows = c.db.q("""select cl.name client, i.no, i.inv_date, round(i.total-i.paid,2) balance, cast(julianday('now')-julianday(i.inv_date) as int) age
      from invoices i join clients cl on cl.id=i.client_id where i.total-i.paid>0.001 order by age desc""")
    b = {"0-30": 0, "31-60": 0, "61-90": 0, "90+": 0}
    for r in rows:
        r["bucket"] = "0-30" if r["age"] <= 30 else "31-60" if r["age"] <= 60 else "61-90" if r["age"] <= 90 else "90+"
        b[r["bucket"]] += r["balance"]
    return {"rows": rows, "buckets": b, "total": round(sum(b.values()), 2)}


@R.get("/summary", roles=BOSS, sub="invoices")
def summary(c):
    d = c.db
    m = "date('now','localtime','start of month')"
    return {"billed_month": d.one(f"select coalesce(sum(total),0) v from invoices where inv_date>={m}")["v"],
            "collected_month": d.one(f"select coalesce(sum(amount),0) v from receipts where rcpt_date>={m}")["v"],
            "outstanding": d.one("select coalesce(sum(total-paid),0) v from invoices")["v"],
            "billed_total": d.one("select coalesce(sum(total),0) v from invoices")["v"],
            "received_total": d.one("select coalesce(sum(amount),0) v from receipts")["v"],
            "unbilled": d.one("select count(*) v from assignments a where a.status='Closed' and not exists(select 1 from invoices i where i.assignment_id=a.id)")["v"]}


def demo(db):
    clients = db.q("select id from clients limit 8")
    svc = db.one("select id from services where name='GST Return Filing'")
    for i, cl in enumerate(clients):
        amt = (1500, 2000, 3000, 5000)[i % 4]
        gst = round(amt * .18, 2)
        iid = db.x("insert into invoices(no,client_id,descr,amount,gst_rate,gst,total,inv_date) values(?,?,?,?,18,?,?,date('now','localtime','-%d day'))" % (i * 17),
                   ("INV-%04d" % (i + 1), cl["id"], "Professional fees", amt, gst, amt + gst))
        if i % 3 == 0:
            db.x("update invoices set paid=total,status='Paid' where id=?", (iid,))
            db.x("insert into receipts(invoice_id,amount,mode) select id,total,'Bank' from invoices where id=?", (iid,))
        elif i % 3 == 1:
            half = round((amt + gst) / 2, 2)
            db.x("update invoices set paid=?,status='Partial' where id=?", (half, iid))
            db.x("insert into receipts(invoice_id,amount,mode) values(?,?,'UPI')", (iid, half))
    if svc:
        db.x("insert or ignore into client_fees(client_id,service_id,fee) values(?,?,?)", (clients[0]["id"], svc["id"], 2500))
