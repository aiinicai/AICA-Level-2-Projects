import csv, io, os, sqlite3, time
from core import framework as F, paths
from core.framework import Router, CA, BOSS, HttpError, Response

MANIFEST = dict(key="admin", name="Administration & Security", core=True, status="ready",
    desc="Module manager, users, settings, audit log, backup and demo data.",
    subs=[("module_manager", "Module manager", "ready"), ("users", "User management", "ready"),
          ("firm_settings", "Firm settings & integrations", "ready"), ("audit_log", "Audit trail", "ready"),
          ("backup", "Backup", "ready"), ("demo_data", "Demo data & reset", "ready"), ("csv_tools", "CSV import / export", "ready"),
          ("access_control", "Granular permissions", "planned"), ("custom_fields", "Custom fields", "planned"),
          ("restore", "One-click restore", "planned")])
R = Router()
SCHEMA = ""
SETTING_KEYS = ["tally_auto_post", "firm_name", "gst_rate", "ca_alert_email", "login_hint", "smtp_host", "smtp_port", "smtp_user", "smtp_pass", "smtp_from",
                "n8n_webhook_url", "tally_url", "tally_company", "tally_fee_ledger", "tally_gst_ledger", "tally_bank_ledger",
                "ai_provider", "openai_key", "openai_model"]
SECRET = ("smtp_pass", "openai_key")
DEMO_USERS = [("manager", "Priya Nair", "manager", "Audit Manager"), ("riya", "Riya Shah", "employee", "Senior Executive"),
              ("amit", "Amit Rao", "employee", "Executive"), ("neha", "Neha Verma", "employee", "Article Assistant")]
DEMO_PW = "demo@123"


# ---- modules ----
@R.get("/modules", roles=CA, sub="module_manager")
def modules(c):
    from modules import ALL
    out = []
    for m in ALL:
        man = m.MANIFEST
        subs = {r["key"]: bool(r["enabled"]) for r in c.db.q("select key,enabled from sub_state where mod=?", (man["key"],))}
        out.append({"key": man["key"], "name": man["name"], "desc": man["desc"], "core": man.get("core", False), "status": man["status"],
                    "requires": man.get("requires", []), "enabled": F.mod_on(c.db, man["key"]),
                    "subs": [{"key": s[0], "name": s[1], "status": s[2], "enabled": subs.get(s[0], False)} for s in man["subs"]]})
    return out


@R.post("/modules/<key>/toggle", roles=CA, sub="module_manager")
def toggle(c):
    from modules import ALL
    m = next((x.MANIFEST for x in ALL if x.MANIFEST["key"] == c.params["key"]), None)
    if not m:
        raise HttpError(404, "Unknown module")
    on = 1 if c.body.get("enabled") else 0
    if m["status"] != "ready":
        raise HttpError(400, "This module is not built yet – it will plug in here later")
    if m.get("core") and not on:
        raise HttpError(400, "Core modules cannot be switched off")
    if on:
        for r in m.get("requires", []):
            if not F.mod_on(c.db, r):
                raise HttpError(400, f"Switch on '{r}' first (required)")
    else:
        dep = [x.MANIFEST["name"] for x in ALL if m["key"] in x.MANIFEST.get("requires", []) and F.mod_on(c.db, x.MANIFEST["key"])]
        if dep:
            raise HttpError(400, "Switch off first: " + ", ".join(dep))
    c.db.x("update module_state set enabled=? where key=?", (on, m["key"]))
    return {"ok": True}


@R.post("/modules/<key>/subs/<sub>/toggle", roles=CA, sub="module_manager")
def toggle_sub(c):
    from modules import ALL
    m = next((x.MANIFEST for x in ALL if x.MANIFEST["key"] == c.params["key"]), None)
    s = next((s for s in (m or {}).get("subs", []) if s[0] == c.params["sub"]), None)
    if not s or s[2] != "ready":
        raise HttpError(400, "Not available yet")
    if m["key"] == "admin" and s[0] == "module_manager":
        raise HttpError(400, "The module manager itself cannot be switched off")
    c.db.x("update sub_state set enabled=? where mod=? and key=?", (1 if c.body.get("enabled") else 0, m["key"], s[0]))
    return {"ok": True}


# ---- users ----
@R.get("/users", sub="users")
def users(c):
    return c.db.q("select id,username,name,role,email,phone,designation,active from users order by role='ca' desc, name") if c.is_boss else \
        c.db.q("select id,name,role from users where active=1 order by name")


@R.post("/users", roles=CA, sub="users")
def user_add(c):
    u, n, pw = c.need("username", "name", "password")
    if len(pw) < 6:
        raise HttpError(400, "Password needs 6+ characters")
    if c.db.one("select 1 from users where username=?", (u,)):
        raise HttpError(400, "Username already exists")
    b = c.body
    return {"id": c.db.x("insert into users(username,name,role,email,phone,designation,pw) values(?,?,?,?,?,?,?)",
            (u, n, b.get("role") or "employee", b.get("email"), b.get("phone"), b.get("designation"), F.hash_pw(pw)))}


@R.put("/users/<id>", roles=CA, sub="users")
def user_upd(c):
    b = c.body
    if str(c.params["id"]) == str(c.user["id"]) and not b.get("active", 1):
        raise HttpError(400, "You cannot deactivate yourself")
    c.db.x("update users set name=?,role=?,email=?,phone=?,designation=?,active=? where id=?",
           (b["name"], b.get("role") or "employee", b.get("email"), b.get("phone"), b.get("designation"), 1 if b.get("active", 1) in (1, True, "1") else 0, c.params["id"]))
    if b.get("password"):
        if len(b["password"]) < 6:
            raise HttpError(400, "Password needs 6+ characters")
        c.db.x("update users set pw=? where id=?", (F.hash_pw(b["password"]), c.params["id"]))
    return {"ok": True}


@R.post("/password", sub="users")
def change_pw(c):
    old, new = c.need("old", "new")
    if not F.check_pw(old, c.user["pw"]) or len(new) < 6:
        raise HttpError(400, "Old password is wrong or new password is too short")
    c.db.x("update users set pw=? where id=?", (F.hash_pw(new), c.user["id"]))
    return {"ok": True}


# ---- settings / audit ----
@R.get("/settings", roles=CA, sub="firm_settings")
def settings(c):
    return {k: ("********" if k in SECRET and F.get_setting(c.db, k) else F.get_setting(c.db, k)) for k in SETTING_KEYS}


@R.put("/settings", roles=CA, sub="firm_settings")
def settings_save(c):
    for k, v in c.body.items():
        if k in SETTING_KEYS and not (k in SECRET and v == "********"):
            F.set_setting(c.db, k, v)
    return {"ok": True}


@R.get("/audit", roles=BOSS, sub="audit_log")
def audit(c):
    return c.db.q("select * from audit_log order by id desc limit ?", (int(c.query.get("limit") or 200),))


# ---- backup ----
@R.get("/backups", roles=CA, sub="backup")
def backups(c):
    d = os.path.join(paths.DATA, "backups")
    return [{"name": f, "kb": os.path.getsize(os.path.join(d, f)) // 1024} for f in sorted(os.listdir(d), reverse=True)]


@R.post("/backups", roles=CA, sub="backup")
def backup_now(c):
    name = "workdesk-%s.db" % time.strftime("%Y%m%d-%H%M%S")
    dest = sqlite3.connect(os.path.join(paths.DATA, "backups", name))
    c.db.c.backup(dest)
    dest.close()
    return {"name": name}


@R.get("/backups/<name>", roles=CA, sub="backup")
def backup_dl(c):
    p = os.path.join(paths.DATA, "backups", os.path.basename(c.params["name"]))
    if not os.path.isfile(p):
        raise HttpError(404, "Not found")
    return Response(open(p, "rb").read(), "application/octet-stream", os.path.basename(p))


# ---- csv ----
EXPORTS = {"clients": "select name,pan,gstin,email,phone,ctype from clients",
           "assignments": "select a.title,c.name client,s.name service,a.period,a.due_date,a.status,u.name employee,a.fee,a.remarks from assignments a join clients c on c.id=a.client_id left join services s on s.id=a.service_id left join users u on u.id=a.assigned_to",
           "invoices": "select i.no,c.name client,i.inv_date,i.amount,i.gst,i.total,i.paid,i.status from invoices i join clients c on c.id=i.client_id",
           "audit": "select ts,user,action,detail from audit_log"}


@R.get("/export/<name>", roles=BOSS, sub="csv_tools")
def export(c):
    sql = EXPORTS.get(c.params["name"])
    if not sql:
        raise HttpError(404, "Unknown export")
    rows = c.db.q(sql)
    out = io.StringIO()
    w = csv.writer(out)
    if rows:
        w.writerow(rows[0].keys())
        w.writerows([r.values() for r in rows])
    return Response("\ufeff" + out.getvalue(), "text/csv; charset=utf-8", c.params["name"] + ".csv")  # BOM so Excel shows ₹ and – correctly


TEMPLATES = {
    "clients": "name,ctype,pan,gstin,email,phone,address\nABC Traders,Company,ABCDE1234F,21ABCDE1234F1Z5,abc@example.com,9000000001,Cuttack\n",
    "employees": "username,name,role,designation,email,phone,password\nriya,Riya Shah,employee,Article Assistant,riya@example.com,9000000002,Change@123\n",
    "assignments": "client,service,title,due_date,status,employee,fee,remarks\nABC Traders,GST Return Filing,GSTR-3B Oct 2026,2026-11-20,In Progress,riya,1500,Pending purchase register\n",
    "applicability": "client,compliance,employee\nABC Traders,GSTR-3B,riya\n",
}


def _rows(text):
    for n, r in enumerate(csv.DictReader(io.StringIO(text.lstrip("\ufeff"))), 2):
        yield n, {(k or "").strip().lower(): (v or "").strip() for k, v in r.items()}


@R.get("/import-template/<kind>", roles=BOSS, sub="csv_tools")
def import_template(c):
    t = TEMPLATES.get(c.params["kind"])
    if not t:
        raise HttpError(404, "Unknown template")
    return Response("\ufeff" + t, "text/csv; charset=utf-8", c.params["kind"] + "_template.csv")


@R.post("/import/<kind>", roles=BOSS, sub="csv_tools")
def import_any(c):
    """Bulk import for a new office: clients, employees, pending/open assignments."""
    kind = c.params["kind"]
    text, = c.need("csv")
    db, ok, bad = c.db, 0, []
    for n, r in _rows(text):
        try:
            if kind == "clients":
                if not r.get("name"):
                    continue
                if db.one("select 1 from clients where lower(name)=lower(?)", (r["name"],)):
                    bad.append(f"row {n}: {r['name']} already exists"); continue
                db.x("insert into clients(name,pan,gstin,email,phone,ctype,address) values(?,?,?,?,?,?,?)",
                     (r["name"], r.get("pan"), r.get("gstin"), r.get("email"), r.get("phone"), r.get("ctype") or "Company", r.get("address")))
            elif kind == "employees":
                if not c.user["role"] == "ca":
                    raise HttpError(403, "Only the CA can create logins")
                if not r.get("username") or len(r.get("password", "")) < 6:
                    bad.append(f"row {n}: username and a 6+ character password are required"); continue
                if db.one("select 1 from users where username=?", (r["username"],)):
                    bad.append(f"row {n}: {r['username']} already exists"); continue
                role = r.get("role") if r.get("role") in ("employee", "manager") else "employee"
                db.x("insert into users(username,name,role,email,phone,designation,pw) values(?,?,?,?,?,?,?)",
                     (r["username"], r.get("name") or r["username"], role, r.get("email"), r.get("phone"), r.get("designation"), F.hash_pw(r["password"])))
            elif kind == "assignments":
                from modules import work
                cl = db.one("select id from clients where lower(name)=lower(?)", (r.get("client", ""),))
                if not cl or not r.get("title"):
                    bad.append(f"row {n}: client not found or title missing"); continue
                sv = db.one("select id from services where lower(name)=lower(?)", (r.get("service", ""),)) if r.get("service") else None
                u = db.one("select id from users where lower(username)=lower(?) or lower(name)=lower(?)", (r.get("employee"), r.get("employee"))) if r.get("employee") else None
                st = r.get("status") if r.get("status") in work.STATUSES else ("In Progress" if u else "New")
                fee, mode = (round(float(r["fee"]), 2), "custom") if r.get("fee") else work.resolve_fee(db, cl["id"], sv["id"] if sv else None, None, None)
                work.create_assignment(db, client_id=cl["id"], service_id=sv["id"] if sv else None, title=r["title"], due_date=r.get("due_date") or None,
                                       assigned_to=u["id"] if u else None, created_by=c.user["id"], source="import", status=st, remarks=r.get("remarks"), fee=fee, fee_mode=mode)
            else:
                raise HttpError(404, "Unknown import")
            ok += 1
        except HttpError:
            raise
        except Exception as e:
            bad.append(f"row {n}: {e}")
    return {"imported": ok, "errors": bad[:25]}


# ---- demo ----
def _vary_demo(db):
    """Make the demo look like a real office: mixed statuses, some due soon, fees and remarks."""
    from modules import work
    rows = db.q("select id, client_id, service_id from assignments order by id")
    for i, r in enumerate(rows):
        st = ["In Progress", "In Progress", "In Review", "Awaiting Documents", "In Progress", "Approved", "In Progress", "New", "In Progress", "Closed"][i % 10]
        fee, mode = work.resolve_fee(db, r["client_id"], r["service_id"], None, None)
        db.x("update assignments set status=?, fee=?, fee_mode=?, remarks=? where id=?",
             (st, fee, mode, "Carry forward from last month; check purchase register." if i % 6 == 0 else None, r["id"]))
        if i % 7 == 3:
            db.x("update assignments set due_date=date('now','localtime',?) where id=?", ("+%d day" % (1 + i % 6), r["id"]))
        if st in ("Approved", "Closed"):
            db.x("update assignments set closed_at=datetime('now') where id=?", (r["id"],))


def load_demo(db):
    from modules import ALL
    for u, n, role, des in DEMO_USERS:
        db.x("insert or ignore into users(username,name,role,designation,pw,demo,email) values(?,?,?,?,?,1,?)",
             (u, n, role, des, F.hash_pw(DEMO_PW), u + "@demo-firm.example"))
    for name in ("work", "compliance", "finance", "employee", "skills", "alerts", "comms"):
        m = next((x for x in ALL if x.MANIFEST["key"] == name), None)
        if m and hasattr(m, "demo"):
            m.demo(db)
    _vary_demo(db)
    F.set_setting(db, "login_hint", "Demo logins (fictional data) – password %s for: manager, riya, amit, neha" % DEMO_PW)


@R.post("/demo/load", roles=CA, sub="demo_data")
def demo_load(c):
    if c.db.one("select count(*) n from clients")["n"]:
        raise HttpError(400, "Data already exists. Use Reset demo data to start fresh.")
    load_demo(c.db)
    return {"ok": True}


@R.post("/demo/reset", roles=CA, sub="demo_data")
def demo_reset(c):
    from modules import ALL
    if not c.body.get("confirm"):
        raise HttpError(400, "Confirmation required")
    for m in ALL:
        for t in getattr(m, "TABLES", []):
            c.db.x("delete from " + t)
    c.db.x("delete from users where demo=1")
    c.db.x("delete from sessions where user_id not in (select id from users)")
    for m in ALL:
        if hasattr(m, "seed"):
            m.seed(c.db)
    load_demo(c.db)
    return {"ok": True}
