#!/usr/bin/env python3
"""
DCMIS Tally Bridge - a small, READ-ONLY local bridge between TallyPrime and the
Debtors & Creditors MIS HTML application.

    TallyPrime (XML over HTTP, e.g. localhost:9000)  <-  this bridge (127.0.0.1:9901)  <-  HTML app

* Runs on the same computer as the HTML app. Listens on 127.0.0.1 only (never on the network).
* Only EXPORT requests built by this script are ever sent to Tally - it cannot create, alter or delete
  anything in Tally, and the app cannot send its own XML.
* Every request from the app must carry the pairing token shown when the bridge starts.
* Tally's address/port live in bridge_config.json next to this file, not in the HTML app.
* Uses only the Python standard library (Python 3.8+). No installation needed.

Start:   python tally_bridge.py            (Windows: py tally_bridge.py)
Options: python tally_bridge.py --tally http://localhost:9000 --port 9901 --new-token
"""
import json, os, re, secrets, sys, time, argparse, threading
import urllib.request, urllib.error
import xml.etree.ElementTree as ET
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from datetime import date, datetime, timedelta

VERSION = "1.0.1"
HERE = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else os.path.dirname(os.path.abspath(__file__))
CFG_PATH = os.path.join(HERE, "bridge_config.json")
DEFAULT_CFG = {"tally_url": "http://localhost:9000", "listen_port": 9901, "token": "", "timeout_seconds": 120,
               "allowed_origins": ["null", "http://localhost", "http://127.0.0.1"], "chunk_days": 31}
LOCK = threading.Lock()   # Tally handles one request at a time best


def load_cfg(args):
    cfg = dict(DEFAULT_CFG)
    if os.path.exists(CFG_PATH):
        with open(CFG_PATH, "r", encoding="utf-8") as f:
            cfg.update(json.load(f))
    if args.tally: cfg["tally_url"] = args.tally.rstrip("/")
    if args.port: cfg["listen_port"] = args.port
    if args.new_token or not cfg.get("token"): cfg["token"] = secrets.token_urlsafe(24)
    with open(CFG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)
    return cfg


# ---------------------------------------------------------------- XML helpers
_BAD_XML = re.compile(r"&#(?:x0*[0-8bBcCeEfF]|x0*1[0-9a-fA-F]|0*(?:[0-8]|1[1-2]|1[4-9]|2[0-9]|3[01]));")
_CTRL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def decode_tally(raw: bytes) -> str:
    """Tally may answer in UTF-16 or UTF-8 and embed control characters (e.g. &#4;) that break XML parsers."""
    if raw.startswith(b"\xff\xfe") or raw.startswith(b"\xfe\xff"):
        txt = raw.decode("utf-16")
    elif len(raw) > 1 and raw[1:2] == b"\x00":
        txt = raw.decode("utf-16-le", errors="replace")
    else:
        txt = raw.decode("utf-8", errors="replace")
    txt = _BAD_XML.sub("", txt)
    return _CTRL.sub("", txt)


def to_json(el):
    """Generic XML -> JSON. Tags ending in .LIST always become lists; attributes are kept under '@'."""
    kids = list(el)
    if not kids:
        return (el.text or "").strip()
    out = {}
    if el.attrib:
        out["@"] = dict(el.attrib)
    for k in kids:
        v = to_json(k)
        tag = k.tag
        if tag.endswith(".LIST"):
            out.setdefault(tag, []).append(v)
        elif tag in out:
            if not isinstance(out[tag], list) or tag not in out.get("__multi", []):
                out[tag] = [out[tag]]
                out.setdefault("__multi", []).append(tag)
            out[tag].append(v)
        else:
            out[tag] = v
    out.pop("__multi", None)
    return out


def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;"))


def envelope(coll_id, obj_type, fetch, company=None, frm=None, to=None, extra_tdl=""):
    sv = "<SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>"
    if company: sv += f"<SVCURRENTCOMPANY>{esc(company)}</SVCURRENTCOMPANY>"
    if frm: sv += f"<SVFROMDATE TYPE=\"Date\">{frm}</SVFROMDATE>"
    if to: sv += f"<SVTODATE TYPE=\"Date\">{to}</SVTODATE>"
    return (f"<ENVELOPE><HEADER><VERSION>1</VERSION><TALLYREQUEST>Export</TALLYREQUEST><TYPE>Collection</TYPE>"
            f"<ID>{coll_id}</ID></HEADER><BODY><DESC><STATICVARIABLES>{sv}</STATICVARIABLES><TDL><TDLMESSAGE>"
            f"<COLLECTION NAME=\"{coll_id}\" ISMODIFY=\"No\"><TYPE>{obj_type}</TYPE><FETCH>{fetch}</FETCH></COLLECTION>"
            f"{extra_tdl}</TDLMESSAGE></TDL></DESC></BODY></ENVELOPE>")


class TallyError(Exception):
    pass


def post_tally(cfg, xml_text):
    req = urllib.request.Request(cfg["tally_url"], data=xml_text.encode("utf-8"), method="POST",
                                 headers={"Content-Type": "text/xml; charset=utf-8"})
    with LOCK:
        try:
            with urllib.request.urlopen(req, timeout=cfg["timeout_seconds"]) as r:
                raw = r.read()
        except urllib.error.URLError as e:
            raise TallyError(f"TallyPrime is not reachable at {cfg['tally_url']} ({e.reason}). "
                             "Open TallyPrime, load the company and enable the HTTP server (see README).")
        except OSError as e:
            raise TallyError(f"TallyPrime is not reachable at {cfg['tally_url']} ({e}).")
    txt = decode_tally(raw)
    txt = re.sub(r'</?[A-Za-z_][\w:.\-]*', lambda m: m.group(0).replace(":", "_"), txt)
    try:
        root = ET.fromstring(txt)
    except ET.ParseError as e:
        raise TallyError(f"TallyPrime returned a response that is not valid XML ({e}).")
    line_err = root.find(".//LINEERROR")
    if line_err is not None and (line_err.text or "").strip():
        raise TallyError("TallyPrime reported: " + line_err.text.strip())
    return root


def collection(cfg, coll_id, obj_type, fetch, tag, **kw):
    root = post_tally(cfg, envelope(coll_id, obj_type, fetch, **kw))
    return [to_json(e) for e in root.iter(tag)]


# ---------------------------------------------------------------- Tally reads (all EXPORT)
LEDGER_FETCH = ("NAME, PARENT, GUID, MASTERID, ALTERID, BILLCREDITPERIOD, ISBILLWISEON, PARTYGSTIN, LEDGERPHONE, "
                "LEDGERMOBILE, EMAIL, LEDGERCONTACT, LEDSTATENAME, PINCODE, ADDRESS.LIST, LEDGSTREGDETAILS.LIST, "
                "OPENINGBALANCE, CLOSINGBALANCE")
VOUCHER_FETCH = ("DATE, VOUCHERTYPENAME, VOUCHERNUMBER, GUID, MASTERID, ALTERID, PARTYLEDGERNAME, REFERENCE, "
                 "REFERENCEDATE, NARRATION, ISCANCELLED, ISOPTIONAL, ISPOSTDATED, ISDELETED, ISINVOICE, "
                 "ALLLEDGERENTRIES.LIST, LEDGERENTRIES.LIST")
BILL_FETCH = "NAME, PARENT, GUID, MASTERID, ALTERID, BILLDATE, BILLCREDITPERIOD, OPENINGBALANCE, CLOSINGBALANCE"


def companies(cfg):
    rows = collection(cfg, "DCMISCompanies", "Company", "NAME, GUID, STARTINGFROM, BOOKSFROM", "COMPANY")
    out = []
    for r in rows:
        if isinstance(r, dict):
            out.append({"name": r.get("NAME") or (r.get("@") or {}).get("NAME", ""), "guid": r.get("GUID", ""),
                        "booksFrom": r.get("BOOKSFROM") or r.get("STARTINGFROM", "")})
    return [c for c in out if c["name"]]


def daterange_chunks(frm, to, days):
    d0, d1 = datetime.strptime(frm, "%Y%m%d").date(), datetime.strptime(to, "%Y%m%d").date()
    while d0 <= d1:
        e = min(d1, d0 + timedelta(days=days - 1))
        yield d0.strftime("%Y%m%d"), e.strftime("%Y%m%d")
        d0 = e + timedelta(days=1)


def fetch_all(cfg, company, types, frm, to):
    t0 = time.time(); warnings = []
    out = {"bridgeVersion": VERSION, "company": company, "from": frm, "to": to, "types": types,
           "groups": [], "ledgers": [], "voucherTypes": [], "vouchers": [], "bills": []}
    # masters needed to classify parties and voucher types are always read (they are small)
    out["groups"] = collection(cfg, "DCMISGroups", "Group", "NAME, PARENT, GUID", "GROUP", company=company)
    out["ledgers"] = collection(cfg, "DCMISLedgers", "Ledger", LEDGER_FETCH, "LEDGER", company=company)
    out["voucherTypes"] = collection(cfg, "DCMISVchTypes", "VoucherType", "NAME, PARENT", "VOUCHERTYPE", company=company)
    vch_types = {"sales", "purchase", "receipts", "payments", "creditnotes", "debitnotes", "journals", "pdc", "billalloc"}
    if vch_types & set(types):
        seen = set()
        for a, b in daterange_chunks(frm, to, int(cfg.get("chunk_days", 31))):
            for v in collection(cfg, "DCMISVouchers", "Voucher", VOUCHER_FETCH, "VOUCHER", company=company, frm=a, to=b):
                g = v.get("GUID") if isinstance(v, dict) else None
                if g and g in seen: continue
                if g: seen.add(g)
                out["vouchers"].append(v)
    if {"dout", "cout"} & set(types):
        rows = []
        for t in ("Bills", "Bill"):   # object type name differs between releases; use whichever answers
            try:
                rows = collection(cfg, "DCMISBills", t, BILL_FETCH, "BILL", company=company, to=to)
                if rows: break
            except TallyError as e:
                warnings.append(f"Bills collection '{t}': {e}")
        out["bills"] = rows
    out["elapsed"] = round(time.time() - t0, 2)
    out["warnings"] = warnings
    return out


# ---------------------------------------------------------------- HTTP server for the app
class Handler(BaseHTTPRequestHandler):
    server_version = "DCMISTallyBridge/" + VERSION

    def _origin_ok(self):
        o = self.headers.get("Origin")
        if o is None: return True   # not a browser request (e.g. curl on this computer)
        allowed = self.server.cfg["allowed_origins"]
        return o == "null" and "null" in allowed or any(o == a or o.startswith(a + ":") for a in allowed if a != "null")

    def _cors(self):
        o = self.headers.get("Origin")
        if o and self._origin_ok():
            self.send_header("Access-Control-Allow-Origin", o)
            self.send_header("Vary", "Origin")
            self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Bridge-Token")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Private-Network", "true")

    def _send(self, code, obj):
        body = json.dumps(obj).encode("utf-8")
        self.send_response(code); self._cors()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body))); self.send_header("Cache-Control", "no-store")
        self.end_headers(); self.wfile.write(body)

    def log_message(self, fmt, *args):   # keep the console readable; never log request bodies
        sys.stdout.write("%s  %s\n" % (datetime.now().strftime("%H:%M:%S"), fmt % args))

    def do_OPTIONS(self):
        if not self._origin_ok(): return self._send(403, {"ok": False, "error": "Origin not allowed"})
        self.send_response(204); self._cors(); self.end_headers()

    def _auth(self):
        if not self._origin_ok():
            self._send(403, {"ok": False, "error": "Origin not allowed"}); return False
        if not secrets.compare_digest(self.headers.get("X-Bridge-Token", ""), self.server.cfg["token"]):
            self._send(401, {"ok": False, "error": "Wrong or missing pairing token"}); return False
        return True

    def do_GET(self):
        if not self._auth(): return
        cfg = self.server.cfg
        if self.path.startswith("/status"):
            try:
                cos = companies(cfg)
                return self._send(200, {"ok": True, "bridgeVersion": VERSION, "tally": {"reachable": True, "url": "local", "companies": cos}})
            except TallyError as e:
                return self._send(200, {"ok": True, "bridgeVersion": VERSION, "tally": {"reachable": False, "error": str(e)}})
        if self.path.startswith("/companies"):
            try: return self._send(200, {"ok": True, "companies": companies(cfg)})
            except TallyError as e: return self._send(502, {"ok": False, "error": str(e)})
        self._send(404, {"ok": False, "error": "Unknown endpoint"})

    def do_POST(self):
        if not self._auth(): return
        if not self.path.startswith("/fetch"): return self._send(404, {"ok": False, "error": "Unknown endpoint"})
        try:
            n = int(self.headers.get("Content-Length", "0"))
            if n > 100000: return self._send(413, {"ok": False, "error": "Request too large"})
            req = json.loads(self.rfile.read(n) or b"{}")
            company = str(req.get("company", "")).strip()
            frm, to = re.sub(r"\D", "", str(req.get("from", ""))), re.sub(r"\D", "", str(req.get("to", "")))
            types = [str(t) for t in req.get("types", [])][:20]
            if not company: return self._send(400, {"ok": False, "error": "Choose a Tally company"})
            if not (len(frm) == 8 and len(to) == 8 and frm <= to): return self._send(400, {"ok": False, "error": "Invalid period"})
            return self._send(200, {"ok": True, **fetch_all(self.server.cfg, company, types, frm, to)})
        except TallyError as e:
            return self._send(502, {"ok": False, "error": str(e)})
        except Exception as e:  # never leak a traceback with data in it
            return self._send(500, {"ok": False, "error": f"Bridge error: {type(e).__name__}"})


def main():
    ap = argparse.ArgumentParser(description="Read-only TallyPrime bridge for the Debtors & Creditors MIS")
    ap.add_argument("--tally", help="TallyPrime HTTP address, default http://localhost:9000")
    ap.add_argument("--port", type=int, help="Port for this bridge on 127.0.0.1, default 9901")
    ap.add_argument("--new-token", action="store_true", help="Create a new pairing token")
    args = ap.parse_args()
    cfg = load_cfg(args)
    srv = ThreadingHTTPServer(("127.0.0.1", int(cfg["listen_port"])), Handler)
    srv.cfg = cfg
    print("=" * 66)
    print(f" DCMIS Tally Bridge {VERSION}  (read-only)")
    print(f" Bridge address : http://127.0.0.1:{cfg['listen_port']}   (this computer only)")
    print(f" TallyPrime     : {cfg['tally_url']}")
    print(f" Pairing token  : {cfg['token']}")
    print("   -> In the app: Tally Sync > Connection > paste this token once.")
    print(" Keep this window open while syncing. Press Ctrl+C to stop.")
    print("=" * 66)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("Bridge stopped.")


if __name__ == "__main__":
    main()
