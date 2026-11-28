"""Offline tests with a fake GST portal (no Chrome / Selenium / internet needed).

Run:  python tests/test_offline.py
"""
import os
import shutil
import sys
import tempfile
import threading
import time
import types

SRC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORK = tempfile.mkdtemp(prefix="gsttest_")
for f in os.listdir(SRC):
    if f.endswith(".py"):
        shutil.copy(os.path.join(SRC, f), WORK)
sys.path.insert(0, WORK)
os.chdir(WORK)

from datetime import date

import naming as N

# ---------------------------------------------------------------- naming
assert N.fy_label(2026, 10) == "2026-27"
assert N.fy_label(2027, 2) == "2026-27"
assert N.quarter_no(4) == 1 and N.quarter_no(12) == 3 and N.quarter_no(1) == 4
assert N.quarter_label(2026, 11) == "Q3 Oct-Dec 2026"
assert N.quarter_label(2027, 2) == "Q4 Jan-Mar 2027"
assert N.clean_name("M/s. ABC Enterprises") == "ABC Enterprises", N.clean_name("M/s. ABC Enterprises")
assert N.clean_name('A/B: "C"?') == "A B C"
assert N.clean_name("Patel & Sons") == "Patel & Sons"
assert N.build_filename("ABC Enterprises", "GSTR2B", "Oct 2026", "XLSX") == "ABC Enterprises GSTR2B Oct 2026.xlsx"
assert N.send_by_date(2026, 10, 18) == date(2026, 11, 18)
assert N.send_by_date(2026, 12, 18) == date(2027, 1, 18)
assert N.is_period_available(2026, 10, date(2026, 11, 26))
assert not N.is_period_available(2026, 11, date(2026, 11, 26))
print("naming ok")

# ---------------------------------------------------------------- clients
import openpyxl
import clients as cl

xl = os.path.join(WORK, "clients.xlsx")
cl.create_template(xl)
wb = openpyxl.load_workbook(xl)
ws = wb.active
rows = [
    ["27AAGCA4521K1Z3", "Agarwal Steel Private Limited", "Agarwal Steel", "a@x.in", "agarwal", "Ps@1#x$z", "Monthly", ""],
    ["24AABFB7810L1Z6", "Bhavani Textiles", "", "b@x.in, b2@x.in", "bhav", " Sp@ce123", "", ""],
    ["27AAPFM9021Q1Z8", "Mehta Enterprises", "", "m@x.in", "mehta", 123456789, "", ""],
    ["27BCGPS5512R1Z4", "M/s Om Sai Agencies", "", "", "omsai", "Om@2026!", "Quarterly", "01-Jan-2026"],
    ["24AAHFP6634C1Z9", "Patel & Sons", "", "p@x.in", "patel", "Wr0ng#pwd", "", ""],
    ["27AAKFR2208N1Z2", "Rathi Pharma", "", "r@x.in", "rathi", "Unkn0wn#1", "", ""],
]
for r in rows:
    ws.append(r)
ws.cell(3, 6).number_format = "General"
wb.save(xl)

cs = cl.load_clients(xl)
by = {c.gstin: c for c in cs}
assert by["27AAGCA4521K1Z3"].display_name == "Agarwal Steel"
assert by["27AAGCA4521K1Z3"].password == "Ps@1#x$z"
assert by["24AABFB7810L1Z6"].password == " Sp@ce123"         # not stripped
assert any("space" in m for _, m in by["24AABFB7810L1Z6"].issues)
assert by["24AABFB7810L1Z6"].emails() == ["b@x.in", "b2@x.in"]
assert by["27AAPFM9021Q1Z8"].has_error                       # number password
assert by["27BCGPS5512R1Z4"].quarterly
assert any("Email" in m for _, m in by["27BCGPS5512R1Z4"].issues)
assert by["27BCGPS5512R1Z4"].pwd_age_days() > 60
print("load ok:", [(c.gstin[-4:], c.issues) for c in cs])

cl.save_client(xl, "24AABFB7810L1Z6", {"gstin": "24AABFB7810L1Z6", "name": "Bhavani Textiles",
                                       "trade_name": "Bhavani Tex", "login_id": "bhav",
                                       "password": "N3w=+pass", "email": "b@x.in", "filing": "Monthly"})
cs = cl.load_clients(xl)
b = next(c for c in cs if c.gstin == "24AABFB7810L1Z6")
assert b.password == "N3w=+pass" and not b.has_error and b.trade_name == "Bhavani Tex"
assert b.pwd_updated == date.today().strftime("%d-%b-%Y")
cl.save_client(xl, None, {"gstin": "29ABCDE1234F1Z5", "name": "New Co", "login_id": "newco",
                          "password": "=Starts+eq", "email": "n@x.in"})
cs = cl.load_clients(xl)
n = next(c for c in cs if c.gstin == "29ABCDE1234F1Z5")
assert n.password == "=Starts+eq", n.password
try:
    cl.save_client(xl, None, {"gstin": "29ABCDE1234F1Z5", "name": "dup", "login_id": "x", "password": "y"})
    raise AssertionError("dup allowed")
except cl.ClientFileError:
    pass
print("save ok")

# ---------------------------------------------------------------- fake portal
SUBMITS = {}


class NotAvailable(Exception):
    pass


class PortalError(Exception):
    pass


BEHAVIOUR = {
    # gstin -> list of login results in order
    "27AAGCA4521K1Z3": ["captcha", "success"],
    "24AAHFP6634C1Z9": ["bad_credentials", "success"],
    "27AAKFR2208N1Z2": ["unknown", "success"],
    "24AABFB7810L1Z6": ["success"],
    "29ABCDE1234F1Z5": ["captcha", "captcha", "captcha", "success"],
    "27BCGPS5512R1Z4": ["success"],
}


class FakePortal:
    def __init__(self, cfg, dl, log=print):
        self.dl = dl
        self.client = None

    def start(self): pass
    def alive(self): return True
    def quit(self): pass
    def logout(self): pass
    def dismiss_popups(self): pass
    def refresh_captcha(self): pass
    def captcha_image_b64(self): return "AAAA"

    def open_login(self, c):
        self.client = c

    def submit_login(self, text):
        g = self.client.gstin
        SUBMITS[g] = SUBMITS.get(g, 0) + 1
        seq = BEHAVIOUR[g]
        return seq[min(SUBMITS[g] - 1, len(seq) - 1)]

    def snapshot(self): return set(os.listdir(self.dl))

    def new_files(self, before):
        return [os.path.join(self.dl, x) for x in sorted(set(os.listdir(self.dl)) - before)]

    def _make(self, name):
        p = os.path.join(self.dl, name)
        open(p, "w").write("x")
        return p

    def download_gstr2b(self, y, m, excel, json):
        out = []
        if excel: out.append(self._make(f"rand_{y}{m}.xlsx"))
        if json: out.append(self._make(f"rand_{y}{m}.json"))
        return out

    def download_gstr1(self, y, m):
        if self.client.gstin == "24AABFB7810L1Z6":
            raise PortalError("GSTR-1 VIEW button not found")
        return [self._make(f"g1_{y}{m}.pdf")]

    def download_gstr3b(self, y, m):
        raise NotAvailable("GSTR-3B not filed yet")


fake = types.ModuleType("portal")
fake.GSTPortal = FakePortal
fake.NotAvailable = NotAvailable
fake.PortalError = PortalError
sys.modules["portal"] = fake

import settings
import jobs
import blocked

cfg = settings.load()
cfg["browser"]["delay_between_clients"] = 0
save_root = os.path.join(WORK, "out")


def run_job(clients, periods, forms, responder):
    j = jobs.JobRunner(cfg, clients, periods, forms, save_root)
    j.start()
    while not j.finished:
        st = j.state()
        p = st["prompt"]
        if p:
            ans = responder(p, j)
            if ans:
                j.respond(p["id"], ans)
        time.sleep(0.05)
    return j.state()


def auto(p, j):
    if p["type"] == "captcha":
        return {"action": "submit", "text": "ABC123"}
    if p["type"] == "manual":
        # simulate the user downloading the file by hand in Chrome
        open(os.path.join(j.tmp_dir, "manual_dl.pdf"), "w").write("x")
        return None      # app should detect it automatically
    return None


cs = cl.load_clients(xl)
forms = {"GSTR2B": {"excel": True, "json": True}, "GSTR1": True, "GSTR3B": True}
st = run_job(cs, [(2026, 9), (2026, 10)], forms, auto)

rows = st["rows"]
def rows_of(g): return [r for r in rows if r["gstin"] == g]

# captcha wrong once then success
assert SUBMITS["27AAGCA4521K1Z3"] == 2
assert all(r["status"] in ("done", "notavail") for r in rows_of("27AAGCA4521K1Z3"))
# wrong password -> exactly one submit, blocked
assert SUBMITS["24AAHFP6634C1Z9"] == 1, SUBMITS
assert all(r["status"] == "blocked" for r in rows_of("24AAHFP6634C1Z9"))
# unclear result -> exactly one submit, blocked
assert SUBMITS["27AAKFR2208N1Z2"] == 1
assert all(r["status"] == "blocked" for r in rows_of("27AAKFR2208N1Z2"))
# number password -> never attempted
assert "27AAPFM9021Q1Z8" not in SUBMITS
assert all(r["status"] == "skipped" for r in rows_of("27AAPFM9021Q1Z8"))
# 3 wrong captchas -> stop, not blocked
assert SUBMITS["29ABCDE1234F1Z5"] == 3
assert all(r["status"] == "failed" for r in rows_of("29ABCDE1234F1Z5"))
# quarterly: GSTR-1/3B only once per quarter (Sep -> Q2, Oct -> Q3 => 2 each)
q = rows_of("27BCGPS5512R1Z4")
assert len([r for r in q if r["form"] == "GSTR1"]) == 2
assert {r["period"] for r in q if r["form"] == "GSTR1"} == {"Q2 Jul-Sep 2026", "Q3 Oct-Dec 2026"}
# manual fallback auto-detected for Bhavani GSTR-1
bh1 = [r for r in rows_of("24AABFB7810L1Z6") if r["form"] == "GSTR1"]
assert all(r["status"] == "done" for r in bh1), bh1
# files renamed
ag = os.path.join(save_root, "Agarwal Steel", "2026-27")
names = sorted(os.listdir(ag))
print(names)
assert "Agarwal Steel GSTR2B Oct 2026.xlsx" in names and "Agarwal Steel GSTR2B Oct 2026.json" in names
assert "Agarwal Steel GSTR1 Sep 2026.pdf" in names
assert os.path.exists(os.path.join(save_root, "Om Sai Agencies", "2026-27", "Om Sai Agencies GSTR1 Q3 Oct-Dec 2026.pdf"))
assert os.path.exists(os.path.join(save_root, "Bhavani Tex", "2026-27", "Bhavani Tex GSTR1 Oct 2026.pdf"))
print("job 1 ok", st["counts"])

# ---- second run: blocked clients must be skipped with ZERO new submits
before = dict(SUBMITS)
st2 = run_job(cs, [(2026, 10)], {"GSTR2B": {"excel": True, "json": False}}, auto)
assert SUBMITS["24AAHFP6634C1Z9"] == before["24AAHFP6634C1Z9"]
assert SUBMITS["27AAKFR2208N1Z2"] == before["27AAKFR2208N1Z2"]
assert all(r["status"] == "blocked" for r in st2["rows"] if r["gstin"] == "24AAHFP6634C1Z9")
print("job 2 ok (blocked skipped)")

# ---- password changed in Excel -> unblocked automatically
cl.save_client(xl, "24AAHFP6634C1Z9", {"gstin": "24AAHFP6634C1Z9", "password": "R1ght#pwd"})
cs = cl.load_clients(xl)
p = next(c for c in cs if c.gstin == "24AAHFP6634C1Z9")
assert blocked.check(p) is None
BEHAVIOUR["24AAHFP6634C1Z9"] = ["success"]
SUBMITS["24AAHFP6634C1Z9"] = 0
st3 = run_job([p], [(2026, 10)], {"GSTR2B": {"excel": True, "json": False}}, auto)
assert st3["rows"][0]["status"] == "done", st3["rows"]
print("job 3 ok (unblocked after password change)")

# ---- skip & stop from the captcha box
def skipper(p, j):
    return {"action": "skip"} if p["type"] == "captcha" else None
c1 = next(c for c in cs if c.gstin == "27AAGCA4521K1Z3")
SUBMITS.clear()
st4 = run_job([c1], [(2026, 10)], {"GSTR3B": True}, skipper)
assert st4["rows"][0]["status"] == "skipped" and not SUBMITS
print("skip ok")

# ---------------------------------------------------------------- email
import emailer
done_rows = [r for r in rows if r["gstin"] == "27AAGCA4521K1Z3" and r["status"] == "done"]
c = next(c for c in cs if c.gstin == "27AAGCA4521K1Z3")
m = emailer.build(cfg, c, done_rows)
assert "18-Nov-2026" in m["subject"], m["subject"]
assert "Agarwal Steel GSTR2B Oct 2026.xlsx" in m["body"]
assert m["to"] == "a@x.in"
r1 = [r for r in done_rows if r["form"] == "GSTR1"]
m2 = emailer.build(cfg, c, r1)
assert m2["subject"].startswith("Filed GST Return - GSTR-1"), m2["subject"]
print(m["subject"]); print(m2["subject"])
print("email ok")

# ---------------------------------------------------------------- api (no window)
import api as apimod
SUBMITS.clear()
BEHAVIOUR["27AAGCA4521K1Z3"] = ["success"]
cfg_path = settings.CONFIG_PATH
a = apimod.Api()
a._cfg["clients_excel"] = xl
a._cfg["download_folder"] = save_root
a._cfg["browser"]["delay_between_clients"] = 0
a._reload()
init = a.get_init()
assert init["ok"] and len(init["clients"]) == 7
assert "password" not in init["clients"][0]
_t = date.today()
r = a.start_job({"gstins": ["27AAGCA4521K1Z3"], "periods": [[2026, 10], [_t.year, _t.month]],
                 "forms": {"GSTR2B": {"excel": True, "json": True}, "GSTR1": False, "GSTR3B": False}})
assert r["ok"], r
while True:
    s = a.get_status()["job"]
    if s["prompt"]:
        a.respond_prompt(s["prompt"]["id"], {"action": "submit", "text": "X"})
    if not s["running"]:
        break
    time.sleep(0.05)
assert len(s["rows"]) == 1, "the current month must be dropped (not over yet)"
el = a.email_list()
assert el["items"] and el["items"][0]["status"] == "ready"
pv = a.email_preview("27AAGCA4521K1Z3")
assert pv["ok"] and pv["attachment_names"] == ["Agarwal Steel GSTR2B Oct 2026.xlsx", "Agarwal Steel GSTR2B Oct 2026.json"], pv
assert a.export_report()["ok"]
print("api ok")
print("\nALL TESTS PASSED")
