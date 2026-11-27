"""Makes MADE-UP bank statements (locked PDFs) to test app/bank.py. No real data.

Layouts copy the SHAPE seen in masked probes: a Kotak-style savings statement (one amount column, running balance,
wrapped descriptions, summary page, Indian digit grouping) and an IndusInd-style customer statement (account
summary, term deposits, one block per account with Brought Forward and Carried Forward, western grouping).
Names, numbers and text are invented.

Use:  python tools/make_dummy_bank.py <out folder> [seed]
Writes kotak_a.pdf, kotak_b.pdf (b has a linked sweep line and an overdrawn stretch), indus_a.pdf, indus_b.pdf
(password Demo@2026) and bank_truth.json with the planted figures.
"""
import json
import random
import string
import sys
from datetime import date, timedelta
from decimal import Decimal as D, ROUND_HALF_UP
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

PASSWORD = "Demo@2026"
MON = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()


def q(x):
    return D(x).quantize(D("0.01"), rounding=ROUND_HALF_UP)


def group_indian(x):
    s = f"{abs(q(x)):.2f}"
    whole, frac = s.split(".")
    if len(whole) > 3:
        head, tail = whole[:-3], whole[-3:]
        parts = []
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        if head:
            parts.insert(0, head)
        whole = ",".join(parts + [tail])
    return ("-" if q(x) < 0 else "") + whole + "." + frac


def group_west(x):
    s = f"{abs(q(x)):,.2f}"
    return ("-" if q(x) < 0 else "") + s


class Layout:
    """Collects pages of lines; a line is a list of (x, text). Renders with a footer on every page."""

    def __init__(self, per_page=52):
        self.pages = [[]]
        self.per_page = per_page

    def add(self, *frags):
        if len(self.pages[-1]) >= self.per_page:
            self.pages.append([])
        self.pages[-1].append(list(frags))

    def new_page(self):
        if self.pages[-1]:
            self.pages.append([])

    def room(self):
        return self.per_page - len(self.pages[-1])

    def render(self, path, footer):
        c = canvas.Canvas(str(path), pagesize=A4)
        n = len(self.pages)
        for i, page in enumerate(self.pages, 1):
            y = 800
            for line in page:
                c.setFont("Helvetica", 7)
                for x, t in line:
                    c.drawString(x, y, t)
                y -= 11
            for fr in footer(i, n):
                c.setFont("Helvetica", 7)
                for x, t in fr:
                    c.drawString(x, y - 6, t)
                y -= 11
            c.showPage()
        c.save()


def lock(src, dst):
    from pypdf import PdfReader, PdfWriter
    r = PdfReader(str(src))
    w = PdfWriter()
    for p in r.pages:
        w.add_page(p)
    w.encrypt(PASSWORD, algorithm="AES-256")
    with open(dst, "wb") as f:
        w.write(f)


WORDS = ["GROCERY", "TRAVEL", "UTILITY", "RENT", "SALARY", "REFUND", "FUEL", "MEDICAL", "INSURANCE", "TRANSFER", "SERVICE", "FEES"]


def desc(rnd):
    kind = rnd.choice(["UPI", "NEFT", "IMPS", "RTGS", "CARD", "INT"])
    ref = "".join(rnd.choices(string.digits, k=12))
    name = " ".join(rnd.sample(WORDS, 2)).title()
    a = f"{kind}/{name}/{ref}"
    return a, f"{kind}-{ref}"


# ----------------------------------------------------------------------------- Kotak style
def build_kotak(rnd, path, variant):
    acct = "".join(rnd.choices(string.digits, k=10))
    start, end = date(2026, 10, 1), date(2026, 10, 31)
    opening = q(D(rnd.randint(20000, 400000)) + D(rnd.randint(0, 99)) / 100)
    n = rnd.randint(36, 70)
    days = sorted(rnd.randint(1, 31) for _ in range(n))
    rows, bal = [], opening
    for i, dd in enumerate(days, 1):
        amt = q(D(rnd.randint(1, 90000)) / 10 * D(rnd.choice([1, 1, 1, 10])) + D(rnd.randint(0, 99)) / 100)
        direction = rnd.choice(["in", "out"])
        if direction == "out" and variant == "a" and bal - amt < 0:
            direction = "in"
        if variant == "b" and i == n // 2:                    # force an overdrawn balance (shown with a minus sign)
            direction, amt = "out", q(bal + D(rnd.randint(1000, 50000)))
        bal = bal + amt if direction == "in" else bal - amt
        a, ref = desc(rnd)
        rows.append({"serial": i, "date": date(2026, 10, dd).isoformat(), "desc": a, "ref": ref, "amount": amt, "dir": direction, "balance": bal})
    closing = bal
    sweep_open = sweep_close = None
    lay = Layout()
    def head(first):
        if first:
            lay.add((30, "Account Statement"))
            lay.add((30, "01 Oct 2026 - 31 Oct 2026"))
            lay.add((30, f"Account No.{acct}"))
            lay.add((30, "BusyMe"))
            lay.add((30, "Account Type Savings A/c"))
            lay.add((30, "Nominee Registered"))
            lay.add((30, "MICR123456789 IFSC TEST0001234"))
        else:
            lay.add((30, "BusyMe"))
            lay.add((30, f"Account No.{acct}"))
            lay.add((30, "Account Statement01 Oct 2026 - 31 Oct 2026"))
        lay.add((30, "Savings Account Transactions"))
        lay.add((30, "#"), (45, "Date"), (100, "Description"), (300, "Chq/Ref. No."), (380, "Withdrawal (Dr.)"), (430, "Deposit (Cr.)"), (490, "Balance"))
    head(True)
    lay.add((30, "-"), (45, "-"), (100, "Opening Balance"), (300, "-"), (380, "-"), (430, "-"), (490, group_indian(opening)))
    for r in rows:
        if lay.room() < 3:
            lay.new_page()
            head(False)
        dt = date.fromisoformat(r["date"])
        text = r["desc"]
        cut = text.rfind("/", 0, 26) if len(text) > 26 else -1
        first, rest = (text[:cut], text[cut:]) if cut > 0 else (text, "")
        lay.add((30, str(r["serial"])), (45, f"{dt.day:02d} {MON[dt.month - 1]} {dt.year}"), (100, first), (300, r["ref"]),
                (380 if r["dir"] == "out" else 430, group_indian(r["amount"])), (490, group_indian(r["balance"])))
        if rest:
            lay.add((100, rest))
    lay.new_page()
    lay.add((30, "BusyMe"))
    lay.add((30, f"Account No.{acct}"))
    lay.add((30, "Account Statement01 Oct 2026 - 31 Oct 2026"))
    lay.add((30, "Account Summary"))
    lay.add((30, "Particulars"), (200, "Opening Balance"), (300, "Closing Balance"))
    lay.add((30, "Savings Account (SA):"), (200, group_indian(opening)), (300, group_indian(closing)))
    summary = [{"label": "Savings Account", "code": "SA", "open": opening, "close": closing}]
    total = None
    if variant == "b":
        sweep_open = q(D(rnd.randint(500000, 9000000)))
        sweep_close = q(sweep_open + D(rnd.randint(-100000, 100000)))
        lay.add((30, "ActiveMoney (AM):"), (200, group_indian(sweep_open)), (300, group_indian(sweep_close)))
        lay.add((30, "Total Balance (SA + AM):"), (200, group_indian(opening + sweep_open)), (300, group_indian(closing + sweep_close)))
        summary.append({"label": "ActiveMoney", "code": "AM", "open": sweep_open, "close": sweep_close})
        total = {"open": opening + sweep_open, "close": closing + sweep_close}
    lay.add((30, "Nominee Details"))
    lay.add((30, "Type of Nomination: Registered"))
    lay.add((30, "Nominee Name Made Up Person"))
    lay.new_page()
    lay.add((30, "BusyMe"))
    lay.add((30, "Important Information - invented filler text for the layout test only."))
    lay.add((30, "Abbreviations: UPI - invented, NEFT - invented, IMPS - invented"))
    lay.render(path.with_suffix(".raw.pdf"), lambda i, n: [[(30, "Statement Generated on 03 Nov 2026, 10:15 Page"), (210, str(i)), (225, "of")], [(30, str(n))]])
    lock(path.with_suffix(".raw.pdf"), path)
    path.with_suffix(".raw.pdf").unlink()
    return {"kind": "kotak", "account": acct, "opening": str(opening), "closing": str(closing), "rows": [
        {**r, "amount": str(r["amount"]), "balance": str(r["balance"])} for r in rows],
        "summary": [{**s, "open": str(s["open"]), "close": str(s["close"])} for s in summary],
        "total": ({"open": str(total["open"]), "close": str(total["close"])} if total else None)}


# ----------------------------------------------------------------------------- IndusInd style
def build_indus(rnd, path, variant):
    numeric = variant == "b"

    def acct():
        if numeric:
            return "".join(rnd.choices(string.digits, k=12))
        return f"{rnd.randint(10, 99)}" + "".join(rnd.choices(string.ascii_uppercase, k=7)) + f"{rnd.randint(100, 999)}"
    accts = [
        {"no": acct(), "type": "SAVINGS ACCOUNT ON-NRE", "product": "SAVINGS ACCOUNT ON", "cur": "INR", "n": rnd.randint(18, 45) if variant == "a" else rnd.randint(50, 70), "scale": 1},
        {"no": acct(), "type": "SAVINGS ACCOUNT ON-NRO", "product": "SAVINGS ACCOUNT ON", "cur": "INR", "n": rnd.randint(1, 6), "scale": 1},
        {"no": acct(), "type": "FOREIGN CURRENCY ACCOUNT (FC)", "product": "FOREIGN CURRENCY ACCOUNT (FC)", "cur": "USD", "n": 0 if variant == "a" else 2, "scale": D("0.05")},
    ]
    if variant == "b":                       # in the real file two accounts print the same account token
        accts[2]["no"] = accts[1]["no"]
    for a in accts:
        bf = q(D(rnd.randint(1000, 900000)) * a["scale"] + D(rnd.randint(0, 99)) / 100)
        bal, rows = bf, []
        days = sorted(rnd.randint(1, 31) for _ in range(a["n"]))
        for dd in days:
            amt = q(D(rnd.randint(100, 150000)) * a["scale"] / 10 + D(rnd.randint(0, 99)) / 100)
            direction = rnd.choice(["in", "out"])
            if direction == "out" and bal - amt < 0:
                direction = "in"
            bal = bal + amt if direction == "in" else bal - amt
            d1, ref = desc(rnd)
            rows.append({"date": date(2026, 10, dd), "desc": d1, "amount": amt, "dir": direction, "balance": bal})
        a["bf"], a["cf"], a["rows"] = bf, bal, rows
    fds = []
    kinds = ["TERM DEPOSIT - NRO", "TERM DEPOSIT - NRE", "NRE TAX SAVER DEPOSIT", "TERM DEPOSIT - NRE", "TERM DEPOSIT - NRO"]
    for k in kinds:
        s = date(2024, rnd.randint(1, 12), rnd.randint(1, 28))
        fds.append({"no": acct(), "type": k, "start": s, "maturity": s + timedelta(days=rnd.choice([365, 730, 1095])), "cur": "INR",
                    "rate": D(rnd.randint(600, 760)) / 100, "lien": D(0), "value": q(D(rnd.randint(50000, 9000000)) + D(rnd.randint(0, 99)) / 100)})
    s = date(2025, rnd.randint(1, 12), rnd.randint(1, 28))
    fds.append({"no": acct(), "type": "TERM DEPOSIT - FC", "start": s, "maturity": s + timedelta(days=365), "cur": "USD", "rate": D("4.25"), "lien": D(0),
                "value": q(D(rnd.randint(1000, 90000)) + D(rnd.randint(0, 99)) / 100)})

    lay = Layout(per_page=48)
    cust = "".join(rnd.choices(string.digits, k=8))
    lay.add((30, "STATEMENT OF CUSTOMER"))
    lay.add((30, cust))
    lay.add((30, "BusyMe"), (330, "Date : 02-Nov-2026"))
    lay.add((30, "Some Street Test City"), (330, "Period : 01-Oct-2026 To 31-Oct-2026"))
    lay.add((30, f"Summary for Customer ID - {cust}"))
    lay.add((30, "Current / Savings Account - Summary"))
    lay.add((30, "Account No"), (100, "Account Type"), (250, "Holder Status"), (320, "Holder Name"), (400, "Currency"), (440, "Lien Amount"), (500, "Balance"))
    inr = [a for a in accts if a["cur"] == "INR"]
    fc = [a for a in accts if a["cur"] != "INR"]
    for grp in (inr, fc):
        for a in grp:
            lay.add((30, a["no"]), (100, a["type"]), (250, "Primary"), (320, "BusyMe"), (400, a["cur"]), (440, "0.00"), (500, group_west(a["cf"])))
        lay.add((30, "Total"), (500, group_west(sum((a["cf"] for a in grp), D(0)))))
    lay.new_page()
    lay.add((30, "STATEMENT OF CUSTOMER"))
    lay.add((30, cust))
    lay.add((30, "Term / Fixed Deposits - Summary"))
    for grp in ([f for f in fds if f["cur"] == "INR"], [f for f in fds if f["cur"] != "INR"]):
        lay.add((30, "Account Number"), (100, "Account Type"), (240, "Holder Status"), (300, "Holder Name"), (360, "Value Date"), (410, "Maturity Date"), (460, "Currency"), (490, "Rate"), (515, "Lien Amount"), (555, "Current Value"))
        for f in grp:
            fmt = lambda x: f"{x.day:02d}-{MON[x.month - 1].upper()}-{x.year % 100:02d}"
            lay.add((30, f["no"]), (100, f["type"]), (240, "Primary"), (300, "BusyMe"), (360, fmt(f["start"])), (410, fmt(f["maturity"])),
                    (460, f["cur"]), (490, f"{f['rate']:.2f}%"), (515, "0.00"), (555, group_west(f["value"])))
            lay.add((100, "(REINVESTMENT) MADE UP"))
        lay.add((30, "Total"), (555, group_west(sum((f["value"] for f in grp), D(0)))))
    for a in accts:
        lay.new_page()
        first = True
        i = 0
        while True:
            lay.add((30, "STATEMENT OF CUSTOMER"))
            lay.add((30, cust))
            lay.add((30, "Transaction Summary for Savings Account, Current Account and Fixed Account."))
            lay.add((30, "Account Number"), (100, "Name"), (250, "Holding Status"), (350, "Customer ID"))
            lay.add((30, a["no"]), (100, "MADE UP C"), (250, "Primary Holder"), (350, cust))
            lay.add((30, "Product Description: " + a["product"]), (330, "Branch Address : Test Road, Test City"))
            lay.add((30, f"Statement Period : 01-Oct-2026 TO 31-Oct-2026"), (330, "Email Id For E Statement : TEST@EXAMPLE.COM"))
            lay.add((30, "Date"), (90, "Particulars"), (300, "Chq No/Ref No"), (380, "Withdrawal"), (430, "Deposit"), (490, "Balance"))
            if first:
                lay.add((30, "01-Oct-2026"), (90, "Brought Forward"), (490, group_west(a["bf"])))
                first = False
            elif variant == "b":                                  # some banks print a page-level Brought Forward
                lay.add((30, "15-Oct-2026"), (90, "Brought Forward"), (490, group_west(a["rows"][i - 1]["balance"])))
            while i < len(a["rows"]) and lay.room() > 4:
                r = a["rows"][i]
                text = r["desc"]
                cut = text.rfind("/", 0, 30) if len(text) > 30 else -1
                f1, rest = (text[:cut], text[cut:]) if cut > 0 else (text, "")
                lay.add((30, f"{r['date'].day:02d}-{MON[r['date'].month - 1]}-{r['date'].year}"), (90, f1),
                        (380 if r["dir"] == "out" else 430, group_west(r["amount"])), (490, group_west(r["balance"])))
                if rest:
                    lay.add((90, rest))
                i += 1
            if i >= len(a["rows"]):
                lay.add((30, "31-Oct-2026"), (90, "Carried Forward"), (490, group_west(a["cf"])))
                lay.add((30, "This is a computer generated statement (invented filler)."))
                break
            if variant == "b":                                    # ... and a page-level Carried Forward
                lay.add((30, "15-Oct-2026"), (90, "Carried Forward"), (490, group_west(a["rows"][i - 1]["balance"])))
            lay.new_page()
    lay.render(path.with_suffix(".raw.pdf"), lambda i, n: [[(30, "Registered office: MADE UP BANK, Test Road, Page"), (300, f"{i} of {n}")]])
    lock(path.with_suffix(".raw.pdf"), path)
    path.with_suffix(".raw.pdf").unlink()
    return {"kind": "indus", "accounts": [{"no": a["no"], "type": a["type"], "product": a["product"], "cur": a["cur"], "bf": str(a["bf"]), "cf": str(a["cf"]),
                                           "rows": [{"date": r["date"].isoformat(), "amount": str(r["amount"]), "dir": r["dir"], "balance": str(r["balance"])} for r in a["rows"]]} for a in accts],
            "fds": [{"no": f["no"], "type": f["type"], "start": f["start"].isoformat(), "maturity": f["maturity"].isoformat(), "cur": f["cur"], "rate": str(f["rate"]), "value": str(f["value"])} for f in fds]}


def main(argv):
    out = Path(argv[1])
    out.mkdir(parents=True, exist_ok=True)
    seed = int(argv[2]) if len(argv) > 2 else 7
    rnd = random.Random(seed)
    truth = {}
    for name, fn, var in (("kotak_a.pdf", build_kotak, "a"), ("kotak_b.pdf", build_kotak, "b"), ("indus_a.pdf", build_indus, "a"), ("indus_b.pdf", build_indus, "b")):
        truth[name] = fn(rnd, out / name, var)
    (out / "bank_truth.json").write_text(json.dumps(truth, indent=1))
    print("written 4 made-up bank statements in", out, "password", PASSWORD)


if __name__ == "__main__":
    main(sys.argv)
