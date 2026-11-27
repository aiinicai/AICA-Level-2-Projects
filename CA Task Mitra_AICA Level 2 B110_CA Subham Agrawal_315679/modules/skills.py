from urllib.parse import quote
from core import framework as F
from core.framework import Router, BOSS, CA, HttpError

MANIFEST = dict(key="skills", name="AI Skills Library", core=False, status="ready", requires=["work"],
    desc="The firm's reusable AI skills, linked to services and launched in one click.",
    subs=[("library", "Skill library", "ready"), ("service_link", "Link skills to services", "ready"),
          ("launcher", "One-click launcher (Claude / ChatGPT)", "ready"),
          ("import_export", "Import / export skill files", "planned"), ("versions", "Skill versions", "planned")])
R = Router()
MIGRATE = ["alter table skills add column status text default 'approved'"]
TABLES = ["skill_links", "skills"]
SCHEMA = """
create table if not exists skills(id integer primary key, name text not null, description text, instructions text not null, docs_needed text,
  provider text default 'claude', status text default 'approved', active int default 1, runs int default 0, created_by int, created text default (datetime('now')));
create table if not exists skill_links(skill_id int not null, service_id int not null, primary key(skill_id,service_id));
"""
LAUNCH = {"claude": "https://claude.ai/new?q=%s", "chatgpt": "https://chatgpt.com/?q=%s", "gemini": ""}


@R.get("/skills", sub="library")
def skills(c):
    rows = c.db.q("select s.*, u.name author from skills s left join users u on u.id=s.created_by "
                  + ("" if c.user["role"] == "ca" else "where s.status='approved' or s.created_by=%d " % c.user["id"]) + "order by (s.status='pending') desc, s.name")
    for r in rows:
        r["service_ids"] = [x["service_id"] for x in c.db.q("select service_id from skill_links where skill_id=?", (r["id"],))]
    return rows


@R.post("/skills", sub="library")
def skill_add(c):
    """CA adds directly; an employee's skill waits for CA approval before anyone can run it."""
    n, ins = c.need("name", "instructions")
    b = c.body
    st = "approved" if c.user["role"] == "ca" else "pending"
    sid = c.db.x("insert into skills(name,description,instructions,docs_needed,provider,created_by,status) values(?,?,?,?,?,?,?)",
                 (n, b.get("description"), ins, b.get("docs_needed"), b.get("provider") or "claude", c.user["id"], st))
    return {"id": sid, "status": st}


@R.put("/skills/<id>", roles=CA, sub="library")
def skill_upd(c):
    b = c.body
    c.db.x("update skills set name=?,description=?,instructions=?,docs_needed=?,provider=?,active=? where id=?",
           (b["name"], b.get("description"), b["instructions"], b.get("docs_needed"), b.get("provider") or "claude",
            1 if b.get("active", 1) in (1, True, "1") else 0, c.params["id"]))
    return {"ok": True}


@R.post("/skills/<id>/approve", roles=CA, sub="library")
def skill_approve(c):
    c.db.x("update skills set status='approved' where id=?", (c.params["id"],))
    return {"ok": True}


@R.post("/skills/<id>/reject", roles=CA, sub="library")
def skill_reject(c):
    c.db.x("delete from skill_links where skill_id=?", (c.params["id"],))
    c.db.x("delete from skills where id=? and status='pending'", (c.params["id"],))
    return {"ok": True}


@R.post("/skills/<id>/link", roles=CA, sub="service_link")
def link(c):
    c.db.x("delete from skill_links where skill_id=?", (c.params["id"],))
    for s in c.body.get("service_ids", []):
        c.db.x("insert or ignore into skill_links(skill_id,service_id) values(?,?)", (c.params["id"], s))
    return {"ok": True}


@R.get("/for-assignment/<aid>", sub="launcher")
def for_assignment(c):
    a = c.db.one("select service_id from assignments where id=?", (c.params["aid"],))
    if not a or not a["service_id"]:
        return []
    return c.db.q("select s.id,s.name,s.description,s.provider,s.docs_needed from skills s join skill_links l on l.skill_id=s.id "
                  "where l.service_id=? and s.active=1 and s.status='approved' order by s.name", (a["service_id"],))


@R.post("/skills/<id>/run", sub="launcher")
def run(c):
    s = c.db.one("select * from skills where id=? and active=1 and status='approved'", (c.params["id"],))
    if not s:
        raise HttpError(404, "Skill not found")
    ctx = ""
    if c.body.get("assignment_id"):
        a = c.db.one("select a.title,a.period,c.name client from assignments a join clients c on c.id=a.client_id where a.id=?", (c.body["assignment_id"],))
        if a:
            ctx = f"\n\nTask context: {a['title']} for {a['client']}" + (f", period {a['period']}" if a["period"] else "") + "."
    prompt = (f"Use this firm skill: {s['name']}\n\n{s['instructions']}{ctx}\n\n"
              f"Documents I will attach: {s['docs_needed'] or 'as required'}.\nPlease ask me for anything missing before you start.")
    c.db.x("update skills set runs=runs+1 where id=?", (s["id"],))
    tpl = LAUNCH.get(s["provider"], "")
    return {"prompt": prompt, "provider": s["provider"], "url": (tpl % quote(prompt)) if tpl else None,
            "note": "Attach the files in the chat. Use only your firm's approved AI account."}


def demo(db):
    sv = {r["name"]: r["id"] for r in db.q("select id,name from services")}
    data = [("GST 2B vs books reconciliation", "Compare GSTR-2B with purchase register and list mismatches.",
             "Act as a GST reconciliation assistant. I will give a GSTR-2B file and the purchase register. Match invoices by GSTIN, invoice number, date and tax amount. "
             "Return: (1) matched, (2) in books but not in 2B, (3) in 2B but not in books, (4) value differences. Show a summary table first.",
             "GSTR-2B (Excel), purchase register (Excel)", ["GST Return Filing"]),
            ("Bank statement vs Tally ledger", "Reconcile bank statement with the bank ledger from Tally.",
             "Act as a bank reconciliation assistant. Compare the bank statement with the Tally bank ledger. Match by date, amount and narration. "
             "List unmatched entries on both sides and prepare a Bank Reconciliation Statement.",
             "Bank statement (PDF/Excel), Tally bank ledger (Excel)", ["Bank Reconciliation", "Accounting"]),
            ("TDS challan check", "Check TDS deducted against challans paid.",
             "Compare the TDS deduction register with the challans. Flag short deduction, late payment and interest.", "TDS register, challans", ["TDS Compliance"])]
    for n, d, ins, docs, svcs in data:
        sid = db.x("insert into skills(name,description,instructions,docs_needed) values(?,?,?,?)", (n, d, ins, docs))
        for s in svcs:
            if s in sv:
                db.x("insert or ignore into skill_links(skill_id,service_id) values(?,?)", (sid, sv[s]))
