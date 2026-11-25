"""4-sheet Master Excel exporter for the Windows v0 Edition."""

from __future__ import annotations

import io
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from app import config
from app.database import get_connection

HEADER_FILL = PatternFill(start_color="1E3A5F", end_color="1E3A5F", fill_type="solid")
HEADER_FONT = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
ZEBRA_FILL = PatternFill(start_color="F4F7FA", end_color="F4F7FA", fill_type="solid")
ALERT_FILL = PatternFill(start_color="FEE2E2", end_color="FEE2E2", fill_type="solid")
ALERT_FONT = Font(name="Calibri", size=10, bold=True, color="B91C1C")
OK_FILL = PatternFill(start_color="DCFCE7", end_color="DCFCE7", fill_type="solid")
OK_FONT = Font(name="Calibri", size=10, bold=True, color="166534")
BODY_FONT = Font(name="Calibri", size=10, color="111827")

THIN_BORDER = Border(
    left=Side(style="thin", color="D1D5DB"),
    right=Side(style="thin", color="D1D5DB"),
    top=Side(style="thin", color="D1D5DB"),
    bottom=Side(style="thin", color="D1D5DB"),
)


def _style_sheet(ws, widths: list[int], right_cols: set[int] | None = None) -> None:
    right_cols = right_cols or set()
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions
    for idx, w in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(idx)].width = w
        c = ws.cell(row=1, column=idx)
        c.fill = HEADER_FILL
        c.font = HEADER_FONT
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        c.border = THIN_BORDER
    ws.row_dimensions[1].height = 24
    for r in range(2, ws.max_row + 1):
        ws.row_dimensions[r].height = 20
        for idx in range(1, len(widths) + 1):
            c = ws.cell(row=r, column=idx)
            if not c.font or c.font.name != "Calibri":
                c.font = BODY_FONT
            if r % 2 == 0 and (not c.fill or c.fill.fill_type is None):
                c.fill = ZEBRA_FILL
            c.border = THIN_BORDER
            c.alignment = Alignment(horizontal="right" if idx in right_cols else "left", vertical="center", wrap_text=True)


def generate_workbook() -> Workbook:
    with get_connection() as conn:
        assets = conn.execute(
            "SELECT a.*, v.name AS vendor_name FROM assets a LEFT JOIN vendors v ON a.vendor_id = v.id ORDER BY a.asset_tag ASC"
        ).fetchall()
        maint = conn.execute(
            """
            SELECT m.*, a.asset_tag, a.name AS asset_name, v.name AS vendor_name, v.phone AS vendor_phone
            FROM maintenance_records m
            JOIN assets a ON m.asset_id = a.id
            LEFT JOIN vendors v ON m.vendor_id = v.id
            ORDER BY m.scheduled_date DESC
            """
        ).fetchall()
        vendors = conn.execute("SELECT * FROM vendors ORDER BY name ASC").fetchall()
        stock = conn.execute(
            "SELECT c.*, v.name AS vendor_name FROM recurring_consumables c LEFT JOIN vendors v ON c.preferred_vendor_id = v.id ORDER BY c.item_name ASC"
        ).fetchall()

    wb = Workbook()
    ws_a = wb.active
    ws_a.title = "Fixed Assets"
    ws_a.append(["Asset Tag", "Asset Name", "Category", "Location", "Purchase Date", "Cost", "Vendor", "Warranty End", "Next Maintenance", "Status"])
    for a in assets:
        ws_a.append([a["asset_tag"], a["name"], a["category"], a["location"], a["purchase_date"] or "-", a["purchase_cost"] if a["purchase_cost"] is not None else "-", a["vendor_name"] or "-", a["warranty_end_date"] or "-", a["next_maintenance_date"] or "-", a["status"]])
    _style_sheet(ws_a, [16, 28, 17, 22, 14, 13, 24, 15, 18, 15], {6})

    ws_m = wb.create_sheet("Maintenance Log")
    ws_m.append(["Scheduled Date", "Asset Tag", "Asset Name", "Vendor", "Phone", "Status", "Cost", "Description"])
    for m in maint:
        ws_m.append([m["scheduled_date"], m["asset_tag"], m["asset_name"], m["vendor_name"] or "Independent", m["vendor_phone"] or "-", m["status"], m["cost"] if m["cost"] is not None else 0.0, m["description"]])
    _style_sheet(ws_m, [15, 16, 26, 24, 17, 14, 13, 38], {7})

    ws_v = wb.create_sheet("Vendor Directory")
    ws_v.append(["Vendor Name", "Type", "Contact Person", "Phone", "Email", "Address"])
    for v in vendors:
        ws_v.append([v["name"], v["vendor_type"], v["contact_person"] or "-", v["phone"], v["email"] or "-", v["address"] or "-"])
    _style_sheet(ws_v, [26, 18, 20, 18, 24, 30])

    ws_s = wb.create_sheet("Stationery & Stock")
    ws_s.append(["Item Name", "Category", "Current Stock", "Unit", "Reorder Threshold", "Status", "Preferred Vendor"])
    for s in stock:
        is_low = s["current_stock"] <= s["minimum_reorder_threshold"]
        ws_s.append([s["item_name"], s["category"], s["current_stock"], s["unit"], s["minimum_reorder_threshold"], "REORDER" if is_low else "OK", s["vendor_name"] or "-"])
        cell = ws_s.cell(row=ws_s.max_row, column=6)
        cell.fill = ALERT_FILL if is_low else OK_FILL
        cell.font = ALERT_FONT if is_low else OK_FONT
    _style_sheet(ws_s, [28, 16, 15, 13, 18, 15, 24], {3, 5})
    return wb


def save_master_excel() -> Path:
    config.ensure_directories()
    wb = generate_workbook()
    out = config.MASTER_EXCEL_PATH
    try:
        wb.save(str(out))
    finally:
        wb.close()
    return out


def generate_excel_bytes() -> bytes:
    wb = generate_workbook()
    buf = io.BytesIO()
    try:
        wb.save(buf)
    finally:
        wb.close()
    buf.seek(0)
    return buf.getvalue()
