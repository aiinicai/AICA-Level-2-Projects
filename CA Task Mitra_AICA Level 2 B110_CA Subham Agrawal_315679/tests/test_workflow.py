"""End-to-end test of CA Task Mitra. Run:  python tests/test_workflow.py
Starts the server on a temporary database and a fake Tally server, then walks the full workflow."""
import json, os, sys, tempfile, threading, time, urllib.request, urllib.error
from http.server import HTTPServer, BaseHTTPRequestHandler

tmp = tempfile.mkdtemp()
os.environ["WD_DATA"] = tmp
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core import server  # noqa: E402

PORT, TPORT = 8791, 8792
RESULTS, TALLY_HITS = [], []


class FakeTally(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_GET(self):
        self.send_response(200); self.end_headers(); self.wfile.write(b"<RESPONSE>TallyPrime Server is Running</RESPONSE>")
    def do_POST(self):
        body = self.rfile.read(int(self.headers["Content-Length"])).decode()
        TALLY_HITS.append(body)
        self.send_response(200); self.end_headers()
        self.wfile.write(b"<RESPONSE><CREATED>1</CREATED><ERRORS>0</ERRORS></RESPONSE>")


threading.Thread(target=HTTPServer(("127.0.0.1", TPORT), FakeTally).serve_forever, daemon=True).start()
threading.Thread(target=lambda: server.run(PORT, open_browser=False), daemon=True).start()
time.sleep(1.5)


class Client:
    def __init__(self): self.cookie = ""
    def call(self, method, path, body=None, expect=200):
        req = urllib.request.Request(f"http://127.0.0.1:{PORT}/api/{path}", method=method, data=json.dumps(body).encode() if body is not None else None,
                                     headers={"Content-Type": "application/json", "Cookie": self.cookie})
        try:
            r = urllib.request.urlopen(req); code = r.status
        except urllib.error.HTTPError as e:
            r, code = e, e.code
        if r.headers.get("Set-Cookie"): self.cookie = r.headers["Set-Cookie"].split(";")[0]
        raw = r.read()
        data = json.loads(raw) if raw[:1] in (b"{", b"[") else raw
        assert code == expect, f"{method} {path} -> {code} (expected {expect}) {data}"
        return data


def check(name, cond):
    RESULTS.append((name, bool(cond)))
    print(("PASS  " if cond else "FAIL  ") + name)


ca, riya, amit = Client(), Client(), Client()
st = ca.call("GET", "auth/status"); check("first run asks for setup", st["setup_needed"])
ca.call("POST", "auth/setup", {"firm": "Test & Co", "name": "CA Test", "username": "ca", "password": "ca@12345", "demo": True})
ca.call("POST", "auth/login", {"username": "ca", "password": "bad"}, expect=401)
ca.call("POST", "auth/login", {"username": "ca", "password": "ca@12345"})
riya.call("POST", "auth/login", {"username": "riya", "password": "demo@123"})
amit.call("POST", "auth/login", {"username": "amit", "password": "demo@123"})
sess = ca.call("GET", "auth/session")
check("12 modules registered", len(sess["modules"]) == 12)
check("planned modules are off", not [m for m in sess["modules"] if m["key"] in ("portal", "documents")][0]["enabled"])

# compliance engine
comps = {c["code"]: c for c in ca.call("GET", "compliance/master")}
r1 = ca.call("POST", "compliance/generate", {"freq": "monthly", "period": "2031-01"})
r2 = ca.call("POST", "compliance/generate", {"freq": "monthly", "period": "2031-01"})
check("generator creates assignments", r1["created"] > 0)
check("re-running creates no duplicates", r2["created"] == 0 and r2["skipped_duplicates"] == r1["created"])
a = [x for x in ca.call("GET", "work/assignments") if x["period"] == "2031-01" and x["title"].startswith("GSTR-3B")][0]
check("due date rule (GSTR-3B Jan -> 20 Feb)", a["due_date"] == "2031-02-20")
ext = ca.call("POST", "compliance/extensions", {"compliance_id": a["compliance_id"], "period": "2031-01", "new_due": "2031-02-28", "reason": "test"})
check("due-date extension updates open assignments", ext["assignments_updated"] > 0)

# roles and workflow
users = {u["username"]: u["id"] for u in ca.call("GET", "admin/users")}
ca.call("POST", f"work/assignments/{a['id']}/assign", {"user_id": users["riya"]})
check("employee sees only own work", all(x["employee"] == "Riya Shah" for x in riya.call("GET", "work/assignments")))
amit.call("GET", f"work/assignments/{a['id']}", expect=404)
check("other employee blocked from foreign task", True)
riya.call("POST", f"work/assignments/{a['id']}/status", {"status": "Approved"}, expect=403)
check("employee cannot approve", True)
riya.call("POST", f"work/assignments/{a['id']}/checklist", {"items": ["Prepare 3B"]})
riya.call("POST", f"work/assignments/{a['id']}/status", {"status": "In Review"})
ca.call("POST", f"work/assignments/{a['id']}/status", {"status": "Approved", "note": "Good"})
check("CA approval recorded", ca.call("GET", f"work/assignments/{a['id']}")["status"] == "Approved")

# finance + tally
inv = ca.call("POST", "finance/invoices", {"client_id": a["client_id"], "assignment_id": a["id"]})
d = ca.call("GET", f"finance/invoices/{inv['id']}")
check("invoice uses fee master + 18% GST", d["amount"] > 0 and abs(d["gst"] - d["amount"] * .18) < .01)
ca.call("POST", "finance/receipts", {"invoice_id": inv["id"], "amount": d["total"] + 1}, expect=400)
ca.call("POST", "finance/receipts", {"invoice_id": inv["id"], "amount": round(d["total"] / 2, 2), "mode": "UPI"})
check("partial receipt -> Partial", ca.call("GET", f"finance/invoices/{inv['id']}")["status"] == "Partial")
riya.call("GET", "finance/invoices", expect=403)
ca.call("PUT", "admin/settings", {"tally_url": f"http://127.0.0.1:{TPORT}", "tally_company": "CA Task Mitra Demo"})
check("tally connection test", ca.call("POST", "tally/test")["ok"])
q = ca.call("GET", "tally/queue"); check("invoice + receipt queued for Tally", len([x for x in q if x["status"] == "Pending"]) >= 2)
res = ca.call("POST", "tally/post-pending")
check("vouchers posted to (fake) Tally", res["posted"] >= 2 and res["failed"] == 0 and any("VCHTYPE=\"Sales\"" in h for h in TALLY_HITS))

# comms
dr = riya.call("POST", "comms/drafts/missing-docs", {"assignment_id": a["id"], "docs": ["Purchase register", "Bank statement"]})
check("employee draft is saved, not sent", riya.call("GET", "comms/drafts")[0]["status"] == "Draft")
riya.call("POST", f"comms/drafts/{dr['id']}/approve", expect=403)
check("employee cannot send", True)
ok = ca.call("POST", f"comms/drafts/{dr['id']}/approve")
check("CA approves and sends (simulated, saved in outbox)", ok["status"] == "Sent" and os.listdir(os.path.join(tmp, "outbox")))

# alerts
rules = ca.call("GET", "alerts/rules")
out = ca.call("POST", f"alerts/rules/{rules[0]['id']}/run")
check("alert rule builds pending list and delivers", out["count"] > 0)

# skills + AI
sk = ca.call("GET", "skills/skills")
run = riya.call("POST", f"skills/skills/{sk[0]['id']}/run", {"assignment_id": a["id"]})
check("skill launcher builds prompt + Claude URL", run["url"].startswith("https://claude.ai/new?q=") and sk[0]["name"] in run["prompt"])
check("AI briefing works", "overdue" in ca.call("GET", "ai/briefing")["text"])
p = ca.call("POST", "ai/parse-task", {"text": "Assign ABC Traders' October GST return to Rahul Riya before 20 November"})
check("plain-English task parsed", p["client"] and p["employee"] and p["due_date"])
check("checklist suggestions", len(riya.call("POST", "ai/checklist-suggest", {"assignment_id": a["id"]})["items"]) >= 4)

# modular switches
ca.call("POST", "admin/modules/compliance/toggle", {"enabled": False})
ca.call("GET", "compliance/master", expect=403)
check("module OFF blocks its API", True)
ca.call("POST", "admin/modules/work/toggle", {"enabled": False}, expect=400)
check("core module cannot be switched off", True)
ca.call("POST", "admin/modules/finance/toggle", {"enabled": False}, expect=400)
check("dependency guard (Tally needs Finance)", True)
ca.call("POST", "admin/modules/compliance/toggle", {"enabled": True})
ca.call("POST", "admin/modules/portal/toggle", {"enabled": True}, expect=400)
check("planned module cannot be switched on yet", True)
ca.call("POST", "admin/modules/finance/subs/invoices/toggle", {"enabled": False})
ca.call("GET", "finance/invoices", expect=403)
check("sub-module OFF blocks its feature", True)
ca.call("POST", "admin/modules/finance/subs/invoices/toggle", {"enabled": True})
check("audit trail records actions", len(ca.call("GET", "admin/audit")) > 10)
check("backup works", ca.call("POST", "admin/backups")["name"].endswith(".db"))
check("CSV export works", b"name" in ca.call("GET", "admin/export/clients"))

# ---------- round 2: issues-1 features ----------
cl0 = ca.call("GET", "work/clients")[0]; sv0 = ca.call("GET", "work/services")[0]
users = {u["username"]: u["id"] for u in ca.call("GET", "admin/users")}
ids = []
for t, mode, fee in [("T-A", "default", None), ("T-B", "custom", 777), ("T-C", "default", None)]:
    r = ca.call("POST", "work/assignments", {"client_id": cl0["id"], "service_id": sv0["id"], "title": t, "fee_mode": mode, "fee": fee, "remarks": "note " + t, "assigned_to": users["riya"]})
    ids.append(r["id"])
a1, a2 = ca.call("GET", f"work/assignments/{ids[0]}"), ca.call("GET", f"work/assignments/{ids[1]}")
check("default fee taken from fee master", a1["fee"] and a1["fee_mode"] == "default")
check("custom fee + remarks stored", a2["fee"] == 777 and a2["remarks"] == "note T-B")
g = ca.call("GET", "work/assignments-groups?by=status")
check("assignments grouped with counts", g["groups"] and all("total" in x and "pending" in x for x in g["groups"]))
check("drill-down by employee works", len(ca.call("GET", "work/assignments?by=employee&grp=Riya%20Shah")) >= 3)
r = riya.call("POST", "work/assignments/bulk-status", {"ids": ids, "status": "In Review"})
check("employee bulk submit for review", r["done"] == 3)
riya.call("POST", "work/assignments/bulk-status", {"ids": ids, "status": "Approved"}, expect=403)
# tally ON: close -> auto invoice -> posted to tally
ca.call("PUT", "admin/settings", {"tally_url": f"http://127.0.0.1:{TPORT}", "tally_company": "CA Task Mitra Demo"})
n0 = len(ca.call("GET", "finance/invoices"))
r = ca.call("POST", "work/assignments/bulk-status", {"ids": [ids[0]], "status": "Closed"})
check("bulk approve & close", r["done"] == 1)
invs = ca.call("GET", "finance/invoices")
check("closing auto-creates invoice", len(invs) == n0 + 1 and invs[0]["descr"].startswith("Professional fees"))
q = ca.call("GET", "tally/queue")
check("auto invoice posted to Tally immediately", any(x["ref"] == invs[0]["no"] and x["status"] == "Posted" for x in q))
# tally OFF: entry stays pending, then goes with next bill
ca.call("PUT", "admin/settings", {"tally_url": "http://127.0.0.1:9"})
ca.call("POST", "work/assignments/bulk-status", {"ids": [ids[1]], "status": "Closed"})
inv_b = ca.call("GET", "finance/invoices")[0]
q = ca.call("GET", "tally/queue")
check("Tally off: bill created, entry stays pending", inv_b["amount"] == 777 and any(x["ref"] == inv_b["no"] and x["status"] != "Posted" for x in q))
ca.call("PUT", "admin/settings", {"tally_url": f"http://127.0.0.1:{TPORT}"})
ca.call("POST", "work/assignments/bulk-status", {"ids": [ids[2]], "status": "Closed"})
q = ca.call("GET", "tally/queue")
check("next bill flushes all pending Tally entries", not [x for x in q if x["status"] != "Posted"])
check("auto-billed work is not left in billing queue", not {x["id"] for x in ca.call("GET", "finance/billing-queue")} & set(ids))
# dashboards
d = ca.call("GET", "work/dashboard")
check("CA dashboard: employee-wise work + totals", d["by_employee"] and "pending" in d and "closed" in d)
dr = riya.call("GET", "work/dashboard")
check("employee dashboard scoped to self", dr["total"] <= d["total"] and "by_employee" not in dr)
check("who reached / yet to come", any(x["state"] == "Yet to come" for x in ca.call("GET", "employee/today")))
# announcements
ca.call("POST", "comms/announcements", {"title": "Office closed Friday", "body": "Diwali"})
ca.call("POST", "comms/announcements", {"title": "Riya only", "body": "Finish GSTR", "to_user": users["riya"]})
check("employee sees firm + own announcements only", {x["title"] for x in riya.call("GET", "comms/announcements")} >= {"Office closed Friday", "Riya only"}
      and "Riya only" not in {x["title"] for x in amit.call("GET", "comms/announcements")})
riya.call("POST", "comms/announcements", {"title": "x"}, expect=403)
# skills approval
sk = riya.call("POST", "skills/skills", {"name": "Riya skill", "instructions": "do x"})
check("employee skill goes to pending", sk["status"] == "pending")
riya.call("PUT", f"skills/skills/{sk['id']}", {"name": "n", "instructions": "i"}, expect=403)
riya.call("POST", f"skills/skills/{sk['id']}/run", {}, expect=404)
ca.call("POST", f"skills/skills/{sk['id']}/approve")
check("CA approves skill", next(x for x in ca.call("GET", "skills/skills") if x["id"] == sk["id"])["status"] == "approved")
# email sign-off
dm = riya.call("POST", "comms/drafts/missing-docs", {"assignment_id": ids[0], "docs": ["Bank statement"]}) if False else None
a_open = next(x for x in riya.call("GET", "work/assignments") if x["status"] not in ("Approved", "Closed"))
dr = riya.call("POST", "comms/drafts/missing-docs", {"assignment_id": a_open["id"], "docs": ["Bank statement"]})
body = next(x for x in ca.call("GET", "comms/drafts") if x["id"] == dr["id"])["body"]
check("e-mail signed with firm name only", body.rstrip().endswith("Regards,\nTest & Co") and "Riya" not in body.split("Regards")[1])
# imports
csv_c = "name,ctype,email\nImport One,Company,a@x.com\nImport Two,Trust,b@x.com\n"
check("client CSV import", ca.call("POST", "admin/import/clients", {"csv": csv_c})["imported"] == 2)
check("employee CSV import (CA only)", ca.call("POST", "admin/import/employees", {"csv": "username,name,password\nnewemp,New Emp,Pass@123\n"})["imported"] == 1)
riya.call("POST", "admin/import/employees", {"csv": "username,name,password\nx,X,Pass@123\n"}, expect=403)
r = ca.call("POST", "admin/import/assignments", {"csv": "client,service,title,due_date,status,employee,fee,remarks\nImport One,GST Return Filing,Old pending GSTR,2026-09-20,In Progress,newemp,900,carried over\nNobody,,Bad row,,,,,\n"})
check("assignment CSV import (+reports bad row)", r["imported"] == 1 and len(r["errors"]) == 1)
r = ca.call("POST", "compliance/applicability/import", {"csv": "client,compliance,employee\nImport One,GSTR-3B,newemp\nImport Two,NOPE,\n"})
check("applicability CSV import", r["imported"] == 1 and len(r["errors"]) == 1)
check("CSV export has BOM for Excel", ca.call("GET", "admin/export/invoices").startswith(b"\xef\xbb\xbf"))
check("export includes fee + remarks columns", b"remarks" in ca.call("GET", "admin/export/assignments"))
# employee compliance calendar scoped
cal_all = ca.call("GET", "compliance/calendar?days=400"); cal_me = riya.call("GET", "compliance/calendar?days=400")
check("employee calendar only own work", all(x["employee"] == "Riya Shah" for x in cal_me) and len(cal_me) <= len(cal_all))

bad = [n for n, ok in RESULTS if not ok]
print(f"\n{len(RESULTS) - len(bad)}/{len(RESULTS)} checks passed")
sys.exit(1 if bad else 0)
