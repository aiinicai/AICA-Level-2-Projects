"""Build docs/Forecast_layout_draft.xlsx - a CFO-view layout mock-up with SYNTHETIC data.

Design draft for review only. The real export (Phase 7) is built from the engine but follows
this layout. All figures are invented.

    python scripts/make_layout_draft.py              # 3-month horizon (default)
    python scripts/make_layout_draft.py --months 2   # 2-month horizon
"""
from __future__ import annotations

import argparse
import calendar
import random
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

import xlsxwriter
from xlsxwriter.utility import xl_rowcol_to_cell

DOCS = Path(__file__).resolve().parents[1] / "docs"
D = Decimal
AS_OF = date(2026, 11, 23)
COMPANY = "Sample Trading & Contracting LLC (synthetic)"

BANKS = [  # bank, account, ccy, balance, rate
    ("Bank A", "Current 0101", "OMR", D("182450.250"), D("1")),
    ("Bank B", "Current 0202", "OMR", D("64210.500"), D("1")),
    ("Bank C", "Current 0303", "OMR", D("23900.000"), D("1")),
    ("Bank D", "USD 0404", "USD", D("40000.000"), D("0.3845")),
]
FACILITY = [("Bank A", D("150000"), D("100000")), ("Bank B", D("100000"), D("75000")),
            ("Bank C", D("50000"), D("50000"))]

INFLOW_CATS = ["Customer collections", "Additional collections", "Bill discount proceeds", "Other inflows"]
OUTFLOW_CATS = ["Vendor PDCs", "Vendor payment allocation", "Bill discount / LC maturities",
                "Payroll", "Rent & utilities", "VAT & taxes", "Other outflows"]
SOURCE_NOTE = {
    "Customer collections": "ERP AR", "Additional collections": "Template",
    "Bill discount proceeds": "Bank file", "Other inflows": "Template",
    "Vendor PDCs": "ERP PDC", "Vendor payment allocation": "ERP AP plan",
    "Bill discount / LC maturities": "Bank file", "Payroll": "Recurring",
    "Rent & utilities": "Recurring", "VAT & taxes": "Recurring", "Other outflows": "Template",
}


# ----------------------------------------------------------------- lots
def build_lots(as_of: date, months: int) -> list[dict]:
    """month_thirds lots from the current lot to the end of (current month + months - 1)."""
    lots, y, m = [], as_of.year, as_of.month
    for _ in range(months):
        eom = calendar.monthrange(y, m)[1]
        for s, e in ((1, 10), (11, 20), (21, eom)):
            start, end = date(y, m, s), date(y, m, e)
            if end < as_of:
                continue
            lots.append(dict(no=len(lots) + 1, start=start, end=end, month=(y, m),
                             label=f"{s:02d}-{e:02d} {start:%b}",
                             status="CURRENT" if start <= as_of <= end else "FORECAST"))
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return lots


def lot_of(lots, d: date) -> int | None:
    if d < lots[0]["start"]:
        return 1  # unpaid and overdue -> current lot
    return next((l["no"] for l in lots if l["start"] <= d <= l["end"]), None)


# ----------------------------------------------------------------- synthetic data
def build_rows(lots) -> list[dict]:
    rnd = random.Random(26)
    horizon_end = lots[-1]["end"]
    span = (horizon_end - AS_OF).days
    rows: list[dict] = []

    def add(src, key, cat, direction, cp, ref, planned, amount, status="Active", override="", eff=None):
        if planned > horizon_end and override != "Deferred":
            return
        eff = eff or planned
        rows.append(dict(src=src, key=key, cat=cat, dir=direction, cp=cp, ref=ref, planned=planned, eff=eff,
                         olot=lot_of(lots, planned), elot=lot_of(lots, eff) if status == "Active" else None,
                         amt=D(amount).quantize(D("0.001")), status=status, override=override,
                         hold_amt=D(0), honour=None, hlot=None, hold_reason=""))

    def money(lo, hi):
        return D(rnd.randint(lo, hi)) + D(rnd.randint(0, 999)) / 1000

    for i in range(1, 41):
        d = AS_OF + timedelta(days=rnd.randint(-5, span))
        status, ov = "Active", ("Overdue - current lot" if d < AS_OF else "")
        if i in (6, 31):
            status, ov = "Excluded - risk", "Risk-adjusted"
        add("AR", f"INV-26-{1400 + i}", "Customer collections", "In", f"Customer {chr(65 + i % 26)}",
            f"PRJ-{10 + i % 5}", d, money(8000, 24000), status, ov)
    for i, (d, a) in enumerate([(date(2026, 12, 5), "22500"), (date(2026, 12, 16), "18000"),
                                (date(2027, 1, 7), "26400"), (date(2027, 1, 19), "15750")], 1):
        add("ADD", f"ADD-{i:03d}", "Additional collections", "In", f"Customer {chr(66 + i)}", f"PRJ-1{i}", d, a)
    for i, (d, a) in enumerate([(date(2026, 11, 26), "45000"), (date(2026, 12, 22), "60000"),
                                (date(2027, 1, 14), "40000")], 1):
        add("BD", f"BD-NEW-{i:02d}", "Bill discount proceeds", "In", "Bank A", f"DISC-77{80 + i}", d, a)
    add("OTH", "OTH-001", "Other inflows", "In", "Insurance claim", "CLM-04", date(2026, 12, 14), "6250")
    add("OTH", "OTH-002", "Other inflows", "In", "Asset disposal", "FA-311", date(2027, 1, 25), "8900")

    for i in range(1, 71):
        d = AS_OF + timedelta(days=rnd.randint(-2, span))
        status, ov, eff = "Active", "", None
        if i in (9, 40):
            ov = "Deferred"
            eff = min(d + timedelta(days=20), horizon_end)
        elif d < AS_OF:
            ov = "Overdue - current lot"
        add("PDC", f"PV-26-{3300 + i}", "Vendor PDCs", "Out", f"Vendor {i:02d}", f"CHQ-{88100 + i}", d,
            money(2500, 12500), status, ov, eff)

    # ---- cheque holds: the cheque stays in Vendor PDCs (as per ERP) and the hold is shown as an
    # adjustment: out of its own lot, back in the lot of the next honouring date.
    def biggest(lot, k=0):
        cands = sorted((x for x in rows if x["src"] == "PDC" and x["elot"] == lot and not x["hold_amt"]
                        and not x["override"]), key=lambda x: -x["amt"])
        return cands[k] if len(cands) > k else None

    for lot, k, part, honour, reason in [
            (2, 0, D(1), "+12", "Await delivery note"),             # full hold, back ~12 days later
            (5, 0, D("0.5"), "+11", "Part payment agreed"),         # half the cheque, back ~11 days later
            (7, 0, D(1), date(2027, 2, 8), "Vendor dispute"),       # back after the horizon
            (7, 1, D(1), None, "Until further notice")]:            # open-ended
        x = biggest(lot, k)
        if x is None:
            continue
        if isinstance(honour, str):
            honour = x["eff"] + timedelta(days=int(honour))
        x["hold_amt"] = (x["amt"] * part).quantize(D("0.001"))
        x["honour"], x["hlot"], x["hold_reason"] = honour, (lot_of(lots, honour) if honour else None), reason
        x["override"] = "Hold" + (" (part)" if part != 1 else "")
    for i, (d, a) in enumerate([(date(2026, 11, 27), "31500"), (date(2026, 12, 4), "27800"),
                                (date(2026, 12, 18), "35250"), (date(2027, 1, 6), "29900"),
                                (date(2027, 1, 22), "33100")], 1):
        add("ALLOC", f"AP-ALLOC-{i:03d}", "Vendor payment allocation", "Out", f"Vendor {80 + i}",
            f"PINV-{5500 + i}", d, a)
    for key, bank, d, a in [("LC-4471", "Bank B", date(2026, 11, 29), "38400"),
                            ("BD-0912", "Bank A", date(2026, 12, 8), "112000"),
                            ("LC-4490", "Bank C", date(2026, 12, 19), "24750"),
                            ("LC-4502", "Bank B", date(2027, 1, 9), "41300"),
                            ("BD-0950", "Bank A", date(2027, 1, 27), "45000")]:
        add("BD", key, "Bill discount / LC maturities", "Out", bank, key, d, a)
    for d in (date(2026, 11, 28), date(2026, 12, 28), date(2027, 1, 28)):
        add("REC", f"PAY-{d:%b%y}".upper(), "Payroll", "Out", "Staff payroll", f"WPS {d:%b}", d, "78500")
    for d in (date(2026, 12, 1), date(2027, 1, 1)):
        add("REC", f"RENT-{d:%b%y}".upper(), "Rent & utilities", "Out", "Landlord / utilities", f"{d:%b}", d, "12400")
    add("REC", "VAT-Q3", "VAT & taxes", "Out", "Tax Authority", "VAT Q3", date(2026, 11, 30), "41200")
    add("OTH", "OTH-OUT-1", "Other outflows", "Out", "Insurance renewal", "POL-2027", date(2026, 12, 12), "9800")
    add("OTH", "OTH-OUT-2", "Other outflows", "Out", "Visa and labour fees", "LAB-01", date(2027, 1, 12), "7350")
    return rows


# ----------------------------------------------------------------- workbook
def main(months: int) -> Path:
    lots = build_lots(AS_OF, months)
    rows = build_rows(lots)
    nos = [l["no"] for l in lots]
    month_keys = list(dict.fromkeys(l["month"] for l in lots))
    lots_in = {mk: [l["no"] for l in lots if l["month"] == mk] for mk in month_keys}
    erp_total = sum((b[3] * b[4]).quantize(D("0.001")) for b in BANKS)
    fac_avail = sum(l - u for _, l, u in FACILITY)

    # ---------- python-side figures (cached values for the formulas) ----------
    cat_lot, risk, defin = defaultdict(D), defaultdict(D), defaultdict(D)
    held_out, repres, open_hold = defaultdict(D), defaultdict(D), D(0)
    for r in rows:
        if r["status"] == "Active":
            cat_lot[(r["cat"], r["elot"])] += r["amt"]
            if r["override"] == "Deferred":
                defin[r["elot"]] += r["amt"]
            if r["hold_amt"]:
                held_out[r["elot"]] += r["hold_amt"]
                if r["hlot"]:
                    repres[r["hlot"]] += r["hold_amt"]
                else:
                    open_hold += r["hold_amt"]
        else:
            risk[r["olot"]] += r["amt"]
    total_held = sum(held_out.values())
    V: dict[str, dict] = defaultdict(dict)  # V[row_key][lot_no] = Decimal
    opening = erp_total
    for n in nos:
        for c in INFLOW_CATS + OUTFLOW_CATS:
            V[c][n] = cat_lot[(c, n)]
        ti = sum(cat_lot[(c, n)] for c in INFLOW_CATS)
        to = sum(cat_lot[(c, n)] for c in OUTFLOW_CATS)
        close = opening + ti - to
        V["open"][n], V["ti"][n], V["to"][n], V["net"][n], V["close"][n] = opening, ti, to, ti - to, close
        V["fac"][n], V["fp"][n] = fac_avail, close + fac_avail
        V["gap"][n] = min(D(0), close + fac_avail)
        V["risk"][n], V["defin"][n] = risk[n], defin[n]
        V["hout"][n], V["hin"][n] = held_out[n], repres[n]
        V["hnet"][n] = held_out[n] - repres[n]
        V["hcum"][n] = V["hnet"][n] + (V["hcum"][n - 1] if n > 1 else D(0))
        V["close_h"][n] = close + V["hcum"][n]
        V["fp_h"][n] = V["close_h"][n] + fac_avail
        V["gap_h"][n] = min(D(0), V["fp_h"][n])
        opening = close

    out = DOCS / "Forecast_layout_draft.xlsx"
    wb = xlsxwriter.Workbook(out)
    wb.set_properties({"title": "Cash flow forecast - layout draft", "comments": "Synthetic data"})
    NUM = "#,##0.000;[Red](#,##0.000);\"-\""
    navy, light, mfill = "#1F3864", "#D9E1F2", "#F2F2F2"
    P = {  # format property sets; month-total columns get a grey fill on top
        "num": {"num_format": NUM}, "tot": {"bold": True, "top": 1, "num_format": NUM},
        "close": {"bold": True, "bottom": 6, "top": 1, "num_format": NUM},
        "gap": {"bold": True, "font_color": "#C00000", "num_format": NUM},
        "memo": {"italic": True, "font_color": "#595959", "num_format": NUM},
    }
    F = {k: wb.add_format(v) for k, v in P.items()}
    FM = {k: wb.add_format({**v, "bg_color": mfill, "left": 1, "right": 1, "left_color": "#BFBFBF",
                            "right_color": "#BFBFBF"}) for k, v in P.items()}
    f = {
        "title": wb.add_format({"bold": True, "font_size": 14, "font_color": navy}),
        "sub": wb.add_format({"bold": True, "font_size": 11}),
        "meta": wb.add_format({"italic": True, "font_color": "#595959"}),
        "band": wb.add_format({"bold": True, "bg_color": "#2F5597", "font_color": "white", "align": "center",
                               "border": 1}),
        "hdr": wb.add_format({"bold": True, "bg_color": navy, "font_color": "white", "align": "center",
                              "valign": "vcenter", "border": 1, "text_wrap": True}),
        "hdr_m": wb.add_format({"bold": True, "bg_color": "#404040", "font_color": "white", "align": "center",
                                "valign": "vcenter", "border": 1, "text_wrap": True}),
        "hdr_l": wb.add_format({"bold": True, "bg_color": navy, "font_color": "white", "border": 1}),
        "status": wb.add_format({"italic": True, "align": "center", "font_size": 9, "bg_color": light}),
        "status_cur": wb.add_format({"bold": True, "align": "center", "font_size": 9, "bg_color": "#FFE699"}),
        "sect": wb.add_format({"bold": True, "bg_color": light, "font_color": navy}),
        "lbl": wb.add_format({"indent": 1}),
        "note": wb.add_format({"font_color": "#7F7F7F", "font_size": 9}),
        "tot_l": wb.add_format({"bold": True, "top": 1}),
        "close_l": wb.add_format({"bold": True, "bottom": 6, "top": 1}),
        "memo_l": wb.add_format({"italic": True, "indent": 1, "font_color": "#595959"}),
        "kpi_l": wb.add_format({"font_size": 9, "font_color": "#595959", "align": "center", "top": 2,
                                "left": 1, "right": 1, "top_color": navy, "text_wrap": True}),
        "kpi": wb.add_format({"bold": True, "font_size": 12, "align": "center", "num_format": NUM,
                              "bottom": 1, "left": 1, "right": 1}),
        "kpi_t": wb.add_format({"bold": True, "font_size": 12, "align": "center", "bottom": 1,
                                "left": 1, "right": 1}),
        "date": wb.add_format({"num_format": "dd-mmm-yy"}),
        "rate": wb.add_format({"num_format": "0.000000"}),
        "check": wb.add_format({"font_color": "#548235", "italic": True, "num_format": NUM}),
        "wrap": wb.add_format({"text_wrap": True, "valign": "top"}),
        "num": F["num"], "tot": F["tot"],
    }

    ws = wb.add_worksheet("Forecast")
    ds = wb.add_worksheet("Data")
    st = wb.add_worksheet("Settings")
    hs = wb.add_worksheet("Hold register")
    ws.activate()

    # ================= Settings =================
    st.set_column(0, 0, 26); st.set_column(1, 6, 15)
    st.write_row(0, 0, ["Lot no", "Label", "Start", "End", "Month", "Status"], f["hdr_l"])
    for i, l in enumerate(lots, 1):
        st.write(i, 0, l["no"]); st.write(i, 1, l["label"])
        st.write_datetime(i, 2, l["start"], f["date"]); st.write_datetime(i, 3, l["end"], f["date"])
        st.write(i, 4, f"{l['start']:%b %y}"); st.write(i, 5, l["status"])
    r0 = len(lots) + 2
    st.write(r0, 0, "As-of date", f["sub"]); st.write_datetime(r0, 1, AS_OF, f["date"])
    st.write(r0 + 1, 0, "Horizon (months)", f["sub"]); st.write(r0 + 1, 1, months)
    bank_hdr = r0 + 3
    st.write_row(bank_hdr, 0, ["Bank", "Account", "Ccy", "Balance (ccy)", "Rate to OMR", "Balance OMR"], f["hdr_l"])
    bank_first = bank_hdr + 1
    for i, (b, a, c, bal, rate) in enumerate(BANKS):
        r = bank_first + i
        st.write_row(r, 0, [b, a, c]); st.write_number(r, 3, bal, f["num"]); st.write_number(r, 4, rate, f["rate"])
        st.write_formula(r, 5, f"=ROUND(D{r + 1}*E{r + 1},3)", f["num"], float((bal * rate).quantize(D("0.001"))))
    erp_row = bank_first + len(BANKS)
    st.write(erp_row, 0, "Total ERP bank balance (OMR)", f["tot_l"])
    st.write_formula(erp_row, 5, f"=SUM(F{bank_first + 1}:F{erp_row})", f["tot"], float(erp_total))
    ERP_CELL = f"Settings!$F${erp_row + 1}"
    fr0 = erp_row + 2
    st.write_row(fr0, 0, ["Facility - bank", "Limit", "Utilised", "Available"], f["hdr_l"])
    for i, (b, lim, used) in enumerate(FACILITY, 1):
        r = fr0 + i
        st.write(r, 0, b); st.write_number(r, 1, lim, f["num"]); st.write_number(r, 2, used, f["num"])
        st.write_formula(r, 3, f"=B{r + 1}-C{r + 1}", f["num"], float(lim - used))
    fac_tot = fr0 + len(FACILITY) + 1
    st.write(fac_tot, 0, "Total facility available", f["tot_l"])
    st.write_formula(fac_tot, 3, f"=SUM(D{fr0 + 2}:D{fac_tot})", f["tot"], float(fac_avail))
    FAC_CELL = f"Settings!$D${fac_tot + 1}"

    # ================= Data =================
    cols = ["Source", "Key", "Category", "Direction", "Counterparty", "Reference", "Planned date",
            "Effective date", "Original lot", "Effective lot", "Amount", "Status", "Override",
            "Hold amount", "Next honouring date", "Honour lot", "Hold reason"]
    ds.write_row(0, 0, cols, f["hdr_l"])
    for i, r in enumerate(rows, 1):
        ds.write_row(i, 0, [r["src"], r["key"], r["cat"], r["dir"], r["cp"], r["ref"]])
        ds.write_datetime(i, 6, r["planned"], f["date"]); ds.write_datetime(i, 7, r["eff"], f["date"])
        ds.write(i, 8, r["olot"]); ds.write(i, 9, r["elot"] if r["elot"] else "")
        ds.write_number(i, 10, r["amt"], f["num"]); ds.write(i, 11, r["status"]); ds.write(i, 12, r["override"])
        if r["hold_amt"]:
            ds.write_number(i, 13, r["hold_amt"], f["num"])
            if r["honour"]:
                ds.write_datetime(i, 14, r["honour"], f["date"])
            else:
                ds.write(i, 14, "Open-ended")
            ds.write(i, 15, r["hlot"] if r["hlot"] else ("" if r["honour"] is None else "Beyond horizon"))
            ds.write(i, 16, r["hold_reason"])
    n_data = len(rows) + 1
    ds.autofilter(0, 0, n_data - 1, len(cols) - 1); ds.freeze_panes(1, 0)
    ds.set_column(0, 1, 13); ds.set_column(2, 2, 28); ds.set_column(3, 3, 9); ds.set_column(4, 5, 18)
    ds.set_column(6, 9, 12); ds.set_column(10, 10, 14); ds.set_column(11, 12, 16)
    ds.set_column(13, 15, 15); ds.set_column(16, 16, 22)
    rng = lambda c: f"Data!${c}$2:${c}${n_data}"  # noqa: E731
    CAT, OLOT, ELOT, AMT, STAT, OVR = rng("C"), rng("I"), rng("J"), rng("K"), rng("L"), rng("M")
    HAMT, HLOT = rng("N"), rng("P")

    # ================= Forecast: column map =================
    LC, MC = {}, {}          # lot no -> col, month key -> month-total col
    c = 2
    for mk in month_keys:
        for n in lots_in[mk]:
            LC[n] = c; c += 1
        MC[mk] = c; c += 1
    HC = c                   # horizon total col
    ws.set_column(0, 0, 36); ws.set_column(1, 1, 10); ws.set_column(2, HC, 13.5)
    for mk in month_keys:
        ws.set_column(MC[mk], MC[mk], 14.5)
    ws.set_column(HC, HC, 14.5)
    ws.hide_gridlines(2)

    ws.write(0, 0, COMPANY, f["title"])
    ws.write(1, 0, f"Working Capital Cash Flow Forecast - OMR - {months}-month horizon", f["sub"])
    ws.write(2, 0, f"As of {AS_OF:%d %b %Y}  |  Scenario: Base  |  Status: DRAFT  |  "
                   "Prepared by: preparer1  |  Reviewed by: ________", f["meta"])

    BAND, HDR, STATUS, LOTNO = 7, 8, 9, 10
    ws.write(BAND, 0, "", f["band"]); ws.write(BAND, 1, "", f["band"])
    ws.write(HDR, 0, "OMR", f["hdr_l"]); ws.write(HDR, 1, "Source", f["hdr"])
    ws.write(STATUS, 0, "", f["status"]); ws.write(STATUS, 1, "", f["status"])
    for mk in month_keys:
        first, last = LC[lots_in[mk][0]], MC[mk]
        mlabel = date(mk[0], mk[1], 1).strftime("%B %Y")
        if first == last:
            ws.write(BAND, first, mlabel, f["band"])
        else:
            ws.merge_range(BAND, first, BAND, last, mlabel, f["band"])
        for n in lots_in[mk]:
            l = lots[n - 1]
            ws.write(HDR, LC[n], f"Lot {n}\n{l['label']}", f["hdr"])
            ws.write(STATUS, LC[n], l["status"], f["status_cur"] if l["status"] == "CURRENT" else f["status"])
            ws.write(LOTNO, LC[n], n)
        partial = lots[lots_in[mk][0] - 1]["start"].day != 1
        ws.write(HDR, MC[mk], f"{date(mk[0], mk[1], 1):%b %y}\ntotal" + (" *" if partial else ""), f["hdr_m"])
        ws.write(STATUS, MC[mk], "MONTH", f["status"])
    ws.write(BAND, HC, "", f["band"])
    ws.write(HDR, HC, "Horizon\ntotal", f["hdr_m"]); ws.write(STATUS, HC, "", f["status"])
    ws.set_row(HDR, 32); ws.set_row(LOTNO, None, None, {"hidden": True})
    ws.freeze_panes(LOTNO + 1, 2)

    cell = lambda r, col: xl_rowcol_to_cell(r, col)  # noqa: E731
    lotref = lambda n: xl_rowcol_to_cell(LOTNO, LC[n], row_abs=True)  # noqa: E731

    def section_bar(r, title):
        ws.write(r, 0, title, f["sect"])
        for col in range(1, HC + 1):
            ws.write_blank(r, col, None, f["sect"])

    def mval(key, mk, kind):
        ns = lots_in[mk]
        if kind == "sum":
            return sum(V[key][n] for n in ns)
        if kind == "first":
            return V[key][ns[0]]
        if kind == "last":
            return V[key][ns[-1]]
        return min(V[key][n] for n in ns)  # min

    def write_row(r, key, lot_formula, kind, fmt):
        """kind: sum (flows) | first (opening) | last (balances) | min (gap)."""
        for n in nos:
            ws.write_formula(r, LC[n], lot_formula(n), F[fmt], float(V[key][n]))
        for mk in month_keys:
            ns = lots_in[mk]
            a, b = cell(r, LC[ns[0]]), cell(r, LC[ns[-1]])
            fml = {"sum": f"=SUM({a}:{b})", "first": f"={a}", "last": f"={b}", "min": f"=MIN({a}:{b})"}[kind]
            ws.write_formula(r, MC[mk], fml, FM[fmt], float(mval(key, mk, kind)))
        mcells = ",".join(cell(r, MC[mk]) for mk in month_keys)
        hv = {"sum": sum(V[key][n] for n in nos), "first": V[key][nos[0]], "last": V[key][nos[-1]],
              "min": min(V[key][n] for n in nos)}[kind]
        fml = {"sum": f"=SUM({mcells})", "first": f"={cell(r, MC[month_keys[0]])}",
               "last": f"={cell(r, MC[month_keys[-1]])}", "min": f"=MIN({mcells})"}[kind]
        ws.write_formula(r, HC, fml, FM[fmt], float(hv))

    r = LOTNO + 2
    section_bar(r, "A. OPENING CASH")
    OPEN = r + 1
    # rows below are laid out first so formulas can reference them
    IN0 = OPEN + 3
    TI = IN0 + len(INFLOW_CATS)
    OUT0 = TI + 3
    TO = OUT0 + len(OUTFLOW_CATS)
    NET, CLOSE = TO + 2, TO + 3
    FSEC = CLOSE + 2; FAC, FP, GAP = FSEC + 1, FSEC + 2, FSEC + 3
    HSEC = GAP + 2
    HOUT, HIN, HNET, HCUM = HSEC + 1, HSEC + 2, HSEC + 3, HSEC + 4
    CLOSEH, FPH, GAPH, HCHK = HSEC + 6, HSEC + 7, HSEC + 8, HSEC + 9
    MSEC = HCHK + 2; MR, MD, MOPEN = MSEC + 1, MSEC + 2, MSEC + 3

    ws.write(OPEN, 0, "Opening bank balance", f["lbl"]); ws.write(OPEN, 1, "ERP / prior", f["note"])
    write_row(OPEN, "open", lambda n: f"={ERP_CELL}" if n == 1 else f"={cell(CLOSE, LC[n - 1])}", "first", "num")

    for title, cats, first, tot_row, key, tlabel in (
            ("B. CASH INFLOWS", INFLOW_CATS, IN0, TI, "ti", "Total inflows"),
            ("C. CASH OUTFLOWS", OUTFLOW_CATS, OUT0, TO, "to", "Total outflows")):
        section_bar(first - 1, title)
        for i, cat in enumerate(cats):
            rr = first + i
            ws.write(rr, 0, cat, f["lbl"]); ws.write(rr, 1, SOURCE_NOTE[cat], f["note"])
            write_row(rr, cat, lambda n, rr=rr: f'=SUMIFS({AMT},{CAT},$A{rr + 1},{ELOT},{lotref(n)},{STAT},"Active")',
                      "sum", "num")
        ws.write(tot_row, 0, tlabel, f["tot_l"]); ws.write_blank(tot_row, 1, None, f["tot_l"])
        write_row(tot_row, key, lambda n, a=first, b=tot_row - 1: f"=SUM({cell(a, LC[n])}:{cell(b, LC[n])})",
                  "sum", "tot")

    ws.write(NET, 0, "D. NET CASH FLOW  (B - C)", f["tot_l"]); ws.write_blank(NET, 1, None, f["tot_l"])
    write_row(NET, "net", lambda n: f"={cell(TI, LC[n])}-{cell(TO, LC[n])}", "sum", "tot")
    ws.write(CLOSE, 0, "E. CLOSING BALANCE  (A + D)", f["close_l"]); ws.write_blank(CLOSE, 1, None, f["close_l"])
    write_row(CLOSE, "close", lambda n: f"={cell(OPEN, LC[n])}+{cell(NET, LC[n])}", "last", "close")

    section_bar(FSEC, "F. FUNDING")
    ws.write(FAC, 0, "Bank facility available", f["lbl"]); ws.write(FAC, 1, "Manual", f["note"])
    write_row(FAC, "fac", lambda n: f"={FAC_CELL}", "last", "num")
    ws.write(FP, 0, "Funding position before holds  (E + facility)", f["close_l"])
    ws.write_blank(FP, 1, None, f["close_l"])
    write_row(FP, "fp", lambda n: f"={cell(CLOSE, LC[n])}+{cell(FAC, LC[n])}", "last", "close")
    ws.write(GAP, 0, "Funding gap before holds  (worst)", f["lbl"])
    write_row(GAP, "gap", lambda n: f"=MIN(0,{cell(FP, LC[n])})", "min", "gap")

    # ---------- G. cheque holds ----------
    section_bar(HSEC, "G. CHEQUE HOLDS  (see PDC detail and Hold register)")
    ws.write(HOUT, 0, "+ PDCs put on hold (out of this lot)", f["lbl"]); ws.write(HOUT, 1, "Hold", f["note"])
    write_row(HOUT, "hout", lambda n: f"=SUMIFS({HAMT},{ELOT},{lotref(n)})", "sum", "num")
    ws.write(HIN, 0, "- Held PDCs re-presented (honouring date)", f["lbl"]); ws.write(HIN, 1, "Hold", f["note"])
    write_row(HIN, "hin", lambda n: f"=SUMIFS({HAMT},{HLOT},{lotref(n)})", "sum", "num")
    ws.write(HNET, 0, "Net hold effect in lot", f["tot_l"]); ws.write_blank(HNET, 1, None, f["tot_l"])
    write_row(HNET, "hnet", lambda n: f"={cell(HOUT, LC[n])}-{cell(HIN, LC[n])}", "sum", "tot")
    ws.write(HCUM, 0, "Cumulative hold effect", f["lbl"])
    write_row(HCUM, "hcum", lambda n: f"={cell(HNET, LC[n])}" if n == 1
              else f"={cell(HCUM, LC[n - 1])}+{cell(HNET, LC[n])}", "last", "num")
    ws.write(CLOSEH, 0, "Closing balance after holds  (E + cumulative)", f["close_l"])
    ws.write_blank(CLOSEH, 1, None, f["close_l"])
    write_row(CLOSEH, "close_h", lambda n: f"={cell(CLOSE, LC[n])}+{cell(HCUM, LC[n])}", "last", "close")
    ws.write(FPH, 0, "NET FUNDING POSITION AFTER HOLDS", f["close_l"]); ws.write_blank(FPH, 1, None, f["close_l"])
    write_row(FPH, "fp_h", lambda n: f"={cell(CLOSEH, LC[n])}+{cell(FAC, LC[n])}", "last", "close")
    ws.write(GAPH, 0, "Shortfall after holds  (still to cover)", f["lbl"])
    write_row(GAPH, "gap_h", lambda n: f"=MIN(0,{cell(FPH, LC[n])})", "min", "gap")
    ws.write(HCHK, 0, "Are the holds sufficient?", f["lbl"])
    chk_ok = wb.add_format({"align": "right", "font_color": "#548235", "italic": True})
    chk_cov = wb.add_format({"align": "right", "font_color": "#2F5597", "bold": True})
    chk_bad = wb.add_format({"align": "right", "font_color": "#C00000", "bold": True})

    def chk_text(fp, fph):
        return "No gap" if fp >= 0 else ("Covered by holds" if fph >= 0 else "NOT sufficient")

    chk_cols = [(LC[n], V["fp"][n], V["fp_h"][n]) for n in nos]
    chk_cols += [(MC[mk], min(V["fp"][n] for n in lots_in[mk]), min(V["fp_h"][n] for n in lots_in[mk]))
                 for mk in month_keys]
    for col, fpv, fphv in chk_cols:
        is_lot = col in LC.values()
        if is_lot:
            fml = (f'=IF({cell(FP, col)}>=0,"No gap",IF({cell(FPH, col)}>=0,"Covered by holds","NOT sufficient"))')
        else:  # month: worst lot of the month
            mk = next(k for k, v in MC.items() if v == col)
            a, b = LC[lots_in[mk][0]], LC[lots_in[mk][-1]]
            fml = (f'=IF(MIN({cell(FP, a)}:{cell(FP, b)})>=0,"No gap",'
                   f'IF(MIN({cell(FPH, a)}:{cell(FPH, b)})>=0,"Covered by holds","NOT sufficient"))')
        txt = chk_text(fpv, fphv)
        ws.write_formula(HCHK, col, fml, {"No gap": chk_ok, "Covered by holds": chk_cov}.get(txt, chk_bad), txt)
    hz = chk_text(min(V["fp"][n] for n in nos), min(V["fp_h"][n] for n in nos))
    ws.write_formula(HCHK, HC, f'=IF({cell(GAP, HC)}>=0,"No gap",IF({cell(GAPH, HC)}>=0,"Covered by holds",'
                               f'"NOT sufficient"))', {"No gap": chk_ok, "Covered by holds": chk_cov}.get(hz, chk_bad), hz)

    section_bar(MSEC, "H. MEMO - NOT INCLUDED IN TOTALS")
    for row, key, label, fml in (
            (MR, "risk", "Risk-adjusted collections excluded",
             lambda n: f'=SUMIFS({AMT},{STAT},"Excluded - risk",{OLOT},{lotref(n)})'),
            (MD, "defin", "Deferred into this lot (included above)",
             lambda n: f'=SUMIFS({AMT},{OVR},"Deferred",{ELOT},{lotref(n)})')):
        ws.write(row, 0, label, f["memo_l"])
        write_row(row, key, fml, "sum", "memo")
    ws.write(MOPEN, 0, "Holds not re-presented within the horizon (open-ended / later)", f["memo_l"])
    ws.write_formula(MOPEN, HC, f"={cell(HOUT, HC)}-{cell(HIN, HC)}", FM["memo"],
                     float(total_held - sum(repres.values())))
    note_row = MOPEN + 1
    if any(lots[lots_in[mk][0] - 1]["start"].day != 1 for mk in month_keys):
        ws.write(note_row, 0, "* Current month total covers the remaining lots only (from the current lot).",
                 f["note"])

    # ---------- KPI strip ----------
    # ranges span lot AND month-total columns; the hidden lot-no row (blank under month totals)
    # restricts counts to lots. A month total's funding position equals its last lot, and lots come
    # first, so MATCH on the minimum always lands on a lot column.
    span = lambda row: f"{cell(row, 2)}:{cell(row, HC - 1)}"  # noqa: E731
    FPR, HDRR = span(FP), span(HDR)
    LNR = f"{xl_rowcol_to_cell(LOTNO, 2, row_abs=True)}:{xl_rowcol_to_cell(LOTNO, HC - 1, row_abs=True)}"
    low = min(V["fp"][n] for n in nos)
    low_lot = next(n for n in nos if V["fp"][n] == low)
    gap_lots = sum(1 for n in nos if V["fp"][n] < 0)
    first_gap = next((n for n in nos if V["fp"][n] < 0), None)
    hdr_txt = lambda n: f"Lot {n}\n{lots[n - 1]['label']}"  # noqa: E731
    FPHR = span(FPH)
    low_h = min(V["fp_h"][n] for n in nos)
    gap_lots_h = sum(1 for n in nos if V["fp_h"][n] < 0)
    kpis = [
        ("Lowest funding before holds", f"=MIN({FPR})", float(low), "kpi"),
        ("Tightest lot (before holds)", f"=INDEX({HDRR},MATCH(MIN({FPR}),{FPR},0))", hdr_txt(low_lot), "kpi_t"),
        ("Lots with gap before / after holds",
         f'=COUNTIFS({FPR},"<0",{LNR},">0")&" / "&COUNTIFS({FPHR},"<0",{LNR},">0")',
         f"{gap_lots} / {gap_lots_h}", "kpi_t"),
        ("First gap (before holds)", f'=IFERROR(INDEX({HDRR},MATCH(1,INDEX(({FPR}<0)*({LNR}>0),0),0)),"None")',
         hdr_txt(first_gap) if first_gap else "None", "kpi_t"),
        ("Total on hold", f"={cell(HOUT, HC)}", float(total_held), "kpi"),
        ("Lowest NET funding after holds", f"=MIN({FPHR})", float(low_h), "kpi"),
    ]
    ws.set_row(5, 30)
    for i, (lab, fml, val, fmt) in enumerate(kpis):
        col = 0 if i == 0 else 1 + i
        ws.write(4, col, lab, f["kpi_l"]); ws.write_formula(5, col, fml, f[fmt], val)

    # ---------- Bank tie-out ----------
    r = note_row + 2
    section_bar(r, "BANK POSITION & ERP TIE-OUT")
    r += 1
    ws.write_row(r, 0, ["Bank / account", "Ccy", "Balance (ccy)", "Rate to OMR", "Balance OMR"], f["hdr_l"])
    for i in range(len(BANKS)):
        rr, sr = r + 1 + i, bank_first + 1 + i
        ws.write_formula(rr, 0, f'=Settings!A{sr}&" - "&Settings!B{sr}', None, f"{BANKS[i][0]} - {BANKS[i][1]}")
        ws.write_formula(rr, 1, f"=Settings!C{sr}", None, BANKS[i][2])
        ws.write_formula(rr, 2, f"=Settings!D{sr}", f["num"], float(BANKS[i][3]))
        ws.write_formula(rr, 3, f"=Settings!E{sr}", f["rate"], float(BANKS[i][4]))
        ws.write_formula(rr, 4, f"=Settings!F{sr}", f["num"], float((BANKS[i][3] * BANKS[i][4]).quantize(D("0.001"))))
    r = r + len(BANKS) + 1
    prior_forecast = erp_total - D("3215.400")
    for i, (lab, fml, val, fmt) in enumerate([
            ("Total ERP bank balance (OMR)", f"={ERP_CELL}", erp_total, "tot"),
            ("Model opening - current lot", f"={cell(OPEN, LC[1])}", V["open"][1], "num"),
            ("Difference (must be nil)", f"={cell(r + 1, 4)}-{cell(r, 4)}", D(0), "check"),
            ("Previous snapshot: forecast balance for today", None, prior_forecast, "num"),
            ("Forecast variance  (ERP - forecast)", f"={cell(r, 4)}-{cell(r + 3, 4)}", erp_total - prior_forecast,
             "tot")]):
        ws.write(r + i, 0, lab, f["tot_l"] if fmt == "tot" else f["lbl"])
        if fml:
            ws.write_formula(r + i, 4, fml, f[fmt], float(val))
        else:
            ws.write_number(r + i, 4, val, f[fmt])
    r += 6

    # ---------- detail blocks ----------
    hold_hl = wb.add_format({"bg_color": "#FFF2CC"})
    hold_num = wb.add_format({"bg_color": "#FFF2CC", "num_format": NUM})
    hold_date = wb.add_format({"bg_color": "#FFF2CC", "num_format": "dd-mmm-yy"})

    def detail(title, sel, start, check_row, with_hold=False):
        section_bar(start, title)
        hdr = ["Counterparty", "Lot", "Date", "Reference", "Key", "Amount", "Action"]
        if with_hold:
            hdr += ["Hold amount", "Next honouring", "Honour lot", "Days held"]
        ws.write_row(start + 1, 0, hdr, f["hdr_l"])
        rr = start + 2
        for lot in nos + [None]:
            grp = sorted((x for x in sel if (x["elot"] if x["status"] == "Active" else None) == lot),
                         key=lambda x: x["eff"])
            if not grp:
                continue
            g0 = rr
            for x in grp:
                di = rows.index(x) + 2
                ws.write_formula(rr, 0, f"=Data!E{di}", None, x["cp"])
                ws.write(rr, 1, lot if lot else "-")
                ws.write_formula(rr, 2, f"=Data!H{di}", f["date"], (x["eff"] - date(1899, 12, 30)).days)
                ws.write_formula(rr, 3, f"=Data!F{di}", None, x["ref"])
                ws.write_formula(rr, 4, f"=Data!B{di}", None, x["key"])
                ws.write_formula(rr, 5, f"=Data!K{di}", f["num"], float(x["amt"]))
                held = bool(x["hold_amt"])
                ws.write(rr, 6, "Hold" if held else (x["override"] or "Active"), hold_hl if held else None)
                if with_hold and held:
                    ws.write_formula(rr, 7, f"=Data!N{di}", hold_num, float(x["hold_amt"]))
                    if x["honour"]:
                        ws.write_formula(rr, 8, f"=Data!O{di}", hold_date, (x["honour"] - date(1899, 12, 30)).days)
                        ws.write_formula(rr, 10, f"=Data!O{di}-Data!H{di}", hold_hl, (x["honour"] - x["eff"]).days)
                    else:
                        ws.write(rr, 8, "Open-ended", hold_hl); ws.write(rr, 10, "-", hold_hl)
                    ws.write(rr, 9, x["hlot"] if x["hlot"] else ("Beyond" if x["honour"] else "-"), hold_hl)
                rr += 1
            if with_hold:
                ws.data_validation(g0, 6, rr - 1, 6, {"validate": "list", "source": ["Active", "Hold", "Deferred"]})
            ws.write(rr, 0, f"Lot {lot} ({lots[lot - 1]['label']}) subtotal" if lot
                     else "Not in totals (excluded)", f["tot_l"])
            ws.write_formula(rr, 5, f"=SUM(F{g0 + 1}:F{rr})", f["tot"], float(sum(x["amt"] for x in grp)))
            chk_col = 6
            if with_hold:
                ws.write_formula(rr, 7, f"=SUM(H{g0 + 1}:H{rr})", f["tot"], float(sum(x["hold_amt"] for x in grp)))
                chk_col = 9
            if lot and check_row is not None:
                ws.write(rr, chk_col, "agrees to grid:", f["note"])
                fml = f"=ABS({cell(rr, 5)}-{cell(check_row, LC[lot])})"
                if with_hold:
                    fml += f"+ABS({cell(rr, 7)}-{cell(HOUT, LC[lot])})"
                ws.write_formula(rr, chk_col + 1, fml, f["check"], 0.0)
            rr += 2
        return rr

    r = detail("PDC DETAIL  (Action: Active / Hold / Deferred - holds need a next honouring date)",
               [x for x in rows if x["src"] == "PDC"], r, OUT0 + OUTFLOW_CATS.index("Vendor PDCs"), True)
    r = detail("BILL DISCOUNT PROCEEDS DETAIL (inflow)", [x for x in rows if x["cat"] == "Bill discount proceeds"],
               r, IN0 + INFLOW_CATS.index("Bill discount proceeds"))
    r = detail("BILL DISCOUNT / LC MATURITIES DETAIL (outflow)",
               [x for x in rows if x["cat"] == "Bill discount / LC maturities"], r,
               OUT0 + OUTFLOW_CATS.index("Bill discount / LC maturities"))

    # ---------- commentary ----------
    section_bar(r, "COMMENTARY (auto-generated, advisory)")
    r += 1
    for n in nos:
        biggest = max(OUTFLOW_CATS, key=lambda c: V[c][n])
        fp, fph = V["fp"][n], V["fp_h"][n]
        txt = (f"Lot {n} ({lots[n - 1]['label']}): closes at {V['close'][n]:,.3f} (net {V['net'][n]:+,.3f}). "
               f"Largest outflow: {biggest} {V[biggest][n]:,.3f}. "
               + (f"Headroom {fp:,.3f} including facility." if fp >= 0
                  else f"FUNDING GAP of {-fp:,.3f} before holds; "
                       + (f"holds cover it, net funding after holds {fph:,.3f}." if fph >= 0
                          else f"holds are NOT sufficient, a further {-fph:,.3f} is needed."))
               + (f" Held cheques of {V['hin'][n]:,.3f} come back in this lot." if V["hin"][n] else ""))
        ws.merge_range(r, 0, r, HC, txt, f["wrap"]); ws.set_row(r, 18); r += 1

    ws.set_landscape(); ws.set_paper(8 if len(nos) > 6 else 9); ws.fit_to_pages(1, 0)
    ws.repeat_rows(BAND, STATUS); ws.repeat_columns(0, 0)
    ws.set_margins(0.3, 0.3, 0.5, 0.5); ws.set_footer("&L&8Synthetic data - draft&R&8Page &P of &N")

    # ================= Hold register =================
    hs.set_column(0, 0, 13); hs.set_column(1, 1, 14); hs.set_column(2, 2, 12); hs.set_column(3, 4, 12)
    hs.set_column(5, 6, 13); hs.set_column(7, 9, 12); hs.set_column(10, 10, 8); hs.set_column(11, 13, 16)
    hs.write(0, 0, "Hold register - cheques held by us, with the next honouring date", f["sub"])
    hs.write(1, 0, "A held cheque leaves its own lot and comes back in the lot of its next honouring date. "
                   "Open-ended holds stay out until a date is set.", f["meta"])
    hs.write_row(3, 0, ["Key", "Vendor", "Cheque no", "Cheque date", "Cheque lot", "Cheque amount", "Amount held",
                        "Next honouring", "Honour lot", "Days held", "Times extended", "Reason", "Held by",
                        "Validity warning"], f["hdr_l"])
    hr = 4
    validity = 180
    for x in rows:
        if x["hold_amt"]:
            hs.write_row(hr, 0, [x["key"], x["cp"], x["ref"]])
            hs.write_datetime(hr, 3, x["eff"], f["date"]); hs.write(hr, 4, x["elot"])
            hs.write_number(hr, 5, x["amt"], f["num"]); hs.write_number(hr, 6, x["hold_amt"], f["num"])
            if x["honour"]:
                hs.write_datetime(hr, 7, x["honour"], f["date"])
                hs.write(hr, 8, x["hlot"] if x["hlot"] else "Beyond horizon")
                hs.write_formula(hr, 9, f"=H{hr + 1}-D{hr + 1}", None, (x["honour"] - x["eff"]).days)
                hs.write_formula(hr, 13, f'=IF(H{hr + 1}-D{hr + 1}>{validity},"Cheque may be stale","")', None, "")
            else:
                hs.write(hr, 7, "Open-ended"); hs.write(hr, 8, "-"); hs.write(hr, 9, "-")
                hs.write(hr, 13, "Set a date")
            hs.write(hr, 10, 0); hs.write(hr, 11, x["hold_reason"]); hs.write(hr, 12, "preparer1")
            hr += 1
    hs.write(hr, 0, "Total held", f["tot_l"])
    hs.write_formula(hr, 6, f"=SUM(G5:G{hr})", f["tot"], float(total_held))
    wb.close()

    print(f"Wrote {out}  ({months} months, {len(nos)} lots, {len(rows)} data rows, "
          f"{sum(1 for x in rows if x['src'] == 'PDC')} PDCs)")
    print(f"ERP opening {erp_total:,.3f} | facility available {fac_avail:,.3f}")
    for n in nos:
        print(f"Lot {n} {lots[n - 1]['label']:>10}: open {V['open'][n]:>13,.3f} in {V['ti'][n]:>12,.3f} "
              f"out {V['to'][n]:>12,.3f} close {V['close'][n]:>13,.3f} funding {V['fp'][n]:>13,.3f} "
              f"| hold out {V['hout'][n]:>10,.3f} back {V['hin'][n]:>10,.3f} funding after {V['fp_h'][n]:>13,.3f}")
    for x in rows:
        if x["hold_amt"]:
            print(f"  HOLD {x['key']} {x['cp']} lot {x['elot']} amt {x['amt']:,.3f} held {x['hold_amt']:,.3f} "
                  f"-> {x['honour'] or 'open-ended'} (lot {x['hlot']})")
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--months", type=int, default=3, choices=range(1, 13))
    main(ap.parse_args().months)
