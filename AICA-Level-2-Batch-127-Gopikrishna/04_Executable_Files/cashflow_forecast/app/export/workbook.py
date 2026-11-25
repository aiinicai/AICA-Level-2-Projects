"""Excel export built with XlsxWriter. Every figure on the Forecast sheet is a live formula.

Sheets
- Forecast: the lot grid (same rows and columns as the screen). Category cells are SUMIFS over Items;
  the hold block is SUMIFS over Holds; opening cash and facility come from Bank; every total,
  closing, funding position, status and month/horizon total is a formula over those cells.
- Items: every item the forecast looked at, with its effective date, lot number and status.
  Only rows with a lot number count in the grid.
- Holds: one row per cheque on hold: lot it was held in and lot it is re-presented in (0 = not
  within the horizon).
- Bank: bank balances (OMR = ROUND(balance x rate)) and facilities, with totals.
- About: as-of date, scenario, who exported it, the formula-check result and warnings.

``build_workbook`` returns the value the app calculated for every formula cell, keyed by
(sheet, cell). The checker recalculates the file in LibreOffice and compares the two.
With ``cached=False`` no results are stored in the file, so a file that is not really
recalculated cannot pass the check by accident.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import xlsxwriter
from xlsxwriter.utility import xl_col_to_name

from app import __version__
from app.engine.forecast import COVERED, LINE_LABELS, LINE_RULES, NO_GAP, NOT_SUFFICIENT, Forecast

FORECAST, ITEMS, HOLDS, BANK, ABOUT = "Forecast", "Items", "Holds", "Bank", "About"
FIRST_GRID_ROW = 7          # 0-based row where the grid body starts
LOT_ROW = 6                 # hidden row with lot numbers (used by SUMIFS)
STATUS_FILL = {NO_GAP: "#d1e7dd", COVERED: "#fff3cd", NOT_SUFFICIENT: "#f8d7da"}


@dataclass
class GridLine:
    label: str
    kind: str                     # section | group | cat | line | total | key | status | memo
    key: str | None = None        # LINE_RULES key, or None
    cat: object = None            # CategoryRow for kind == "cat"
    hint: str = ""


def _layout(fc: Forecast) -> list[GridLine]:
    out = [GridLine("A. Opening cash", "section"), GridLine(LINE_LABELS["opening"], "line", "opening")]
    for title, cats, total in (("B. Cash inflows", fc.inflow_rows, "inflows"),
                               ("C. Cash outflows", fc.outflow_rows, "outflows")):
        out.append(GridLine(title, "section"))
        groups, last = {r.group for r in cats}, None
        for r in cats:
            if len(groups) > 1 and r.group != last:
                out.append(GridLine(r.group, "group"))
                last = r.group
            out.append(GridLine(r.name, "cat", cat=r))
        out.append(GridLine(LINE_LABELS[total], "total", total))
    out += [
        GridLine("D. " + LINE_LABELS["net"], "total", "net"),
        GridLine("E. " + LINE_LABELS["closing"], "key", "closing"),
        GridLine("F. Funding", "section"),
        GridLine(LINE_LABELS["facility"], "line", "facility"),
        GridLine(LINE_LABELS["fp_before"], "total", "fp_before"),
        GridLine(LINE_LABELS["gap_before"], "line", "gap_before"),
        GridLine("G. Cheque holds", "section", hint="Rows B-F are as per ERP. Holds are applied here."),
        GridLine(LINE_LABELS["hold_out"], "line", "hold_out"),
        GridLine(LINE_LABELS["hold_in"], "line", "hold_in"),
        GridLine(LINE_LABELS["hold_net"], "total", "hold_net"),
        GridLine(LINE_LABELS["hold_cum"], "line", "hold_cum"),
        GridLine(LINE_LABELS["closing_after"], "total", "closing_after"),
        GridLine(LINE_LABELS["fp_after"], "key", "fp_after"),
        GridLine(LINE_LABELS["shortfall_after"], "line", "shortfall_after"),
        GridLine("Are the holds sufficient?", "status", "status"),
        GridLine("H. Memo (not in totals)", "section"),
    ]
    out += [GridLine(LINE_LABELS[k], "memo", k) for k in ("risk_excluded", "deferred_in", "holds_open")]
    return out


def _num(v: Decimal | None):
    return None if v is None else float(v)


def build_workbook(fc: Forecast, path: Path, *, cached: bool, generated_by: str = "",
                   generated_at: datetime | None = None, check_note: str = "") -> dict[tuple[str, str], object]:
    """Write the workbook to ``path``; return {(sheet, cell): value the app calculated}."""
    s = fc.settings
    dp = s.currency_decimals
    expected: dict[tuple[str, str], object] = {}
    wb = xlsxwriter.Workbook(str(path), {"strings_to_formulas": False, "strings_to_urls": False})
    wb.set_properties({"title": f"Cash flow forecast {fc.as_of:%d-%b-%Y}", "subject": fc.scenario,
                       "author": generated_by or "Cash Flow Forecast", "comments": "Synthetic data only"})
    zeros = "0" * dp
    money_fmt = f'#,##0.{zeros};(#,##0.{zeros});"-"' if dp else '#,##0;(#,##0);"-"'
    F = {
        "title": wb.add_format({"bold": True, "font_size": 14, "font_color": "#1f3864"}),
        "sub": wb.add_format({"italic": True, "font_color": "#595959"}),
        "band": wb.add_format({"bold": True, "align": "center", "bg_color": "#1f3864", "font_color": "white",
                               "border": 1}),
        "head": wb.add_format({"bold": True, "align": "center", "bg_color": "#d9e1f2", "border": 1,
                               "text_wrap": True}),
        "head_tot": wb.add_format({"bold": True, "align": "center", "bg_color": "#b4c6e7", "border": 1,
                                   "text_wrap": True}),
        "lotst": wb.add_format({"font_size": 8, "align": "center", "font_color": "#595959"}),
        "section": wb.add_format({"bold": True, "bg_color": "#eef2f8", "font_color": "#1f3864"}),
        "group": wb.add_format({"italic": True, "indent": 1, "font_color": "#595959"}),
        "cat_l": wb.add_format({"indent": 2}),
        "line_l": wb.add_format({}),
        "total_l": wb.add_format({"bold": True, "top": 1}),
        "key_l": wb.add_format({"bold": True, "top": 1, "bottom": 6, "bg_color": "#fff2cc"}),
        "memo_l": wb.add_format({"italic": True, "font_color": "#7f7f7f"}),
        "status_l": wb.add_format({"bold": True}),
        "m": wb.add_format({"num_format": money_fmt}),
        "m_sub": wb.add_format({"num_format": money_fmt, "bg_color": "#f2f2f2"}),
        "m_total": wb.add_format({"num_format": money_fmt, "bold": True, "top": 1}),
        "m_key": wb.add_format({"num_format": money_fmt, "bold": True, "top": 1, "bottom": 6,
                                "bg_color": "#fff2cc"}),
        "m_memo": wb.add_format({"num_format": money_fmt, "italic": True, "font_color": "#7f7f7f"}),
        "m_locked": wb.add_format({"num_format": money_fmt, "font_color": "#7f7f7f", "bg_color": "#f2f2f2"}),
        "status": wb.add_format({"bold": True, "align": "center"}),
        "th": wb.add_format({"bold": True, "bg_color": "#d9e1f2", "border": 1, "text_wrap": True,
                             "valign": "top"}),
        "date": wb.add_format({"num_format": "dd-mmm-yyyy"}),
        "int": wb.add_format({"num_format": "0"}),
        "lotno": wb.add_format({"num_format": '0;-0;"none"'}),
        "rate": wb.add_format({"num_format": "0.000000"}),
        "bold": wb.add_format({"bold": True}),
        "m_bold": wb.add_format({"num_format": money_fmt, "bold": True, "top": 1}),
        "wrap": wb.add_format({"text_wrap": True, "valign": "top"}),
    }

    ws = wb.add_worksheet(FORECAST)
    wi = wb.add_worksheet(ITEMS)
    wh = wb.add_worksheet(HOLDS)
    wbk = wb.add_worksheet(BANK)
    wa = wb.add_worksheet(ABOUT)

    def put(sheet, ws_, r, c, formula, value, fmt):
        """Write a formula; remember what the app calculated for that cell."""
        cell = f"{xl_col_to_name(c)}{r + 1}"
        expected[(sheet, cell)] = value
        cached_value = None
        if cached:
            cached_value = value if isinstance(value, str) else _num(value)
        ws_.write_formula(r, c, formula, fmt, cached_value)
        return cell

    # ------------------------------------------------------------------ Items
    item_cols = ["Source", "Key", "Reference", "Counterparty", "Category", "Cat ID", "Direction",
                 "Original date", "Effective date", "Lot #", "Lot", "Amount", "Status", "Deferred into lot",
                 "Memo lot # (risk excluded)", "Flags", "Project", "Bank"]
    wi.write_row(0, 0, item_cols, F["th"])
    for n, o in enumerate(fc.items, start=1):
        it = o.item
        counted = o.status == "active" and o.lot is not None
        wi.write_row(n, 0, [it.source, it.key, it.reference, it.counterparty, o.category])
        wi.write_number(n, 5, o.category_id, F["int"])
        wi.write_string(n, 6, it.direction)
        wi.write_datetime(n, 7, datetime.combine(it.planned_date, datetime.min.time()), F["date"])
        wi.write_datetime(n, 8, datetime.combine(o.eff_date, datetime.min.time()), F["date"])
        if counted:
            wi.write_number(n, 9, o.lot + 1, F["int"])
            wi.write_string(n, 10, fc.fc_lots[o.lot].label)
        wi.write_number(n, 11, float(o.eff_amount), F["m"])
        wi.write_string(n, 12, o.status)
        if counted and "deferred" in o.flags:
            wi.write_string(n, 13, "yes")
        if o.memo_lot is not None:
            wi.write_number(n, 14, o.memo_lot + 1, F["int"])
        wi.write_row(n, 15, [", ".join(o.flags), it.project, it.bank])
    last_item = max(2, len(fc.items) + 1)
    wi.autofilter(0, 0, last_item - 1, len(item_cols) - 1)
    wi.freeze_panes(1, 0)
    wi.set_column(0, 0, 14); wi.set_column(1, 2, 16); wi.set_column(3, 4, 28); wi.set_column(5, 5, 7)
    wi.set_column(6, 6, 9); wi.set_column(7, 8, 13); wi.set_column(9, 9, 6); wi.set_column(10, 10, 12)
    wi.set_column(11, 11, 15); wi.set_column(12, 12, 15); wi.set_column(13, 14, 10); wi.set_column(15, 17, 18)

    def irng(col: str) -> str:
        return f"{ITEMS}!${col}$2:${col}${last_item}"

    # ------------------------------------------------------------------ Holds
    hold_cols = ["Source", "Key", "Reference", "Counterparty", "Category", "Cheque date", "Cheque amount",
                 "Amount held", "Held in lot #", "Held in lot", "Next honouring date", "Re-presented in lot #",
                 "Re-presented in lot", "Days held", "Times extended", "Reason", "Held by", "Warnings"]
    wh.write_row(0, 0, hold_cols, F["th"])
    for n, o in enumerate(fc.holds, start=1):
        h, it = o.hold, o.item
        wh.write_row(n, 0, [it.source, it.key, it.reference, it.counterparty, o.category])
        wh.write_datetime(n, 5, datetime.combine(o.eff_date, datetime.min.time()), F["date"])
        wh.write_number(n, 6, float(o.eff_amount), F["m"])
        wh.write_number(n, 7, float(h.amount), F["m"])
        wh.write_number(n, 8, h.out_lot + 1, F["int"])
        wh.write_string(n, 9, fc.fc_lots[h.out_lot].label)
        if h.honour_date:
            wh.write_datetime(n, 10, datetime.combine(h.honour_date, datetime.min.time()), F["date"])
        else:
            wh.write_string(n, 10, "open-ended")
        wh.write_number(n, 11, (h.honour_lot + 1) if h.honour_lot is not None else 0, F["lotno"])
        wh.write_string(n, 12, fc.fc_lots[h.honour_lot].label if h.honour_lot is not None
                        else "not within horizon")
        if h.days_held is not None:
            wh.write_number(n, 13, h.days_held, F["int"])
        wh.write_number(n, 14, h.times_extended, F["int"])
        wh.write_row(n, 15, [h.reason, h.held_by, " | ".join(h.warnings)])
    last_hold = max(2, len(fc.holds) + 1)
    wh.freeze_panes(1, 0)
    wh.set_column(0, 0, 12); wh.set_column(1, 2, 15); wh.set_column(3, 4, 26); wh.set_column(5, 7, 14)
    wh.set_column(8, 8, 8); wh.set_column(9, 9, 12); wh.set_column(10, 10, 14); wh.set_column(11, 11, 10)
    wh.set_column(12, 12, 18); wh.set_column(13, 14, 9); wh.set_column(15, 17, 26)
    if not fc.holds:
        wh.write_string(2, 0, "No cheques are on hold.", F["sub"])

    def hrng(col: str) -> str:
        return f"{HOLDS}!${col}$2:${col}${last_hold}"

    # ------------------------------------------------------------------ Bank
    wbk.write_string(0, 0, f"Bank balances ({s.base_currency}) used as opening cash", F["bold"])
    wbk.write_row(1, 0, ["Bank", "Account", "Currency", "As of", "Balance", f"Rate to {s.base_currency}",
                         f"{s.base_currency} equivalent"], F["th"])
    r = 2
    for b in fc.balances:
        wbk.write_row(r, 0, [b.bank, b.account, b.currency])
        wbk.write_datetime(r, 3, datetime.combine(b.as_of, datetime.min.time()), F["date"])
        wbk.write_number(r, 4, float(b.balance), F["m"])
        wbk.write_number(r, 5, float(b.rate), F["rate"])
        put(BANK, wbk, r, 6, f"=ROUND(E{r + 1}*F{r + 1},{dp})", b.omr, F["m"])
        r += 1
    if not fc.balances:                       # keep the total below the (empty) table, never on top of it
        wbk.write_string(r, 0, "(no bank balance loaded)", F["sub"])
        r += 1
    bal_first, bal_last = 3, r
    wbk.write_string(r, 0, "Total opening cash", F["bold"])
    opening_cell = put(BANK, wbk, r, 6, f"=SUM(G{bal_first}:G{bal_last})", fc.erp_opening, F["m_bold"])
    r += 3
    wbk.write_string(r, 0, "Bank facilities available", F["bold"])
    wbk.write_row(r + 1, 0, ["Bank", "Facility type", "As of", "Limit", "Utilised", "Available"], F["th"])
    r += 2
    fac_first = r + 1
    for f in fc.facilities:
        wbk.write_row(r, 0, [f.bank, f.facility_type])
        wbk.write_datetime(r, 2, datetime.combine(f.as_of, datetime.min.time()), F["date"])
        if f.limit is not None:
            wbk.write_number(r, 3, float(f.limit), F["m"])
        if f.utilised is not None:
            wbk.write_number(r, 4, float(f.utilised), F["m"])
        wbk.write_number(r, 5, float(f.available), F["m"])
        r += 1
    if not fc.facilities:
        wbk.write_string(r, 0, "(no facility loaded)", F["sub"])
        r += 1
    fac_last = r
    wbk.write_string(r, 0, "Total facility available", F["bold"])
    facility_cell = put(BANK, wbk, r, 5, f"=SUM(F{fac_first}:F{fac_last})", fc.facility_total, F["m_bold"])
    wbk.set_column(0, 1, 18); wbk.set_column(2, 3, 13); wbk.set_column(4, 6, 17)

    # ------------------------------------------------------------------ Forecast
    layout = _layout(fc)
    row_of: dict[str, int] = {}
    cat_rows: dict[str, list[int]] = {"inflow": [], "outflow": []}
    for k, gl in enumerate(layout):
        rr = FIRST_GRID_ROW + k
        if gl.key:
            row_of[gl.key] = rr
        if gl.kind == "cat":
            cat_rows[gl.cat.direction].append(rr)

    # columns: locked actuals (values), then the forecast columns
    cols = []
    for lt in fc.lots:
        if lt.status == "actual":
            cols.append(("actual", lt, fc.locked.get(lt.start)))
    for c in fc.columns:
        cols.append((c.kind, c, None))
    lot_col: dict[int, int] = {}                 # forecast lot index -> sheet column
    for j, (kind, c, _) in enumerate(cols):
        if kind == "lot":
            lot_col[c.lots[0]] = 2 + j

    def L(c: int) -> str:
        return xl_col_to_name(c)

    risk = "risk-adjusted collections excluded" if fc.exclude_risk else "risk-adjusted collections included"
    ws.write_string(0, 0, f"Working capital forecast · {s.base_currency}", F["title"])
    ws.write_string(1, 0, f"As of {fc.as_of:%d-%b-%Y} · Scenario: {fc.scenario} · {risk} · "
                          f"lots of {s.lot_length_days} days", F["sub"])
    ws.write_string(2, 0, "All figures are live formulas over the Items, Holds and Bank sheets. "
                          "Rows B-F are as per ERP; holds are applied in block G.", F["sub"])

    # month bands (row 3), labels (row 4), lot status (row 5), lot numbers (row 6, hidden)
    j = 0
    while j < len(cols):
        kind, c, _ = cols[j]
        if kind == "horizon":
            ws.write_string(3, 2 + j, "", F["band"])
            j += 1
            continue
        label = c.band                     # Lot (actual) and Column both carry the period heading
        k = j
        while k + 1 < len(cols) and cols[k + 1][0] != "horizon" and cols[k + 1][1].band == label:
            k += 1
        if k > j:
            ws.merge_range(3, 2 + j, 3, 2 + k, label, F["band"])
        else:
            ws.write_string(3, 2 + j, label, F["band"])
        j = k + 1
    ws.write_string(4, 0, "Lot", F["head"])
    ws.write_string(4, 1, "Cat ID", F["head"])
    for j, (kind, c, locked) in enumerate(cols):
        cc = 2 + j
        ws.write_string(4, cc, c.label, F["head"] if kind in ("lot", "actual") else F["head_tot"])
        if kind == "actual":
            ws.write_string(5, cc, "ACTUAL - locked", F["lotst"])
        elif kind == "lot":
            ws.write_string(5, cc, fc.fc_lots[c.lots[0]].status.upper(), F["lotst"])
            ws.write_number(LOT_ROW, cc, c.lots[0] + 1)
        elif kind == "month" and c.partial:
            ws.write_string(5, cc, "* part month", F["lotst"])
    ws.write_string(LOT_ROW, 0, "Lot number (used by the formulas)")
    ws.set_row(LOT_ROW, None, None, {"hidden": True})

    label_fmt = {"section": F["section"], "group": F["group"], "cat": F["cat_l"], "line": F["line_l"],
                 "total": F["total_l"], "key": F["key_l"], "memo": F["memo_l"], "status": F["status_l"]}
    num_fmt = {"cat": F["m"], "line": F["m"], "total": F["m_total"], "key": F["m_key"], "memo": F["m_memo"]}

    def lot_formula(key: str, i: int, cc: int) -> str:
        c, rr = L(cc), lambda k: row_of[k] + 1
        prev = L(lot_col[i - 1]) if i > 0 else None
        lot_no = f"{c}${LOT_ROW + 1}"
        if key == "opening":
            return f"={BANK}!${opening_cell[0]}${opening_cell[1:]}" if i == 0 else f"={prev}{rr('closing')}"
        if key in ("inflows", "outflows"):
            rows = cat_rows["inflow" if key == "inflows" else "outflow"]
            return f"=SUM({c}{rows[0] + 1}:{c}{rows[-1] + 1})" if rows else "=0"
        if key == "net":
            return f"={c}{rr('inflows')}-{c}{rr('outflows')}"
        if key == "closing":
            return f"={c}{rr('opening')}+{c}{rr('net')}"
        if key == "facility":
            return f"={BANK}!${facility_cell[0]}${facility_cell[1:]}"
        if key == "fp_before":
            return f"={c}{rr('closing')}+{c}{rr('facility')}"
        if key == "gap_before":
            return f"=MIN(0,{c}{rr('fp_before')})"
        if key == "hold_out":
            return f"=SUMIFS({hrng('H')},{hrng('I')},{lot_no})"
        if key == "hold_in":
            return f"=SUMIFS({hrng('H')},{hrng('L')},{lot_no})"
        if key == "hold_net":
            return f"={c}{rr('hold_out')}-{c}{rr('hold_in')}"
        if key == "hold_cum":
            return f"={c}{rr('hold_net')}" if i == 0 else f"={prev}{rr('hold_cum')}+{c}{rr('hold_net')}"
        if key == "closing_after":
            return f"={c}{rr('closing')}+{c}{rr('hold_cum')}"
        if key == "fp_after":
            return f"={c}{rr('closing_after')}+{c}{rr('facility')}"
        if key == "shortfall_after":
            return f"=MIN(0,{c}{rr('fp_after')})"
        if key == "status":
            return (f'=IF({c}{rr("fp_after")}<0,"{NOT_SUFFICIENT}",'
                    f'IF({c}{rr("fp_before")}<0,"{COVERED}","{NO_GAP}"))')
        if key == "risk_excluded":
            return f"=SUMIFS({irng('L')},{irng('O')},{lot_no})"
        if key == "deferred_in":
            return f'=SUMIFS({irng("L")},{irng("J")},{lot_no},{irng("N")},"yes")'
        if key == "holds_open":
            return f"=SUMIFS({hrng('H')},{hrng('I')},{lot_no},{hrng('L')},0)"
        raise KeyError(key)

    def summary_formula(rule: str, row: int, col) -> str:
        cells = [f"{L(lot_col[i])}{row + 1}" for i in col.lots]
        if rule == "first":
            return f"={cells[0]}"
        if rule == "last":
            return f"={cells[-1]}"
        return f"={'SUM' if rule == 'sum' else 'MIN'}({','.join(cells)})"

    for k, gl in enumerate(layout):
        rr = FIRST_GRID_ROW + k
        ws.write_string(rr, 0, gl.label, label_fmt[gl.kind])
        if gl.kind == "section":
            for j in range(len(cols)):
                ws.write_blank(rr, 2 + j, None, F["section"])
            if gl.hint:
                ws.write_comment(rr, 0, gl.hint)
            continue
        if gl.kind == "group":
            continue
        if gl.kind == "cat":
            ws.write_number(rr, 1, gl.cat.category_id)
        for j, (kind, c, locked) in enumerate(cols):
            cc = 2 + j
            if kind == "actual":
                src = (locked or {})
                if gl.kind == "status":
                    ws.write_string(rr, cc, src.get("funding_status", ""), F["status"])
                    continue
                v = (src.get("categories", {}).get(gl.cat.name) if gl.kind == "cat"
                     else src.get("lines", {}).get(gl.key))
                if v is not None:
                    ws.write_number(rr, cc, float(Decimal(v)), F["m_locked"])
                continue
            fmt = F["status"] if gl.kind == "status" else (num_fmt[gl.kind] if kind == "lot" else F["m_sub"])
            if kind == "lot":
                i = c.lots[0]
                if gl.kind == "cat":
                    formula = (f"=SUMIFS({irng('L')},{irng('F')},$B{rr + 1},{irng('J')},{L(cc)}${LOT_ROW + 1})")
                    value = gl.cat.values[i]
                elif gl.kind == "status":
                    formula, value = lot_formula("status", i, cc), fc.lot_status[i]
                else:
                    formula, value = lot_formula(gl.key, i, cc), fc.lines[gl.key][i]
            else:                                   # month / horizon total
                if gl.kind == "status":
                    first, last = L(lot_col[c.lots[0]]), L(lot_col[c.lots[-1]])
                    rng = f"{first}{rr + 1}:{last}{rr + 1}"
                    formula = (f'=IF(COUNTIF({rng},"{NOT_SUFFICIENT}")>0,"{NOT_SUFFICIENT}",'
                               f'IF(COUNTIF({rng},"{COVERED}")>0,"{COVERED}","{NO_GAP}"))')
                    value = fc.status(c)
                elif gl.kind == "cat":
                    formula, value = summary_formula("sum", rr, c), fc.row(gl.cat, c)
                else:
                    formula, value = summary_formula(LINE_RULES[gl.key], rr, c), fc.line(gl.key, c)
            put(FORECAST, ws, rr, cc, formula, value, fmt)

    srow = row_of["status"]
    last_col = 2 + len(cols) - 1
    for st, fill in STATUS_FILL.items():
        ws.conditional_format(srow, 2, srow, last_col, {"type": "cell", "criteria": "==", "value": f'"{st}"',
                                                        "format": wb.add_format({"bg_color": fill})})
    for key in ("fp_after", "fp_before", "closing", "closing_after"):
        ws.conditional_format(row_of[key], 2, row_of[key], last_col,
                              {"type": "cell", "criteria": "<", "value": 0,
                               "format": wb.add_format({"font_color": "#c00000"})})
    ws.set_column(0, 0, 46)
    ws.set_column(1, 1, 6, None, {"hidden": True})
    ws.set_column(2, last_col, 14)
    ws.set_row(4, 30)
    ws.freeze_panes(FIRST_GRID_ROW, 2)
    ws.set_landscape(); ws.set_paper(9); ws.fit_to_pages(1, 0); ws.repeat_rows(3, 5); ws.repeat_columns(0, 0)
    ws.activate()

    # ------------------------------------------------------------------ About
    wa.set_column(0, 0, 30); wa.set_column(1, 1, 90)
    info = [
        ("Report", "Working capital forecast (cash flow in lots)"),
        ("As of", f"{fc.as_of:%d-%b-%Y}"),
        ("Scenario", fc.scenario),
        ("Risk-adjusted collections", "excluded" if fc.exclude_risk else "included"),
        ("Currency", f"{s.base_currency}, {dp} decimals. Only {s.base_currency} flows are forecast."),
        ("Lots", f"{s.lot_scheme}, {s.lot_length_days} days"
                 + (f", anchored on {s.anchor:%d-%b-%Y}" if s.anchor else "")
                 + f"; {len(fc.fc_lots)} lots in the horizon"),
        ("Exported by", generated_by or "-"),
        ("Exported at", f"{generated_at:%d-%b-%Y %H:%M}" if generated_at else "-"),
        ("App version", __version__),
        ("Formula check", check_note or "Not checked yet."),
        ("How the figures work", "Forecast category cells = SUMIFS(Items amount, category, lot number). "
                                 "Hold rows = SUMIFS over Holds. Opening cash and facility come from Bank. "
                                 "All totals are formulas, so editing an amount on Items or Holds updates the "
                                 "forecast. Hidden helpers: column B (category id) and row 7 (lot number)."),
        ("Data", "Synthetic data only."),
    ]
    wa.write_string(0, 0, "About this workbook", F["title"])
    for n, (k, v) in enumerate(info, start=2):
        wa.write_string(n, 0, k, F["bold"])
        wa.write_string(n, 1, v, F["wrap"])
    n = len(info) + 3
    wa.write_string(n, 0, "Recalculation self-test", F["bold"])
    put(ABOUT, wa, n, 1, "=2+3", Decimal(5), F["int"])
    if fc.warnings:
        wa.write_string(n + 2, 0, "Warnings", F["bold"])
        for m, w in enumerate(fc.warnings[:200]):
            wa.write_string(n + 3 + m, 1, w, F["wrap"])
    wb.close()
    return expected
