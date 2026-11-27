"""Makes MADE-UP Zerodha-style contract notes (locked PDFs) to test app/zcn.py. No real data.

Layout copies the shape seen in a masked probe of a real note: header page, summary page (12 numbers per ISIN),
charges page, notes page, trade page. Names, ISINs, prices and numbers are invented.
Use:  python tools/make_dummy_zcn.py <out folder> [seed] [number of days]
Writes <day>-contract-notes_ASM339.pdf (password Demo@2026) and zcn_truth.json with the planted figures.
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
NAMES = ["ALPHA INDUSTRIES", "BETA BANK", "GAMMA POWER", "DELTA FOODS", "EPSILON PHARMA", "ZETA MOTORS", "ETA FINANCE", "THETA STEEL"]


def q(x, p="0.01"):
    return D(x).quantize(D(p), rounding=ROUND_HALF_UP)


def inr(x):
    """12,345.67 style with brackets for negatives (Indian grouping not needed for the reader)."""
    s = f"{abs(x):,.2f}"
    return f"({s})" if x < 0 else s


def build_day(rnd, day, no):
    secs = rnd.sample(range(len(NAMES)), rnd.randint(2, 4))
    trades, summary = [], []
    for i in secs:
        isin = f"INE{100 + i:03d}A01{rnd.randint(100, 999)}"
        name = NAMES[i]
        base = D(rnd.randint(40, 2500)) + D(rnd.randint(0, 99)) / 100
        sides = ["B"] * rnd.randint(1, 4) + (["S"] if rnd.random() < 0.3 else [])
        for sd in sides:
            qty = rnd.randint(1, 60)
            price = q(base * (D(1) + D(rnd.randint(-15, 15)) / 1000), "0.0001")
            tot = q(qty * price)
            trades.append({"order_no": str(rnd.randint(10 ** 15, 10 ** 16 - 1)), "order_time": f"{rnd.randint(9, 15):02d}:{rnd.randint(0, 59):02d}:{rnd.randint(0, 59):02d}",
                           "trade_no": str(rnd.randint(10 ** 6, 10 ** 9)), "trade_time": f"{rnd.randint(9, 15):02d}:{rnd.randint(0, 59):02d}:{rnd.randint(0, 59):02d}",
                           "name": name + "-EQ", "isin": isin, "side": sd, "qty": qty, "p1": price, "p2": q(price, "0.01"), "total": tot})
    for isin in dict.fromkeys(t["isin"] for t in trades):
        tt = [t for t in trades if t["isin"] == isin]
        b = [t for t in tt if t["side"] == "B"]
        s = [t for t in tt if t["side"] == "S"]
        bq, bv = sum(t["qty"] for t in b), sum((t["total"] for t in b), D(0))
        sq, sv = sum(t["qty"] for t in s), sum((t["total"] for t in s), D(0))
        bb = rnd.choice([D(0), D("50.00"), q(bv * D("0.0005"))]) if bq else D(0)    # brokerage on the buy side
        sb_ = rnd.choice([D(0), D("50.00"), q(sv * D("0.0005"))]) if sq else D(0)  # brokerage on the sell side
        bw = q(bv / bq, "0.0001") if bq else D(0)
        sw = q(sv / sq, "0.0001") if sq else D(0)
        bval = bv + bb                      # summary buy value includes brokerage
        sval = sv - sb_                     # summary sell value is after brokerage
        summary.append({"isin": isin, "name": tt[0]["name"], "buy_qty": bq, "buy_wap": bw, "buy_brok": q(bb / bq, "0.0001") if bq else D(0),
                        "buy_wap_net": q(bval / bq, "0.0001") if bq else D(0), "buy_value": bval,
                        "sell_qty": sq, "sell_wap": sw, "sell_brok": q(sb_ / sq, "0.0001") if sq else D(0),
                        "sell_wap_net": q(sval / sq, "0.0001") if sq else D(0), "sell_value": sval,
                        "net_qty": abs(bq - sq), "net_total": abs(sval - bval), "_brok": bb + sb_, "_gross_buy": bv, "_gross_sell": sv})
    buy = sum((s["_gross_buy"] for s in summary), D(0))
    sell = sum((s["_gross_sell"] for s in summary), D(0))
    brok = sum((s["_brok"] for s in summary), D(0))
    turnover = buy + sell
    exch = q(turnover * D("0.0000297"))
    sebi = q(turnover * D("0.000001"))
    stt = q(turnover * D("0.001"))
    stamp = q(buy * D("0.00015"))
    gst = q((brok + exch + sebi) * D("0.09"))
    obligation = sell - buy
    charges = [("Taxable value of Supply (Brokerage) ()1", -brok), ("Exchange transaction charges ()2", -exch),
               ("CGST (@9% of Brokerage, SEBI, Stamp & Transaction Charges) ()3", -gst),
               ("SGST (@9% of Brokerage, SEBI, Stamp & Transaction Charges) ()3", -gst),
               ("Securities transaction tax ()", -stt), ("SEBI turnover fees ()", -sebi), ("Stamp duty ()", -stamp)]
    net = obligation + sum((c[1] for c in charges), D(0))
    settle = day + timedelta(days=1)
    return {"trade_date": day, "settle_date": settle, "settle_no": f"2026{rnd.randint(100, 999)}", "contract_no": f"CNT-26/27-{rnd.randint(10 ** 8, 10 ** 9 - 1)}",
            "summary": summary, "trades": trades, "obligation": obligation, "charges": charges, "net": net}


def make_pdf(path, d):
    c = canvas.Canvas(str(path), pagesize=A4)
    state = {"y": 800}

    def row(t):
        c.setFont("Helvetica", 7)
        c.drawString(30, state["y"], t)
        state["y"] -= 11

    def page():
        c.showPage()
        state["y"] = 800

    row("COMBINED CONTRACT NOTE CUM TAX INVOICE")
    row("(Tax Invoice under Section 31 of GST Act)")
    row("Made-up Broking Ltd, 1 Test Road, Test City, India")
    row(f"Contract Note No: {d['contract_no']} NSE-Cash NSE-F&O")
    row(f"Trade Date: {d['trade_date'].strftime('%d/%m/%Y')} Settlement No: {d['settle_no']}")
    row(f"Settlement Date: {d['settle_date'].strftime('%d/%m/%Y')}")
    row("UCC: TST001")
    row("BusyMe    PAN: ABCDE1234F (made-up)")
    page()
    row("Dear BusyMe,")
    row("We have bought/sold for you and on your account the following transactions:")
    row("Equity")
    row("Security Description Buy Sell Net Obligation for ISIN")
    for s in d["summary"]:
        nums = [str(s["buy_qty"]), f"{s['buy_wap']:.4f}", f"{s['buy_brok']:.4f}", f"{s['buy_wap_net']:.4f}", f"{s['buy_value']:.2f}",
                str(s["sell_qty"]), f"{s['sell_wap']:.4f}", f"{s['sell_brok']:.4f}", f"{s['sell_wap_net']:.4f}", f"{s['sell_value']:.2f}",
                str(s["net_qty"]), f"{s['net_total']:.2f}"]
        row(f"{s['isin']} {s['name']} " + " ".join(nums))
    row("1 WAP (Weighted Average Price) = Total buy/sell value for ISIN divided by total number of shares")
    page()
    row("NSE-Cash NSE-F&O NET TOTAL")
    row(f"Pay in/Pay out obligation () {inr(d['obligation'])} 0.00 {inr(d['obligation'])}")
    for label, v in d["charges"]:
        row(f"{label} {inr(v)} {inr(v)}")
    row("Clearing charges ()")
    row("IGST (@18% of Brokerage, SEBI, Stamp & Transaction Charges) ()3")
    row(f"Net amount receivable/(payable by client) () {inr(d['net'])} 0.00 {inr(d['net'])}")
    page()
    row("1In the case of cross currency trades the exchange rate is applied.")
    row("2NSE exchange transaction charges are credited to the Investor Protection Fund.")
    row("Tax is levied on reverse charge basis : No")
    page()
    row("Annexure A")
    row("Equity")
    row("Order No. Order Time Trade No. Trade Time Security / Contract Description Buy(B) / Sell(S) Exchange Quantity Net Rate Closing Rate Net Total")
    for t in d["trades"]:
        tot = -t["total"] if t["side"] == "B" else t["total"]
        row(f"{t['order_no']} {t['order_time']} {t['trade_no']} {t['trade_time']} {t['name']}/{t['isin']} {t['side']} NSE {t['qty']} {t['p1']:.4f} {t['p2']:.2f} {inr(tot)}")
    c.save()


def encrypt(src, dst):
    from pypdf import PdfReader, PdfWriter
    r = PdfReader(str(src))
    w = PdfWriter()
    for p in r.pages:
        w.add_page(p)
    w.encrypt(PASSWORD, algorithm="AES-256")
    with open(dst, "wb") as f:
        w.write(f)


def truth(d):
    return {"trade_date": d["trade_date"].isoformat(), "settle_date": d["settle_date"].isoformat(), "settle_no": d["settle_no"], "contract_no": d["contract_no"],
            "summary": [{k: (str(v) if not isinstance(v, int) else v) for k, v in s.items() if not k.startswith("_")} for s in d["summary"]],
            "trades": [{k: (str(v) if not isinstance(v, int) else v) for k, v in t.items()} for t in d["trades"]],
            "obligation": str(d["obligation"]), "net": str(d["net"]), "charges": [[a, str(b)] for a, b in d["charges"]]}


def main(argv):
    out = Path(argv[1])
    out.mkdir(parents=True, exist_ok=True)
    seed = int(argv[2]) if len(argv) > 2 else 5
    n = int(argv[3]) if len(argv) > 3 else 3
    rnd = random.Random(seed)
    day = date(2026, 10, 1)
    tr = {}
    for i in range(n):
        day += timedelta(days=rnd.randint(1, 5))
        while day.weekday() > 4:
            day += timedelta(days=1)
        d = build_day(rnd, day, i)
        name = f"{day.strftime('%d-%m-%Y')}-contract-notes_ASM339.pdf"
        raw = out / ("raw_" + name)
        make_pdf(raw, d)
        encrypt(raw, out / name)
        raw.unlink()
        tr[name] = truth(d)
    (out / "zcn_truth.json").write_text(json.dumps(tr, indent=1))
    print("written", n, "made-up contract notes in", out, "password", PASSWORD)


if __name__ == "__main__":
    main(sys.argv)
