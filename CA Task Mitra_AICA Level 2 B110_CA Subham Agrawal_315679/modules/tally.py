import re
import urllib.request
from xml.sax.saxutils import escape as esc
from core import framework as F
from core.framework import Router, BOSS, HttpError

MANIFEST = dict(key="tally", name="Tally Integration", core=False, status="ready", requires=["finance"],
    desc="Posts invoices and receipts to a TallyPrime company (demo company only).",
    subs=[("connection", "Connection test", "ready"), ("post_invoices", "Post invoices (Sales vouchers)", "ready"),
          ("post_receipts", "Post receipts (Receipt vouchers)", "ready"), ("import_clients", "Import clients / outstanding", "planned")])
R = Router()
TABLES = ["tally_queue"]
SCHEMA = """
create table if not exists tally_queue(id integer primary key, kind text, ref_id int, status text default 'Pending', message text,
  created text default (datetime('now')), posted_at text, unique(kind,ref_id));
"""


def cfg(db):
    return (F.get_setting(db, "tally_url") or "http://localhost:9000", F.get_setting(db, "tally_company"),
            F.get_setting(db, "tally_fee_ledger") or "Professional Fees", F.get_setting(db, "tally_gst_ledger") or "Output GST",
            F.get_setting(db, "tally_bank_ledger") or "Bank Account")


def flush(db):
    """Try every pending entry (oldest first). If Tally is off they simply stay pending and go with the next bill."""
    if F.get_setting(db, "tally_auto_post", "1") != "1" or not F.get_setting(db, "tally_company"):
        return
    for q in db.q("select * from tally_queue where status in ('Pending','Failed') order by id"):
        if not post_one(db, q):
            break  # Tally is not reachable - stop, keep the rest pending


@F.subscribe("invoice.created", "tally")
def on_invoice(db, p):
    if F.sub_on(db, "tally", "post_invoices"):
        db.x("insert or ignore into tally_queue(kind,ref_id) values('invoice',?)", (p["id"],))
        flush(db)


@F.subscribe("receipt.created", "tally")
def on_receipt(db, p):
    if F.sub_on(db, "tally", "post_receipts"):
        db.x("insert or ignore into tally_queue(kind,ref_id) values('receipt',?)", (p["id"],))
        flush(db)


def envelope(company, body, report="Vouchers"):
    cur = f"<SVCURRENTCOMPANY>{esc(company)}</SVCURRENTCOMPANY>" if company else ""
    return (f"<ENVELOPE><HEADER><TALLYREQUEST>Import Data</TALLYREQUEST></HEADER><BODY><IMPORTDATA><REQUESTDESC>"
            f"<REPORTNAME>{report}</REPORTNAME><STATICVARIABLES>{cur}</STATICVARIABLES></REQUESTDESC><REQUESTDATA>{body}</REQUESTDATA></IMPORTDATA></BODY></ENVELOPE>")


def ledger_xml(name, parent):
    return (f'<TALLYMESSAGE xmlns:UDF="TallyUDF"><LEDGER NAME="{esc(name)}" ACTION="Create"><NAME>{esc(name)}</NAME>'
            f"<PARENT>{esc(parent)}</PARENT></LEDGER></TALLYMESSAGE>")


def voucher_xml(vtype, date, number, narration, entries):
    """entries: list of (ledger, signed_amount) – Tally convention: debit is negative, credit positive."""
    led = "".join(f"<ALLLEDGERENTRIES.LIST><LEDGERNAME>{esc(n)}</LEDGERNAME><ISDEEMEDPOSITIVE>{'Yes' if a < 0 else 'No'}</ISDEEMEDPOSITIVE>"
                  f"<AMOUNT>{a:.2f}</AMOUNT></ALLLEDGERENTRIES.LIST>" for n, a in entries)
    return (f'<TALLYMESSAGE xmlns:UDF="TallyUDF"><VOUCHER VCHTYPE="{vtype}" ACTION="Create"><DATE>{date.replace("-", "")}</DATE>'
            f"<VOUCHERTYPENAME>{vtype}</VOUCHERTYPENAME><VOUCHERNUMBER>{esc(number)}</VOUCHERNUMBER><NARRATION>{esc(narration)}</NARRATION>"
            f"{led}</VOUCHER></TALLYMESSAGE>")


def send(url, xml, timeout=6):
    req = urllib.request.Request(url, data=xml.encode("utf-8"), headers={"Content-Type": "text/xml"})
    return urllib.request.urlopen(req, timeout=timeout).read().decode("utf-8", "ignore")


def result_ok(resp):
    err = re.search(r"<LINEERROR>(.*?)</LINEERROR>", resp, re.S)
    created = re.search(r"<CREATED>(\d+)</CREATED>", resp)
    if err:
        return False, err.group(1).strip()
    return (bool(created and int(created.group(1)) > 0), resp[:200])


def post_one(db, q):
    url, company, fee_l, gst_l, bank_l = cfg(db)
    if q["kind"] == "invoice":
        i = db.one("select i.*, c.name client from invoices i join clients c on c.id=i.client_id where i.id=?", (q["ref_id"],))
        parts = [ledger_xml(i["client"], "Sundry Debtors"), ledger_xml(fee_l, "Indirect Incomes"), ledger_xml(gst_l, "Duties & Taxes")]
        v = voucher_xml("Sales", i["inv_date"], i["no"], i["descr"] or "Professional fees",
                        [(i["client"], -i["total"]), (fee_l, i["amount"]), (gst_l, i["gst"])])
    else:
        r = db.one("select r.*, i.no, c.name client from receipts r join invoices i on i.id=r.invoice_id join clients c on c.id=i.client_id where r.id=?", (q["ref_id"],))
        parts = [ledger_xml(r["client"], "Sundry Debtors"), ledger_xml(bank_l, "Bank Accounts")]
        v = voucher_xml("Receipt", r["rcpt_date"], f"RCPT-{r['id']}", f"Against {r['no']} ({r['mode'] or ''})", [(bank_l, -r["amount"]), (r["client"], r["amount"])])
    try:
        send(url, envelope(company, "".join(parts), "All Masters"))  # create missing ledgers; "already exists" errors are harmless
        ok, msg = result_ok(send(url, envelope(company, v)))
    except Exception as e:
        ok, msg = False, "Cannot reach Tally: %s" % e
    db.x("update tally_queue set status=?, message=?, posted_at=case when ? then datetime('now') end where id=?", ("Posted" if ok else "Failed", msg, ok, q["id"]))
    return ok


@R.get("/queue", roles=BOSS, sub="connection")
def queue(c):
    return c.db.q("""select q.*, coalesce(i.no, 'Receipt #'||q.ref_id) ref, coalesce(i.total, r.amount) amount from tally_queue q
      left join invoices i on q.kind='invoice' and i.id=q.ref_id left join receipts r on q.kind='receipt' and r.id=q.ref_id order by q.id desc limit 200""")


@R.post("/post-pending", roles=BOSS, sub="connection")
def post_pending(c):
    ok = bad = 0
    for q in c.db.q("select * from tally_queue where status in ('Pending','Failed') order by id"):
        if post_one(c.db, q):
            ok += 1
        else:
            bad += 1
    return {"posted": ok, "failed": bad}


@R.post("/test", roles=BOSS, sub="connection")
def test(c):
    url, company, *_ = cfg(c.db)
    try:
        r = urllib.request.urlopen(url, timeout=6).read().decode("utf-8", "ignore")
        return {"ok": "TallyPrime Server is Running" in r or "Tally" in r, "message": r[:120], "company": company}
    except Exception as e:
        return {"ok": False, "message": "Cannot reach Tally at %s – open TallyPrime, load the company and enable port 9000. (%s)" % (url, e)}
