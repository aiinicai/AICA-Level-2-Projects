"""Generates three SYNTHETIC trial balance + general ledger test sets in different export layouts (fictional company, no real data).

  1_Tally_*   Tally Prime style  (AED)  - grouped Trial Balance with group sub-totals and party ledgers, two-row 'Closing Balance' header;
                                          'Ledger Vouchers' GL printed as one block per ledger
  2_Oracle_*  Oracle GL style    (USD)  - report banner, segmented account (Company.CostCentre.Natural.Sub.Product), Beginning / Period / Ending
                                          Dr-Cr columns, repeated page headers, company and report totals; journal-line GL with Entered and Accounted columns
  3_Random_*  Ad-hoc 'someone's Excel' (EUR) - cover sheet, a single signed amount column with text amounts, Dr/Cr marker, notes, section sub-totals;
                                          GL with abbreviated headings

All three reconcile to the same underlying figures as the other sample data (see sample_data/make_sample_data.py).
Run:  python sample_data/make_format_samples.py [output_dir]
"""
from __future__ import annotations

import json
import random
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font

sys.path.insert(0, str(Path(__file__).resolve().parent))
from make_sample_data import ENTITY, YEAR, build  # noqa: E402

BOLD = Font(bold=True)
NUM = "#,##0.00"


# ---------------------------------------------------------------------------------------------- Tally
TALLY_GROUPS = [   # (group, [sub-groups or ledger codes]) ; sub-group = (name, [codes]) ; code strings are ledgers
    ("Capital Account", ["3000", "3100"]),
    ("Loans (Liability)", ["2300", "2200"]),
    ("Current Liabilities", [("Sundry Creditors", ["2000"]), ("Duties & Taxes", ["2500"]), ("Provisions", ["2400"]), "2100"]),
    ("Fixed Assets", ["1500", "1510"]),
    ("Investments", ["1400", "1410"]),
    ("Current Assets", [("Bank Accounts", ["1000"]), ("Cash-in-hand", ["1010"]), ("Sundry Debtors", ["1100"]), "1110",
                        ("Loans & Advances (Asset)", ["1200"]), ("Deposits & Prepayments", ["1300"])]),
    ("Suspense A/c", ["1900"]),
    ("Sales Accounts", ["4000", "4100"]),
    ("Purchase Accounts", ["5000"]),
    ("Indirect Incomes", ["4200", "4300", "4500", "4600"]),
    ("Indirect Expenses", ["6000", "6010", "6020", "6030", "6040", "6050", "6060", "6070", "6080", "6090", "6100", "6110", "6120", "6130", "6140", "6150", "6160"]),
]
TALLY_NAMES = {"3100": "Profit & Loss A/c (opening)", "1000": "Emirates NBD - Current A/c", "1010": "Cash", "1900": "Suspense Account"}
CUST = ["Hamdan Trading Co", "Skyline Contracting LLC", "Desert Retail FZE", "Pearl Distribution", "Falcon Industries LLC"]
SUPP = ["Gulf Wholesale FZE", "Al Reem Supplies LLC", "Orient Logistics", "Noor Legal Consultants"]


def tally_prepare(tb, gl, rnd):
    """Tally keeps debtors and creditors as one ledger per party: split the receivable / payable GL lines across party ledgers.
    Returns (gl lines with a 'ledger' key, {code: [(party, closing balance)]}) so the TB and GL agree to the cent."""
    parties = {"1100": CUST[:4], "2000": SUPP}
    out, totals = [], {}
    for l in gl:
        if l["code"] in parties:
            ps = parties[l["code"]]
            amt = round(l["debit"] - l["credit"], 2)
            shares = [rnd.random() + 0.4 for _ in ps]
            t = sum(shares)
            parts = [round(amt * x / t, 2) for x in shares]
            parts[-1] = round(amt - sum(parts[:-1]), 2)
            for pname, a in zip(ps, parts):
                m = dict(l)
                m["ledger"], m["debit"], m["credit"] = pname, max(a, 0.0), max(-a, 0.0)
                out.append(m)
                totals.setdefault(l["code"], {}).setdefault(pname, 0.0)
                totals[l["code"]][pname] = round(totals[l["code"]][pname] + a, 2)
        else:
            m = dict(l)
            m["ledger"] = TALLY_NAMES.get(l["code"], l["name"])
            out.append(m)
    return out, {c: list(v.items()) for c, v in totals.items()}


def _split(v, parties, rnd):
    shares = [rnd.random() + 0.4 for _ in parties]
    t = sum(shares)
    a = [round(v * s / t, 2) for s in shares]
    a[-1] = round(v - sum(a[:-1]), 2)
    return a


def write_tally_tb(path, tb, ccy, rnd, party_totals):
    bal = {c: v for c, _, v in tb}
    name = {c: TALLY_NAMES.get(c, n) for c, n, _ in tb}
    wb = Workbook()
    ws = wb.active
    ws.title = "Trial Balance"
    ws["A1"] = ENTITY
    ws["A1"].font = Font(bold=True, size=13)
    ws["A2"] = "Office 1204, Business Bay, Dubai, United Arab Emirates"
    ws["A3"] = "Trial Balance"
    ws["A3"].font = BOLD
    ws["A4"] = f"1-Jan-{YEAR} to 31-Dec-{YEAR}"
    ws["A5"] = f"(amounts in {ccy})"
    ws["A7"], ws["B7"] = "Particulars", "Closing Balance"
    ws.merge_cells("B7:C7")
    ws["B8"], ws["C8"] = "Debit", "Credit"
    for c in ("A7", "B7", "A8", "B8", "C8"):
        ws[c].font = BOLD
    ws["B7"].alignment = Alignment(horizontal="center")
    r = 9
    grand_d = grand_c = 0.0

    def put(label, v, indent, bold):
        nonlocal r
        cell = ws.cell(r, 1, label)
        cell.alignment = Alignment(indent=indent)
        if bold:
            cell.font = BOLD
        if abs(v) > 0.004:
            col = 2 if v > 0 else 3
            ws.cell(r, col, round(abs(v), 2)).number_format = NUM
            if bold:
                ws.cell(r, col).font = BOLD
        r += 1

    def ledgers(code, indent):
        v = bal[code]
        if code in party_totals:
            for p_, a in party_totals[code]:
                put(p_, a, indent, False)
        else:
            put(name[code], v, indent, False)

    def total(item):
        if isinstance(item, str):
            return bal[item]
        return sum(total(i) for i in item[1])

    for gname, items in TALLY_GROUPS:
        gt = sum(total(i) for i in items)
        put(gname, gt, 0, True)
        for it in items:
            if isinstance(it, str):
                ledgers(it, 1)
            else:
                put(it[0], total(it), 1, True)
                for code in it[1]:
                    ledgers(code, 2)
        grand_d += max(gt, 0)
        grand_c += max(-gt, 0)
    r += 0
    ws.cell(r, 1, "Grand Total").font = BOLD
    ws.cell(r, 2, round(grand_d, 2)).number_format = NUM
    ws.cell(r, 3, round(grand_c, 2)).number_format = NUM
    ws.cell(r, 2).font = ws.cell(r, 3).font = BOLD
    for k, w in zip("ABC", (58, 20, 20)):
        ws.column_dimensions[k].width = w
    wb.save(path)


def write_tally_gl(path, gl, tb, ccy):
    # gl lines here already carry a 'ledger' key (see tally_prepare)
    wb = Workbook()
    ws = wb.active
    ws.title = "Ledger Vouchers"
    ws["A1"] = ENTITY
    ws["A1"].font = Font(bold=True, size=13)
    ws["A2"] = "Ledger Vouchers"
    ws["A3"] = f"1-Jan-{YEAR} to 31-Dec-{YEAR}   (amounts in {ccy})"
    r = 5
    names = {c: TALLY_NAMES.get(c, n) for c, n, _ in tb}
    by = defaultdict(list)
    order = []
    for l in gl:
        if l["ledger"] not in by:
            order.append(l["ledger"])
        by[l["ledger"]].append(l)
    tb_order = {c: i for i, (c, _, _) in enumerate(tb)}
    order.sort(key=lambda led: min(tb_order[x["code"]] for x in by[led]))
    for led in order:
        lines = by[led]
        ws.cell(r, 1, f"Ledger: {led}").font = BOLD
        r += 1
        for i, h in enumerate(["Date", "Particulars", "Vch Type", "Vch No.", "Debit", "Credit", "Narration"], 1):
            ws.cell(r, i, h).font = BOLD
        r += 1
        td = tc = 0.0
        for l in lines:
            if l["ref"] == "OPENING":
                ws.cell(r, 2, "Opening Balance")
                ws.cell(r, 5 if l["debit"] else 6, l["debit"] or l["credit"]).number_format = NUM
            else:
                ws.cell(r, 1, l["date"]).number_format = "d-mmm-yy"
                ws.cell(r, 2, l["cp"] or ("Journal" if l["debit"] else "Journal"))
                ws.cell(r, 3, "Journal" if l["code"][0] in "123" else ("Sales" if l["code"][0] == "4" else "Payment"))
                ws.cell(r, 4, l["ref"])
                if l["debit"]:
                    ws.cell(r, 5, l["debit"]).number_format = NUM
                if l["credit"]:
                    ws.cell(r, 6, l["credit"]).number_format = NUM
                ws.cell(r, 7, l["desc"])
            td += l["debit"]
            tc += l["credit"]
            r += 1
        ws.cell(r, 2, "Closing Balance").font = BOLD
        net = td - tc
        ws.cell(r, 5 if net >= 0 else 6, round(abs(net), 2)).number_format = NUM
        r += 2
    for k, w in zip("ABCDEFG", (12, 30, 12, 12, 16, 16, 50)):
        ws.column_dimensions[k].width = w
    wb.save(path)


# ---------------------------------------------------------------------------------------------- Oracle
def _seg(code):
    return f"101.000.{code}.0000.000"


def write_oracle_tb(path, tb, ccy, rnd):
    wb = Workbook()
    ws = wb.active
    ws.title = "XXGL_TRIAL_BALANCE"
    banner = ["Oracle General Ledger", "Trial Balance - Summary", f"{ENTITY}", f"Ledger: SGT_PRIMARY_LEDGER     Currency: {ccy}     Balance Type: Actual",
              f"Period: DEC-{str(YEAR)[2:]}     Period From: JAN-{str(YEAR)[2:]}     Run Date: 05-JAN-{YEAR + 1} 09:14:22", ""]
    for i, t in enumerate(banner, 1):
        ws.cell(i, 1, t)
    ws["A1"].font = Font(bold=True, size=12)
    hdr = ["Account", "Account Description", "Beginning Balance Dr", "Beginning Balance Cr", "Period Activity Dr", "Period Activity Cr",
           "Ending Balance Dr", "Ending Balance Cr"]
    r = 7
    rows_cache = []
    def header_row():
        nonlocal r
        for i, h in enumerate(hdr, 1):
            ws.cell(r, i, h).font = BOLD
        r += 1
    header_row()
    td = tc = 0.0
    n = 0
    for code, nm, v in tb:
        n += 1
        if n == 14:                      # page break: Oracle repeats the heading block
            r += 1
            ws.cell(r, 1, "Page 2 of 2")
            r += 1
            ws.cell(r, 1, "Oracle General Ledger - Trial Balance - Summary")
            r += 1
            header_row()
        act = round(v * rnd.uniform(0.04, 0.15), 2)
        extra = round(abs(v) * rnd.uniform(0.0, 0.1), 2)
        beg = round(v - act, 2)
        pdr, pcr = max(act, 0) + extra, max(-act, 0) + extra
        ws.cell(r, 1, _seg(code))
        ws.cell(r, 2, nm)
        for col, val in ((3, max(beg, 0)), (4, max(-beg, 0)), (5, pdr), (6, pcr), (7, max(v, 0)), (8, max(-v, 0))):
            if abs(val) > 0.004:
                ws.cell(r, col, round(val, 2)).number_format = NUM
        td += max(v, 0)
        tc += max(-v, 0)
        r += 1
    ws.cell(r, 1, "Total for Company 101").font = BOLD
    ws.cell(r, 7, round(td, 2)).number_format = NUM
    ws.cell(r, 8, round(tc, 2)).number_format = NUM
    r += 2
    ws.cell(r, 1, "Report Total").font = BOLD
    ws.cell(r, 7, round(td, 2)).number_format = NUM
    ws.cell(r, 8, round(tc, 2)).number_format = NUM
    r += 2
    ws.cell(r, 1, "*** End of Report ***")
    for k, w in zip("ABCDEFGH", (26, 58, 20, 20, 20, 20, 20, 20)):
        ws.column_dimensions[k].width = w
    wb.save(path)


def write_oracle_gl(path, gl, tb, ccy):
    wb = Workbook()
    ws = wb.active
    ws.title = "GL Journal Lines"
    ws["A1"] = "Oracle General Ledger - Journal Line Detail (Posted)"
    ws["A2"] = f"Ledger: SGT_PRIMARY_LEDGER   Currency: {ccy}   Period: JAN-{str(YEAR)[2:]} to DEC-{str(YEAR)[2:]}"
    hdr = ["Period", "Journal Source", "Journal Category", "Batch Name", "Journal Name", "Doc Sequence", "Effective Date", "Account", "Account Description",
           "Line Description", "Entered Dr", "Entered Cr", "Accounted Dr", "Accounted Cr", "Currency", "Third Party Name", "Created By", "Posted Date"]
    for i, h in enumerate(hdr, 1):
        ws.cell(4, i, h).font = BOLD
    names = {c: n for c, n, _ in tb}
    cat = {"1": "Adjustment", "2": "Adjustment", "3": "Adjustment", "4": "Receivables", "5": "Payables", "6": "Payables"}
    src = {"4": "Receivables", "5": "Payables", "6": "Payables"}
    mon = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
    for r, l in enumerate(gl, 5):
        d = l["date"]
        row = [f"{mon[d.month - 1]}-{str(d.year)[2:]}", src.get(l["code"][0], "Manual"), cat.get(l["code"][0], "Adjustment"), f"BATCH {d:%Y%m}-{(r % 9) + 1}",
               f"JNL {l['ref']}", 100000 + r, d, _seg(l["code"]), names[l["code"]], l["desc"], l["debit"] or None, l["credit"] or None,
               l["debit"] or None, l["credit"] or None, ccy, l["cp"], "BATCH_USER", d]
        for i, v in enumerate(row, 1):
            c = ws.cell(r, i, v)
            if i in (7, 18):
                c.number_format = "DD-MON-YYYY"
            if i in (11, 12, 13, 14):
                c.number_format = NUM
    for i, w in enumerate((9, 14, 16, 18, 18, 12, 14, 24, 40, 46, 14, 14, 14, 14, 9, 26, 12, 14), 1):
        ws.column_dimensions[ws.cell(4, i).column_letter].width = w
    wb.save(path)


# ---------------------------------------------------------------------------------------------- Random
def write_random_tb(path, tb, ccy, rnd):
    wb = Workbook()
    cover = wb.active
    cover.title = "Cover"
    cover["B3"] = "FY closing pack - DRAFT v3 (do not circulate)"
    cover["B4"] = "Prepared by: accounts dept"
    cover["B6"] = "Sheets: TB final, Notes"
    ws = wb.create_sheet("TB final")
    notes = {"1900": "to be cleared - ask Ahmed", "6110": "mgmt to confirm", "1200": "intercompany", "6150": "director - check", "6120": "per agreement"}
    ws["B2"] = f"{ENTITY.split(' (')[0]} - trial balance FY{YEAR}"
    ws["B3"] = f"in {ccy}   -   Dr = positive, (Cr) = negative"
    hdr = ["S.No", "Head of Account", "Section", "Closing Bal", "Dr/Cr", "Remarks"]
    for i, h in enumerate(hdr, 2):
        ws.cell(5, i, h).font = BOLD
    r = 6
    sections = {"1": "Assets", "2": "Liabilities", "3": "Equity", "4": "Income", "5": "Expenses", "6": "Expenses"}
    sno = 0
    cur = None
    sec_total = defaultdict(float)
    order = sorted(tb, key=lambda t: t[0])
    for code, nm, v in order:
        sec = sections[code[0]]
        if cur and sec != cur:
            ws.cell(r, 3, f"Total {cur}").font = BOLD
            ws.cell(r, 5, f"{sec_total[cur]:,.2f}" if sec_total[cur] >= 0 else f"({-sec_total[cur]:,.2f})")
            r += 2
        cur = sec
        sno += 1
        ws.cell(r, 2, sno)
        ws.cell(r, 3, nm)
        ws.cell(r, 4, sec)
        # a mix of true numbers and numbers stored as text, 'EUR' prefix on a few
        if sno % 5 == 0:
            txt = f"{ccy} {abs(v):,.2f}"
        elif sno % 3 == 0:
            txt = f"{abs(v):,.2f}"
        else:
            txt = None
        if txt:
            ws.cell(r, 5, txt)
            ws.cell(r, 5).alignment = Alignment(horizontal="right")
        else:
            ws.cell(r, 5, round(abs(v), 2)).number_format = NUM
        ws.cell(r, 6, "Dr" if v >= 0 else "Cr")
        if code in notes:
            ws.cell(r, 7, notes[code])
        sec_total[sec] += v
        r += 1
    ws.cell(r, 3, f"Total {cur}").font = BOLD
    ws.cell(r, 5, f"({-sec_total[cur]:,.2f})" if sec_total[cur] < 0 else f"{sec_total[cur]:,.2f}")
    r += 2
    ws.cell(r, 3, "Check (should be nil)").font = BOLD
    ws.cell(r, 5, round(sum(v for _, _, v in tb), 2))
    for k, w in zip("BCDEFG", (6, 56, 12, 20, 8, 30)):
        ws.column_dimensions[k].width = w
    ws2 = wb.create_sheet("Notes")
    ws2["A1"] = "Notes to accounts - see Word file"
    wb.save(path)


def write_random_gl(path, gl, tb, ccy):
    wb = Workbook()
    ws = wb.active
    ws.title = "ledger dump"
    ws["A1"] = "ledger dump from old system - all heads"
    hdr = ["Dt", "Ledger", "Narr", "Dr", "Cr", "Vch#", "Party"]
    for i, h in enumerate(hdr, 1):
        ws.cell(3, i, h).font = BOLD
    names = {c: n for c, n, _ in tb}
    for r, l in enumerate(gl, 4):
        ws.cell(r, 1, l["date"].strftime("%d.%m.%Y"))               # dates as text, dd.mm.yyyy
        ws.cell(r, 2, f"{l['code']} {names[l['code']]}")            # code and name in one cell
        ws.cell(r, 3, l["desc"])
        ws.cell(r, 4, l["debit"] or None).number_format = NUM
        ws.cell(r, 5, l["credit"] or None).number_format = NUM
        ws.cell(r, 6, l["ref"])
        ws.cell(r, 7, l["cp"])
    for k, w in zip("ABCDEFG", (12, 56, 50, 16, 16, 12, 26)):
        ws.column_dimensions[k].width = w
    wb.save(path)


def main(argv):
    out = Path(argv[1]) if len(argv) > 1 else Path(__file__).resolve().parent / "format_tests"
    out.mkdir(parents=True, exist_ok=True)
    expected = {}
    for tag, ccy, fn_tb, fn_gl in (("1_Tally", "AED", write_tally_tb, write_tally_gl), ("2_Oracle", "USD", write_oracle_tb, write_oracle_gl),
                                   ("3_Random", "EUR", write_random_tb, write_random_gl)):
        tb, gl, exp = build(ccy, 1.0, 11)
        rnd = random.Random(5)
        if tag == "1_Tally":
            gl, ptot = tally_prepare(tb, gl, rnd)
            fn_tb(out / f"{tag}_TB_{ccy}.xlsx", tb, ccy, rnd, ptot)
        else:
            fn_tb(out / f"{tag}_TB_{ccy}.xlsx", tb, ccy, rnd)
        fn_gl(out / f"{tag}_GL_{ccy}.xlsx", gl, tb, ccy)
        expected[tag] = {**exp, "tb_file": f"{tag}_TB_{ccy}.xlsx", "gl_file": f"{tag}_GL_{ccy}.xlsx",
                         "tb_net_by_name": {n: v for _, n, v in tb}}
    (out / "expected_figures.json").write_text(json.dumps(expected, indent=1, default=str), encoding="utf-8")
    print("written to", out)


if __name__ == "__main__":
    main(sys.argv)
