"""
Adding mutual-fund schemes: AMFI search, validation, NAV-history rule, use in transactions and CAS, edit and removal.

Runs the real bridge in-process with everything it writes redirected to a temporary folder (as bridge_check.py).
Deterministic and offline: AMFI's scheme list comes from the cached NAVAll.txt, and the NAV history of the two test
codes is synthetic (patched into sources.mf_nav_history); every other code uses the real cache.

Usage:  python verify/scheme_check.py
"""
import http.client
import json
import os
import shutil
import sys
import tempfile
import threading
import uuid
from datetime import date, timedelta
from http.server import ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TMP = Path(tempfile.mkdtemp(prefix="lt_scheme_check_"))
os.environ["LOOKTHROUGH_USER_DIR"] = str(TMP / "user")
sys.path[:0] = [str(ROOT / "bridge"), str(ROOT / "verify")]
import build_dataset  # noqa: E402
import cas_fixtures as CF  # noqa: E402
import contract_note_fixtures as CNF  # noqa: E402
import lookthrough_bridge as B  # noqa: E402
import sources as S  # noqa: E402

results = []


def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS  " if ok else "FAIL  ") + name + ("" if ok else f"   -> {detail}"))


QUANT_D, QUANT_R, QUANT_IDCW, QUANT_ISIN = "120828", "100177", "120827", "INF966L01689"
SBI_SMALL_D = "125497"
_real = S.mf_nav_history


def fake_history(code, refresh=False):
    if code not in (QUANT_D, QUANT_R, SBI_SMALL_D):
        return _real(code, refresh)
    days = 1200 if code != SBI_SMALL_D else 150  # SBI Small Cap made "too new" (about 5 months) for the 13-month rule
    start, base = date(2026, 8, 31) - timedelta(days=days), (250.0 if code == QUANT_D else 230.0)
    data = [{"date": (start + timedelta(days=i)).strftime("%d-%m-%Y"), "nav": f"{base * (1 + 0.0004 * i):.4f}"} for i in range(days + 1)]
    return {"meta": {"scheme_name": code}, "data": list(reversed(data))}


S.mf_nav_history = fake_history

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
        c = http.client.HTTPConnection("127.0.0.1", PORT, timeout=180)
        h = {"Host": f"localhost:{PORT}"}
        if self.cookie:
            h["Cookie"] = self.cookie
        data = raw
        if body is not None:
            data, h["Content-Type"] = json.dumps(body).encode(), "application/json"
        if ctype:
            h["Content-Type"] = ctype
        c.request(method, path, body=data, headers=h)
        r = c.getresponse()
        out = r.read()
        sc = r.getheader("Set-Cookie")
        if sc:
            self.cookie = sc.split(";")[0]
        return r.status, (json.loads(out) if out else {})

    def cas(self, pdf, member):
        bnd = uuid.uuid4().hex
        body = (f"--{bnd}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"cas.pdf\"\r\nContent-Type: application/pdf\r\n\r\n".encode() + pdf
                + f"\r\n--{bnd}\r\nContent-Disposition: form-data; name=\"member_id\"\r\n\r\n{member}\r\n--{bnd}--\r\n".encode())
        return self.req("POST", "/api/cas", raw=body, ctype=f"multipart/form-data; boundary={bnd}")


def ds():
    return json.loads((TMP / "live" / "dataset.json").read_text(encoding="utf-8"))


admin, viewer = Client(), Client()
admin.req("POST", "/api/setup", {"user": "cio", "password": "Look2026"})
admin.req("POST", "/api/users", {"action": "create", "user": "view1", "password": "View2026", "role": "viewer"})
viewer.req("POST", "/api/login", {"user": "view1", "password": "View2026"})
_, j = admin.req("POST", "/api/entities", {"action": "add", "name": "Scheme Test Client", "type": "Individual", "relationship": "Test"})
MID = j["record"]["member_id"]

# ------------------------------------------------------------------ search
st, _ = viewer.req("GET", "/api/amfi-search?q=quant+small+cap")
check("Search: a viewer cannot search to add schemes (analyst role)", st == 403, st)
st, j = admin.req("GET", "/api/amfi-search?q=qu")
check("Search: fewer than 3 characters is refused with guidance", st == 400 and "at least 3" in j["error"], (st, j))
st, j = admin.req("GET", "/api/amfi-search?q=quant+small+cap")
g = next((x for x in j.get("results", []) if x["direct"]["code"] == QUANT_D), None)
check("Search: finds the Direct and Regular Growth codes as one pair (IDCW options left out)",
      st == 200 and g and g["regular"]["code"] == QUANT_R and g["direct"]["isin"] == QUANT_ISIN
      and not any("idcw" in x["direct"]["name"].lower() for x in j["results"]), g)
_, j = admin.req("GET", "/api/amfi-search?q=INF879O01027")
check("Search: by ISIN; an already-tracked scheme is marked with its id", j["results"] and j["results"][0]["tracked_as"] == "S05", j.get("results", [])[:1])
_, j = admin.req("GET", "/api/amfi-search?q=hdfc+liquid")
check("Search: a liquid fund is marked as not equity-oriented", j["results"] and all(x["not_equity"] for x in j["results"]), [x["direct"]["name"] for x in j["results"]][:3])

# ------------------------------------------------------------------ validation
good = {"action": "add", "amfi_code_direct": QUANT_D, "amfi_code_regular": QUANT_R, "name": "Quant Small Cap Fund", "category": "Small Cap", "benchmark": "NIFTYSMALL"}


def add(**kw):
    return admin.req("POST", "/api/schemes", {**good, **kw})


liquid = next(x for x in S.amfi_navall() if "hdfc liquid fund - direct plan - growth" in x["name"].lower())
st, j = add(amfi_code_direct=liquid["code"], amfi_code_regular="", name="HDFC Liquid")
check("Add: a liquid (debt) fund is refused with the tax reason", st == 400 and "equity-oriented" in j["error"], (st, j))
st, j = add(amfi_code_direct=QUANT_IDCW)
check("Add: an IDCW option is refused (Growth only)", st == 400 and "not a Growth option" in j["error"], (st, j))
st, j = add(amfi_code_regular=QUANT_D)
check("Add: a Direct code in the Regular slot is refused", st == 400 and "not the Regular plan" in j["error"], (st, j))
st, j = add(amfi_code_direct="120586", amfi_code_regular="", name="Duplicate")
check("Add: a scheme already tracked is refused with its id", st == 400 and "already tracked as S01" in j["error"], (st, j))
st, j = add(category="Liquid")
check("Add: a category outside the equity list is refused", st == 400 and "category" in j["error"], (st, j))
st, j = add(benchmark="SP500")
check("Add: an unknown benchmark is refused", st == 400 and "benchmark" in j["error"], (st, j))
st, j = add(amfi_code_direct=SBI_SMALL_D, amfi_code_regular="", name="SBI Small Cap")
check("Add: a scheme with under 13 month-end NAVs is refused with the reason", st == 400 and "at least 13" in j["error"], (st, j))
st, _ = viewer.req("POST", "/api/schemes", good)
check("Add: a viewer cannot add schemes", st == 403, st)
check("Add: nothing was saved by the refused attempts", not ds()["schemes"][12:], [s["scheme_id"] for s in ds()["schemes"][12:]])

# ------------------------------------------------------------------ add and use
st, j = add()
check("Add: a valid equity scheme is added as S13", st == 200 and j["record"]["scheme_id"] == "S13", (st, j))
s13 = next((s for s in ds()["schemes"] if s["scheme_id"] == "S13"), None)
check("Add: it is in the rebuilt dataset with both plans, its ISINs and source 'user'",
      s13 and s13["source"] == "user" and s13["has_regular"] and s13["isin_direct"] == QUANT_ISIN and s13["amfi_code"] == QUANT_D, s13)
navs = [n for n in ds()["nav_history"] if n["scheme_id"] == "S13"]
check("Add: its month-end NAV history (Direct and Regular) is in the dataset", {n["plan"] for n in navs} == {"Direct", "Regular"} and len(navs) >= 26, len(navs))
st, j = add(name="Another name")
check("Add: the same scheme cannot be added twice", st == 400 and "already tracked as S13" in j["error"], (st, j))

_, pdf = None, None
items = []
CF._folio(items, 560, "7788990011", ["Folio No: 7788990011", "Quant Small Cap Fund - Direct Plan - Growth Option - ISIN: INF966L01689 Registrar : KFINTECH"],
          0.0, [("12-Jun-2026", "Purchase", 19999.00, 262.40, 1.00)])
cas_pdf = CNF._pdf([[(40, 580, "Consolidated Account Statement"), (40, 570, "01-Jun-2026 To 31-Aug-2026")] + items])
st, prev = admin.cas(cas_pdf, MID)
fo = prev["folios"][0] if st == 200 else {}
check("CAS: once added, a CAS folio of the scheme matches it by ISIN (S13 Direct)", fo.get("scheme_id") == "S13" and fo.get("plan") == "Direct", fo)

st, j = admin.req("POST", "/api/transactions", {"action": "add", "member_id": MID, "asset_type": "MF", "instrument": "S13", "plan": "Direct",
                                                  "txn_type": "Purchase", "date": "2026-06-12", "units": 76.216, "price": 262.4})
check("Use: a transaction can be recorded in the new scheme", st == 200, (st, j))
TXN = j.get("record", {}).get("txn_id")
st, j = admin.req("POST", "/api/schemes", {"action": "delete", "scheme_id": "S13"})
check("Remove: refused while a transaction uses the scheme", st == 400 and "delete them first" in j["error"], (st, j))
st, j = admin.req("POST", "/api/schemes", {"action": "update", "scheme_id": "S13", "category": "Flexi Cap", "benchmark": "NIFTY500"})
check("Edit: category and benchmark of an added scheme can change", st == 200 and next(s for s in ds()["schemes"] if s["scheme_id"] == "S13")["category"] == "Flexi Cap", (st, j))
st, j = admin.req("POST", "/api/schemes", {"action": "update", "scheme_id": "S13", "category": "Gilt"})
check("Edit: an invalid category is refused", st == 400, (st, j))
st, j = admin.req("POST", "/api/schemes", {"action": "update", "scheme_id": "S01", "category": "Flexi Cap"})
check("Edit: a configured scheme is read-only", st == 400 and "not a scheme you added" in j["error"], (st, j))
st, j = admin.req("POST", "/api/schemes", {"action": "delete", "scheme_id": "S01"})
check("Remove: a configured scheme cannot be removed", st == 400 and "not a scheme you added" in j["error"], (st, j))
admin.req("POST", "/api/transactions", {"action": "delete", "txn_id": TXN})
st, j = admin.req("POST", "/api/schemes", {"action": "delete", "scheme_id": "S13"})
check("Remove: once unused, the added scheme is removed and leaves the dataset", st == 200 and not any(s["scheme_id"] == "S13" for s in ds()["schemes"]), (st, j))
audit_raw = (TMP / "user" / "audit.jsonl").read_text(encoding="utf-8")
check("Audit: add, edit and removal are recorded", all(a in audit_raw for a in ('"SCHEME_ADD"', '"SCHEME_EDIT"', '"SCHEME_DELETE"')))
real = json.loads((ROOT / "data" / "config" / "schemes.json").read_text(encoding="utf-8"))
check("The committed scheme configuration is untouched (12 schemes)", len(real) == 12)

httpd.shutdown()
S.mf_nav_history = _real
shutil.rmtree(TMP, ignore_errors=True)
n = sum(results)
line = f"{n}/{len(results)} scheme checks passed"
print("\n" + line)
(ROOT / "verify" / "scheme_result.txt").write_text(line + "\n", encoding="utf-8")
sys.exit(0 if all(results) else 1)
