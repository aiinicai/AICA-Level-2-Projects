"""
excel_export.py
-----------------
Big-4-close-binder-grade Excel workbook:

  Overview          — cover/executive summary: run parameters, KPI tiles,
                       the variance bridge and severity charts, legal
                       notice and watermark.
  Flux Detail        — a native Excel Table (real AutoFilter + sortable
                       columns, not just conditional formatting), frozen
                       header, a heatmap on Variance %, both commentary
                       columns (AI-generated reference + controller
                       final), and a live "Display Units" dropdown
                       (Actual / $000s / $Mn) that rescales every amount
                       column through a formula — no need to re-export
                       to change the view.
  Entity Summary     — per-entity rollup with data-bar visualization.
  Sign-Off           — controller governance record.

Raw values always live in hidden helper columns at the right of the
Flux Detail table; the visible Prior/Current/Variance columns are
formulas dividing by a scale factor driven by the dropdown, so the
sheet stays fully live in Excel/Google Sheets/LibreOffice.
"""

from __future__ import annotations

import io
from datetime import datetime, timezone

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.formatting.rule import ColorScaleRule, DataBarRule
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.table import Table, TableStyleInfo
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.drawing.image import Image as XLImage

from ..legal import PROJECT_NOTICE, DRAFT_WATERMARK, FINAL_WATERMARK
from . import charts

NAVY = "14213D"
NAVY_LIGHT = "1F335A"
GOLD = "C9A227"
WHITE = "FFFFFF"

HEADER_FILL = PatternFill(start_color=NAVY, end_color=NAVY, fill_type="solid")
HEADER_FONT = Font(color=WHITE, bold=True, size=10)
TITLE_FONT = Font(bold=True, size=16, color=NAVY, name="Calibri")
GOLD_FILL = PatternFill(start_color=GOLD, end_color=GOLD, fill_type="solid")
MATERIAL_FILL = PatternFill(start_color="FFF2CC", end_color="FFF2CC", fill_type="solid")
APPROVED_FILL = PatternFill(start_color="D9F2E3", end_color="D9F2E3", fill_type="solid")
THIN_GREY = Side(style="thin", color="D6DBE2")
BOX_BORDER = Border(left=THIN_GREY, right=THIN_GREY, top=THIN_GREY, bottom=THIN_GREY)

CURRENCY_FMT = '#,##0.00;[Red](#,##0.00)'
CURRENCY_FMT_ACTUAL = '#,##0;[Red](#,##0)'
PCT_FMT = '#,##0.0"%";[Red]-#,##0.0"%"'


def _readiness(run):
    rows = list(run["rows"].values())
    material_rows = [r for r in rows if r["data"]["is_material"]]
    approved = [r for r in material_rows if r["status"] == "approved"]
    signed = run["signoff"]["controller_name"] is not None
    ready = signed and len(material_rows) > 0 and len(approved) == len(material_rows)
    return ready, len(material_rows), len(approved)


def build_workbook(run: dict) -> bytes:
    meta = run["meta"]
    rows = list(run["rows"].values())
    ready, n_material, n_approved = _readiness(run)
    watermark = FINAL_WATERMARK if ready else DRAFT_WATERMARK
    watermark_color = "1E7A46" if ready else "B00020"

    wb = Workbook()
    _build_overview(wb, run, watermark, watermark_color, ready, n_material, n_approved)
    _build_flux_detail(wb, run, watermark, watermark_color)
    _build_entity_summary(wb, rows)
    _build_signoff(wb, run, watermark, ready, n_material, n_approved)

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


# ---------------------------------------------------------------------
# Overview / executive summary
# ---------------------------------------------------------------------

def _build_overview(wb, run, watermark, watermark_color, ready, n_material, n_approved):
    meta = run["meta"]
    rows = list(run["rows"].values())
    ws = wb.active
    ws.title = "Overview"
    ws.sheet_view.showGridLines = False

    ws.column_dimensions["A"].width = 3
    for col in "BCDEFGH":
        ws.column_dimensions[col].width = 15

    ws["B2"] = "Financial Statement Flux Analyzer"
    ws["B2"].font = TITLE_FONT
    ws["B3"] = f"{meta.get('statement_label', '')} — {meta.get('comparison_label', '')}"
    ws["B3"].font = Font(size=12, color="5A6472")
    ws["B4"] = "AICA Level 2 Capstone — Batch 89 · CA Shrey Chopra"
    ws["B4"].font = Font(size=10, italic=True, color="8FA0B3")

    ws["B6"] = watermark
    ws["B6"].font = Font(bold=True, size=13, color=watermark_color)
    ws.merge_cells("B6:E6")

    ws["B8"] = "Run Parameters"
    ws["B8"].font = Font(bold=True, size=11, color=NAVY)
    params = [
        ("Statement", meta.get("statement_label", "")),
        ("Comparison basis", meta.get("comparison_label", "")),
        ("Materiality threshold", f"{meta.get('threshold_pct', '')}% (min. $1,000 floor)"),
        ("Generated (UTC)", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")),
    ]
    for i, (k, v) in enumerate(params, start=9):
        ws.cell(row=i, column=2, value=k).font = Font(bold=True, size=9.5, color="5A6472")
        ws.cell(row=i, column=3, value=v).font = Font(size=9.5)

    # KPI tiles
    entities = sorted(set(r["data"]["entity"] for r in rows))
    material = [r for r in rows if r["data"]["is_material"]]
    net_variance = sum(r["data"]["variance_usd"] for r in rows)

    kpis = [
        ("Entities", str(len(entities))),
        ("Lines Reviewed", str(len(rows))),
        ("Flagged Material", str(len(material))),
        ("Controller-Approved", f"{n_approved} / {n_material}"),
        ("Net Variance", f"${net_variance:,.0f}"),
    ]
    kpi_row = 14
    ws.cell(row=kpi_row, column=2, value="Key Metrics").font = Font(bold=True, size=11, color=NAVY)
    for i, (label, value) in enumerate(kpis):
        col = 2 + i
        c1 = ws.cell(row=kpi_row + 1, column=col, value=value)
        c1.font = Font(bold=True, size=14, color=NAVY)
        c1.alignment = Alignment(horizontal="center")
        c1.fill = PatternFill(start_color="F6F7F9", end_color="F6F7F9", fill_type="solid")
        c1.border = BOX_BORDER
        c2 = ws.cell(row=kpi_row + 2, column=col, value=label)
        c2.font = Font(size=8.5, color="5A6472")
        c2.alignment = Alignment(horizontal="center", wrap_text=True)
        c2.fill = PatternFill(start_color="F6F7F9", end_color="F6F7F9", fill_type="solid")
        c2.border = BOX_BORDER
    ws.row_dimensions[kpi_row + 1].height = 26

    # Charts
    material_dicts = [r["data"] for r in rows]
    deltas, prior_total, current_total = charts.entity_totals(material_dicts)
    wf_png = charts.waterfall_chart(deltas, prior_total, current_total,
                                     title=f"Net Variance Bridge — {meta.get('statement_label', '')}")
    sev_png = charts.severity_bar_chart(charts.severity_counts(material_dicts))

    img1 = XLImage(io.BytesIO(wf_png))
    img1.width, img1.height = 620, 300
    ws.add_image(img1, "B19")

    img2 = XLImage(io.BytesIO(sev_png))
    img2.width, img2.height = 380, 300
    ws.add_image(img2, "I19")

    notice_row = 38
    ws.cell(row=notice_row, column=2, value=PROJECT_NOTICE).font = Font(italic=True, size=8, color="8FA0B3")
    ws.merge_cells(start_row=notice_row, start_column=2, end_row=notice_row + 2, end_column=10)
    ws.cell(row=notice_row, column=2).alignment = Alignment(wrap_text=True, vertical="top")

    ws.cell(row=42, column=2,
            value="Final judgement on every flagged item rests with the reviewing Controller, not with the "
                  "rule engine or any AI-assisted wording — see the Sign-Off sheet.").font = Font(italic=True, size=9, color="5A6472")

    ws.page_setup.orientation = "landscape"
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 1
    ws.sheet_properties.pageSetUpPr.fitToPage = True


# ---------------------------------------------------------------------
# Flux Detail — native Excel Table with a live unit-scale toggle
# ---------------------------------------------------------------------

VISIBLE_HEADERS = [
    "Entity", "Category", "Line Item", "Prior", "Current", "Variance",
    "Variance (%)", "Material", "Severity", "Review Status", "Reviewed By",
    "AI-Generated Commentary (reference only)", "Controller Final Commentary (exported)",
]
RAW_HEADERS = ["_raw_prior", "_raw_current", "_raw_variance"]


def _build_flux_detail(wb, run, watermark, watermark_color):
    meta = run["meta"]
    rows = list(run["rows"].values())
    ws = wb.create_sheet("Flux Detail")

    ws["A1"] = f"{watermark} — {meta.get('statement_label', '')} Flux Analysis"
    ws["A1"].font = Font(bold=True, size=13, color=watermark_color)
    ws["A2"] = f"{meta.get('comparison_label', '')}  |  Materiality threshold: {meta.get('threshold_pct', '')}% (min. $1,000)"
    ws["A2"].font = Font(size=9.5, color="5A6472")
    ws["A3"] = PROJECT_NOTICE
    ws["A3"].font = Font(italic=True, size=7.5, color="8FA0B3")

    # Live display-units control
    ws["A5"] = "Display Units:"
    ws["A5"].font = Font(bold=True, size=9.5, color=NAVY)
    ws["B5"] = "Actual"
    ws["B5"].font = Font(bold=True, size=9.5, color=WHITE)
    ws["B5"].fill = GOLD_FILL
    ws["B5"].alignment = Alignment(horizontal="center")
    dv = DataValidation(type="list", formula1='"Actual,Thousands,Millions"', allow_blank=False,
                         showDropDown=False)
    dv.error = "Choose Actual, Thousands, or Millions."
    dv.prompt = "Pick how amounts are displayed across this sheet."
    ws.add_data_validation(dv)
    dv.add(ws["B5"])
    ws["C5"] = "=IF($B$5=\"Millions\",1000000,IF($B$5=\"Thousands\",1000,1))"
    ws["C5"].font = Font(size=8, color="C7CDD6")
    ws["D5"] = "← pick Actual / Thousands / $Mn — every amount column below updates live"
    ws["D5"].font = Font(italic=True, size=8.5, color="8FA0B3")

    start = 7  # header row
    n_visible = len(VISIBLE_HEADERS)
    n_raw = len(RAW_HEADERS)

    for c, name in enumerate(VISIBLE_HEADERS, start=1):
        cell = ws.cell(row=start, column=c, value=name)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(horizontal="center", wrap_text=True, vertical="center")
    for c, name in enumerate(RAW_HEADERS, start=n_visible + 1):
        ws.cell(row=start, column=c, value=name)

    for i, r in enumerate(rows):
        d = r["data"]
        row_idx = start + 1 + i
        raw_prior_col = get_column_letter(n_visible + 1)
        raw_current_col = get_column_letter(n_visible + 2)
        raw_var_col = get_column_letter(n_visible + 3)

        ws.cell(row=row_idx, column=1, value=d["entity"])
        ws.cell(row=row_idx, column=2, value=d["category"])
        ws.cell(row=row_idx, column=3, value=d["line_item"])
        prior_cell = ws.cell(row=row_idx, column=4, value=f"={raw_prior_col}{row_idx}/$C$5")
        prior_cell.number_format = CURRENCY_FMT
        current_cell = ws.cell(row=row_idx, column=5, value=f"={raw_current_col}{row_idx}/$C$5")
        current_cell.number_format = CURRENCY_FMT
        var_cell = ws.cell(row=row_idx, column=6, value=f"={raw_var_col}{row_idx}/$C$5")
        var_cell.number_format = CURRENCY_FMT
        pct_cell = ws.cell(row=row_idx, column=7, value=round(d["variance_pct"], 1))
        pct_cell.number_format = PCT_FMT
        ws.cell(row=row_idx, column=8, value="Yes" if d["is_material"] else "No")
        ws.cell(row=row_idx, column=9, value=(d.get("severity") or "none").capitalize())
        ws.cell(row=row_idx, column=10, value=r["status"].capitalize())
        ws.cell(row=row_idx, column=11, value=r["reviewer"] or "")
        ai_cell = ws.cell(row=row_idx, column=12, value=r["ai_commentary"])
        ai_cell.alignment = Alignment(wrap_text=True, vertical="top")
        ctrl_cell = ws.cell(row=row_idx, column=13, value=r["controller_commentary"])
        ctrl_cell.alignment = Alignment(wrap_text=True, vertical="top")

        ws.cell(row=row_idx, column=n_visible + 1, value=round(d["prior_amount"], 2))
        ws.cell(row=row_idx, column=n_visible + 2, value=round(d["current_amount"], 2))
        ws.cell(row=row_idx, column=n_visible + 3, value=round(d["variance_usd"], 2))

        # Size the row to comfortably fit the longer of the two commentary
        # columns (~58 characters/line at this column width) so wrapped
        # text never visually bleeds into the row below.
        longest = max(len(r["ai_commentary"] or ""), len(r["controller_commentary"] or ""))
        est_lines = max(2, -(-longest // 58) + 1)  # ceil division, +1 line buffer
        ws.row_dimensions[row_idx].height = min(230, max(30, est_lines * 14 + 8))

    n_rows = len(rows)

    if n_rows > 0:
        last_row = start + n_rows
        table_ref = f"A{start}:{get_column_letter(n_visible)}{last_row}"
        table = Table(displayName="FluxDetail", ref=table_ref)
        table.tableStyleInfo = TableStyleInfo(
            name="TableStyleMedium2", showFirstColumn=False, showLastColumn=False,
            showRowStripes=True, showColumnStripes=False,
        )
        ws.add_table(table)

        pct_col = get_column_letter(7)
        rule = ColorScaleRule(
            start_type="min", start_color="63BE7B",
            mid_type="percentile", mid_value=50, mid_color="FFEB84",
            end_type="max", end_color="F8696B",
        )
        ws.conditional_formatting.add(f"{pct_col}{start+1}:{pct_col}{last_row}", rule)

        for i in range(n_rows):
            row_idx = start + 1 + i
            if ws.cell(row=row_idx, column=8).value == "Yes":
                fill = APPROVED_FILL if ws.cell(row=row_idx, column=10).value == "Approved" else MATERIAL_FILL
                for c in range(1, n_visible + 1):
                    cell = ws.cell(row=row_idx, column=c)
                    if c not in (4, 5, 6, 7):  # leave the scale-color-rule / currency cells' own fills alone
                        cell.fill = fill

        # Hide helper raw columns
        for c in range(n_visible + 1, n_visible + n_raw + 1):
            ws.column_dimensions[get_column_letter(c)].hidden = True

    ws.freeze_panes = f"D{start+1}"

    widths = [24, 18, 30, 13, 13, 13, 11, 10, 11, 13, 14, 46, 46]
    for c, w in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(c)].width = w
    ws.row_dimensions[start].height = 30

    ws.page_setup.orientation = "landscape"
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.print_title_rows = f"{start}:{start}"


# ---------------------------------------------------------------------
# Entity Summary
# ---------------------------------------------------------------------

def _build_entity_summary(wb, rows):
    ws = wb.create_sheet("Entity Summary")
    df = _summary(rows)

    ws["A1"] = "Entity Summary"
    ws["A1"].font = Font(bold=True, size=13, color=NAVY)
    start = 3

    for c, name in enumerate(df.columns, start=1):
        cell = ws.cell(row=start, column=c, value=name)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(horizontal="center", wrap_text=True)
    for r, row in enumerate(df.itertuples(index=False), start=start + 1):
        for c, val in enumerate(row, start=1):
            cell = ws.cell(row=r, column=c, value=val)
            if df.columns[c - 1] == "Net Variance ($)":
                cell.number_format = CURRENCY_FMT_ACTUAL

    n_rows = len(df)
    if n_rows:
        last_row = start + n_rows
        table = Table(displayName="EntitySummary", ref=f"A{start}:{get_column_letter(len(df.columns))}{last_row}")
        table.tableStyleInfo = TableStyleInfo(name="TableStyleMedium2", showRowStripes=True)
        ws.add_table(table)

        net_col = get_column_letter(df.columns.get_loc("Net Variance ($)") + 1)
        bar_rule = DataBarRule(start_type="min", start_value=None, end_type="max", end_value=None,
                                color="1E7A46", showValue=True, minLength=None, maxLength=None)
        ws.conditional_formatting.add(f"{net_col}{start+1}:{net_col}{last_row}", bar_rule)

    for c, name in enumerate(df.columns, start=1):
        width = max([len(str(name))] + [len(str(v)) for v in df[name].astype(str)])
        ws.column_dimensions[get_column_letter(c)].width = min(width + 4, 40)
    ws.freeze_panes = f"A{start+1}"


def _summary(rows) -> pd.DataFrame:
    by_entity = {}
    for r in rows:
        d = r["data"]
        e = d["entity"]
        by_entity.setdefault(e, {"lines": 0, "material": 0, "approved": 0, "net": 0.0})
        by_entity[e]["lines"] += 1
        if d["is_material"]:
            by_entity[e]["material"] += 1
            if r["status"] == "approved":
                by_entity[e]["approved"] += 1
        by_entity[e]["net"] += d["variance_usd"]

    out = []
    for e, v in by_entity.items():
        out.append({
            "Entity": e,
            "Lines Reviewed": v["lines"],
            "Material Flags": v["material"],
            "Controller-Approved": v["approved"],
            "Net Variance ($)": round(v["net"]),
        })
    return pd.DataFrame(out).sort_values("Material Flags", ascending=False)


# ---------------------------------------------------------------------
# Sign-Off
# ---------------------------------------------------------------------

def _build_signoff(wb, run, watermark, ready, n_material, n_approved):
    ws = wb.create_sheet("Sign-Off")
    signoff = run["signoff"]
    ws["A1"] = "Controller Sign-Off Record"
    ws["A1"].font = Font(bold=True, size=13, color=NAVY)
    ws["A3"] = "Status"
    ws["B3"] = "FINAL — All material items controller-approved" if ready else f"DRAFT — {n_approved}/{n_material} material items approved"
    ws["A4"] = "Controller Name"
    ws["B4"] = signoff.get("controller_name") or "(pending)"
    ws["A5"] = "Controller Title"
    ws["B5"] = signoff.get("controller_title") or "(pending)"
    ws["A6"] = "Signed Off At (UTC)"
    ts = signoff.get("signed_off_at")
    ws["B6"] = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M") if ts else "(pending)"
    ws["A8"] = "Note"
    ws["B8"] = (
        "Every AI-Generated Commentary value in this workbook is a system-drafted reference note and is "
        "never treated as final. The Controller Final Commentary column is the one editable, authoritative "
        "field, and it only carries the FINAL watermark once every material line is marked 'Approved' and "
        "the controller below has signed off. Final judgement on each flagged item rests with the "
        "controller, not with the rule engine or any AI-assisted wording."
    )
    ws["B8"].alignment = Alignment(wrap_text=True)
    for r in (3, 4, 5, 6):
        ws.cell(row=r, column=1).font = Font(bold=True, size=10, color="5A6472")
    ws.column_dimensions["A"].width = 20
    ws.column_dimensions["B"].width = 85
    ws.row_dimensions[8].height = 60
