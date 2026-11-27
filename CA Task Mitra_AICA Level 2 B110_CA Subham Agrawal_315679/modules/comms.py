from core import framework as F, mail
from core.framework import Router, BOSS, HttpError

MANIFEST = dict(key="comms", name="Communication", core=False, status="ready", requires=["work"],
    desc="Missing-document e-mails drafted by staff and sent only after CA approval.",
    subs=[("drafts", "Missing-document drafts", "ready"), ("approval_queue", "CA approval queue", "ready"),
          ("smtp_send", "Send from firm mailbox (SMTP)", "ready"), ("announcements", "Announcements & staff messages", "ready"), ("whatsapp", "WhatsApp messages", "planned"),
          ("sms_otp", "SMS & OTP", "planned"), ("templates", "Message templates", "planned")])
R = Router()
TABLES = ["announcement_reads", "announcements", "email_drafts"]
SCHEMA = """
create table if not exists email_drafts(id integer primary key, assignment_id int, client_id int, to_email text, subject text, body text,
  status text default 'Draft', created_by int, approved_by int, created text default (datetime('now')), sent_at text, result text);
create table if not exists announcements(id integer primary key, title text not null, body text, to_user int, created_by int,
  created text default (datetime('now')), pinned int default 0);
create table if not exists announcement_reads(announcement_id int, user_id int, primary key(announcement_id,user_id));
"""


@R.post("/drafts/missing-docs", sub="drafts")
def missing(c):
    aid, = c.need("assignment_id")
    docs = [d for d in c.body.get("docs", []) if d]
    a = c.db.one("select a.*, c.name client, c.email from assignments a join clients c on c.id=a.client_id where a.id=?", (aid,))
    if not a or (not c.is_boss and a["assigned_to"] != c.user["id"]):
        raise HttpError(404, "Assignment not found")
    if not docs:
        raise HttpError(400, "Select or type at least one missing document")
    firm = F.get_setting(c.db, "firm_name", "our firm")
    lines = "\n".join(f"  {i}. {d}" for i, d in enumerate(docs, 1))
    body = (f"Dear {a['client']},\n\nWe are working on: {a['title']}"
            + (f" (due {a['due_date']})" if a["due_date"] else "") +
            f".\n\nTo proceed, please send us the following documents:\n{lines}\n\n"
            + (c.body.get("note") + "\n\n" if c.body.get("note") else "") +
            f"Kindly share them at the earliest so that the work is completed on time.\n\nRegards,\n{firm}")
    did = c.db.x("insert into email_drafts(assignment_id,client_id,to_email,subject,body,created_by) values(?,?,?,?,?,?)",
                 (aid, a["client_id"], a["email"], f"Documents required – {a['title']}", body, c.user["id"]))
    c.db.x("update assignments set status='Awaiting Documents', updated=datetime('now') where id=? and status in ('New','In Progress')", (aid,))
    return {"id": did, "status": "Draft saved – waiting for CA approval"}


@R.get("/drafts", sub="drafts")
def drafts(c):
    sql = ("select d.*, cl.name client, u.name author, a.title from email_drafts d left join clients cl on cl.id=d.client_id "
           "left join users u on u.id=d.created_by left join assignments a on a.id=d.assignment_id")
    where, args = [], []
    if not c.is_boss:
        where.append("d.created_by=?"); args.append(c.user["id"])
    if c.query.get("status"):
        where.append("d.status=?"); args.append(c.query["status"])
    return c.db.q(sql + (" where " + " and ".join(where) if where else "") + " order by d.id desc limit 200", args)


@R.put("/drafts/<id>", roles=BOSS, sub="approval_queue")
def draft_edit(c):
    b = c.body
    c.db.x("update email_drafts set to_email=?, subject=?, body=? where id=? and status in ('Draft','Failed')", (b["to_email"], b["subject"], b["body"], c.params["id"]))
    return {"ok": True}


@R.post("/drafts/<id>/approve", roles=BOSS, sub="approval_queue")
def approve(c):
    d = c.db.one("select * from email_drafts where id=?", (c.params["id"],))
    if not d or d["status"] not in ("Draft", "Failed"):
        raise HttpError(400, "Draft not found or already processed")
    if not d["to_email"]:
        raise HttpError(400, "The client has no e-mail address – edit the draft and add one")
    if not F.sub_on(c.db, "comms", "smtp_send"):
        raise HttpError(403, "Sending is switched off")
    try:
        res = mail.send_mail(c.db, d["to_email"], d["subject"], d["body"])
        c.db.x("update email_drafts set status='Sent', approved_by=?, sent_at=datetime('now'), result=? where id=?", (c.user["id"], res, d["id"]))
        return {"status": "Sent", "result": res}
    except Exception as e:
        c.db.x("update email_drafts set status='Failed', result=? where id=?", (str(e)[:200], d["id"]))
        raise HttpError(502, "Could not send: %s" % e)


@R.post("/drafts/<id>/reject", roles=BOSS, sub="approval_queue")
def reject(c):
    c.db.x("update email_drafts set status='Rejected', approved_by=? where id=? and status='Draft'", (c.user["id"], c.params["id"]))
    return {"ok": True}


@R.get("/announcements", sub="announcements")
def ann_list(c):
    me = c.user["id"]
    return c.db.q("""select n.*, u.name author, t.name to_name, (select count(*) from announcement_reads r where r.announcement_id=n.id and r.user_id=?) seen
        from announcements n left join users u on u.id=n.created_by left join users t on t.id=n.to_user
        where (n.to_user is null or n.to_user=? or n.created_by=? or ?) order by n.pinned desc, n.id desc limit 100""", (me, me, me, 1 if c.is_boss else 0))


@R.post("/announcements", roles=BOSS, sub="announcements")
def ann_add(c):
    t, = c.need("title")
    b = c.body
    return {"id": c.db.x("insert into announcements(title,body,to_user,created_by,pinned) values(?,?,?,?,?)",
                         (t, b.get("body"), b.get("to_user") or None, c.user["id"], 1 if b.get("pinned") in (1, True, "1", "true") else 0))}


@R.post("/announcements/<id>/seen", sub="announcements")
def ann_seen(c):
    c.db.x("insert or ignore into announcement_reads(announcement_id,user_id) values(?,?)", (c.params["id"], c.user["id"]))
    return {"ok": True}


@R.post("/announcements/<id>/delete", roles=BOSS, sub="announcements")
def ann_del(c):
    c.db.x("delete from announcements where id=?", (c.params["id"],))
    c.db.x("delete from announcement_reads where announcement_id=?", (c.params["id"],))
    return {"ok": True}


def demo(db):
    ca = db.one("select id from users where role='ca' limit 1")
    if ca:
        db.x("insert into announcements(title,body,created_by,pinned) values(?,?,?,1)",
             ("Welcome to CA Task Mitra", "Please check in every morning, update task status daily and log your hours.", ca["id"]))
    a = db.one("select a.id, a.title, a.client_id, c.name, c.email from assignments a join clients c on c.id=a.client_id where a.assigned_to is not null limit 1")
    u = db.one("select id,name from users where username='riya'")
    if a and u:
        db.x("insert into email_drafts(assignment_id,client_id,to_email,subject,body,created_by) values(?,?,?,?,?,?)",
             (a["id"], a["client_id"], a["email"], "Documents required – " + a["title"],
              f"Dear {a['name']},\n\nPlease send the following documents:\n  1. Purchase register\n  2. Bank statement\n\nRegards,\nDemo CA Firm", u["id"]))
