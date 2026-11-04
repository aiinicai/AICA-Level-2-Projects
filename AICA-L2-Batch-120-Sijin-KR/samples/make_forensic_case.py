"""Synthetic forensic case: ZENITH TRADING FZCO, financial year 2025 (all names, numbers and accounts are invented).

    python samples/make_forensic_case.py                 -> samples/forensic_case/        (the fraud case)
    python samples/make_forensic_case.py --clean OUT     -> OUT/                          (same company, no fraud: every forensic check should pass)

Fraud scenarios seeded in the case (each is found by a named check):
  holiday / weekend / night journals ........ FA-05      round-sum 'advances' and consultancy payments ... FA-05
  amounts just below the 50,000 approval limit FA-05      same person prepares and approves .............. FA-05
  backdated revenue ......................... FA-05      ghost vendor = employee's bank account ......... FA-06, FA-12
  vendor paid into a changed bank account ... FA-12      balance swept to an unapproved account ......... FA-12
  receipt passed straight out ............... FA-12      bank payments missing from the GL .............. FA-12
  forged / pasted / expired / over-limit signatures FA-11   revenue overstated, receivables up, no cash .... FA-13
  year-end sale reversed after year-end ..... FA-13      stock short, dispatched not billed, unrecorded . FA-14
Command to review the case (also in the README):
  python -m auditsignoff fa --case "ZENITH TRADING FZCO" --gl samples/forensic_case/gl.xlsx --period-end 2025-12-31 --years 2025 \
     --vendors samples/forensic_case/vendors.xlsx --employees samples/forensic_case/employees.xlsx --bank samples/forensic_case/bank_statement.xlsx \
     --mandate samples/forensic_case/mandate.xlsx --signatures samples/forensic_case/signatures --fs-data samples/forensic_case/fs_data.xlsx \
     --stock samples/forensic_case/stock_register.xlsx --holidays 2025-01-01 2025-12-02 2025-12-03 --related "Faisal Nazir" "Nazir Consultancy"
"""
import math
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

import openpyxl
from PIL import Image, ImageDraw

NAME, FY = "ZENITH TRADING FZCO", 2025
PE = datetime(2025, 12, 31)
HOLIDAYS = ["2025-01-01", "2025-12-02", "2025-12-03"]       # New Year; National Day (verify against the official calendar)

VENDORS = [("Alpha Supplies LLC", "AE070331234567890123456", "Dubai, Al Quoz", "0501110001"), ("Bright Services FZE", "AE120260001234567890001", "Sharjah, SAIF Zone", "0502220002"),
           ("Crest Logistics LLC", "AE450400000123456789012", "Dubai, Jebel Ali", "0503330003"), ("Delta Components Trading", "AE210350000987654321098", "Dubai, Deira", "0504440004"),
           ("Emirates Packaging LLC", "AE660230000555566667777", "Ajman, Industrial Area", "0505550005"), ("Falcon Freight LLC", "AE330360000111122223333", "Dubai, Al Qusais", "0506660006"),
           ("Gulf Electronics Wholesale", "AE880280000444455556666", "Dubai, Naif", "0507770007"), ("Horizon IT Services", "AE590500000222233334444", "Abu Dhabi, Mussafah", "0508880008")]
CUSTOMERS = ["Sky Retail LLC", "Marina Mart LLC", "Oasis Stores LLC", "Pearl Electronics", "Desert Gadgets LLC", "City Digital LLC"]
GHOST = ("Nazir Consultancy Services", "AE770331111122223333444", "Dubai, Karama", "0509990009")            # shares the culprit's account, address and phone
EMPLOYEES = [("Faisal Nazir", "AE770331111122223333444", "Dubai, Karama", "0509990009"), ("Rahul Menon", "AE120260005555666677778", "Dubai, Bur Dubai", "0504441234"),
             ("Aisha Khan", "AE440330000999988887777", "Sharjah, Al Nahda", "0505552345")]
UNAPPROVED = ("Gulf Horizon Trading", "AE990380000777788889999")
ALPHA_NEW = "AE550310000123123123123"                                                                       # Alpha's 'changed' account


# ---------------------------------------------------------------- signatures
def _catmull(pts, n=14):
    out, P = [], [pts[0]] + pts + [pts[-1]]
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for k in range(n):
            t = k / n
            out.append(tuple(0.5 * ((2 * p1[j]) + (-p0[j] + p2[j]) * t + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * t * t + (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * t ** 3) for j in (0, 1)))
    return out + [pts[-1]]


def _base(seed, n=9):
    r, x, pts = random.Random(seed), 30, []
    for _ in range(n):
        x += r.uniform(25, 45)
        pts.append((x, r.uniform(30, 120)))
    return pts


def _sign(pts, path, jitter=0.0, seed=0):
    r = random.Random(seed)
    sc, sh, rot = 1 + r.uniform(-.05, .05), r.uniform(-8, 8), r.uniform(-.04, .04)
    q = []
    for x, y in pts:
        x, y = x + r.gauss(0, jitter), y + r.gauss(0, jitter)
        xr = (x - 200) * math.cos(rot) - (y - 75) * math.sin(rot) + 200
        yr = (x - 200) * math.sin(rot) + (y - 75) * math.cos(rot) + 75
        q.append((xr * sc + sh, yr * sc + r.uniform(-4, 4)))
    im = Image.new("RGB", (420, 150), "white")
    ImageDraw.Draw(im).line(_catmull(q), fill=(15, 25, 90), width=3, joint="curve")
    im.save(path)


# ---------------------------------------------------------------- general ledger, bank, masters
def build(out, fraud=True):
    out = Path(out); (out / "signatures").mkdir(parents=True, exist_ok=True)
    r = random.Random(2025)
    gl, bank = [], []
    n = [1000]

    def post(d, dr, cr, amt, desc, user, appr, party, created=None):
        n[0] += 1
        v = f"JV{n[0]}"
        for acct, a, b in ((dr, amt, 0), (cr, 0, amt)):
            gl.append([d, created or d, v, acct, desc, a, b, user, appr, party])

    def bd(d, step=1):
        while d.weekday() >= 5 or d.strftime("%Y-%m-%d") in HOLIDAYS:
            d += timedelta(days=step)
        return d

    def wd(i, total):
        return bd(datetime(2025, 1, 2) + timedelta(days=int(i * 355 / total)))

    def strat(nn, lo=2.0, hi=4.9):                                  # evenly spread on a log scale (so the clean ledger conforms to Benford's law)
        qs = [(i + r.random()) / nn for i in range(nn)]
        r.shuffle(qs)
        return [round(10 ** (lo + (hi - lo) * q), 2) for q in qs]
    users = ["amal", "bashir", "chitra", "dev"]
    bank_rows = []                                                  # (date, narration, party, iban, debit, credit)
    # sales and receipts
    big = [120500.0, 143200.0, 168900.0, 205750.0, 262300.0, 318400.0]
    sa = strat(234) + big
    r.shuffle(sa)
    for i in range(240):
        d, a, c = wd(i, 240), sa[i], r.choice(CUSTOMERS)
        u = r.choice(users)
        post(d, "Trade receivables", "Revenue", a, "Sales invoice", u, "approver1", c)
        if r.random() < 0.82:
            rd = bd(d + timedelta(days=r.randint(15, 40)))
            if rd <= datetime(2025, 12, 24):
                post(rd, "Bank", "Trade receivables", a, "Customer receipt", u, "approver1", c)
                bank_rows.append((rd, "Customer receipt", c, "", 0, a))
    # purchases and vendor payments
    pa = strat(170)
    for i in range(170):
        d, a, (vn, iban, _, _) = wd(i, 170), pa[i], r.choice(VENDORS)
        u = r.choice(users)
        post(d, "Inventory", "Trade payables", a, "Supplier invoice", u, "approver1", vn)
        pd_ = bd(d + timedelta(days=r.randint(10, 30)))
        if pd_ <= datetime(2025, 12, 24):
            post(pd_, "Trade payables", "Bank", a, "Supplier payment", u, "approver1", vn)
            bank_rows.append((pd_, "Supplier payment", vn, iban, a, 0))
    for m in range(1, 13):                                          # payroll through WPS
        d = bd(datetime(2025, m, 28), -1)
        a = round(78000 + r.uniform(0, 4000), 2)
        post(d, "Salaries", "Bank", a, "Salaries WPS", "amal", "approver1", "Payroll")
        bank_rows.append((d, "WPS salary payment", "Payroll", "", a, 0))

    sigs = [("CHQ-10231", datetime(2025, 3, 14), 42000, "Omar Siddiqui", "", "omar_1.png"), ("CHQ-10288", datetime(2025, 5, 9), 88000, "Omar Siddiqui", "", "omar_2.png"),
            ("CHQ-10377", datetime(2025, 8, 30), 35000, "Leena Thomas", "", "leena_1.png"), ("CHQ-10350", datetime(2025, 9, 18), 48000, "Leena Thomas", "", "leena_2.png")]
    if fraud:
        # --- round-sum 'staff advances' by the finance manager, many on weekends, holidays and at night
        for i in range(60):
            d = wd(i, 60) + timedelta(days=r.randint(0, 2))
            a = r.choice([10000, 15000, 20000, 25000, 30000, 50000])
            post(d, "Staff advances", "Bank", a, "Staff advance - cash", "faisal", "faisal", "Faisal Nazir", created=d.replace(hour=23, minute=40) if i % 4 == 0 else None)
            bank_rows.append((d, "Cash withdrawal - advance", "Faisal Nazir", "", a, 0))
        for d in (datetime(2025, 1, 1), datetime(2025, 12, 2), datetime(2025, 12, 3), datetime(2025, 6, 7), datetime(2025, 6, 14)):   # holidays and Saturdays
            post(d, "Consultancy", "Bank", 45000, "Consultancy fee - cash", "faisal", "faisal", "Nazir Consultancy Services", created=d.replace(hour=22, minute=15))
            bank_rows.append((d, "Transfer", GHOST[0], GHOST[1], 45000, 0))
        # --- splitting below the 50,000 approval limit to the ghost vendor
        for k in range(6):
            d, a = datetime(2025, 8, 4) + timedelta(days=k * 3), 48600 + k * 130.5
            while d.weekday() >= 5:
                d += timedelta(days=1)
            post(d, "Consultancy", "Bank", a, "Consultancy services", "faisal", "approver1", "Nazir Consultancy Services")
            bank_rows.append((d, "Transfer", GHOST[0], GHOST[1], a, 0))
        # --- backdated revenue and a year-end sale reversed in January
        post(datetime(2025, 12, 29), "Trade receivables", "Revenue", 180000, "Adjustment", "faisal", "approver1", "Marina Mart LLC", created=datetime(2026, 2, 10, 11, 5))
        post(datetime(2025, 12, 30), "Trade receivables", "Revenue", 300000, "Year-end sale", "faisal", "approver1", "Gulf Horizon Trading")
        post(datetime(2026, 1, 8), "Revenue", "Trade receivables", 300000, "Credit note - sale returned", "faisal", "approver1", "Gulf Horizon Trading")
        # --- vendor paid into a changed account (recorded in the GL, wrong account in the bank)
        post(datetime(2025, 10, 15), "Trade payables", "Bank", 185000, "Supplier payment", "faisal", "approver1", "Alpha Supplies LLC")
        bank_rows.append((datetime(2025, 10, 15), "Supplier payment", "Alpha Supplies LLC", ALPHA_NEW, 185000, 0))
        # --- receipt passed through; balance swept; cash withdrawals - none of these reach the GL
        post(datetime(2025, 11, 10), "Bank", "Trade receivables", 420000, "Customer receipt", "amal", "approver1", "Sky Retail LLC")
        bank_rows.append((datetime(2025, 11, 10), "Customer receipt", "Sky Retail LLC", "", 0, 420000))
        bank_rows.append((datetime(2025, 11, 12), "Transfer", UNAPPROVED[0], UNAPPROVED[1], 415000, 0))
        for d in (datetime(2025, 9, 11), datetime(2025, 10, 9), datetime(2025, 11, 20)):
            bank_rows.append((d, "Cash withdrawal", "Self", "", 60000, 0))
        # signatures: pasted, expired, over limit, not on the mandate, forged
        sigs += [("CHQ-10340", datetime(2025, 7, 22), 61500, "Omar Siddiqui", "", "omar_3_pasted.png"), ("CHQ-10402", datetime(2025, 11, 4), 28000, "Leena Thomas", "", "leena_3.png"),
                 ("CHQ-10417", datetime(2025, 10, 20), 80000, "Leena Thomas", "", "leena_4.png"), ("CHQ-10431", datetime(2025, 12, 2), 49500, "Faisal Nazir", "", "faisal_1.png"),
                 ("CHQ-10455", datetime(2025, 12, 30), 1450000, "Omar Siddiqui", "", "omar_forged.png")]
    # ---- bank statement with running balance (the sweep is sized from the live balance)
    bank_rows.sort(key=lambda x: x[0])
    run, low = 0.0, 0.0
    for b in bank_rows:
        run += b[5] - b[4]
        low = min(low, run)
    opening = round(1_300_000 - low, 2)
    final, run = [], opening
    sweep_done = not fraud
    for b in bank_rows:
        if not sweep_done and b[0] > datetime(2025, 12, 29):
            amt_s = round((run * 0.93) / 1000) * 1000
            run -= amt_s
            final.append((datetime(2025, 12, 30), "Transfer", UNAPPROVED[0], UNAPPROVED[1], amt_s, 0, run))
            sweep_done = True
        run += b[5] - b[4]
        final.append((*b, run))
    if not sweep_done:
        amt_s = round((run * 0.93) / 1000) * 1000
        run -= amt_s
        final.append((datetime(2025, 12, 30), "Transfer", UNAPPROVED[0], UNAPPROVED[1], amt_s, 0, run))
    sweep_amt = next((f[4] for f in final if f[4] > 1_000_000), 0)
    if fraud:
        sigs = [(d_, dt, (sweep_amt if doc == "CHQ-10455" else a_), who, sec, img) for d_, dt, a_, who, sec, img in [(s[0], s[1], s[2], s[3], s[4], s[5]) for s in sigs] for doc in [d_]]
    gl.sort(key=lambda x: (x[0], x[2]))
    _xlsx(out / "gl.xlsx", ["Date", "Created On", "Voucher No", "Account", "Description", "Debit", "Credit", "Posted By", "Approved By", "Vendor"], gl)
    _xlsx(out / "bank_statement.xlsx", ["Date", "Narration", "Beneficiary Name", "Beneficiary IBAN", "Debit", "Credit", "Balance"],
          [[opening and datetime(2025, 1, 1), "Opening balance", "", "", 0, 0, opening]] + [list(f) for f in final])
    _xlsx(out / "vendors.xlsx", ["Vendor Name", "IBAN", "Address", "Phone", "TRN"], [[v[0], v[1], v[2], v[3], f"1001{i:011d}"] for i, v in enumerate(VENDORS + ([GHOST] if fraud else []), 1)])
    _xlsx(out / "employees.xlsx", ["Employee Name", "IBAN", "Address", "Phone"], [list(e) for e in EMPLOYEES])
    # ---- signatures and mandate
    S = out / "signatures"
    base = {"Omar Siddiqui": _base(11), "Leena Thomas": _base(23), "Faisal Nazir": _base(37)}
    _sign(base["Omar Siddiqui"], S / "specimen_omar.png"); _sign(base["Leena Thomas"], S / "specimen_leena.png")
    for i, (doc, dt, a_, who, sec, img) in enumerate(sigs):
        if img.endswith("pasted.png"):
            (S / img).write_bytes((S / "omar_1.png").read_bytes())
        elif img.endswith("forged.png"):                             # a rough imitation of Omar's signature
            rr = random.Random(99)
            _sign([(x + rr.gauss(0, 22), y + rr.gauss(0, 22)) for x, y in base[who]], S / img, 3, 7)
        else:
            _sign(base[who], S / img, 2.5, i + 1)
    _xlsx(S / "signature_register.xlsx", ["Document", "Date", "Amount", "Claimed Signatory", "Second Signatory", "Image"], [list(s) for s in sigs])
    _xlsx(out / "mandate.xlsx", ["Name", "Designation", "Single signing limit (AED)", "Joint signing above (AED)", "Specimen", "Valid from", "Valid to"],
          [["Omar Siddiqui", "Managing Director", 100000, 100000, "specimen_omar.png", datetime(2022, 1, 1), None],
           ["Leena Thomas", "Director", 50000, 50000, "specimen_leena.png", datetime(2022, 1, 1), datetime(2025, 9, 30)]])
    # ---- financial statements (CY, PY) and stock register
    glrev = sum(x[6] - x[5] for x in gl if x[3] == "Revenue")
    stock, book = _stock(r, fraud)
    R = lambda x: round(x, -3)
    if fraud:                                  # revenue overstated by 9%; receivables balloon; profit without cash; stock inflated; payables and opex squeezed
        rev = R(glrev * 1.09); prev = R(rev / 1.22)
        cogs, pcogs = R(rev * 0.60), R(prev * 0.67)
        rec, prec = R(rev * 0.386), R(prev * 0.18)
        inv, pinv = round(book * 1.18, -4), R(pcogs * 0.246)
        pay, ppay = R(cogs * 0.0795), R(pcogs * 0.137)
        sga, psga, ni, pni, cfo, pcfo = R(rev * 0.099), R(prev * 0.142), R(rev * 0.163), R(prev * 0.084), R(rev * 0.015), R(prev * 0.078)
        ppe, pppe, ltd, pltd, dep, pdep = R(rev * 0.14), R(prev * 0.16), R(rev * 0.06), R(prev * 0.085), R(rev * 0.026), R(prev * 0.029)
        ca, pca = rec + inv + R(rev * 0.15), prec + pinv + R(prev * 0.13)
        cl, pcl = R(rev * 0.109), R(prev * 0.157)
    else:                                      # everything grows in step
        g = 1.08
        rev, cogs = R(glrev), R(glrev * 0.66)
        sga, ni, cfo = R(rev * 0.14), R(rev * 0.06), R(rev * 0.075)
        rec, inv, pay = R(rev * 0.20), round(book, -3), R(cogs * 0.14)
        ppe, ltd, dep = R(rev * 0.15), R(rev * 0.07), R(rev * 0.026)
        ca = rec + inv + R(rev * 0.15); cl = R(rev * 0.12)
        prev, pcogs, psga, pni, pcfo, prec, pinv, ppay, pppe, pltd, pdep = (R(x / g) for x in (rev, cogs, sga, ni, cfo, rec, inv, pay, ppe, ltd, dep))
        pca, pcl = R(ca / g), R(cl / g)
    ta, pta = ca + ppe, pca + pppe
    cy = [rev, cogs, sga, dep, ni, cfo, rec, inv, pay, ca, ta, ppe, cl, ltd]
    py = [prev, pcogs, psga, pdep, pni, pcfo, prec, pinv, ppay, pca, pta, pppe, pcl, pltd]
    lab = ["Revenue", "Cost of sales", "Selling, general and administrative expenses", "Depreciation", "Net profit for the year", "Net cash from operating activities", "Trade receivables", "Inventories",
           "Trade payables", "Total current assets", "Total assets", "Property, plant and equipment", "Total current liabilities", "Long-term borrowings"]
    _xlsx(out / "fs_data.xlsx", ["Item", "CY 2025", "PY 2024"], [[a, b, c] for a, b, c in zip(lab, cy, py)])
    _xlsx(out / "stock_register.xlsx", ["Item", "Location", "Opening Qty", "GRN Qty", "Issued Qty", "Adjustment Qty", "Closing Book Qty", "Physical Count Qty", "Unit Cost", "Invoiced Sales Qty", "Invoiced Purchases Qty"], stock)
    return out


def _stock(r, fraud):
    names = ["Smartphone A12", "Smartphone B7", "Tablet 10in", "Laptop 15in", "Laptop 13in", "Monitor 27in", "Wireless earbuds", "Smart watch", "Power bank 20k", "USB-C charger", "HDMI cable",
             "Keyboard", "Mouse", "Webcam HD", "Router AX", "SSD 1TB", "Printer laser", "Toner black", "Docking station", "Speaker BT", "Camera action", "Projector mini", "Game console", "VR headset"]
    rows = []
    for i, nm in enumerate(names):
        op, grn = r.randint(60, 300), r.randint(120, 400)
        iss = r.randint(100, op + grn - 20)
        cost = r.choice([15, 25, 40, 60, 90, 160, 220, 320, 480])
        rows.append([nm, "Main warehouse - Dubai", op, grn, iss, 0, op + grn - iss, op + grn - iss, cost, iss, grn])
    if fraud:
        for i, frac in ((0, .35), (3, .30), (11, .40)):                       # stock missing at the count
            rows[i][7] = int(rows[i][6] * (1 - frac)); rows[i][8] = max(rows[i][8], 160)
        rows[3][8] = 480; rows[0][8] = 320
        for i, q in ((4, 55), (6, 70)):                                       # dispatched, not invoiced
            rows[i][9] = rows[i][4] - q; rows[i][8] = max(rows[i][8], 90)
        rows[9][10] = rows[9][3] + 140                                         # invoiced, never received
        rows[10][10] = rows[10][3] - 150; rows[10][8] = 60                    # received, not invoiced
        rows[13][6] += 90                                                      # roll-forward break
        rows[15][6], rows[15][7] = -35, -35                                    # negative stock
        rows[16][5] = -int(rows[16][2] * 0.25); rows[16][6] = rows[16][2] + rows[16][3] - rows[16][4] + rows[16][5]; rows[16][7] = rows[16][6]; rows[16][8] = 160
        rows[18][1] = "Third Party - Al Quoz"; rows[18][8] = 320
        rows[20][7] = rows[20][6] + 120; rows[20][8] = 220                      # surplus: unrecorded purchases
    book = sum(x[6] * x[8] for x in rows if x[6] > 0)
    return rows, book


def _xlsx(path, head, rows):
    wb = openpyxl.Workbook(); ws = wb.active
    ws.append(head)
    for r_ in rows:
        ws.append(r_)
    wb.save(path)


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["--clean"]:
        build(a[1] if len(a) > 1 else "forensic_case_clean", fraud=False)
    else:
        build(Path(__file__).parent / "forensic_case", fraud=True)
