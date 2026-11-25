"""Generate a full SYNTHETIC input set: ERP-style exports, bank files, templates and history.

    python scripts/make_synthetic.py                       # as-of 2026-11-24, 3 months, seed 26
    python scripts/make_synthetic.py --as-of 2026-12-01 --months 2 --seed 7

Writes synthetic_data/day1_<date>/ and synthetic_data/day2_<date+1>/ (the next day's re-upload:
cleared cheques and paid invoices drop out, a few new rows appear, keys stay stable) plus
synthetic_data/acceptance/ (a month with 70 PDCs and lot totals worked out independently).

Every name is invented ("Vendor 07 (synthetic)"). Deliberate test cases are listed in
synthetic_data/README.md and repeated in each folder's _manifest.txt.
"""
from __future__ import annotations

import argparse
import calendar
import csv
import random
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

import xlsxwriter

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "synthetic_data"
D = Decimal
TAG = "(synthetic)"


# ------------------------------------------------------------------ helpers
def money(rnd: random.Random, lo: int, hi: int) -> Decimal:
    """Random amount in OMR with 3 decimals, built from integer baisa (exact)."""
    return D(rnd.randint(lo * 1000, hi * 1000)) / 1000


def month_end(y: int, m: int) -> date:
    return date(y, m, calendar.monthrange(y, m)[1])


def add_months(d: date, n: int) -> date:
    y, m = divmod(d.month - 1 + n, 12)
    return date(d.year + y, m + 1, 1)


def horizon_end(as_of: date, months: int) -> date:
    last = add_months(date(as_of.year, as_of.month, 1), months - 1)
    return month_end(last.year, last.month)


def write_xlsx(path: Path, headers: list[str], rows: list[list], title_rows: list[str] | None = None,
               total_label_col: int | None = None, amount_col: int | None = None) -> None:
    """ERP-like export: optional report title rows above the header and a total row at the bottom."""
    wb = xlsxwriter.Workbook(path)
    ws = wb.add_worksheet("Data" if not title_rows else "Report")
    f_date = wb.add_format({"num_format": "dd/mm/yyyy"})
    f_amt = wb.add_format({"num_format": "#,##0.000"})
    f_bold = wb.add_format({"bold": True})
    r = 0
    for t in title_rows or []:
        ws.write(r, 0, t, f_bold); r += 1
    if title_rows:
        r += 1
    ws.write_row(r, 0, headers, f_bold)
    for c, h in enumerate(headers):
        ws.set_column(c, c, max(12, len(h) + 3))
    first = r + 1
    for row in rows:
        r += 1
        for c, v in enumerate(row):
            if isinstance(v, date):
                ws.write_datetime(r, c, v, f_date)
            elif isinstance(v, Decimal):
                ws.write_number(r, c, v, f_amt)
            elif v not in ("", None):
                ws.write(r, c, v)
    if total_label_col is not None and amount_col is not None and rows:
        r += 1
        ws.write(r, total_label_col, "Total", f_bold)
        col = chr(65 + amount_col)
        ws.write_formula(r, amount_col, f"=SUM({col}{first + 1}:{col}{r})", f_amt,
                         float(sum(row[amount_col] for row in rows)))
    wb.close()


def write_csv(path: Path, headers: list[str], rows: list[list]) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(headers)
        for row in rows:
            w.writerow([v.strftime("%d-%m-%Y") if isinstance(v, date) else (f"{v:.3f}" if isinstance(v, Decimal) else v)
                        for v in row])


# ------------------------------------------------------------------ category master
CATEGORIES = [  # name, direction, group, order, treatment, default_for_source, aliases
    ("Customer collections", "Inflow", "Collections", 10, "Fixed", "collections", "Receivables; AR collections"),
    ("Additional collections", "Inflow", "Collections", 20, "Fixed", "additional", "Advances; Retention release"),
    ("Bill discount proceeds", "Inflow", "Financing", 30, "Fixed", "bill_discount_in", "Discounting proceeds"),
    ("Other inflows", "Inflow", "Other", 40, "Fixed", "other_in", "Miscellaneous receipts"),
    ("Vendor PDCs", "Outflow", "Suppliers", 110, "Deferrable", "vendor_pdc", "PDC; Post dated cheques"),
    ("Vendor payment allocation", "Outflow", "Suppliers", 120, "Deferrable", "allocation", "Supplier transfers"),
    ("Bill discount / LC maturities", "Outflow", "Financing", 130, "Fixed", "bill_discount_out",
     "LC maturity; Discount maturity"),
    ("Payroll", "Outflow", "Staff costs", 140, "Fixed", "", "Salaries; WPS; Wages"),
    ("Rent & utilities", "Outflow", "Overheads", 150, "Fixed", "", "Rent; Utilities; Electricity"),
    ("VAT & taxes", "Outflow", "Statutory", 160, "Fixed", "", "VAT; Tax; Income tax"),
    ("Visa & labour fees", "Outflow", "Statutory", 165, "Fixed", "", "Labour fees; Visa fees"),
    ("Other outflows", "Outflow", "Other", 190, "Deferrable", "other_out", "Miscellaneous payments"),
]
CAT_HEADERS = ["Category", "Inflow/Outflow", "Summary Group", "Display Order", "Default Treatment",
               "Default For Source", "Aliases"]


# ------------------------------------------------------------------ the day-1 data set
@dataclass
class DaySet:
    as_of: date
    receivables: list[list]
    pdcs: list[list]
    plan: list[list]
    bank: list[list]
    additional: list[list]
    other_wide: list[list]
    other_long: list[list]
    balances: list[list]
    facility: list[list]
    history: list[list]
    manifest: list[str]


CUSTOMERS = [f"Customer {chr(65 + i)} {TAG}" for i in range(12)]
VENDORS = [f"Vendor {i:02d} {TAG}" for i in range(1, 61)]
BANKS = ["Bank A", "Bank B", "Bank C"]


def build_day1(as_of: date, months: int, seed: int) -> DaySet:
    rnd = random.Random(seed)
    end = horizon_end(as_of, months)
    span = (end - as_of).days
    man: list[str] = []

    # receivables: open invoices; some overdue, some flagged risk
    rec = []
    for i in range(1, 61):
        due = as_of + timedelta(days=rnd.randint(-20, span))
        rec.append([f"INV-26-{1400 + i:04d}", rnd.choice(CUSTOMERS), f"PRJ-{10 + i % 6}", due,
                    money(rnd, 3000, 28000), "Y" if i in (6, 31, 47) else ""])
    man.append("Receivables: 3 title rows above the header and a Total row at the bottom (must be skipped).")
    man.append("Receivables: ERP headers 'Doc No', 'Party Name', 'Due On', 'Outstanding (OMR)' (alias matching).")
    overdue = sum(1 for r in rec if r[3] < as_of)
    man.append(f"Receivables: {overdue} invoices already past due -> placed in the current lot.")
    man.append("Receivables: INV-26-1406, 1431, 1447 flagged 'Risk Flag = Y' (Risk-adjusted scenario).")

    # PDC register: some vouchers carry two cheques (key = voucher + cheque)
    pdcs, chq = [], 300100
    for i in range(1, 101):
        d = as_of + timedelta(days=rnd.randint(-3, span))
        n_chq = 2 if i % 17 == 0 else 1
        for k in range(n_chq):
            chq += 1
            pdcs.append([f"PV-26-{3300 + i:04d}", VENDORS[(i * 7) % len(VENDORS)], f"{chq:06d}",
                         d + timedelta(days=30 * k), money(rnd, 1500, 14000), rnd.choice(BANKS)])
    pdcs = [p for p in pdcs if p[3] <= end]
    dup = list(pdcs[10])
    pdcs.append(dup)
    man.append(f"PDC register: {len(pdcs)} rows; vouchers with two cheques share a voucher no (key = voucher + cheque).")
    man.append(f"PDC register: row for voucher {dup[0]} cheque {dup[2]} appears TWICE (duplicate warning).")
    man.append("PDC register: cheques dated before the as-of date are uncleared -> current lot.")

    # payment plan (CSV); one invoice also paid by a PDC (overlap)
    plan = []
    for i in range(1, 9):
        d = as_of + timedelta(days=rnd.randint(2, span))
        plan.append([VENDORS[30 + i], f"PINV-{5500 + i}", d, money(rnd, 15000, 40000)])
    p = pdcs[20]
    plan.append([p[1], "PINV-OVERLAP-1", p[3] + timedelta(days=1), p[4]])
    man.append(f"Payment plan (CSV): PINV-OVERLAP-1 for {p[1]} has the same amount as PDC {p[0]}/{p[2]} "
               "one day apart (overlap warning: possibly paid twice).")

    # bank BD / LC file; proceeds financed one receivable invoice
    fin = rec[15]
    bank = [
        ["DISC-7781", "Bank A", "Discount proceeds", as_of + timedelta(days=2), money(rnd, 30000, 50000), fin[0]],
        ["DISC-7790", "Bank A", "Discount proceeds", as_of + timedelta(days=28), money(rnd, 40000, 60000), ""],
        ["LC-4471", "Bank B", "LC maturity", as_of + timedelta(days=5), money(rnd, 30000, 45000), ""],
        ["DISC-0912", "Bank A", "Discount maturity", as_of + timedelta(days=14), money(rnd, 90000, 115000), ""],
        ["LC-4490", "Bank C", "LC maturity", as_of + timedelta(days=25), money(rnd, 20000, 30000), ""],
        ["LC-4502", "Bank B", "LC maturity", as_of + timedelta(days=45), money(rnd, 35000, 45000), ""],
        ["DISC-0950", "Bank A", "Discount maturity", min(end, as_of + timedelta(days=64)), money(rnd, 40000, 50000), ""],
    ]
    man.append(f"Bank file: DISC-7781 discount proceeds finance receivable {fin[0]} "
               "-> that invoice must not be counted again as a collection.")
    man.append("Bank file: ERP headers 'Deal No', 'Deal Type', 'Value Date' (alias matching).")

    additional = [
        ["ADD-001", "PRJ-12", CUSTOMERS[2], as_of + timedelta(days=11), D("22500.000"), "Advance on variation 3"],
        ["ADD-002", "PRJ-13", CUSTOMERS[7], as_of + timedelta(days=22), D("18000.000"), "Retention release"],
        ["ADD-003", "PRJ-15", CUSTOMERS[4], as_of + timedelta(days=44), D("26400.000"), "Mobilisation advance"],
    ]

    # other & recurring: WIDE layout, with an unknown header
    other_wide, d = [], date(as_of.year, as_of.month, 1)
    while d <= end:
        pay = date(d.year, d.month, 28)
        if pay >= as_of:
            other_wide.append([pay, f"Payroll {pay:%b %Y}", D("78500.000"), "", "", ""])
        rent = date(d.year, d.month, 1)
        if rent >= as_of:
            other_wide.append([rent, f"Office rent {rent:%b %Y}", "", D("12400.000"), "", ""])
        vat_d = month_end(d.year, d.month)
        if d.month in (1, 4, 7, 10) and vat_d >= as_of:  # quarterly return, paid at the end of the next month
            other_wide.append([vat_d, "VAT return", "", "", D("41200.000"), ""])
        d = add_months(d, 1)
    other_wide.append([as_of + timedelta(days=40), "Visa renewals - site staff", "", "", "", D("7350.000")])
    man.append("Other (WIDE): header 'Visa Renewal Fees' is NOT in the category list -> Exceptions screen; "
               "rapidfuzz should suggest 'Visa & labour fees'.")

    other_long = [
        ["OTH-001", "Other inflows", "Insurance claim", as_of + timedelta(days=20), D("6250.000"), "Inflow"],
        ["OTH-002", "Other outflows", "Insurance renewal", as_of + timedelta(days=18), D("9800.000"), "Outflow"],
        ["OTH-003", "Marketing campaign", "Trade exhibition stand", as_of + timedelta(days=33), D("5400.000"),
         "Outflow"],
        ["OTH-004", "", "Asset disposal", as_of + timedelta(days=60), D("8900.000"), "Inflow"],
    ]
    man.append("Other (LONG): category 'Marketing campaign' is unknown -> Exceptions (map it or add it as new).")
    man.append("Other (LONG): OTH-004 has no category -> default for 'other_in' (Other inflows).")

    balances = [
        ["Bank A", "Current 0101", "OMR", as_of, D("182450.250"), D("1")],
        ["Bank B", "Current 0202", "OMR", as_of, D("64210.500"), D("1")],
        ["Bank C", "Current 0303", "OMR", as_of, D("23900.000"), D("1")],
        ["Bank D", "USD 0404", "USD", as_of, D("40000.000"), D("0.3845")],
    ]
    facility = [
        ["Bank A", "Overdraft", as_of, D("150000.000"), D("100000.000"), D("50000.000")],
        ["Bank B", "Overdraft", as_of, D("100000.000"), D("75000.000"), D("25000.000")],
        ["Bank C", "Overdraft", as_of, D("50000.000"), D("50000.000"), D("0.000")],
    ]

    # payment history: customer-specific delay so the model has something to learn
    delay_mean = {c: rnd.choice([2, 5, 12, 25, 40, 60]) for c in CUSTOMERS}
    history = []
    for i in range(1, 421):
        c = rnd.choice(CUSTOMERS)
        inv = date(2025, 1, 1) + timedelta(days=rnd.randint(0, 600))
        due = inv + timedelta(days=rnd.choice([30, 45, 60, 90]))
        delay = max(-5, int(rnd.gauss(delay_mean[c], 6)))
        paid = due + timedelta(days=delay)
        if paid >= as_of:
            continue
        history.append([f"INV-H-{i:05d}", c, f"PRJ-{10 + i % 6}", inv, due, paid, money(rnd, 1500, 30000)])
    man.append(f"Payment history: {len(history)} paid invoices, each customer with its own typical delay.")

    return DaySet(as_of, rec, pdcs, plan, bank, additional, other_wide, other_long, balances, facility,
                  history, man)


def build_day2(d1: DaySet, seed: int) -> DaySet:
    """Next day's re-upload: cleared cheques and paid invoices drop out, new rows appear, keys stable."""
    rnd = random.Random(seed + 1)
    as_of = d1.as_of + timedelta(days=1)
    rec = [r for r in d1.receivables if r[3] >= d1.as_of or rnd.random() > 0.4]
    paid = len(d1.receivables) - len(rec)
    rec.append(["INV-26-1499", CUSTOMERS[3], "PRJ-14", as_of + timedelta(days=30), D("14250.000"), ""])
    seen, pdcs = set(), []
    for p in d1.pdcs:  # drop the duplicate and cheques cleared on day 1
        k = (p[0], p[2])
        if k in seen or p[3] < as_of:
            continue
        seen.add(k); pdcs.append(p)
    cleared = len({(p[0], p[2]) for p in d1.pdcs}) - len(pdcs)
    pdcs += [["PV-26-3501", VENDORS[5], "309001", as_of + timedelta(days=12), D("6400.000"), "Bank B"],
             ["PV-26-3502", VENDORS[9], "309002", as_of + timedelta(days=36), D("3925.500"), "Bank A"]]
    balances = [[b[0], b[1], b[2], as_of, b[4] + D("-1250.000") if b[0] == "Bank A" else b[4], b[5]]
                for b in d1.balances]
    man = [f"Day 2 = re-upload on {as_of}: same keys as day 1.",
           f"{paid} receivables paid (gone), 1 new (INV-26-1499).",
           f"{cleared} cheques cleared or de-duplicated (gone), 2 new PDCs (PV-26-3501, 3502).",
           "Overrides made on day 1 against keys still present must still apply after this upload."]
    return DaySet(as_of, rec, pdcs, d1.plan, d1.bank, d1.additional, d1.other_wide, d1.other_long, balances,
                  [[f[0], f[1], as_of, *f[3:]] for f in d1.facility], d1.history, man)


def write_day(ds: DaySet, folder: Path, full: bool) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    t = [f"Sample ERP {TAG} - Receivables ageing", f"As at {ds.as_of:%d-%b-%Y}"]
    write_xlsx(folder / "erp_receivables.xlsx",
               ["Doc No", "Party Name", "Project Code", "Due On", "Outstanding (OMR)", "Risk Flag"],
               ds.receivables, t, total_label_col=1, amount_col=4)
    write_xlsx(folder / "erp_pdc_register.xlsx",
               ["PV No", "Supplier Name", "Chq No", "Chq Date", "Chq Amount", "Bank Name"], ds.pdcs,
               [f"Sample ERP {TAG} - Post-dated cheques issued", f"As at {ds.as_of:%d-%b-%Y}"],
               total_label_col=1, amount_col=4)
    write_csv(folder / "erp_payment_plan.csv", ["Supplier", "Bill No", "Payment Date", "Allocated Amount"], ds.plan)
    write_xlsx(folder / "bank_bd_lc.xlsx",
               ["Deal No", "Bank Name", "Deal Type", "Value Date", "Deal Amount", "Customer Invoice"], ds.bank)
    write_xlsx(folder / "additional_collections.xlsx",
               ["Reference", "Project", "Customer", "Expected Date", "Amount", "Note"], ds.additional)
    write_xlsx(folder / "other_recurring_wide.xlsx",
               ["Date", "Particulars", "Payroll", "Rent & utilities", "VAT & taxes", "Visa Renewal Fees"],
               ds.other_wide)
    write_xlsx(folder / "other_recurring_long.xlsx",
               ["Reference", "Category", "Description", "Date", "Amount", "Inflow/Outflow"], ds.other_long)
    write_csv(folder / "bank_balances.csv",
              ["Bank", "Account", "Currency", "As-of Date", "Balance", "Rate to OMR"], ds.balances)
    write_csv(folder / "bank_facility.csv",
              ["Bank", "Facility Type", "As-of Date", "Limit", "Utilised", "Available"], ds.facility)
    if full:
        write_xlsx(folder / "category_list.xlsx", CAT_HEADERS, [list(c) for c in CATEGORIES])
        write_xlsx(folder / "payment_history.xlsx",
                   ["Invoice No", "Customer", "Project", "Invoice Date", "Due Date", "Paid Date", "Amount"],
                   ds.history)
    (folder / "_manifest.txt").write_text(
        f"SYNTHETIC DATA - as of {ds.as_of}\n\n" + "\n".join(f"- {m}" for m in ds.manifest) + "\n", encoding="utf-8")


# ------------------------------------------------------------------ acceptance fixture
def month_thirds(y: int, m: int) -> list[tuple[int, date, date]]:
    e = calendar.monthrange(y, m)[1]
    return [(1, date(y, m, 1), date(y, m, 10)), (2, date(y, m, 11), date(y, m, 20)), (3, date(y, m, 21), date(y, m, e))]


def build_acceptance(seed: int, y: int = 2026, m: int = 12, n: int = 70) -> None:
    """A month with exactly n PDCs and the lot totals worked out with a plain loop ("by hand")."""
    rnd = random.Random(seed + 100)
    folder = OUT / "acceptance"
    folder.mkdir(parents=True, exist_ok=True)
    days = calendar.monthrange(y, m)[1]
    rows = []
    for i in range(1, n + 1):
        # force cheques onto the lot boundaries too (10th, 11th, 20th, 21st, month end)
        day = [1, 10, 11, 20, 21, days][i - 1] if i <= 6 else rnd.randint(1, days)
        rows.append([f"PV-ACC-{i:03d}", f"Vendor {i:02d} {TAG}", f"{700000 + i}", date(y, m, day),
                     money(rnd, 500, 15000), rnd.choice(BANKS)])
    rows.sort(key=lambda r: (r[3], r[0]))

    lots = month_thirds(y, m)
    expected = []
    for no, s, e in lots:
        amt, cnt = D(0), 0
        for r in rows:
            if s <= r[3] <= e:
                amt += r[4]; cnt += 1
        expected.append((no, s, e, cnt, amt))
    assert sum(x[3] for x in expected) == n

    path = folder / f"pdc_month_{y}_{m:02d}.xlsx"
    wb = xlsxwriter.Workbook(path)
    ws = wb.add_worksheet("Data")
    f_date = wb.add_format({"num_format": "dd/mm/yyyy"}); f_amt = wb.add_format({"num_format": "#,##0.000"})
    f_b = wb.add_format({"bold": True})
    hdr = ["Voucher No", "Vendor", "Cheque No", "Cheque Date", "Amount", "Bank"]
    ws.write_row(0, 0, hdr, f_b)
    for r, row in enumerate(rows, 1):
        ws.write(r, 0, row[0]); ws.write(r, 1, row[1]); ws.write(r, 2, row[2])
        ws.write_datetime(r, 3, row[3], f_date); ws.write_number(r, 4, row[4], f_amt); ws.write(r, 5, row[5])
    ws.set_column(0, 5, 16)
    hc = wb.add_worksheet("Hand check")
    hc.write_row(0, 0, ["Lot", "From", "To", "Count", "Total (formula)", "Total (expected)", "Difference"], f_b)
    for i, (no, s, e, cnt, amt) in enumerate(expected, 1):
        hc.write(i, 0, no); hc.write_datetime(i, 1, s, f_date); hc.write_datetime(i, 2, e, f_date)
        hc.write_formula(i, 3, f'=COUNTIFS(Data!D:D,">="&B{i + 1},Data!D:D,"<="&C{i + 1})', None, cnt)
        hc.write_formula(i, 4, f'=SUMIFS(Data!E:E,Data!D:D,">="&B{i + 1},Data!D:D,"<="&C{i + 1})', f_amt, float(amt))
        hc.write_number(i, 5, amt, f_amt)
        hc.write_formula(i, 6, f"=E{i + 1}-F{i + 1}", f_amt, 0)
    hc.set_column(0, 6, 15)
    wb.close()

    with (folder / f"pdc_month_{y}_{m:02d}_expected.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["lot", "start", "end", "count", "total"])
        for no, s, e, cnt, amt in expected:
            w.writerow([no, s.isoformat(), e.isoformat(), cnt, f"{amt:.3f}"])
    print(f"acceptance: {path.name} ({n} PDCs) ->",
          ", ".join(f"lot {no}: {cnt} / {amt:,.3f}" for no, _, _, cnt, amt in expected))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--as-of", type=date.fromisoformat, default=date(2026, 11, 24))
    ap.add_argument("--months", type=int, default=3)
    ap.add_argument("--seed", type=int, default=26)
    a = ap.parse_args()
    d1 = build_day1(a.as_of, a.months, a.seed)
    d2 = build_day2(d1, a.seed)
    f1, f2 = OUT / f"day1_{d1.as_of}", OUT / f"day2_{d2.as_of}"
    write_day(d1, f1, full=True)
    write_day(d2, f2, full=False)
    build_acceptance(a.seed)
    for f, ds in ((f1, d1), (f2, d2)):
        print(f"{f.relative_to(ROOT)}: {len(ds.receivables)} receivables, {len(ds.pdcs)} PDCs, "
              f"{len(ds.plan)} plan rows, {len(ds.bank)} bank rows, {len(ds.other_wide) + len(ds.other_long)} other")


if __name__ == "__main__":
    main()
