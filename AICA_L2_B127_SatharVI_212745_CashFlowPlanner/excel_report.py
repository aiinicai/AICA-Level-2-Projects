"""Write an auditable Excel report. Formula caches also support read-only viewers."""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

import xlsxwriter
from openpyxl import load_workbook
from xlsxwriter.utility import xl_col_to_name

from engine import CATEGORIES, PAYMENTS, RECEIPTS
from sources import InputError

MONEY = '#,##0.000;[Red](#,##0.000);0.000'


def styles(book):
    def fmt(**options):
        return book.add_format({"font_name": "Calibri", "font_size": 11, "font_color": "#243A46", **options})
    return {
        "title": fmt(bg_color="#183A42", font_color="#FFFFFF", font_size=17, bold=True, valign="vcenter"),
        "note": fmt(font_color="#4D6870", italic=True, valign="vcenter"),
        "header": fmt(bg_color="#227467", font_color="#FFFFFF", bold=True, valign="vcenter"),
        "num": fmt(num_format=MONEY), "input": fmt(num_format=MONEY, font_color="#294E8A"),
        "text": fmt(), "muted": fmt(font_color="#657880"),
        "section": fmt(bg_color="#E6F0ED", bold=True),
        "subtotal": fmt(bg_color="#E6F0ED", bold=True, num_format=MONEY),
        "close": fmt(bg_color="#183A42", font_color="#FFFFFF", bold=True, num_format=MONEY),
        "negative": fmt(bg_color="#FCE4D8", font_color="#843A1D", bold=True, num_format=MONEY),
        "hash": fmt(font_name="Consolas", font_size=9),
    }


def title(sheet, count, text, note, f):
    sheet.hide_gridlines(2)
    sheet.merge_range(0, 0, 0, count - 1, text, f["title"])
    sheet.merge_range(1, 0, 1, count - 1, note, f["note"])
    sheet.set_row(0, 35)
    sheet.set_row(1, 25)
    sheet.set_row(3, 25)
    sheet.set_landscape()
    sheet.fit_to_pages(1, 0)
    sheet.repeat_rows(0, 3)
    sheet.set_footer("&LConstruction Cash Flow Planner&RPage &P of &N")


def headers(sheet, values, f):
    for index, value in enumerate(values):
        sheet.write_string(3, index, value, f["header"])


def ledger(sheet, model, f):
    title(sheet, 10, "Cash entries", "Included cash drives the forecast. Exclusions retain their signed source amount and reason.", f)
    headers(sheet, ["Period", "Category", "Reference", "Project", "Party", "Source type", "Signed amount",
                    "Included cash", "Source location", "Decision"], f)
    for col, width in enumerate((22, 24, 26, 13, 24, 24, 18, 18, 48, 38)):
        sheet.set_column(col, col, width)
    for r, e in enumerate(model.entries, 4):
        sheet.write_row(r, 0, [e.period, e.category, e.reference, e.project, e.party, e.basis], f["text"])
        sheet.write_number(r, 6, float(e.value), f["input"])
        sheet.write_formula(r, 7, f'=IF(J{r+1}="Included",G{r+1},0)', f["num"], 0 if e.reason else float(e.value))
        sheet.write_string(r, 8, e.evidence, f["muted"])
        sheet.write_string(r, 9, e.reason or "Included", f["text"])
    sheet.autofilter(3, 0, len(model.entries) + 3, 9)
    sheet.freeze_panes(4, 2)


def layout():
    return (["Opening cash"] + list(RECEIPTS) + ["Total receipts"] + list(PAYMENTS) +
            ["Total payments", "Funding", "Net movement", "Closing cash"])


def cash_flow(sheet, model, f):
    periods = model.periods
    title(sheet, len(periods) + 1, model.company + "  /  Management cash flow",
          f"OMR  •  Actuals through {model.cutoff:%d %B %Y}  •  Negative amounts are cash outflows or deficits", f)
    headers(sheet, ["Cash flow · OMR"] + periods, f)
    sheet.set_column(0, 0, 26)
    sheet.set_column(1, len(periods), 23)
    sheet.freeze_panes(4, 1)
    sheet.set_tab_color("#227467")
    labels = layout()
    positions = {label: i for i, label in enumerate(labels, 5)}  # Excel row numbers
    for label, r in positions.items():
        style = "close" if label == "Closing cash" else "section" if label not in CATEGORIES else "text"
        sheet.write_string(r - 1, 0, label, f[style])
    end = len(model.entries) + 4
    def source_range(letter):
        return f"'Cash entries'!${letter}$5:${letter}${end}"
    for c, period in enumerate(periods, 1):
        col = xl_col_to_name(c)
        def formula(label, expr, cached, style="num"):
            sheet.write_formula(positions[label]-1, c, expr, f[style], float(cached))
        if c == 1:
            sheet.write_number(positions["Opening cash"]-1, c, float(model.opening[period]), f["input"])
        else:
            formula("Opening cash", f"={xl_col_to_name(c-1)}{positions['Closing cash']}", model.opening[period], "subtotal")
        for cat in CATEGORIES:
            formula(cat, f"=ROUND(SUMIFS({source_range('H')},{source_range('A')},{col}$4,"
                         f"{source_range('B')},$A{positions[cat]}),3)", model.totals[period, cat])
        for name, group in (("Total receipts", RECEIPTS), ("Total payments", PAYMENTS)):
            formula(name, f"=ROUND(SUM({col}{positions[group[0]]}:{col}{positions[group[-1]]}),3)",
                    sum(model.totals[period, cat] for cat in group), "subtotal")
        formula("Net movement", f"=ROUND({col}{positions['Total receipts']}+{col}{positions['Total payments']}+"
                f"{col}{positions['Funding']},3)", model.closing[period] - model.opening[period], "subtotal")
        formula("Closing cash", f"=ROUND({col}{positions['Opening cash']}+{col}{positions['Net movement']},3)",
                model.closing[period], "close")
    r = positions["Closing cash"] - 1
    sheet.set_row(r, 25)
    sheet.conditional_format(r, 1, r, len(periods), {"type": "cell", "criteria": "<", "value": 0, "format": f["negative"]})
    sheet.print_area(0, 0, r, len(periods))
    return r + 1


def controls(sheet, model, f):
    title(sheet, 5, "Reconciliations", "Source controls tested at generation. Regenerate after editing the input folder.", f)
    headers(sheet, ["Control", "Calculated", "Expected", "Difference", "Source / reference"], f)
    for col, width in enumerate((58, 21, 21, 20, 52)):
        sheet.set_column(col, col, width)
    for r, (name, value, expected, loc) in enumerate(model.checks, 4):
        sheet.write_string(r, 0, name)
        sheet.write_number(r, 1, float(value), f["num"])
        sheet.write_number(r, 2, float(expected), f["num"])
        sheet.write_formula(r, 3, f"=ROUND(B{r+1}-C{r+1},3)", f["num"], float(value - expected))
        sheet.write_string(r, 4, loc)
    sheet.freeze_panes(4, 1)


def period_summary(sheet, model, f):
    """Show complete monthly bridges, and year totals limited to the months in scope."""
    title(sheet, 7, "Monthly and annual cash bridge",
          "Year rows cover the months shown. Opening and closing cash are point-in-time balances.", f)
    columns = ("Period", "Opening cash", "Total receipts", "Total payments", "Funding", "Net movement", "Closing cash")
    headers(sheet, columns, f)
    sheet.set_column(0, 0, 33)
    sheet.set_column(1, 6, 20)
    sheet.freeze_panes(4, 1)
    cash_rows = {name: i for i, name in enumerate(layout(), 5)}
    keys = list(dict.fromkeys(period[:7] for period in model.periods))
    groups = [(key, [i for i,p in enumerate(model.periods, 1) if p.startswith(key)], False) for key in keys]
    for year in dict.fromkeys(key[:4] for key in keys):
        months = [key for key in keys if key.startswith(year)]
        label = f"{year} covered ({months[0]} to {months[-1]})"
        groups.append((label, [i for i,p in enumerate(model.periods, 1) if p.startswith(year)], True))
    for r, (label, indices, annual) in enumerate(groups, 4):
        periods = [model.periods[i-1] for i in indices]
        style = f["subtotal"] if annual else f["num"]
        sheet.write_string(r, 0, label, f["section"] if annual else f["text"])
        for c, name in enumerate(columns[1:], 1):
            source_row = cash_rows[name]
            first, last = xl_col_to_name(indices[0]), xl_col_to_name(indices[-1])
            if name in ("Opening cash", "Closing cash"):
                opening = name == "Opening cash"
                value = model.opening[periods[0]] if opening else model.closing[periods[-1]]
                expr = f"='Cash flow'!{first if opening else last}{source_row}"
            else:
                categories = {"Total receipts": RECEIPTS, "Total payments": PAYMENTS, "Funding": ("Funding",),
                              "Net movement": CATEGORIES}[name]
                value = sum(model.totals[p, cat] for p in periods for cat in categories)
                expr = f"=ROUND(SUM('Cash flow'!{first}{source_row}:{last}{source_row}),3)"
            sheet.write_formula(r, c, expr, style, float(value))


def manifest(sheet, model, f):
    title(sheet, 4, "Source register", "Only the selected folder is used. The SHA-256 digest identifies the exact version read.", f)
    headers(sheet, ("Role", "File", "As of", "SHA-256"), f)
    for c, w in enumerate((18, 36, 18, 80)):
        sheet.set_column(c, c, w)
    for r, source in enumerate(model.sources.values(), 4):
        sheet.write_row(r, 0, [source.role, source.name, str(model.cutoff)])
        sheet.write_string(r, 3, source.digest, f["hash"])
    sheet.freeze_panes(4, 0)


def save(model, output):
    output = Path(output)
    if output.suffix.lower() != ".xlsx":
        raise InputError("Choose a filename ending in .xlsx.")
    if output.exists():
        raise InputError("This file already exists. Choose a new name to preserve both versions.")
    fd, name = tempfile.mkstemp(suffix=".xlsx", prefix=".cashflow-", dir=output.parent)
    os.close(fd)
    temp = Path(name)
    try:
        with xlsxwriter.Workbook(temp, {"strings_to_formulas": False, "strings_to_urls": False}) as book:
            book.set_properties({"title": "Construction cash flow", "author": "Construction Cash Flow Planner"})
            f = styles(book)
            main = book.add_worksheet("Cash flow")
            period_summary(book.add_worksheet("Period summary"), model, f)
            ledger(book.add_worksheet("Cash entries"), model, f)
            closing_row = cash_flow(main, model, f)
            controls(book.add_worksheet("Reconciliations"), model, f)
            manifest(book.add_worksheet("Sources"), model, f)
        check = load_workbook(temp, read_only=True, data_only=True)
        try:
            balances = list(next(check["Cash flow"].iter_rows(min_row=closing_row, max_row=closing_row, values_only=True)))[1:]
            if balances != [float(model.closing[p]) for p in model.periods]:
                raise InputError("Saved workbook did not reproduce the expected closing balances.")
        finally:
            check.close()
        # Publish the completed file without an overwrite race.
        if os.name == "nt":
            os.rename(temp, output)
        else:
            os.link(temp, output)
    finally:
        temp.unlink(missing_ok=True)
    return output
