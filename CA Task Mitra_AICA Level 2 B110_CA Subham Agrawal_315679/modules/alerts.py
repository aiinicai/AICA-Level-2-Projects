import json, datetime as dt, urllib.request
from core import framework as F, mail
from core.framework import Router, BOSS, HttpError

MANIFEST = dict(key="alerts", name="Automation & Alerts", core=False, status="ready", requires=["work"],
    desc="Scheduled pending-work alerts to the CA through an n8n webhook, with e-mail fallback.",
    subs=[("rules", "Alert rules", "ready"), ("scheduler", "Automatic scheduler", "ready"), ("n8n_webhook", "n8n webhook", "ready"),
          ("email_fallback", "Direct e-mail fallback", "ready"), ("log", "Alert log", "ready")])
R = Router()
TABLES = ["alert_log", "alert_rules"]
SCHEMA = """
create table if not exists alert_rules(id integer primary key, name text, compliance_id int, offsets text default '-2,0,1', send_hour int default 8,
  recipient text, active int default 1);
create table if not exists alert_log(id integer primary key, rule_id int, run_date text, count int, channel text, status text, message text, created text default (datetime('now')));
create unique index if not exists ux_alert_once on alert_log(rule_id, run_date) where status!='Manual';
"""


def pending_for(db, rule, dues=None):
    sql = """select cl.name client, a.title, a.period, a.due_date, a.status, coalesce(u.name,'Unassigned') employee from assignments a
      join clients cl on cl.id=a.client_id left join users u on u.id=a.assigned_to where a.compliance_id=? and a.status not in ('Approved','Closed')"""
    args = [rule["compliance_id"]]
    if dues:
        sql += " and a.due_date in (%s)" % ",".join("?" * len(dues))
        args += dues
    return db.q(sql + " order by a.due_date, cl.name", args)


def build(db, rule, items, when):
    co = db.one("select code from compliance where id=?", (rule["compliance_id"],)) if rule["compliance_id"] else None
    code = co["code"] if co else "assignments"
    lines = "\n".join(f"- {i['client']} | due {i['due_date']} | {i['status']} | {i['employee']}" for i in items)
    return {"rule": rule["name"], "title": f"Pending {code} list – {when} ({len(items)})", "date": when, "count": len(items),
            "items": items, "text": f"Pending {code} as on {when}: {len(items)} client(s)\n\n{lines}"}


def deliver(db, rule, payload):
    to = rule.get("recipient") or F.get_setting(db, "ca_alert_email")
    url = F.get_setting(db, "n8n_webhook_url")
    if url and F.sub_on(db, "alerts", "n8n_webhook"):
        try:
            req = urllib.request.Request(url, data=json.dumps({**payload, "to": to}, default=str).encode(), headers={"Content-Type": "application/json"})
            urllib.request.urlopen(req, timeout=15).read()
            return "n8n webhook", "Sent via n8n"
        except Exception as e:
            err = "n8n failed (%s); " % str(e)[:80]
    else:
        err = ""
    if not (F.sub_on(db, "alerts", "email_fallback") and to):
        raise RuntimeError(err + "no e-mail fallback / recipient")
    return "email", err + mail.send_mail(db, to, payload["title"], payload["text"])


def run_rule(db, rule, today, manual=False):
    offs = [int(x) for x in str(rule["offsets"]).replace(" ", "").split(",") if x]
    dues = None if manual else [(today - dt.timedelta(days=o)).isoformat() for o in offs]
    items = pending_for(db, rule, dues)
    if not items and not manual:
        db.x("insert or ignore into alert_log(rule_id,run_date,count,channel,status,message) values(?,?,0,'-','Nothing pending','No pending items')", (rule["id"], today.isoformat()))
        return None
    payload = build(db, rule, items, today.isoformat())
    try:
        ch, msg = deliver(db, rule, payload)
        st = "Manual" if manual else "Sent"
    except Exception as e:
        ch, msg, st = "-", str(e), "Failed" if not manual else "Manual"
    db.x("insert or ignore into alert_log(rule_id,run_date,count,channel,status,message) values(?,?,?,?,?,?)",
         (rule["id"], today.isoformat(), len(items), ch, st, msg))
    return {"count": len(items), "channel": ch, "status": st, "message": msg}


def TICK(db):
    if not F.sub_on(db, "alerts", "scheduler"):
        return
    now = dt.datetime.now()
    for r in db.q("select * from alert_rules where active=1"):
        if now.hour >= int(r["send_hour"] or 8) and not db.one("select 1 from alert_log where rule_id=? and run_date=? and status!='Manual'", (r["id"], now.date().isoformat())):
            run_rule(db, r, now.date())


@R.get("/rules", roles=BOSS, sub="rules")
def rules(c):
    return c.db.q("select r.*, co.code from alert_rules r left join compliance co on co.id=r.compliance_id order by r.id")


@R.post("/rules", roles=BOSS, sub="rules")
def rule_add(c):
    n, comp = c.need("name", "compliance_id")
    b = c.body
    return {"id": c.db.x("insert into alert_rules(name,compliance_id,offsets,send_hour,recipient) values(?,?,?,?,?)",
                         (n, comp, b.get("offsets") or "-2,0,1", int(b.get("send_hour") or 8), b.get("recipient")))}


@R.put("/rules/<id>", roles=BOSS, sub="rules")
def rule_upd(c):
    b = c.body
    c.db.x("update alert_rules set name=?,compliance_id=?,offsets=?,send_hour=?,recipient=?,active=? where id=?",
           (b["name"], b["compliance_id"], b.get("offsets"), int(b.get("send_hour") or 8), b.get("recipient"), 1 if b.get("active", 1) in (1, True, "1") else 0, c.params["id"]))
    return {"ok": True}


@R.post("/rules/<id>/run", roles=BOSS, sub="rules")
def rule_run(c):
    r = c.db.one("select * from alert_rules where id=?", (c.params["id"],))
    if not r:
        raise HttpError(404, "Rule not found")
    return run_rule(c.db, r, dt.date.today(), manual=True) or {"count": 0, "message": "Nothing pending"}


@R.get("/log", roles=BOSS, sub="log")
def log(c):
    return c.db.q("select l.*, r.name rule from alert_log l left join alert_rules r on r.id=l.rule_id order by l.id desc limit 100")


def demo(db):
    co = db.one("select id from compliance where code='GSTR-3B'")
    if co:
        db.x("insert into alert_rules(name,compliance_id,offsets,send_hour) values(?,?,?,?)", ("GSTR-3B pending list (18th, 20th, 21st)", co["id"], "-2,0,1", 8))
