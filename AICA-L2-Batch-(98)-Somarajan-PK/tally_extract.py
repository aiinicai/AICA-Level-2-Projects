"""Extract BANK BOOKS from Tally Prime automatically.

Reads every ledger under the group  Current Assets > Bank Accounts  (including sub-groups)
through Tally's built-in XML server and writes:
    <out>/tally_bank_books.json        all banks (used by recon_engine.py and the web app)
    <out>/bank_books_<bank>.csv        one CSV per bank (Date, Narration, Voucher_Ref, Receipt, Payment, Balance)
    <out>/banks/<bank>/                empty folder - put that bank's bank_statement.csv here
    <out>/config.json                  starter settings (created only if missing)

Tally setup (once): open the company, then  F1 (Help) > Settings > Connectivity > Client/Server configuration
-> set "TallyPrime acts as" = Server or Both, Port = 9000 (older: Gateway of Tally > F12 > Advanced Config).

Usage:
    python tally_extract.py --from 01-10-2026 --to 31-10-2026
    python tally_extract.py --from 01-10-2026 --to 31-10-2026 --company "ABC Traders" --out tally_export
    python tally_extract.py --from-xml ledgers.xml daybook.xml --from 01-10-2026 --to 31-10-2026   (offline/testing)

Data stays on your computer: this script only talks to Tally on localhost.
Only use SYNTHETIC or anonymised company data when feeding results to any AI tool.
"""
import argparse, csv, json, re, sys
import urllib.error, urllib.request
from datetime import date, datetime
from pathlib import Path
from xml.etree import ElementTree as ET
from xml.sax.saxutils import escape

GROUP = "Bank Accounts"


class TallyError(Exception):
    """Problem talking to Tally or reading its reply (message is safe to show the user)."""


# ---------------------------------------------------------------- helpers
def safe_name(n):
    return re.sub(r"[^A-Za-z0-9]+", "_", n).strip("_").lower()


def dmy(s):
    return datetime.strptime(s, "%d-%m-%Y").date()


def tally_date(d):
    return d.strftime("%Y%m%d")


def clean_xml(text):
    """Tally can emit invalid character references (e.g. &#4;). Drop them so the XML parses."""
    return re.sub(r"&#(?:[0-8]|11|12|1[4-9]|2[0-9]|3[01]);|[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)


def amt(x):
    x = (x or "").replace(",", "").strip()
    m = re.match(r"-?\d+(\.\d+)?", x)          # ignore suffixes like ' Dr' / ' Cr'
    v = float(m.group(0)) if m else 0.0
    return v


def post(host, port, xml, timeout=120):
    req = urllib.request.Request(f"http://{host}:{port}", data=xml.encode("utf-8"),
                                 headers={"Content-Type": "text/xml; charset=utf-8"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read()
    except (urllib.error.URLError, ConnectionError, TimeoutError) as e:
        raise TallyError(
            f"Cannot reach Tally at {host}:{port} ({e}).\n"
            "Open Tally Prime with your company loaded, then enable the XML server:\n"
            "  F1 (Help) > Settings > Connectivity > Client/Server configuration > TallyPrime acts as = Server/Both, port 9000.")
    try:
        return clean_xml(raw.decode("utf-16") if raw[:2] in (b"\xff\xfe", b"\xfe\xff") else raw.decode("utf-8", "replace"))
    except UnicodeDecodeError:
        return clean_xml(raw.decode("latin-1"))


# ---------------------------------------------------------------- requests
def envelope(body_header, static, tdl=""):
    return ("<ENVELOPE><HEADER><VERSION>1</VERSION><TALLYREQUEST>Export</TALLYREQUEST>" + body_header +
            "</HEADER><BODY><DESC><STATICVARIABLES><SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>" + static +
            "</STATICVARIABLES>" + (f"<TDL><TDLMESSAGE>{tdl}</TDLMESSAGE></TDL>" if tdl else "") +
            "</DESC></BODY></ENVELOPE>")


def company_var(company):
    return f"<SVCURRENTCOMPANY>{escape(company)}</SVCURRENTCOMPANY>" if company else ""


def req_bank_ledgers(company):
    tdl = (f'<COLLECTION NAME="ReconBankLedgers" ISMODIFY="No"><TYPE>Ledger</TYPE><CHILDOF>{GROUP}</CHILDOF>'
           "<BELONGSTO>Yes</BELONGSTO><FETCH>Name, Parent, OpeningBalance</FETCH></COLLECTION>")
    return envelope("<TYPE>Collection</TYPE><ID>ReconBankLedgers</ID>", company_var(company), tdl)


def req_companies():
    tdl = '<COLLECTION NAME="ReconCompanies" ISMODIFY="No"><TYPE>Company</TYPE><FETCH>Name</FETCH></COLLECTION>'
    return envelope("<TYPE>Collection</TYPE><ID>ReconCompanies</ID>", "", tdl)


def req_daybook(company, d_from, d_to):
    static = f"<SVFROMDATE>{tally_date(d_from)}</SVFROMDATE><SVTODATE>{tally_date(d_to)}</SVTODATE>" + company_var(company)
    return envelope("<TYPE>Data</TYPE><ID>Day Book</ID>", static)


# ---------------------------------------------------------------- parsing
def parse_bank_ledgers(xml_text):
    """-> {ledger name: opening balance as Dr-positive}.  Tally exports Dr balances as negative numbers."""
    root = ET.fromstring(xml_text)
    out = {}
    for led in root.iter("LEDGER"):
        name = led.get("NAME") or (led.findtext("NAME") or "").strip()
        if not name:
            continue
        out[name] = -amt(led.findtext("OPENINGBALANCE"))
    return out


def parse_companies(xml_text):
    root = ET.fromstring(xml_text)
    names = [c.get("NAME") or (c.findtext("NAME") or "").strip() for c in root.iter("COMPANY")]
    return sorted({n for n in names if n})


def first_text(el, *tags):
    for t in tags:
        v = el.findtext(t)
        if v and v.strip():
            return v.strip()
    return ""


def parse_vouchers(xml_text, banks):
    """-> list of bank-ledger postings: dict(bank, date, narration, ref, receipt, payment)."""
    root = ET.fromstring(xml_text)
    rows = []
    for v in root.iter("VOUCHER"):
        if (v.findtext("ISCANCELLED") or "").strip().lower() == "yes":
            continue
        if (v.findtext("ISOPTIONAL") or "").strip().lower() == "yes":
            continue
        ds = (v.findtext("DATE") or "").strip()
        if len(ds) != 8:
            continue
        d = datetime.strptime(ds, "%Y%m%d").date()
        entries = list(v.findall("ALLLEDGERENTRIES.LIST")) + list(v.findall("LEDGERENTRIES.LIST"))
        names = [(e.findtext("LEDGERNAME") or "").strip() for e in entries]
        vtype, vno, narr = first_text(v, "VOUCHERTYPENAME"), first_text(v, "VOUCHERNUMBER"), first_text(v, "NARRATION")
        for e, nm in zip(entries, names):
            if nm not in banks:
                continue
            a = amt(e.findtext("AMOUNT"))          # Tally: negative = Debit (receipt), positive = Credit (payment)
            if a == 0:
                continue
            ref = ""
            for ba in e.iter("BANKALLOCATIONS.LIST"):
                ref = first_text(ba, "INSTRUMENTNUMBER", "UNIQUEREFERENCENUMBER", "TRANSACTIONNAME")
                if ref:
                    break
            others = [n for n in names if n and n != nm and n not in banks] or [n for n in names if n and n != nm]
            who = ", ".join(dict.fromkeys(others))
            text = " ".join(x for x in (f"{vtype} {vno}".strip(), f"- {who}" if who else "", f"| {narr}" if narr else "") if x)
            rows.append(dict(bank=nm, date=d, narration=text, ref=ref, receipt=-a if a < 0 else 0.0, payment=a if a > 0 else 0.0))
    return rows


def build_banks(opening_fy, rows, d_from, d_to):
    """Roll opening balance forward to period start, then build running-balance rows for the period."""
    banks = []
    for name, fy_open in opening_fy.items():
        mine = sorted((r for r in rows if r["bank"] == name), key=lambda r: r["date"])
        bal = fy_open + sum(r["receipt"] - r["payment"] for r in mine if r["date"] < d_from)
        period_open, out = bal, []
        for r in mine:
            if not (d_from <= r["date"] <= d_to):
                continue
            bal += r["receipt"] - r["payment"]
            out.append({"Date": r["date"].strftime("%d-%m-%Y"), "Narration": r["narration"], "Voucher_Ref": r["ref"],
                        "Receipt": f"{r['receipt']:.2f}" if r["receipt"] else "",
                        "Payment": f"{r['payment']:.2f}" if r["payment"] else "", "Balance": f"{bal:.2f}"})
        banks.append({"name": name, "parent": GROUP, "opening_balance": round(period_open, 2),
                      "closing_balance": round(bal, 2), "rows": out})
    return sorted(banks, key=lambda b: b["name"].lower())


def write_outputs(out, company, d_from, d_to, banks):
    out.mkdir(parents=True, exist_ok=True)
    (out / "tally_bank_books.json").write_text(json.dumps(
        {"company": company or "(current Tally company)", "source": "Tally Prime XML", "group": GROUP,
         "period_from": d_from.strftime("%d-%m-%Y"), "period_to": d_to.strftime("%d-%m-%Y"), "banks": banks},
        indent=1), encoding="utf-8")
    write_bank_files(out, banks)


def write_bank_files(out, banks):
    for b in banks:
        sn = safe_name(b["name"])
        with open(out / f"bank_books_{sn}.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["Date", "Narration", "Voucher_Ref", "Receipt", "Payment", "Balance"])
            w.writeheader()
            w.writerows(b["rows"])
        (out / "banks" / sn).mkdir(parents=True, exist_ok=True)
        (out / "banks" / sn / "PUT_BANK_STATEMENT_HERE.txt").write_text(
            f"Save the bank statement for '{b['name']}' here as bank_statement.csv\n"
            "Columns: Date (DD-MM-YYYY), Narration, Ref_No, Withdrawal, Deposit, Balance\n"
            "Optional: opening_items.csv (Date, Narration, Ref, Amount) for cheques outstanding at period start.\n",
            encoding="utf-8")
    cfg = out / "config.json"
    if not cfg.exists():
        cfg.write_text(json.dumps({"approval_limit": 50000, "stale_days": 90, "date_tolerance": 3}, indent=2), encoding="utf-8")


def check_connection(host="localhost", port=9000, company=None):
    """Connectivity check for the UI: -> dict(companies=[...], bank_ledgers=[...])."""
    try:
        companies = parse_companies(post(host, port, req_companies(), timeout=20))
    except ET.ParseError:
        companies = []
    try:
        banks = sorted(parse_bank_ledgers(post(host, port, req_bank_ledgers(company), timeout=60)))
    except ET.ParseError:
        raise TallyError("Tally replied, but not with XML this tool understands. Is a company open, and is the port the Tally XML server port?")
    return dict(companies=companies, bank_ledgers=banks)


def pull(host, port, company, d_from, d_to, fy=None, dump_dir=None):
    """Pull bank books (Current Assets > Bank Accounts) from Tally -> dict in tally_bank_books.json shape."""
    fy = fy or date(d_from.year if d_from.month >= 4 else d_from.year - 1, 4, 1)
    led_xml = post(host, port, req_bank_ledgers(company))
    day_xml = post(host, port, req_daybook(company, fy, d_to), timeout=600)
    if dump_dir:
        dump_dir = Path(dump_dir)
        dump_dir.mkdir(parents=True, exist_ok=True)
        (dump_dir / "raw_ledgers.xml").write_text(led_xml, encoding="utf-8")
        (dump_dir / "raw_daybook.xml").write_text(day_xml, encoding="utf-8")
    return assemble(led_xml, day_xml, company, d_from, d_to)


def assemble(led_xml, day_xml, company, d_from, d_to):
    try:
        opening = parse_bank_ledgers(led_xml)
        rows = parse_vouchers(day_xml, set(opening)) if opening else []
    except ET.ParseError as e:
        raise TallyError(f"Could not read Tally's reply ({e}). Re-run with --dump-xml to inspect it.")
    if not opening:
        raise TallyError(f"No ledgers found under the group '{GROUP}'. Check the company is open and has bank ledgers.")
    banks = build_banks(opening, rows, d_from, d_to)
    return {"company": company or "(current Tally company)", "source": "Tally Prime XML", "group": GROUP,
            "period_from": d_from.strftime("%d-%m-%Y"), "period_to": d_to.strftime("%d-%m-%Y"), "banks": banks}


def main(argv=None):
    try:
        return _main(argv)
    except TallyError as e:
        raise SystemExit(str(e))


def _main(argv=None):
    ap = argparse.ArgumentParser(description="Extract bank books (Current Assets > Bank Accounts) from Tally Prime")
    ap.add_argument("--from", dest="d_from", required=True, help="Period start DD-MM-YYYY")
    ap.add_argument("--to", dest="d_to", required=True, help="Period end DD-MM-YYYY")
    ap.add_argument("--fy-start", help="Financial year start DD-MM-YYYY (default: 1 April on/before --from)")
    ap.add_argument("--company", help="Tally company name (default: the company currently open)")
    ap.add_argument("--host", default="localhost")
    ap.add_argument("--port", type=int, default=9000)
    ap.add_argument("--out", default="tally_export")
    ap.add_argument("--dump-xml", action="store_true", help="Save raw Tally responses to <out>/raw_*.xml for troubleshooting")
    ap.add_argument("--from-xml", nargs=2, metavar=("LEDGERS_XML", "DAYBOOK_XML"), help="Parse saved responses instead of calling Tally")
    a = ap.parse_args(argv)
    d_from, d_to = dmy(a.d_from), dmy(a.d_to)
    if d_to < d_from:
        raise SystemExit("--to must not be before --from")
    fy = dmy(a.fy_start) if a.fy_start else date(d_from.year if d_from.month >= 4 else d_from.year - 1, 4, 1)
    out = Path(a.out)

    if a.from_xml:
        led_xml, day_xml = (clean_xml(Path(p).read_text(encoding="utf-8")) for p in a.from_xml)
        data = assemble(led_xml, day_xml, a.company, d_from, d_to)
    else:
        print(f"Reading bank ledgers and vouchers from Tally at {a.host}:{a.port} (from {fy:%d-%m-%Y}, to roll the opening balance forward) ...")
        data = pull(a.host, a.port, a.company, d_from, d_to, fy, out if a.dump_xml else None)
    banks = data["banks"]
    write_outputs(out, a.company, d_from, d_to, banks)

    print(f"\nFound {len(banks)} bank account(s) under {GROUP}:")
    for b in banks:
        print(f"  - {b['name']}: {len(b['rows'])} entries | opening {b['opening_balance']:,.2f} | closing {b['closing_balance']:,.2f}")
    print("\nCheck each closing balance against Tally (Display > Account Books > Bank Books) before reconciling.")
    print(f"Saved to {out.resolve()}")
    print("Next: put each bank's statement under banks/<bank>/bank_statement.csv, then run:")
    print(f"  python recon_engine.py --data {out}")
    return banks


if __name__ == "__main__":
    main()
