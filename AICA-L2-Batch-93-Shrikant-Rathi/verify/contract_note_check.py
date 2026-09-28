"""
Contract-note import: the PDF reader, and the import through a real bridge.

The notes are fictitious (verify/contract_note_fixtures.py) and built as real PDFs at run time, in two different
broker layouts plus a password-protected copy. The bridge runs with everything it writes redirected to a temporary
folder, exactly as in bridge_check.py; data/user, data/live and app/ are never written.

Usage:  python verify/contract_note_check.py
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
TMP = Path(tempfile.mkdtemp(prefix="lt_cn_check_"))
os.environ["LOOKTHROUGH_USER_DIR"] = str(TMP / "user")
sys.path[:0] = [str(ROOT / "bridge"), str(ROOT / "verify")]
import build_dataset  # noqa: E402
import contract_note as CN  # noqa: E402
import contract_note_fixtures as FX  # noqa: E402
import lookthrough_bridge as B  # noqa: E402

results = []


def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS  " if ok else "FAIL  ") + name + ("" if ok else f"   -> {detail}"))


DS = json.loads((ROOT / "data" / "live" / "dataset.json").read_text(encoding="utf-8"))
COS, AS_ON = DS["companies"], DS["meta"]["as_on"]
REF = lambda code, d: B.month_end_closes(DS, code, d)  # noqa: E731


def parse(pdf, pw=""):
    return CN.parse(pdf, pw, COS, AS_ON, ref_prices=REF)


def refused(pdf, pw, words):
    try:
        parse(pdf, pw)
        return False, "accepted"
    except CN.ContractNoteError as e:
        return words.lower() in str(e).lower(), str(e)


# ------------------------------------------------------------------ reader: layout A (ISIN, fills, net rate)
pdf_a, exp_a = FX.layout_a()
a = parse(pdf_a)
by = {t["instrument"]: t for t in a["trades"]}
check("A: three securities found; two HDFC Bank fills combined into one trade", len(a["trades"]) == 3 and by.get("HDFCBANK", {}).get("fills") == 2, a["trades"])
check("A: every company matched by ISIN", all(t["match"] == "ISIN" for t in a["trades"]), [t["match"] for t in a["trades"]])
check("A: HDFC Bank quantity 100 at the weighted gross rate 730.70 (not the net rate incl. brokerage)",
      by["HDFCBANK"]["qty"] == 100 and abs(by["HDFCBANK"]["rate"] - 730.70) < 1e-9, by["HDFCBANK"])
check("A: trade date and contract-note number read", a["trade_date"] == "2026-08-14" and a["contract_note_no"] == "DSL/2026/004512", (a["trade_date"], a["contract_note_no"]))
check("A: note reconciles to its net amount to the paisa", a["reconciliation"]["status"] == "reconciled" and a["reconciliation"]["difference"] == 0.0
      and abs(a["reconciliation"]["stated_net"] - exp_a["net"]) < 0.005, a["reconciliation"])
ch = exp_a["charges"]
check("A: every charge read, CGST and SGST summed", a["charges"] == {"brokerage": ch["brokerage"], "exchange": ch["exchange"], "sebi": ch["sebi"],
      "stamp": ch["stamp"], "stt": ch["stt"], "gst": round(ch["cgst"] + ch["sgst"], 2)}, a["charges"])
alloc = sum(t["charges"] for t in a["trades"])
check("A: charges allocated to cost exclude STT (sum = all charges - STT)", abs(alloc - (sum(a["charges"].values()) - a["charges"]["stt"])) <= 0.02, alloc)
check("A: buy price including charges = (value + allocated charges) / qty",
      all(abs(t["price_with_charges"] - (t["value"] + t["charges"]) / t["qty"]) < 1e-3 for t in a["trades"]))
check("A: no issues on a clean note", all(not t["issues"] for t in a["trades"]) and not a["warnings"], [t["issues"] for t in a["trades"]] + a["warnings"])

# ------------------------------------------------------------------ reader: layout B (names, words, a sale)
pdf_b, exp_b = FX.layout_b()
b = parse(pdf_b)
bb = {t["instrument"]: t for t in b["trades"]}
check("B: companies matched by name when no ISIN is printed", set(bb) == {"RELIANCE", "ICICIBANK"} and all(t["match"] == "name" for t in b["trades"]), bb.keys())
check("B: '20 x 1,290.00' read as 20 shares at Rs 1,290 (not 1,290 shares at Rs 20)", bb["RELIANCE"]["qty"] == 20 and bb["RELIANCE"]["rate"] == 1290.0, bb["RELIANCE"])
rf = {t["instrument"]: t for t in parse(FX.layout_b(rate_first=True)[0])["trades"]}
check("B: rate printed BEFORE quantity ('1,290.00  20') still read as 20 shares at Rs 1,290", rf["RELIANCE"]["qty"] == 20 and rf["RELIANCE"]["rate"] == 1290.0, rf.get("RELIANCE"))
check("B: sale recognised; sale price is net of its share of charges", bb["ICICIBANK"]["side"] == "Sell"
      and abs(bb["ICICIBANK"]["price_with_charges"] - (bb["ICICIBANK"]["value"] - bb["ICICIBANK"]["charges"]) / 10) < 1e-3, bb["ICICIBANK"])
check("B: dd-Mon-yyyy trade date and note number read", b["trade_date"] == "2026-08-21" and b["contract_note_no"] == "CN-889201", (b["trade_date"], b["contract_note_no"]))
check("B: buys - sells + charges reconciles to the stated net amount", b["reconciliation"]["status"] == "reconciled", b["reconciliation"])

# ------------------------------------------------------------------ reader: controls
bad = parse(FX.layout_b(net_override=exp_b["net"] + 100)[0])
check("A note whose net amount does not add up is flagged, with the difference", bad["reconciliation"]["status"] == "difference"
      and abs(bad["reconciliation"]["difference"] - 100) < 0.01 and any("does not reconcile" in w for w in bad["warnings"]), bad["reconciliation"])
odd = parse(FX.layout_b(trades=[("Reliance Industries Limited", "Buy", 20, 129.00)])[0])
check("A rate far from the month-end price is flagged (quantity/rate/company check)", any("away from the month-end price" in x for x in odd["trades"][0]["issues"]), odd["trades"][0]["issues"])
unk = parse(FX.layout_b(trades=[("Zyxwv Imaginary Industries Limited", "Buy", 5, 100.00)])[0])
check("An unknown company is left unmatched with an issue, never guessed", unk["trades"][0]["instrument"] is None and unk["trades"][0]["issues"], unk["trades"][0])

enc = FX.encrypted(pdf_a)
ok, why = refused(enc, "", "password-protected")
check("Password-protected note without a password: asks for it", ok, why)
ok, why = refused(enc, "Wrong999", "not correct")
check("Wrong password: refused", ok, why)
e2 = parse(enc, FX.PASSWORD)
check("Right password (AES-256): same trades as the unprotected note", [(t["instrument"], t["qty"], t["rate"]) for t in e2["trades"]]
      == [(t["instrument"], t["qty"], t["rate"]) for t in a["trades"]])
ok, why = refused(b"PK\x03\x04 not a pdf", "", "not a PDF")
check("A non-PDF file is refused", ok, why)
ok, why = refused(FX._pdf([[]]), "", "scanned")
check("A PDF with no text (a scan) is refused with the reason", ok, why)
ok, why = refused(FX._pdf([[(60, 500, "Monthly newsletter"), (60, 480, "Markets were volatile in August 2026")]]), "", "No trades")
check("A PDF that is not a contract note yields no trades and is refused", ok, why)

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
        r = c.getresponse()
        out = r.read()
        sc = r.getheader("Set-Cookie")
        if sc:
            self.cookie = sc.split(";")[0]
        return r.status, (json.loads(out) if out else {})

    def upload(self, pdf, password="", name="note.pdf"):
        bnd = uuid.uuid4().hex
        parts = [f"--{bnd}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{name}\"\r\nContent-Type: application/pdf\r\n\r\n".encode() + pdf + b"\r\n",
                 f"--{bnd}\r\nContent-Disposition: form-data; name=\"password\"\r\n\r\n{password}\r\n".encode(), f"--{bnd}--\r\n".encode()]
        return self.req("POST", "/api/contract-note", raw=b"".join(parts), ctype=f"multipart/form-data; boundary={bnd}")


admin, viewer = Client(), Client()
admin.req("POST", "/api/setup", {"user": "cio", "password": "Look2026"})
admin.req("POST", "/api/users", {"action": "create", "user": "view1", "password": "View2026", "role": "viewer"})
viewer.req("POST", "/api/login", {"user": "view1", "password": "View2026"})
st, j = admin.req("POST", "/api/entities", {"action": "add", "name": "Test Client", "type": "Individual", "relationship": "Test"})
MID = j["record"]["member_id"]

st, j = viewer.upload(pdf_a)
check("Bridge: a viewer cannot read contract notes (analyst role needed)", st == 403, (st, j))
st, prev = admin.upload(enc, FX.PASSWORD, "note_a.pdf")
check("Bridge: encrypted note read with its password; preview only", st == 200 and len(prev["trades"]) == 3 and prev["file"] == "note_a.pdf", (st, prev))
led = json.loads((TMP / "user" / "ledger.json").read_text(encoding="utf-8"))
check("Bridge: reading a note saves nothing", not led["transactions"], led["transactions"])
audit_raw = (TMP / "user" / "audit.jsonl").read_text(encoding="utf-8")
check("Bridge: the read is audited, the password is not", "CONTRACT_NOTE_READ" in audit_raw and FX.PASSWORD not in audit_raw)

rows = [{"member_id": MID, "instrument": t["instrument"], "plan": "", "txn_type": t["side"], "date": prev["trade_date"], "units": t["qty"],
         "price": t["price_with_charges"]} for t in prev["trades"]]
refv = {"sha256": prev["sha256"], "contract_note_no": prev["contract_note_no"], "file": prev["file"]}
st, j = admin.req("POST", "/api/transactions", {"action": "import", "trades": rows, "ref": refv})
check("Bridge: confirmed trades recorded together", st == 200 and len(j["record"]) == 3, (st, j))
new = [t for t in json.loads((TMP / "live" / "dataset.json").read_text(encoding="utf-8"))["transactions"] if t["member_id"] == MID]
check("Bridge: the imported trades are in the rebuilt dataset, with amounts computed by the bridge",
      len(new) == 3 and all(abs(t["amount"] - round(t["units"] * t["price"], 2)) < 0.005 for t in new), new)
check("Bridge: each imported trade carries the note number", all("DSL/2026/004512" in t.get("note", "") for t in new), [t.get("note") for t in new])
st, j = admin.req("POST", "/api/transactions", {"action": "import", "trades": rows, "ref": refv})
check("Bridge: the same contract note cannot be imported twice", st == 400 and "already imported" in j["error"], (st, j))

# all-or-nothing: note B sells ICICI 10 (the entity holds 30 from note A) and buys Reliance; make the sale too large
_, pb = admin.upload(pdf_b)
rows_b = [{"member_id": MID, "instrument": t["instrument"], "plan": "", "txn_type": t["side"], "date": pb["trade_date"],
           "units": (500 if t["side"] == "Sell" else t["qty"]), "price": t["price_with_charges"]} for t in pb["trades"]]
before = len(json.loads((TMP / "user" / "ledger.json").read_text(encoding="utf-8"))["transactions"])
st, j = admin.req("POST", "/api/transactions", {"action": "import", "trades": rows_b, "ref": {"sha256": pb["sha256"], "contract_note_no": pb["contract_note_no"]}})
after = len(json.loads((TMP / "user" / "ledger.json").read_text(encoding="utf-8"))["transactions"])
check("Bridge: a sale larger than the holding refuses the WHOLE import (nothing saved)", st == 400 and after == before, (st, j, before, after))
rows_b[[t["txn_type"] for t in rows_b].index("Sell")]["units"] = 10
st, j = admin.req("POST", "/api/transactions", {"action": "import", "trades": rows_b, "ref": {"sha256": pb["sha256"], "contract_note_no": pb["contract_note_no"]}})
check("Bridge: the corrected note B (buy and a covered sale) is recorded", st == 200 and len(j["record"]) == 2, (st, j))
st, j = admin.req("POST", "/api/transactions", {"action": "import", "trades": rows_b, "ref": {"sha256": "x" * 64}})
check("Bridge: an import without a valid note reference is refused", st == 400, (st, j))
st, j = admin.upload(b"not a pdf at all")
check("Bridge: a non-PDF upload is refused with a reason", st == 400 and "not a PDF" in j["error"], (st, j))
audit_raw = (TMP / "user" / "audit.jsonl").read_text(encoding="utf-8")
check("Bridge: the import is audited with the note number, file hash and transaction ids",
      '"TXN_IMPORT"' in audit_raw and prev["sha256"] in audit_raw and "DSL/2026/004512" in audit_raw)

httpd.shutdown()
shutil.rmtree(TMP, ignore_errors=True)
n = sum(results)
line = f"{n}/{len(results)} contract-note checks passed"
print("\n" + line)
(ROOT / "verify" / "contract_note_result.txt").write_text(line + "\n", encoding="utf-8")
sys.exit(0 if all(results) else 1)
