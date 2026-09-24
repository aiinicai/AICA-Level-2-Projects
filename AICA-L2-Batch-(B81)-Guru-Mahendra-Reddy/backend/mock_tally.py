#!/usr/bin/env python
"""A stand-in for Tally Prime, speaking the same XML on the same port.

    python mock_tally.py            # listens on 9000

Why this exists: demonstrating the connector should not depend on a Tally
licence, a Windows machine and a successful import all lining up on the day.
This answers the four requests the connector actually makes — list companies,
ledgers, day book, bills outstanding — with the same seventeen months of data
`tally_export.py` writes, in Tally's own response shape.

**Including Tally's sign convention**, which is the point of doing it this way.
A mock that returned the intuitive signs would let a sign error through to the
one environment that matters. Inside `ALLLEDGERENTRIES.LIST` a negative AMOUNT
is a debit, exactly as Tally emits it.

It is a demonstration aid and prints every request it serves. Do not leave it
running alongside a real Tally instance — they cannot both hold port 9000, and
the one that wins is whichever started first.
"""
from __future__ import annotations

import logging
import sys
import xml.etree.ElementTree as ET
from datetime import date
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.seed import tallydata as T                       # noqa: E402
from app.seed.tallycheck import run as trial_balance      # noqa: E402
from tally_export import COMPANY, LEDGERS, esc, td        # noqa: E402

log = logging.getLogger("mock-tally")

_STATE: dict = {}


def state() -> dict:
    if not _STATE:
        r = trial_balance(verbose=False)
        _STATE["opening"] = r["opening"]
        _STATE["closing"] = r["closing"]
        _STATE["model"] = r["model"]
    return _STATE


def _companies() -> str:
    return (f"<ENVELOPE><BODY><DATA><COLLECTION>"
            f"<COMPANY NAME=\"{esc(COMPANY)}\"><NAME>{esc(COMPANY)}</NAME></COMPANY>"
            f"</COLLECTION></DATA></BODY></ENVELOPE>")


def _ledgers() -> str:
    s = state()
    rows = []
    for name, parent in LEDGERS:
        opening = s["opening"].get(name, 0.0)
        closing = s["closing"].get(name, 0.0)
        rows.append(
            f'<LEDGER NAME="{esc(name)}">'
            f'<NAME>{esc(name)}</NAME><PARENT>{esc(parent)}</PARENT>'
            f'<OPENINGBALANCE>{-opening:.2f}</OPENINGBALANCE>'
            f'<CLOSINGBALANCE>{-closing:.2f}</CLOSINGBALANCE>'
            f'<ISDEEMEDPOSITIVE>{"Yes" if closing >= 0 else "No"}</ISDEEMEDPOSITIVE>'
            f'<GUID>mock-{abs(hash(name)) % 10**10}</GUID>'
            f'<ISREVENUE>{"Yes" if "Expenses" in parent or "Income" in parent or "Sales" in parent else "No"}</ISREVENUE>'
            f'</LEDGER>')
    return ("<ENVELOPE><BODY><DATA><COLLECTION>" + "".join(rows)
            + "</COLLECTION></DATA></BODY></ENVELOPE>")


def _day_book(frm: date | None, to: date | None) -> str:
    out = []
    for v in state()["model"]["vouchers"]:
        if frm and v.when < frm:
            continue
        if to and v.when > to:
            continue
        lines = "".join(
            f'<ALLLEDGERENTRIES.LIST>'
            f'<LEDGERNAME>{esc(l.ledger)}</LEDGERNAME>'
            f'<ISDEEMEDPOSITIVE>{"Yes" if l.amount > 0 else "No"}</ISDEEMEDPOSITIVE>'
            f'<AMOUNT>{-l.amount:.2f}</AMOUNT>'
            f'</ALLLEDGERENTRIES.LIST>'
            for l in v.lines)
        out.append(
            f'<VOUCHER>'
            f'<DATE>{td(v.when)}</DATE>'
            f'<VOUCHERTYPENAME>{esc(v.vtype)}</VOUCHERTYPENAME>'
            f'<VOUCHERNUMBER>{esc(v.number)}</VOUCHERNUMBER>'
            f'<NARRATION>{esc(v.narration)}</NARRATION>'
            f'<PARTYLEDGERNAME>{esc(v.party)}</PARTYLEDGERNAME>'
            f'<GUID>mock-{esc(v.number)}</GUID>'
            f'{lines}</VOUCHER>')
    return "<ENVELOPE><BODY><DATA>" + "".join(out) + "</BODY></DATA></ENVELOPE>".replace(
        "</BODY></DATA>", "</DATA></BODY>")


def _bills(receivable: bool) -> str:
    """What is still open on 31-Aug-2026 — the residue of the settlement run."""
    out = []
    if receivable:
        model = state()["model"]
        for cust, bills in model["open_bills"].items():
            for ref, amount, raised, due in bills:
                out.append(
                    f'<BILLFIXED><BILLPARTY>{esc(cust)}</BILLPARTY>'
                    f'<BILLREF>{esc(ref)}</BILLREF>'
                    f'<BILLDATE>{td(raised)}</BILLDATE>'
                    f'<BILLDUEDATE>{td(due)}</BILLDUEDATE>'
                    f'<BILLAMT>{amount:.2f}</BILLAMT>'
                    f'</BILLFIXED>')
    else:
        from app.seed.exampledata import _bills as example_bills
        for r in example_bills():
            out.append(
                f'<BILLFIXED><BILLPARTY>{esc(r["vendor"])}</BILLPARTY>'
                f'<BILLREF>{esc(r["bill_no"])}</BILLREF>'
                f'<BILLDATE>{td(r["bill_date"])}</BILLDATE>'
                f'<BILLDUEDATE>{td(r["due_date"])}</BILLDUEDATE>'
                f'<BILLAMT>{float(r["outstanding"]):.2f}</BILLAMT>'
                f'</BILLFIXED>')
    return "<ENVELOPE><BODY><DATA>" + "".join(out) + "</DATA></BODY></ENVELOPE>"


def _parse_dates(root: ET.Element) -> tuple[date | None, date | None]:
    def one(tag):
        for e in root.iter(tag):
            t = (e.text or "").strip()
            if len(t) == 8 and t.isdigit():
                return date(int(t[:4]), int(t[4:6]), int(t[6:]))
        return None
    return one("SVFROMDATE"), one("SVTODATE")


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):                                    # noqa: N802
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length).decode("utf-8", errors="replace")
        try:
            root = ET.fromstring(body)
        except ET.ParseError:
            return self._send("<ENVELOPE></ENVELOPE>")

        blob = body.lower()
        report = next((e.text or "" for e in root.iter("REPORTNAME")), "")
        coll_id = next((e.text or "" for e in root.iter("ID")), "")
        what = f"{report} {coll_id}".strip().lower()

        if "compan" in what or "<type>company</type>" in blob:
            log.info("→ list of companies")
            return self._send(_companies())
        if "ledger" in what or "<type>ledger</type>" in blob:
            log.info("→ chart of accounts (%d ledgers)", len(LEDGERS))
            return self._send(_ledgers())
        if "day book" in what or "daybook" in what:
            frm, to = _parse_dates(root)
            xml = _day_book(frm, to)
            log.info("→ day book %s .. %s (%d vouchers)", frm, to, xml.count("<VOUCHER>"))
            return self._send(xml)
        if "receivable" in what:
            log.info("→ bills receivable")
            return self._send(_bills(True))
        if "payable" in what:
            log.info("→ bills payable")
            return self._send(_bills(False))

        log.info("→ %r (nothing to serve; answering empty, as Tally would)", what)
        return self._send("<ENVELOPE><BODY><DATA></DATA></BODY></ENVELOPE>")

    def _send(self, xml: str) -> None:
        data = xml.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/xml; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *a):     # quiet; we log what matters ourselves
        pass


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="  %(message)s")
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 9000
    s = state()
    n = len(s["model"]["vouchers"])
    print(f"""
  Mock Tally endpoint — a stand-in for Tally Prime
  ===============================================

  Listening on http://localhost:{port}
  Serving: {COMPANY}
    {len(LEDGERS)} ledgers, {n:,} vouchers, {T.FY_START:%b-%Y} to {T.PERIOD_END:%b-%Y}
    Two ledgers are deliberately unrecognisable, so the ledger-mapping
    screen has something real to do.

  In Cash Runway:  Setup > Tally > Test connection.
  Ctrl-C to stop.
""")
    HTTPServer(("127.0.0.1", port), Handler).serve_forever()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\n  Stopped.\n")
