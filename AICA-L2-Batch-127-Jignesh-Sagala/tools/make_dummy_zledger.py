"""Makes a MADE-UP Zerodha-style funds ledger PDF (locked) to test app/zledger.py. No real data.
Use: python tools/make_dummy_zledger.py <out folder> [seed] [credit|debit]
"""
import json
import random
import sys
from datetime import date, timedelta
from decimal import Decimal as D, ROUND_HALF_UP
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

PASSWORD = "Demo@2026"


def q(x):
    return D(x).quantize(D("0.01"), rounding=ROUND_HALF_UP)


def build(out, seed=5, conv="credit", shuffle_same_day=False):
    rnd = random.Random(seed)
    day = date(2026, 10, 26)
    bal = q(D(rnd.randint(2000, 90000)))
    rows = []
    for i in range(rnd.randint(14, 30)):
        if rnd.random() < 0.4:
            day = min(day + timedelta(days=1), date(2026, 10, 31))
        kind = rnd.choice(["settle_in", "settle_out", "dp", "tds"])
        amt = q(D(rnd.randint(100, 60000)) / 10 + D(rnd.randint(0, 99)) / 100)
        if kind == "settle_in":
            cr, dr = amt, D(0)
        elif kind == "settle_out":
            cr, dr = D(0), amt
        else:
            cr, dr = D(0), q(D(rnd.randint(10, 400)) / 10)
        bal = bal + cr - dr if conv == "credit" else bal + dr - cr
        text = {"settle_in": "Net settlement for Equity with EQ-26/27-%d" % rnd.randint(1000, 9999), "settle_out": "Net settlement for Equity with EQ-26/27-%d" % rnd.randint(1000, 9999),
                "dp": "DP Charges for Sale of TESTCO on DP-26/27-%d" % rnd.randint(10000, 99999), "tds": "TDS amount reversed for TDS-26/27-%d" % rnd.randint(100, 999)}[kind]
        sdate = (day + timedelta(days=1)) if kind.startswith("settle") else None
        rows.append({"date": day, "sdate": sdate, "text": text, "debit": dr, "credit": cr, "balance": bal})
    c = canvas.Canvas(str(out / "raw.pdf"), pagesize=A4)
    y = 800

    def line(*fr):
        nonlocal y
        if y < 60:
            c.showPage()
            y = 800
            hdr()
        c.setFont("Helvetica", 7)
        for x, t in fr:
            c.drawString(x, y, t)
        y -= 11

    def hdr():
        nonlocal y
        c.setFont("Helvetica", 7)
        c.drawString(30, y, "Transaction Settlement Date Segment Type Settlement No Voucher No. Narration Debit (Rs) Credit (Rs.) Balance (Rs.)")
        y -= 11
    line((30, "MADE UP BROKING LTD"))
    line((30, "Client: BusyMe    PAN: ABCDE1234F (made-up)"))
    line((30, "From Date: 2026-10-26"), (300, "To Date: 2026-10-31"))
    line((30, "Statement of Ledger of Funds for the period from 2026-10-26 to 2026-10-31:"))
    hdr()
    for r in rows:
        fr = [(30, r["date"].isoformat())]
        if r["sdate"]:
            fr.append((80, r["sdate"].isoformat()))
        fr += [(130, "NSE CM / NSE-EQ " + r["text"]), (430, f"{r['debit']:.2f}"), (480, f"{r['credit']:.2f}"), (525, f"{r['balance']:,.2f}")]
        line(*fr)
        line((130, "Settlement number: 2026123"))
    line((30, "Closing Ledger balance as on 2026-10-31:"))
    c.save()
    from pypdf import PdfReader, PdfWriter
    r = PdfReader(str(out / "raw.pdf"))
    w = PdfWriter()
    for p in r.pages:
        w.add_page(p)
    w.encrypt(PASSWORD, algorithm="AES-256")
    with open(out / "ledger.pdf", "wb") as f:
        w.write(f)
    (out / "raw.pdf").unlink()
    (out / "ledger_truth.json").write_text(json.dumps({"conv": conv, "closing": str(bal), "n": len(rows),
                                                         "rows": [{"date": r["date"].isoformat(), "debit": str(r["debit"]), "credit": str(r["credit"]), "balance": str(r["balance"])} for r in rows]}))
    return rows


if __name__ == "__main__":
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    build(out, int(sys.argv[2]) if len(sys.argv) > 2 else 5, sys.argv[3] if len(sys.argv) > 3 else "credit")
    print("written ledger.pdf password", PASSWORD)
