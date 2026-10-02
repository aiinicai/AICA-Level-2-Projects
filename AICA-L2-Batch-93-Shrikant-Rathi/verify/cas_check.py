"""
Mutual-fund CAS import: the PDF reader, and the import through a real bridge.

The statement is fictitious (verify/cas_fixtures.py: made-up investor and folios, real scheme ISINs, realistic NAVs),
built as a PDF at run time. The bridge runs with everything it writes redirected to a temporary folder, as in
bridge_check.py; data/user, data/live and app/ are never written.

Usage:  python verify/cas_check.py
"""
import http.client
import json
import os
import shutil
import sys
import tempfile
import threading
import uuid
from http.server import ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TMP = Path(tempfile.mkdtemp(prefix="lt_cas_check_"))
os.environ["LOOKTHROUGH_USER_DIR"] = str(TMP / "user")
sys.path[:0] = [str(ROOT / "bridge"), str(ROOT / "verify")]
import build_dataset  # noqa: E402
import cas_fixtures as F  # noqa: E402
import cas_statement as C  # noqa: E402
import contract_note_fixtures as CNF  # noqa: E402
import lookthrough_bridge as B  # noqa: E402

results = []


def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS  " if ok else "FAIL  ") + name + ("" if ok else f"   -> {detail}"))


DS = json.loads((ROOT / "data" / "live" / "dataset.json").read_text(encoding="utf-8"))


def parse(pdf, pw=""):
    return C.parse(pdf, pw, DS["schemes"], DS["meta"]["as_on"], ref_navs=lambda s, p, d: B.month_end_navs(DS, s, p, d))


def refused(pdf, pw, words):
    try:
        parse(pdf, pw)
        return False, "accepted"
    except C.CasError as e:
        return words.lower() in str(e).lower(), str(e)


# ------------------------------------------------------------------ reader
pdf, close = F.build()
r = parse(pdf)
fo = {f["scheme_id"] or "X": f for f in r["folios"]}
check("4 folios and 9 transactions read; statement period read", r["summary"]["folios"] == 4 and r["summary"]["transactions"] == 9
      and r["period"] == {"from": "2026-04-01", "to": "2026-08-31"}, (r["summary"], r["period"]))
check("Every folio's unit chain reconciles from opening to closing balance", r["summary"]["reconciled"] == 4 and all(f["reconciled"] for f in r["folios"]))
check("Closing balances read exactly", all(abs(fo[k]["closing"] - v) < 1e-9 for k, v in close.items()), {k: fo[k]["closing"] for k in close})
check("Scheme and plan from ISIN: ICICI Large Cap Direct, Parag Parikh Regular, SBI Contra Direct",
      (fo["S01"]["plan"], fo["S05"]["plan"], fo["S12"]["plan"]) == ("Direct", "Regular", "Direct"))
check("KFintech layout (ISIN on the scheme line) and CAMS layout (ISIN below) both named correctly",
      fo["S05"]["name"] == "Parag Parikh Flexi Cap Fund - Regular Plan - Growth" and fo["S01"]["name"] == "ICICI Prudential Large Cap Fund - Direct Plan - Growth",
      (fo["S05"]["name"], fo["S01"]["name"]))
check("Types: SIP instalments, redemption and switch-out as Sell, lump sum as Purchase",
      [t["txn_type"] for t in fo["S01"]["txns"]] == ["SIP", "SIP", "SIP", "Sell", "SIP"] and [t["txn_type"] for t in fo["S05"]["txns"]] == ["Purchase", "Sell"])
t0 = fo["S01"]["txns"][0]
check("Stamp duty attached to its purchase and added to cost: (9,999.50 + 0.50) / units",
      t0["charges"] == {"stamp": 0.5} and abs(t0["price_with_charges"] - round(10000.0 / t0["units"], 4)) < 1e-9, t0)
s1 = fo["S01"]["txns"][3]
check("Redemption recorded at NAV (no stamp duty; STT not deducted)", s1["price_with_charges"] == 121.0 and s1["units"] == 30.0, s1)
check("A scheme the app does not track is flagged and cannot be matched", fo["X"]["scheme_id"] is None and any("not one of the schemes" in x for x in fo["X"]["issues"]))
check("An opening balance (history before the statement) is flagged", any("Opening balance 100.000" in x for x in fo["S12"]["issues"]), fo["S12"]["issues"])
check("A clean statement raises no transaction issues", all(not t["issues"] for f in r["folios"] for t in f["txns"]), [t["issues"] for f in r["folios"] for t in f["txns"]])

bad = parse(F.build(tamper=True)[0])
bf = next(f for f in bad["folios"] if f["scheme_id"] == "S01")
check("A misread or altered balance breaks the unit chain and is flagged", not bf["reconciled"] and any("does not follow" in x for t in bf["txns"] for x in t["issues"]), bf)
orig = list(F.F1)
F.F1[0] = ("10-Apr-2026", "Systematic Investment Purchase - Instalment No 1", 9999.50, 1152.0, 0.50)
odd = parse(F.build()[0])
F.F1[:] = orig
check("A NAV far from the scheme's month-end NAVs is flagged (wrong scheme or plan)",
      any("away from the month-end NAV" in x for x in next(f for f in odd["folios"] if f["scheme_id"] == "S01")["txns"][0]["issues"]))
mism = CNF._pdf([[(40, 570, "Consolidated Account Statement"), (40, 550, "Folio No: 1"), (40, 539, "X Fund - Direct Plan - Growth - ISIN: INF109K016L0"),
                  (40, 528, "Opening Unit Balance: 0.000"), (40, 517, "10-Apr-2026   Purchase   10,000.00   50.000   115.2000   50.000"),
                  (40, 506, "Closing Unit Balance: 50.000")]])
mt = parse(mism)["folios"][0]["txns"][0]
check("Units x NAV that does not equal the amount is flagged", any("does not equal the amount" in x for x in mt["issues"]), mt)
enc = F.encrypted(pdf, F.PASSWORD)
ok, why = refused(enc, "", "password-protected")
check("Password-protected CAS without a password: asks for it", ok, why)
ok, why = refused(enc, "nope", "not correct")
check("Wrong password: refused", ok, why)
check("Right password: same statement", parse(enc, F.PASSWORD)["summary"] == r["summary"])
ok, why = refused(F.summary_only(), "", "summary CAS")
check("A summary CAS (no transactions) is refused with what to request instead", ok, why)
ok, why = refused(CNF.layout_a()[0], "", "No mutual-fund folios")
check("A contract note uploaded as a CAS is refused", ok, why)

# ------------------------------------------------------------------ through the bridge
(TMP / "live").mkdir()
shutil.copy(ROOT / "data" / "live" / "dataset.json", TMP / "live" / "dataset.json")
for mod in (build_dataset, B):
    mod.LIVE, mod.APP_OUT = TMP / "live", TMP / "app" / "LookThrough.html"
build_dataset.build(fetch=False)
httpd = ThreadingHTTPServer(("127.0.0.1", 0), B.Handler)
PORT = httpd.server_address[1]
threading.Thread(target=httpd.serve_forever, daemon=True).start()


class Client:
    def __init__(self):
        self.cookie = None

    def req(self, method, path, body=None, raw=None, ctype=None):
        c = http.client.HTTPConnection("127.0.0.1", PORT, timeout=120)
        h = {"Host": f"localhost:{PORT}"}
        if self.cookie:
            h["Cookie"] = self.cookie
        data = raw
        if body is not None:
            data, h["Content-Type"] = json.dumps(body).encode(), "application/json"
        if ctype:
            h["Content-Type"] = ctype
        c.request(method, path, body=data, headers=h)
        resp = c.getresponse()
        out = resp.read()
        sc = resp.getheader("Set-Cookie")
        if sc:
            self.cookie = sc.split(";")[0]
        return resp.status, (json.loads(out) if out else {})

    def upload(self, pdf, password="", member="", name="cas.pdf"):
        bnd = uuid.uuid4().hex
        parts = [f"--{bnd}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{name}\"\r\nContent-Type: application/pdf\r\n\r\n".encode() + pdf + b"\r\n"]
        for k, v in (("password", password), ("member_id", member)):
            parts.append(f"--{bnd}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n".encode())
        parts.append(f"--{bnd}--\r\n".encode())
        return self.req("POST", "/api/cas", raw=b"".join(parts), ctype=f"multipart/form-data; boundary={bnd}")


def rows_of(prev, member, pick):
    return [{"member_id": member, "instrument": f["scheme_id"], "plan": f["plan"], "txn_type": t["txn_type"], "date": t["date"], "units": t["units"],
             "price": t["price_with_charges"], "folio": f["folio"]} for f in prev["folios"] if pick(f) for t in f["txns"]]


def user_txns():
    return json.loads((TMP / "user" / "ledger.json").read_text(encoding="utf-8"))["transactions"]


admin, viewer = Client(), Client()
admin.req("POST", "/api/setup", {"user": "cio", "password": "Look2026"})
admin.req("POST", "/api/users", {"action": "create", "user": "view1", "password": "View2026", "role": "viewer"})
viewer.req("POST", "/api/login", {"user": "view1", "password": "View2026"})
_, j = admin.req("POST", "/api/entities", {"action": "add", "name": "CAS Test Client", "type": "Individual", "relationship": "Test"})
MID = j["record"]["member_id"]

st, j = viewer.upload(pdf, member=MID)
check("Bridge: a viewer cannot read a CAS (analyst role needed)", st == 403, (st, j))
st, prev = admin.upload(enc, F.PASSWORD, MID, "cas_aug.pdf")
check("Bridge: encrypted CAS read with its password; preview for the chosen entity", st == 200 and prev["member_id"] == MID and prev["summary"]["folios"] == 4, (st, prev.get("error")))
check("Bridge: reading a CAS saves nothing and is audited without the password",
      not json.loads((TMP / "user" / "ledger.json").read_text(encoding="utf-8"))["transactions"]
      and "CAS_READ" in (TMP / "user" / "audit.jsonl").read_text(encoding="utf-8") and F.PASSWORD not in (TMP / "user" / "audit.jsonl").read_text(encoding="utf-8"))

tracked_no_opening = rows_of(prev, MID, lambda f: f["scheme_id"] and not f["opening"])
st, j = admin.req("POST", "/api/transactions", {"action": "import", "kind": "cas", "trades": tracked_no_opening, "ref": {"sha256": prev["sha256"], "file": "cas_aug.pdf"}})
check("Bridge: 7 transactions (two tracked folios) recorded together", st == 200 and len(j["record"]) == 7, (st, j))
ds_now = json.loads((TMP / "live" / "dataset.json").read_text(encoding="utf-8"))
units = {}
for t in ds_now["transactions"]:
    if t["member_id"] == MID:
        k = (t["instrument"], t["plan"])
        units[k] = round(units.get(k, 0) + (-t["units"] if t["txn_type"] == "Sell" else t["units"]), 3)
check("Bridge: resulting holdings equal the statement's closing balances (S01 Direct, S05 Regular)",
      units == {("S01", "Direct"): close["S01"], ("S05", "Regular"): close["S05"]}, units)
check("Bridge: each transaction carries its folio", all(t.get("note", "").startswith("CAS, folio ") for t in ds_now["transactions"] if t["member_id"] == MID))

sbi = rows_of(prev, MID, lambda f: f["scheme_id"] == "S12")
n_before = len(user_txns())
st, j = admin.req("POST", "/api/transactions", {"action": "import", "kind": "cas", "trades": sbi, "ref": {"sha256": prev["sha256"]}})
check("Bridge: a sale of units bought before the statement (not recorded) is refused, nothing saved",
      st == 400 and "larger than the units held" in j["error"] and len(user_txns()) == n_before, (st, j))

st, prev2 = admin.upload(pdf, "", MID, "cas_aug_again.pdf")
dups = [t["duplicate_of"] for f in prev2["folios"] for t in f["txns"] if f["scheme_id"] and not f["opening"]]
check("Bridge: re-reading an overlapping statement marks the 7 recorded rows as already recorded", len(dups) == 7 and all(dups), dups)
st, j = admin.req("POST", "/api/transactions", {"action": "import", "kind": "cas", "trades": tracked_no_opening[:1], "ref": {"sha256": prev2["sha256"]}})
check("Bridge: importing an already-recorded transaction is refused", st == 400 and "already recorded as U" in j["error"], (st, j))
twice = tracked_no_opening[:1] * 2
twice[0] = dict(twice[0], date="2026-04-09")
twice[1] = dict(twice[1], date="2026-04-09")
st, j = admin.req("POST", "/api/transactions", {"action": "import", "kind": "cas", "trades": twice, "ref": {"sha256": prev2["sha256"]}})
check("Bridge: the same transaction twice within one import is refused", st == 400 and "already recorded" in j["error"], (st, j))
st, j = admin.req("POST", "/api/transactions", {"action": "import", "kind": "cas", "trades": [dict(tracked_no_opening[0], instrument="S99")], "ref": {"sha256": prev2["sha256"]}})
check("Bridge: a scheme the app does not track is refused", st == 400 and "not a configured scheme" in j["error"], (st, j))
st, j = admin.upload(CNF.layout_a()[0], "", MID)
check("Bridge: a contract note sent to the CAS reader is refused with a reason", st == 400 and "No mutual-fund folios" in j["error"], (st, j))
audit_raw = (TMP / "user" / "audit.jsonl").read_text(encoding="utf-8")
check("Bridge: the import is audited as a CAS statement with the file hash", '"TXN_IMPORT"' in audit_raw and '"CAS statement"' in audit_raw and prev["sha256"] in audit_raw)

httpd.shutdown()
shutil.rmtree(TMP, ignore_errors=True)
n = sum(results)
line = f"{n}/{len(results)} CAS checks passed"
print("\n" + line)
(ROOT / "verify" / "cas_result.txt").write_text(line + "\n", encoding="utf-8")
sys.exit(0 if all(results) else 1)
