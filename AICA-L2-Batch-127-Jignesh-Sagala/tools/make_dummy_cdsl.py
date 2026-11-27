"""Makes a MADE-UP CDSL-style Consolidated Account Statement for testing the reader.

All names, ISINs, folios and numbers are invented. The layout copies the shape of a real CDSL CAS:
  - cover with the period, 12-month value table, asset split
  - account-detail pages that also carry "ISIN : ... UCC : ..." rows
  - demat transactions, demat holdings (wrapped names, ISIN on another row, zero rows)
  - mutual fund transactions per scheme (opening, purchases, multi-line redemptions, closing)
  - mutual fund holdings table (wrapped names, ISIN glued to folio, zero-unit rows, Grand Total)
Blocks are drawn in shuffled order, so the order of text inside the PDF is not the reading order.

Use:  python make_dummy_cdsl.py OUTFOLDER [seed]
Writes cdsl_made_up.pdf (password Demo@2026) and cdsl_truth.json.
"""
import json
import random
import sys
from decimal import Decimal as D, ROUND_HALF_UP
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

PASSWORD = "Demo@2026"
W, H = A4
FUNDS = [
    ("Orion", "Flexi Cap Fund"), ("Orion", "Large Cap Fund"), ("Orion", "Small Cap Fund"),
    ("Kestrel", "Mid Cap Fund"), ("Kestrel", "Index Fund Nifty 50"), ("Kestrel", "Balanced Advantage Fund"),
    ("Meridian", "Multi Asset Allocation Fund"), ("Meridian", "Focused Equity Fund"),
    ("Falcon", "Liquid Fund"), ("Falcon", "Corporate Bond Fund"), ("Falcon", "Gilt Fund"),
    ("Aster", "Large and Mid Cap Fund"), ("Aster", "Infrastructure Fund"), ("Aster", "ELSS Tax Saver Fund"),
    ("Cobalt", "Nifty Next 50 Index Fund"), ("Cobalt", "Pharma and Healthcare Fund"),
    ("Sable", "Value Fund"), ("Sable", "Dividend Yield Fund"), ("Sable", "Momentum 30 Index Fund"),
    ("Juniper", "Technology Opportunities Fund"),
]
PLANS = [("Direct Plan - Growth", "Direct"), ("Regular Plan - Growth", "Regular")]
SHARES = [
    "Alpha Textiles Limited", "Bharat Power and Grid Limited", "Crest Pharma Limited", "Delta Motors Limited",
    "Everest Cement Limited", "Fortune Foods Limited", "Gamma Steel and Alloys Limited", "Helios Software Services Limited",
    "Indus Housing Finance Limited", "Jade Chemicals Limited", "Kiran Retail Limited", "Lotus Consumer Products Limited",
    "Metro Infra Projects Limited", "Nova Insurance Company Limited", "Orbit Gold ETF", "Pioneer Bank Limited",
    "Quartz Logistics Limited",
]


def q2(x):
    return x.quantize(D("0.01"), ROUND_HALF_UP)


def q3(x):
    return x.quantize(D("0.001"), ROUND_HALF_UP)


def q4(x):
    return x.quantize(D("0.0001"), ROUND_HALF_UP)


def inr(x, dp=2):
    """Indian digit grouping: 12,34,567.89"""
    x = D(x)
    neg = x < 0
    s = f"{abs(x):.{dp}f}"
    whole, _, frac = s.partition(".")
    if len(whole) > 3:
        head, tail = whole[:-3], whole[-3:]
        parts = []
        while len(head) > 2:
            parts.insert(0, head[-2:]); head = head[:-2]
        if head:
            parts.insert(0, head)
        whole = ",".join(parts + [tail])
    return ("-" if neg else "") + whole + (("." + frac) if dp else "")


def units_s(x):
    return f"{x:.3f}"


def wrap(text, n):
    words, lines, cur = text.split(), [], ""
    for w in words:
        if cur and len(cur) + 1 + len(w) > n:
            lines.append(cur); cur = w
        else:
            cur = (cur + " " + w).strip()
    if cur:
        lines.append(cur)
    return lines


def build(seed=7):
    rnd = random.Random(seed)
    # ---- mutual fund folios
    schemes = []
    used = set()
    k = 0
    for fh, nm in FUNDS:
        plan = PLANS[rnd.randint(0, 1)]
        key = (fh, nm, plan[1])
        if key in used:
            continue
        used.add(key)
        k += 1
        schemes.append({
            "code": f"{rnd.randint(100, 9999)}", "name": f"{fh} {nm} - {plan[0]}", "fund_house": fh,
            "isin": f"INF{k:03d}D{rnd.randint(10000, 99999)}",
            "folio": f"{rnd.randint(10**7, 10**10 - 1)}" + (f"/{rnd.randint(1, 99)}" if rnd.random() < 0.7 else ""),
            "nav": q4(D(rnd.uniform(12, 900))),
        })
    for s_ in schemes:
        s_["table"] = 1
    for idx in (0, 3, 5):                                            # same scheme, second folio (joint holder), own table
        cp = dict(schemes[idx])
        cp["folio"] = f"{rnd.randint(10**7, 10**10 - 1)}/{rnd.randint(1, 99)}"
        cp["code"] = schemes[idx]["code"]
        cp["table"] = 2
        cp["joint"] = True
        schemes.append(cp)
    # ---- transactions for the first 11 schemes: some purchases, some redemptions, a few zero closings
    for i, s in enumerate(schemes):
        s["txns"] = []
        if i >= 11 and not s.get("joint"):
            s["opening"] = None
            continue
        opening = q3(D(rnd.uniform(50, 4000))) if i != 7 else D("0.000")
        s["opening"] = opening
        bal = opening
        rows = []
        if i in (2, 9):                                           # redemption of everything: closing zero
            amt_units = bal
            rows.append(("red", amt_units))
        else:
            for _ in range(rnd.randint(1, 3)):
                if rnd.random() < 0.65 or bal < 30:
                    amount = D(rnd.choice([2000, 5000, 10000, 25000]))
                    price = s["nav"]
                    u = q3(amount / price)
                    rows.append(("pur", u, amount))
                    bal += u
                else:
                    u = q3(bal * D(str(rnd.choice([0.1, 0.25, 0.5]))))
                    rows.append(("red", u))
                    bal -= u
        if i in (2, 9):
            bal = D("0.000")
        s["closing"] = q3(bal)
        for r in rows:
            price = s["nav"]
            if r[0] == "pur":
                s["txns"].append({"date": f"{rnd.randint(1, 28):02d}-10-2026", "kind": "Purchase", "amount": r[2],
                                  "price": price, "units": r[1]})
            else:
                u = r[1]
                s["txns"].append({"date": f"{rnd.randint(1, 28):02d}-10-2026", "kind": "Redemption",
                                  "amount": -q2(u * price), "price": price, "units": -u})
        s["txns"].sort(key=lambda t: t["date"][:2])
        # keep opening + sum = closing exactly
        s["closing"] = q3(opening + sum((t["units"] for t in s["txns"]), D(0)))
    for i, s in enumerate(schemes):
        if s["opening"] is None:
            s["closing"] = q3(D(rnd.uniform(20, 9000))) if i not in (13, 17) else D("0.000")
        u = s["closing"]
        s["units"] = u
        s["value"] = q2(u * s["nav"])
        s["cost"] = q2(s["value"] * D(str(rnd.uniform(0.7, 1.15)))) if u > 0 else D("0.00")
        s["gain"] = s["value"] - s["cost"]
        s["gain_pct"] = q2(s["gain"] / s["cost"] * 100) if s["cost"] > 0 else D("0.00")
    # ---- demat holdings
    demat = []
    for i, nm in enumerate(SHARES):
        price = q4(D(rnd.uniform(15, 4200)))
        qty = D(rnd.choice([1, 3, 5, 10, 12, 25, 40, 75, 120, 300]))
        if i in (5, 12):                                             # zero rows ("--" balances)
            qty = D(0)
        demat.append({"isin": (f"INE{i + 1:03d}A0{rnd.randint(1000, 9999)}" if i % 6 != 4 else f"IN9{i + 1:03d}A{rnd.randint(10000, 99999)}"), "name": nm + " # EQUITY SHARES WITH FACE VALUE RS. " + str(rnd.choice([1, 2, 5, 10])) + "/- EACH",
                      "qty": qty, "price": price, "value": q2(qty * price)})
    # ---- totals
    mf_cost = sum((s["cost"] for s in schemes), D(0))
    mf_val = sum((s["value"] for s in schemes), D(0))
    dem_val = sum((x["value"] for x in demat), D(0))
    months = []
    base = mf_val + dem_val
    for m, label in enumerate(["Nov 2025", "Dec 2025", "Jan 2026", "Feb 2026", "Mar 2026", "Apr 2026", "May 2026",
                               "Jun 2026", "Jul 2026", "Aug 2026", "Sep 2026", "Oct 2026"]):
        months.append((label, q2(base * D(str(0.8 + 0.018 * m)))))
    months[-1] = ("Oct 2026", q2(base))
    totals = {t: (sum((x["cost"] for x in schemes if x["table"] == t), D(0)), sum((x["value"] for x in schemes if x["table"] == t), D(0))) for t in (1, 2)}
    return {"totals": totals, "schemes": schemes, "demat": demat, "mf_cost": mf_cost, "mf_val": mf_val, "dem_val": dem_val, "months": months}


# ----------------------------------------------------------------------------- drawing
class Pager:
    def __init__(self, path):
        self.c = canvas.Canvas(str(path), pagesize=A4)
        self.y = H - 40
        self.n = 1
        self.blocks = []              # (height, draw function(y_top))

    def add(self, height, fn):
        self.blocks.append((height, fn))

    def flush_page(self, shuffle_rnd):
        order = list(range(len(self.blocks)))
        shuffle_rnd.shuffle(order)
        pos, y = {}, H - 40
        for i, (h, fn) in enumerate(self.blocks):         # positions in reading order
            pos[i] = y
            y -= h
        for i in order:                                    # drawn in shuffled order
            self.blocks[i][1](pos[i])
        self.c.setFont("Helvetica", 7)
        self.c.drawString(W / 2 - 20, 20, f"Page {self.n} of 99")
        self.c.showPage()
        self.n += 1
        self.blocks = []

    def used(self):
        return sum(h for h, _ in self.blocks)


LH = 9.5
XS = (352, 396, 440, 490, 520, 545, 570)      # right edges of the 7 transaction number columns


def make_pdf(path, d, shuffle_seed=3):
    rnd = random.Random(shuffle_seed)
    P = Pager(path)
    c = P.c
    avail = H - 90

    def text(x, y, s, size=7.5, bold=False, right=False):
        c.setFont("Helvetica-Bold" if bold else "Helvetica", size)
        if right:
            c.drawRightString(x, y, s)
        else:
            c.drawString(x, y, s)

    def add_block(h, fn):
        if P.used() + h > avail:
            P.flush_page(rnd)
        P.add(h, fn)

    def page_break():
        if P.blocks:
            P.flush_page(rnd)

    # ===== page 1: cover
    def cover(y):
        text(40, y - 10, "Consolidated Account Statement (CAS) for securities held in demat", 9, True)
        text(40, y - 22, "form and investments in mutual funds for the period from 01-10-2026", 9, True)
        text(40, y - 34, "to 31-10-2026", 9, True)
        text(40, y - 46, "Investor: BusyMe    PAN: ABCDE1234F (made-up)", 9, True)
        text(40, y - 64, "Summary of Investments", 9, True)
    add_block(72, cover)
    # month table and split (page 3 in the real file)
    def months(y):
        text(40, y - 10, "Month-wise Portfolio Valuation (In `)   Change in `   Change in %", 8, True)
        yy = y - 22
        prev = None
        for lab, v in d["months"]:
            text(40, yy, lab)
            text(180, yy, inr(v), right=True)
            if prev is not None:
                ch = v - prev
                text(260, yy, inr(ch), right=True)
                text(320, yy, f"{ch / prev * 100:.2f}", right=True)
            prev = v
            yy -= LH
        text(40, yy - 6, "Asset Class   Value   Allocation", 8, True)
        text(40, yy - 18, "Equity"); text(180, yy - 18, inr(d["dem_val"]), right=True); text(260, yy - 18, "40.10", right=True)
        text(40, yy - 28, "Mutual Fund Folios"); text(180, yy - 28, inr(d["mf_val"]), right=True); text(260, yy - 28, "59.90", right=True)
        text(40, yy - 38, "Total"); text(180, yy - 38, inr(d["dem_val"] + d["mf_val"]), right=True); text(260, yy - 38, "100.00", right=True)
    add_block(12 * LH + 85, months)
    page_break()

    # ===== account-detail pages: "ISIN :" rows that are NOT transactions
    for s in d["schemes"]:
        def acct(y, s=s):
            text(40, y - 10, f"AMC Name : {s['fund_house']} Mutual Fund")
            text(40, y - 20, f"Scheme Name : {s['name']}")
            text(40, y - 30, f"Folio No : {s['folio']}   Mode of Holding : Single")
            text(40, y - 40, f"ISIN : {s['isin']}   UCC : MADEUP{s['code']}")
        add_block(46, acct)
    page_break()

    # ===== demat transactions (ignored by the reader)
    def dtx_head(y):
        text(40, y - 10, "ISIN  Security  Transaction  Description  Date  Credit Qty  Debit Qty  Stamp Duty", 7.5, True)
    add_block(16, dtx_head)
    for x in d["demat"][:8]:
        def dtx(y, x=x):
            text(40, y - 10, x["isin"]); text(110, y - 10, x["name"][:34])
            text(300, y - 10, "PAYOUT-CR"); text(400, y - 10, "05-10-2026"); text(470, y - 10, "10.000", right=True)
            text(40, y - 20, "More text for this credit row"); text(300, y - 20, "0")
        add_block(26, dtx)

    # ===== demat holdings
    def dhead(y):
        text(40, y - 10, "ISIN  Security  Current Bal  Free Bal  Lent Bal  Safekeep Bal  Pledged Bal  Market Price / Face Value  Value (`)", 6.5, True)
    page_break()
    add_block(18, dhead)
    for i, x in enumerate(d["demat"]):
        lines = wrap(x["name"], 34)
        variant = i % 3
        def mk(x=x, lines=lines, variant=variant):
            def draw(y):
                mid = len(lines) // 2
                def tail(yy):
                    if x["qty"] == 0:
                        for k2, xx in enumerate((300, 335, 370, 405, 440)):
                            text(xx, yy, "--")
                    else:
                        text(330, yy, units_s(x["qty"]), right=True)
                        for xx in (345, 370, 395):
                            text(xx, yy, "--")
                        text(450, yy, units_s(x["qty"]), right=True)
                    text(510, yy, f"{x['price']:.4f}", right=True)
                    text(560, yy, inr(x["value"]), right=True)
                for j, ln in enumerate(lines):
                    yy = y - 10 - j * LH
                    if variant == 0:
                        if j == 0:
                            text(40, yy, x["isin"]); text(100, yy, ln); tail(yy)
                        else:
                            text(100, yy, ln)
                    elif variant == 1:
                        if j == 0:
                            text(40, yy, x["isin"])
                        text(100, yy, ln)
                        if j == mid:
                            tail(yy)
                    else:
                        if j == 0:
                            text(40, yy, x["isin"])
                        else:
                            text(100, yy, ln)
                        if j == len(lines) - 1:
                            tail(yy)
            return draw
        add_block(len(lines) * LH + 8, mk())
    def dtotal(y):
        text(40, y - 10, f"Portfolio Value ` {inr(d['dem_val'])} as on 31-10-2026", 8, True)
    add_block(20, dtotal)
    page_break()

    # ===== MF transactions per scheme
    for s in d["schemes"]:
        if s["opening"] is None:
            continue
        def mk_tx(s=s):
            def draw(y):
                text(40, y - 10, f"{s['code']} - {s['name']}", 8, True)
                text(40, y - 20, f"ISIN :{s['isin']}   UCC : MADEUP{s['code']}")
                text(40, y - 30, f"Opening Balance {units_s(s['opening'])}")
                yy = y - 40
                for t in s["txns"]:
                    text(40, yy, t["date"])
                    if t["kind"] == "Purchase":
                        text(90, yy, "Purchase - Systematic Investment - DIRECT")
                        text(285, yy, "9" + str(rnd.randint(10**9, 10**10 - 1))[:9])
                        nums = [f"{t['amount']:.0f}", f"{t['price']:.4f}", f"{t['price']:.4f}", units_s(t["units"]), "10", "0", "0"]
                        for xx, nn in zip(XS, nums):
                            text(xx, yy, nn, right=True)
                        yy -= LH
                    else:
                        # description wraps over 3 lines; the numbers sit on the middle line
                        text(90, yy, "Redemption - Online Redemption -")
                        text(90, yy - LH, "Through Distributor Platform -")
                        text(90, yy - 2 * LH, "ORD" + str(rnd.randint(10**15, 10**16 - 1)))
                        nums = [f"{t['amount']:.2f}", f"{t['price']:.4f}", f"{t['price']:.4f}", units_s(t["units"]), "0", "0", "0"]
                        for xx, nn in zip(XS, nums):
                            text(xx, yy - LH, nn, right=True)
                        text(90, yy - 3 * LH, f"STT {abs(t['amount']) * D('0.00001'):.2f}")
                        yy -= 4 * LH
                text(40, yy, f"Closing Balance {units_s(s['closing'])}")
            return draw
        h = 30 + 4 * LH * len(s["txns"]) + 16
        add_block(h, mk_tx())
    page_break()

    # ===== MF holdings tables: table 1 (first holder) and table 2 (joint-holder folios), each with its own Grand Total
    for tbl in (1, 2):
        def mhead(y):
            text(40, y - 10, "Scheme Name   INSTRMNT   Folio No.   Closing Bal (Units)   NAV (`)   Cumulative Amount Invested (in INR)   Valuation (`)   Unrealised Gain/Loss   Gain/Loss(%)", 6, True)
        add_block(16, mhead)
        for i, s in enumerate([x for x in d["schemes"] if x["table"] == tbl]):
            lines = wrap(f"{s['code']} - {s['name']}", 26)
            glued = (i % 4 == 1)
            split = (i % 7 == 3 and len(lines) >= 3)
            def mk_h(s=s, lines=lines, glued=glued, split=split):
                def draw(y):
                    mid = len(lines) // 2
                    for j, ln in enumerate(lines):
                        yy = y - 10 - j * LH
                        text(40, yy, ln)
                        if split and j == mid - 1:
                            text(175, yy, s["isin"][:10])
                        if split and j == mid + 1:
                            text(175, yy, s["isin"][10:])
                        if j == mid:
                            if split:
                                text(235, yy, s["folio"])
                            elif glued:
                                text(175, yy, s["isin"] + s["folio"])
                            else:
                                text(175, yy, s["isin"]); text(235, yy, s["folio"])
                            u = "0" if s["units"] == 0 else units_s(s["units"])
                            text(335, yy, u, right=True)
                            text(375, yy, f"{s['nav']:.4f}" if s["units"] != 0 else f"{s['nav']:.2f}", right=True)
                            text(430, yy, inr(s["cost"]), right=True)
                            text(485, yy, inr(s["value"]), right=True)
                            text(535, yy, inr(s["gain"]), right=True)
                            text(570, yy, f"{s['gain_pct']:.2f}", right=True)
                return draw
            hh = len(lines) * LH + 8
            if P.used() + hh > avail:                    # the header repeats at the top of each new page, as in the real file
                P.flush_page(rnd)
                P.add(16, mhead)
            P.add(hh, mk_h())
        def gtotal(y, tbl=tbl):
            text(40, y - 10, f"Grand Total   {inr(d['totals'][tbl][0])}   {inr(d['totals'][tbl][1])}", 8, True)
        add_block(20, gtotal)
        page_break()
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


def _txn_truth(d):
    out, seen = {}, {}
    for s in d["schemes"]:
        if s["opening"] is None:
            continue
        seen[s["isin"]] = seen.get(s["isin"], 0) + 1
        key = s["isin"] if seen[s["isin"]] == 1 else f"{s['isin']}#{seen[s['isin']]}"
        out[key] = {"opening": str(s["opening"]), "closing": str(s["closing"]),
                    "units": [str(t["units"]) for t in s["txns"]], "kinds": [t["kind"] for t in s["txns"]]}
    return out


def truth(d):
    def f(x):
        return str(x)
    return {
        "mf_holdings": [{"isin": s["isin"], "folio": s["folio"], "units": f(s["units"]), "nav": f(s["nav"] if s["units"] != 0 else q2(s["nav"])), "cost": f(s["cost"]),
                         "value": f(s["value"]), "gain": f(s["gain"]), "gain_pct": f(s["gain_pct"])} for s in d["schemes"]],
        "mf_totals": [{"cost": f(d["totals"][t][0]), "value": f(d["totals"][t][1])} for t in (1, 2)],
        "mf_txn": _txn_truth(d),
        "demat": [{"isin": x["isin"], "qty": f(x["qty"]), "price": f(x["price"]), "value": f(x["value"])} for x in d["demat"]],
        "demat_total": f(d["dem_val"]),
        "months": [[lab, f(v)] for lab, v in d["months"]],
        "period": ["01-10-2026", "31-10-2026"],
    }


def main(argv):
    out = Path(argv[1]) if len(argv) > 1 else Path(".")
    seed = int(argv[2]) if len(argv) > 2 else 7
    out.mkdir(parents=True, exist_ok=True)
    d = build(seed)
    raw = out / "_raw.pdf"
    make_pdf(raw, d, shuffle_seed=seed + 100)
    encrypt(raw, out / "cdsl_made_up.pdf")
    raw.unlink()
    (out / "cdsl_truth.json").write_text(json.dumps(truth(d), indent=1), encoding="utf-8")
    print("written:", out / "cdsl_made_up.pdf", "and cdsl_truth.json;", len(d["schemes"]), "folios,", len(d["demat"]), "shares; password", PASSWORD)


if __name__ == "__main__":
    main(sys.argv)
