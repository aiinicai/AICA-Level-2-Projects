import json, re, datetime as dt, urllib.request
from core import framework as F
from core.framework import Router, BOSS, HttpError
from modules import work

MANIFEST = dict(key="ai", name="AI Assistant", core=False, status="ready", requires=["work"],
    desc="Morning briefing, plain-English task creation and checklist suggestions. AI output always needs human confirmation.",
    subs=[("briefing", "Morning briefing", "ready"), ("nl_task", "Plain-English task creation", "ready"),
          ("checklist_ai", "Checklist suggestions", "ready"), ("llm", "Use OpenAI for wording (needs API key)", "ready"),
          ("delay_prediction", "Delay prediction", "planned")])
R = Router()
SCHEMA = ""
MONTHS = {m: i for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}
CHECKLISTS = {"gst": ["Collect sales and purchase data", "Reconcile GSTR-2B with books", "Prepare liability and ITC working", "Maker review", "File return and save acknowledgement"],
              "tds": ["Collect deduction details", "Verify PAN and section rates", "Check challan payments", "Prepare return / statement", "File and save acknowledgement"],
              "income": ["Collect Form 16/26AS/AIS", "Compute income and deductions", "Prepare return", "Client approval", "File and e-verify"],
              "audit": ["Obtain trial balance and ledgers", "Verify opening balances", "Test sample vouchers", "Prepare working papers", "Draft report", "Partner review"],
              "bank": ["Import bank statement", "Match with Tally bank ledger", "List unmatched items", "Prepare reconciliation statement"]}


def llm(db, prompt, system="You are a concise assistant for an Indian CA firm."):
    key = F.get_setting(db, "openai_key")
    if not key or not F.sub_on(db, "ai", "llm"):
        return None
    try:
        req = urllib.request.Request("https://api.openai.com/v1/chat/completions", headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"},
            data=json.dumps({"model": F.get_setting(db, "openai_model") or "gpt-4o-mini", "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}]}).encode())
        return json.loads(urllib.request.urlopen(req, timeout=40).read())["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print("llm error", e)
        return None


@R.get("/briefing", sub="briefing")
def briefing(c):
    db = c.db
    sc = "" if c.is_boss else " and a.assigned_to=%d" % c.user["id"]
    q = lambda w: db.one("select count(*) n from assignments a where a.status not in ('Approved','Closed')" + sc + w)["n"]
    stats = {"overdue": q(" and a.due_date<date('now','localtime')"), "due_3_days": q(" and a.due_date between date('now','localtime') and date('now','localtime','+3 day')"),
             "awaiting_docs": q(" and a.status='Awaiting Documents'"), "in_review": db.one("select count(*) n from assignments a where a.status='In Review'" + sc)["n"]}
    top = db.q("select c.name client, a.title, a.due_date, coalesce(u.name,'Unassigned') who from assignments a join clients c on c.id=a.client_id left join users u on u.id=a.assigned_to "
               "where a.status not in ('Approved','Closed')" + sc + " order by a.due_date limit 5")
    load = db.q("select u.name, count(*) n from assignments a join users u on u.id=a.assigned_to where a.status not in ('Approved','Closed') group by u.id order by n desc limit 3") if c.is_boss else []
    pend = db.one("select count(*) n from email_drafts where status='Draft'")["n"] if F.mod_on(db, "comms") and c.is_boss else 0
    text = (f"Good morning, {c.user['name'].split()[0]}. {stats['overdue']} assignment(s) are overdue, {stats['due_3_days']} fall due in the next 3 days, "
            f"{stats['awaiting_docs']} are waiting for client documents and {stats['in_review']} await review." + (f" {pend} e-mail draft(s) need your approval." if pend else ""))
    if load:
        text += " Highest workload: " + ", ".join(f"{x['name']} ({x['n']})" for x in load) + "."
    polished = llm(db, "Rewrite this as a crisp 3-line morning briefing. Keep all numbers and names exact:\n" + text + "\nMost urgent: " + json.dumps(top))
    return {"text": polished or text, "ai_polished": bool(polished), "stats": stats, "urgent": top}


def parse(db, text):
    t = text.lower()
    users = db.q("select id,name from users where active=1")
    clients = db.q("select id,name from clients where active=1")
    emp = next((u for u in users if u["name"].split()[0].lower() in t), None)
    cl = max((x for x in clients if x["name"].lower().replace("'s", "") in t.replace("'s", "")), key=lambda x: len(x["name"]), default=None)
    due = None
    m = re.search(r"(\d{1,2})(?:st|nd|rd|th)?\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*", t)
    if m:
        y = dt.date.today().year
        d = dt.date(y, MONTHS[m.group(2)], min(int(m.group(1)), 28 if MONTHS[m.group(2)] == 2 else 30 if MONTHS[m.group(2)] in (4, 6, 9, 11) else 31))
        due = (d if d >= dt.date.today() - dt.timedelta(days=60) else d.replace(year=y + 1)).isoformat()
    svc = next((s for k, n in (("gst", "GST Return Filing"), ("tds", "TDS Compliance"), ("itr", "Income Tax Return"), ("income tax", "Income Tax Return"),
                               ("audit", "Tax Audit"), ("bank", "Bank Reconciliation")) if k in t
                for s in db.q("select id,name from services where name=?", (n,))), None)
    title = text.strip().rstrip(".")[:90]
    return {"client": cl, "employee": emp, "due_date": due, "service": svc, "title": title}


@R.post("/parse-task", roles=BOSS, sub="nl_task")
def parse_task(c):
    t, = c.need("text")
    return parse(c.db, t)


@R.post("/create-task", roles=BOSS, sub="nl_task")
def create_task(c):
    cid, title = c.need("client_id", "title")
    b = c.body
    aid = work.create_assignment(c.db, client_id=cid, title=title, service_id=b.get("service_id") or None, due_date=b.get("due_date"),
                                 assigned_to=b.get("assigned_to") or None, created_by=c.user["id"], source="ai-assisted")
    if b.get("assigned_to"):
        c.db.x("update assignments set status='In Progress' where id=?", (aid,))
    return {"id": aid}


@R.post("/checklist-suggest", sub="checklist_ai")
def checklist_suggest(c):
    a = c.db.one("select a.title, s.name service, cl.name client from assignments a left join services s on s.id=a.service_id join clients cl on cl.id=a.client_id where a.id=?", (c.body.get("assignment_id"),))
    if not a:
        raise HttpError(404, "Assignment not found")
    key = (a["service"] or "") + " " + a["title"]
    key = key.lower()
    base = next((v for k, v in CHECKLISTS.items() if k in key), ["Collect documents", "Prepare working", "Review", "File / deliver"])
    out = llm(c.db, f"Suggest 6 short checklist steps and the documents needed for: {a['title']} ({a['service']}). Return one item per line, no numbering.")
    items = [re.sub(r"^[-*\d.\s]+", "", x).strip() for x in out.splitlines() if x.strip()][:8] if out else base
    return {"items": items, "ai_generated": bool(out)}
