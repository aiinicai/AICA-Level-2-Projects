#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
 IT SOX Assessor
================================================================================
A desktop application (PyQt5) that reads uploaded IT SOX Policy document(s)
(PDF) and an IT SOX Risk & Control Matrix (RCM) Excel file, intelligently maps
policy content to SOX control numbers, and auto-generates a professional,
ready-to-use "Pre-Deployment SOX Assessment Questionnaire" workbook for a new
system - complete with a Cover Page, one worksheet per control (with Yes/No/
N/A dropdowns, comments and action-date columns) and a Summary & Sign-off
sheet that automatically rolls up completion status from every control sheet.

HOW TO RUN
----------
1. Save this file as  IT_SOX_Assessor.py
2. Double-click it, or run:   python IT_SOX_Assessor.py
   (Works fine inside IDLE too - just press F5.)
3. The script will automatically check for and install any missing Python
   libraries the first time it runs (internet connection required for that
   one-time install). No other setup is needed.

REQUIRED LIBRARIES (for manual install if auto-install ever fails):

    pip install PyQt5 openpyxl pypdf

================================================================================
"""

# ------------------------------------------------------------------------
# STEP 0 : AUTO-INSTALL REQUIRED LIBRARIES  (runs before anything else)
# ------------------------------------------------------------------------
import sys
import subprocess
import importlib

REQUIRED_PACKAGES = {
    # import_name : pip_package_name
    "PyQt5":  "PyQt5",
    "openpyxl": "openpyxl",
    "pypdf":  "pypdf",
}


def _ensure_packages_installed():
    missing = []
    for import_name, pip_name in REQUIRED_PACKAGES.items():
        try:
            importlib.import_module(import_name)
        except ImportError:
            missing.append(pip_name)

    if missing:
        print("[IT SOX Assessor] Installing missing libraries:", ", ".join(missing))
        try:
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", "--quiet", *missing]
            )
        except Exception as exc:  # pragma: no cover
            print("Automatic installation failed:", exc)
            print("Please install manually with:")
            print("    pip install " + " ".join(REQUIRED_PACKAGES.values()))
            sys.exit(1)

        # Re-check after install
        still_missing = []
        for import_name, pip_name in REQUIRED_PACKAGES.items():
            try:
                importlib.import_module(import_name)
            except ImportError:
                still_missing.append(pip_name)
        if still_missing:
            print("Could not import after install:", still_missing)
            print("Please install manually with:")
            print("    pip install " + " ".join(REQUIRED_PACKAGES.values()))
            sys.exit(1)


_ensure_packages_installed()

# ------------------------------------------------------------------------
# STEP 1 : NORMAL IMPORTS (safe now that packages are guaranteed present)
# ------------------------------------------------------------------------
import os
import re
import traceback
import math
from datetime import datetime

from PyQt5.QtCore import Qt, QDate
from PyQt5.QtGui import QFont, QIcon, QColor
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QPushButton, QListWidget,
    QListWidgetItem, QVBoxLayout, QHBoxLayout, QGridLayout, QFileDialog,
    QLineEdit, QComboBox, QMessageBox, QGroupBox, QTextEdit, QFrame,
    QDateEdit, QAbstractItemView, QSizePolicy, QSplitter
)

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.utils import get_column_letter

try:
    from pypdf import PdfReader
except ImportError:  # very old pypdf name fallback
    from PyPDF2 import PdfReader  # type: ignore


# ============================================================================
#  COLOR THEME
# ============================================================================
NAVY = "1F3864"
BLUE = "2E75B6"
TEAL = "17A2B8"
GOLD = "F2A900"
GREEN = "2E8B57"
RED = "C0392B"
LIGHT_GREY = "F2F2F2"
WHITE = "FFFFFF"


# ============================================================================
#  PART A : INTELLIGENCE ENGINE
#  (reads the RCM workbook + the policy PDF and builds a structured,
#   control-by-control assessment dataset)
# ============================================================================

CONTROL_ID_PATTERN = re.compile(r"^[A-Za-z]{1,6}-?\d{1,4}$")


def _norm(text):
    """Normalise a cell value to a stripped string."""
    if text is None:
        return ""
    return str(text).strip()


def _header_key(cell_value):
    return _norm(cell_value).lower()


def _find_col(headers, *keywords):
    """Return index of the first header whose lowercase text contains
    ANY of the given keywords (all keywords are alternatives)."""
    for idx, h in enumerate(headers):
        h_low = h.lower()
        for kw in keywords:
            if kw in h_low:
                return idx
    return None


def _looks_like_header_row(row_values):
    joined = " ".join(_header_key(v) for v in row_values)
    return "control id" in joined


def scan_workbook_tables(path):
    """
    Generic scanner: walks every sheet, every row, and whenever it finds a
    row that looks like a table header (contains a 'Control ID' style
    heading), it captures that table (header + following non-blank rows)
    as a list-of-dicts. Also captures a free-form 'section name' from any
    stand-alone label rows (e.g. 'Pre-Deployment Questions:').
    Returns: list of {"section": str, "headers": [...], "rows": [dict,...]}
    """
    wb = load_workbook(path, data_only=True)
    tables = []
    for sheet in wb.worksheets:
        current_section = sheet.title
        rows = list(sheet.iter_rows(values_only=True))
        i = 0
        n = len(rows)
        while i < n:
            row = rows[i]
            values = [v for v in row]
            non_empty = [v for v in values if _norm(v) != ""]

            # A lone short text cell (ending with ':' or just a title-ish
            # row with only 1 populated cell) -> treat as a section label
            if len(non_empty) == 1 and isinstance(non_empty[0], str) and len(non_empty[0]) < 80:
                candidate = _norm(non_empty[0])
                if candidate and not _looks_like_header_row(values):
                    current_section = candidate.rstrip(":").strip()
                    i += 1
                    continue

            if _looks_like_header_row(values):
                headers = [_norm(v) for v in values]
                # trim trailing empty header cells
                while headers and headers[-1] == "":
                    headers.pop()
                data_rows = []
                j = i + 1
                while j < n:
                    r = rows[j]
                    r_values = [v for v in r]
                    if all(_norm(v) == "" for v in r_values):
                        break
                    if _looks_like_header_row(r_values):
                        break
                    record = {}
                    for c, h in enumerate(headers):
                        if not h:
                            continue
                        record[h] = _norm(r_values[c]) if c < len(r_values) else ""
                    if any(v for v in record.values()):
                        data_rows.append(record)
                    j += 1
                tables.append({
                    "section": current_section,
                    "headers": headers,
                    "rows": data_rows,
                })
                i = j
                continue
            i += 1
    return tables


def parse_rcm(path):
    """
    Reads the uploaded RCM Excel workbook and returns an ordered dict:
        { control_id : {
              "control_id":..., "domain":..., "sub_process":...,
              "risk":..., "objective":..., "description":...,
              "evidence":[...], "policy_reference":...,
              "questions":[ {"question":..., "evidence":...}, ... ]
          } }
    Works even if the workbook layout differs slightly, because it looks
    for header keywords rather than fixed column positions.
    """
    tables = scan_workbook_tables(path)
    controls = {}

    def get_or_create(cid):
        cid = cid.strip().upper()
        if cid not in controls:
            controls[cid] = {
                "control_id": cid,
                "domain": "",
                "sub_process": "",
                "risk": "",
                "objective": "",
                "description": "",
                "evidence": [],
                "policy_reference": "",
                "questions": [],
            }
        return controls[cid]

    for table in tables:
        headers = table["headers"]
        if not headers:
            continue
        col_id = _find_col(headers, "control id")
        if col_id is None:
            continue
        col_domain = _find_col(headers, "domain", "itgc area", "control area")
        col_sub = _find_col(headers, "sub-process", "sub process")
        col_risk = _find_col(headers, "risk")
        col_obj = _find_col(headers, "control objective")
        col_desc = _find_col(headers, "control description", "control statement")
        col_evi = _find_col(headers, "evidence")
        col_ref = _find_col(headers, "policy reference", "rcm reference", "reference")
        col_question = _find_col(headers, "assessment question")
        col_q_evidence = _find_col(headers, "expected evidence")

        is_question_table = col_question is not None

        for row in table["rows"]:
            cid_val = None
            for h in headers:
                if h.lower() == headers[col_id].lower():
                    cid_val = row.get(h, "")
                    break
            if not cid_val:
                continue
            rec = get_or_create(cid_val)

            def val(col_idx):
                if col_idx is None:
                    return ""
                h = headers[col_idx]
                return row.get(h, "")

            if col_domain is not None and val(col_domain):
                rec["domain"] = val(col_domain)
            if col_sub is not None and val(col_sub):
                rec["sub_process"] = val(col_sub)
            if col_risk is not None and val(col_risk):
                rec["risk"] = val(col_risk)
            if col_obj is not None and val(col_obj):
                rec["objective"] = val(col_obj)
            if col_desc is not None and val(col_desc):
                rec["description"] = val(col_desc)
            if col_evi is not None and val(col_evi):
                rec["evidence"] = [e.strip() for e in re.split(r"[;\n]", val(col_evi)) if e.strip()]
            if col_ref is not None and val(col_ref):
                rec["policy_reference"] = val(col_ref)

            if is_question_table:
                q_text = val(col_question)
                q_evi = val(col_q_evidence) if col_q_evidence is not None else ""
                if q_text:
                    rec["questions"].append({"question": q_text, "evidence": q_evi})

    return controls


def _split_clauses(text, max_items=3, min_len=15):
    """Break a longer descriptive sentence/paragraph into clean clauses
    suitable for turning into individual assessment questions."""
    if not text:
        return []
    parts = re.split(r"(?<=[.;])\s+", text)
    clauses = []
    for p in parts:
        p = p.strip().strip(".;").strip()
        if len(p) >= min_len:
            clauses.append(p)
        if len(clauses) >= max_items:
            break
    return clauses


def _to_question(clause):
    clause = clause[0].lower() + clause[1:] if clause else clause
    return f"Does the new system's process ensure that {clause}?"


def _risk_question(risk_text):
    risk_text = risk_text.strip().strip(".").strip()
    if not risk_text:
        return None
    risk_text = risk_text[0].lower() + risk_text[1:]
    return f"Has an adequate control been designed and implemented to prevent/detect the risk that {risk_text}?"


def build_assessment_dataset(controls):
    """
    The 'intelligence engine' step: for every control coming from the RCM,
    build the final list of assessment questions by combining:
      1. Any explicit pre-deployment questions already present in the RCM.
      2. Auto-generated questions derived from the control description
         (clause-by-clause) - covers scenarios where the RCM has no
         dedicated question bank.
      3. A risk-based question derived from the documented risk statement.
    Returns the same control dict enriched with a final "final_questions"
    list of {"question","evidence"} used to render the sheet.
    """
    for cid, rec in controls.items():
        final_qs = []
        seen = set()

        for q in rec["questions"]:
            qt = q["question"].strip()
            if qt and qt.lower() not in seen:
                seen.add(qt.lower())
                final_qs.append({
                    "question": qt,
                    "evidence": q["evidence"] or (rec["evidence"][0] if rec["evidence"] else "")
                })

        evidence_cycle = rec["evidence"] if rec["evidence"] else [""]
        clauses = _split_clauses(rec["description"], max_items=3)
        for idx, clause in enumerate(clauses):
            qt = _to_question(clause)
            if qt.lower() not in seen:
                seen.add(qt.lower())
                final_qs.append({
                    "question": qt,
                    "evidence": evidence_cycle[idx % len(evidence_cycle)]
                })

        rq = _risk_question(rec["risk"])
        if rq and rq.lower() not in seen:
            seen.add(rq.lower())
            final_qs.append({
                "question": rq,
                "evidence": evidence_cycle[0] if evidence_cycle else ""
            })

        if not final_qs:
            final_qs.append({
                "question": f"Has the requirement described under control {cid} been implemented and evidenced for the new system?",
                "evidence": evidence_cycle[0] if evidence_cycle else ""
            })

        rec["final_questions"] = final_qs
    return controls


def parse_policy_pdf(path):
    """
    Extract a short descriptive note + title from a policy PDF.
    Robust against PDFs where the pages are scanned/rendered as images
    (no extractable text layer) - in that case pypdf will return an
    empty string and this function will simply leave "note" blank; the
    caller (generate_workbook) applies an RCM-derived fallback summary
    so the Cover Page is never left empty.
    """
    info = {"filename": os.path.basename(path), "title": "", "note": ""}
    full_text = ""
    try:
        reader = PdfReader(path)
        for page in reader.pages[:5]:
            try:
                full_text += (page.extract_text() or "") + "\n"
            except Exception:
                continue
    except Exception:
        full_text = ""

    full_text = full_text or ""
    lines = [l.strip() for l in full_text.splitlines() if l.strip()]
    if lines:
        info["title"] = lines[0][:120]

    # Try several common section headings to find a short descriptive note
    headings = ["purpose", "overview", "policy purpose", "introduction",
                "executive summary", "policy statement", "summary"]
    note = ""
    for heading in headings:
        pattern = (r"\b" + re.escape(heading) +
                   r"\b\s*[:\-]?\s*(.+?)(?:\n\s*\d+[\.\)]?\s*[A-Z][a-zA-Z ]+\n|\n\s*(?:scope|definitions)\b|\Z)")
        m = re.search(pattern, full_text, re.IGNORECASE | re.DOTALL)
        if m:
            candidate = re.sub(r"\s+", " ", m.group(1)).strip()
            if len(candidate) >= 40:
                note = candidate
                break

    if not note and full_text.strip():
        # Fall back to the first substantial block of running text
        candidate = re.sub(r"\s+", " ", full_text).strip()
        if len(candidate) >= 40:
            note = candidate

    info["note"] = note[:600]

    if not info["title"]:
        info["title"] = os.path.splitext(info["filename"])[0].replace("_", " ").strip()

    return info


def synthesize_summary_from_controls(controls):
    """
    Builds a professional fallback Policy Summary purely from the parsed
    RCM data. Used whenever the uploaded policy PDF has no extractable
    text (e.g. scanned/rendered PDFs) so the Cover Page is never blank.
    """
    domains = []
    subprocesses = []
    for rec in controls.values():
        if rec.get("domain") and rec["domain"] not in domains:
            domains.append(rec["domain"])
        if rec.get("sub_process") and rec["sub_process"] not in subprocesses:
            subprocesses.append(rec["sub_process"])

    parts = []
    parts.append(
        f"This policy defines mandatory IT SOX / ITGC requirements covering "
        f"{len(controls)} control(s)"
    )
    if domains:
        parts[-1] += f" across the following control area(s): {', '.join(domains)}."
    else:
        parts[-1] += "."
    if subprocesses:
        parts.append(
            "Key process areas addressed include: " + "; ".join(subprocesses[:8]) + "."
        )
    parts.append(
        "The requirements are intended to ensure changes/activities affecting "
        "in-scope systems are appropriately requested, risk-assessed, tested, "
        "approved, implemented and evidenced, with adequate segregation of "
        "duties and auditable records maintained throughout."
    )
    return " ".join(parts)[:700]


# ---------------------------------------------------------------------------
# Small helpers used by the Excel generator to size columns/rows so that all
# content is visible without manual resizing or horizontal scrolling.
# ---------------------------------------------------------------------------

def _estimate_lines(text, col_width_chars):
    """Rough estimate of how many wrapped lines a string will take inside a
    column of the given (Excel) character width. Deliberately conservative
    (slightly overestimates) so text is never clipped."""
    text = _norm(text)
    if not text:
        return 1
    chars_per_line = max(int(col_width_chars * 1.15), 8)
    words = text.split(" ")
    lines = 1
    cur = 0
    for w in words:
        wl = len(w) + 1
        if cur + wl > chars_per_line:
            lines += 1
            cur = wl
        else:
            cur += wl
    return max(1, lines)


def _row_height_for_texts(texts_and_widths, base_line_pt=15, min_height=18, max_height=300):
    """texts_and_widths: list of (text, column_width_in_chars).
    Returns a row height (points) tall enough for the tallest wrapped cell."""
    max_lines = 1
    for text, width in texts_and_widths:
        max_lines = max(max_lines, _estimate_lines(text, width))
    height = max_lines * base_line_pt + 6
    return max(min_height, min(max_height, height))


# ============================================================================
#  PART B : EXCEL WORKBOOK GENERATOR
# ============================================================================

THIN = Side(style="thin", color="B7B7B7")
BORDER_ALL = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)


def _fill(hex_color):
    return PatternFill(start_color=hex_color, end_color=hex_color, fill_type="solid")


def _style_range(ws, start_row, start_col, end_row, end_col, border=BORDER_ALL, fill=None):
    """Applies borders and/or fills across all cells in a range (including merged ranges)
    so that no cell borders are omitted when gridlines are hidden."""
    for r in range(start_row, end_row + 1):
        for c in range(start_col, end_col + 1):
            cell = ws.cell(row=r, column=c)
            if border is not None:
                cell.border = border
            if fill is not None:
                cell.fill = fill


def _set_col_widths(ws, widths):
    for i, w in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(i)].width = w


def _title_block(ws, row, text, size=16, color=WHITE, fill=NAVY, span=8):
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=span)
    _style_range(ws, row, 1, row, span, border=BORDER_ALL, fill=_fill(fill))
    c = ws.cell(row=row, column=1, value=text)
    c.font = Font(size=size, bold=True, color=color)
    c.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[row].height = size * 1.8
    return row + 1


def _apply_professional_view(ws, zoom=80, landscape=True, fit_width=True):
    """Applies the shared 'professional look' settings to a worksheet:
    80% zoom, hidden gridlines, and print settings that fit all columns
    on one page width so nothing needs to be scrolled to see."""
    ws.sheet_view.showGridLines = False
    ws.sheet_view.zoomScale = zoom
    ws.sheet_view.zoomScaleNormal = zoom
    try:
        ws.page_setup.orientation = "landscape" if landscape else "portrait"
        ws.page_setup.paperSize = ws.PAPERSIZE_A4
        if fit_width:
            ws.page_setup.fitToWidth = 1
            ws.page_setup.fitToHeight = 0
            ws.sheet_properties.pageSetUpPr.fitToPage = True
        ws.print_options.horizontalCentered = True
    except Exception:
        pass


def build_cover_sheet(wb, policy_info, controls, system_name, assessed_by, target_go_live):
    ws = wb.active
    ws.title = "Cover Page"
    _set_col_widths(ws, [30, 95, 30])

    row = 2
    row = _title_block(ws, row, "IT SOX ASSESSOR", size=22, span=2)
    row = _title_block(ws, row, "Pre-Deployment SOX Assessment Questionnaire", size=13,
                        fill=BLUE, span=2)
    row += 1

    def field(label, value, wrap=False):
        nonlocal row
        c1 = ws.cell(row=row, column=1, value=label)
        c1.font = Font(bold=True, color=WHITE)
        c1.fill = _fill(TEAL)
        c1.alignment = Alignment(vertical="center", wrap_text=True)
        c1.border = BORDER_ALL

        c2 = ws.cell(row=row, column=2, value=value)
        c2.fill = _fill(WHITE)
        c2.alignment = Alignment(wrap_text=wrap, vertical="top" if wrap else "center")
        c2.border = BORDER_ALL

        if wrap:
            ws.row_dimensions[row].height = _row_height_for_texts([(value, 95)], base_line_pt=14)
        else:
            ws.row_dimensions[row].height = 20
        row += 1

    field("Policy Name", policy_info.get("title", ""))
    field("Source File", policy_info.get("filename", ""))
    field("Policy Summary / Purpose", policy_info.get("note", ""), wrap=True)
    field("New System / Application Name", system_name or "")
    field("Assessment Prepared By", assessed_by or "")
    field("Assessment Date", datetime.now().strftime("%d-%b-%Y"))
    field("Target Go-Live Date", target_go_live or "")
    field("Total SOX Controls Assessed", str(len(controls)))
    control_list = ", ".join(sorted(controls.keys()))
    field("Control Numbers Covered", control_list, wrap=True)

    row += 1
    ws.cell(row=row, column=1, value="Control Index").font = Font(bold=True, size=12, color=NAVY)
    row += 1
    headers = ["Control No.", "Control Area", "Total Assessment Questions"]
    header_row_idx = row
    for c, h in enumerate(headers, start=1):
        cell = ws.cell(row=row, column=c, value=h)
        cell.font = Font(bold=True, color=WHITE)
        cell.fill = _fill(NAVY)
        cell.border = BORDER_ALL
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    row += 1
    for cid in sorted(controls.keys()):
        rec = controls[cid]
        area = " - ".join([p for p in [rec.get("domain", ""), rec.get("sub_process", "")] if p])
        band = LIGHT_GREY if (row - header_row_idx) % 2 == 0 else WHITE
        ws.cell(row=row, column=1, value=cid)
        ws.cell(row=row, column=2, value=area)
        ws.cell(row=row, column=3, value=len(rec["final_questions"]))
        for c in range(1, 4):
            cell = ws.cell(row=row, column=c)
            cell.border = BORDER_ALL
            cell.fill = _fill(band)
            cell.alignment = Alignment(horizontal="center" if c != 2 else "left",
                                        vertical="center", wrap_text=True)
        ws.row_dimensions[row].height = _row_height_for_texts([(area, 60)], base_line_pt=14)
        row += 1

    _apply_professional_view(ws, zoom=80, landscape=False, fit_width=True)
    return ws


def _safe_sheet_name(name):
    name = re.sub(r'[\\/*?:\[\]]', "-", name)
    return name[:31]


# Column character-widths used for the control sheet table (kept in one
# place so width settings and row-height wrapping estimates stay in sync).
CONTROL_COL_WIDTHS = [6, 46, 26, 26, 18, 11, 24, 13]
CONTROL_WRAP_COLS = {2: 46, 3: 26, 4: 26, 7: 24}  # column index -> width chars


def build_control_sheet(wb, cid, rec):
    ws = wb.create_sheet(_safe_sheet_name(cid))
    _set_col_widths(ws, CONTROL_COL_WIDTHS)

    row = 1
    row = _title_block(ws, row, f"SOX Control Assessment - {cid}", size=14, span=8)

    def meta_row(label, value):
        nonlocal row
        # Left header block (Cols A-B)
        ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=2)
        _style_range(ws, row, 1, row, 2, border=BORDER_ALL, fill=_fill(BLUE))
        lc = ws.cell(row=row, column=1, value=label)
        lc.font = Font(bold=True, color=WHITE)
        lc.alignment = Alignment(vertical="center", wrap_text=True)

        # Right value block (Cols C-H)
        ws.merge_cells(start_row=row, start_column=3, end_row=row, end_column=8)
        _style_range(ws, row, 3, row, 8, border=BORDER_ALL, fill=_fill(WHITE))
        vc = ws.cell(row=row, column=3, value=value)
        vc.alignment = Alignment(wrap_text=True, vertical="center")

        merged_width = sum(CONTROL_COL_WIDTHS[2:8])
        ws.row_dimensions[row].height = _row_height_for_texts(
            [(value, merged_width)], base_line_pt=15)
        row += 1

    area = " - ".join([p for p in [rec.get("domain", ""), rec.get("sub_process", "")] if p])
    meta_row("Control Number", cid)
    meta_row("Control Title", area or cid)
    meta_row("Control Statement", rec.get("description", ""))
    meta_row("Assessment Objective", rec.get("objective", ""))
    row += 1

    header_row = row
    headers = ["S.No", "Assessment Question", "Control Objective", "Expected Evidence",
               "Policy/RCM Reference", "Response", "Comments", "Action Date"]
    for c, h in enumerate(headers, start=1):
        cell = ws.cell(row=header_row, column=c, value=h)
        cell.font = Font(bold=True, color=WHITE)
        cell.fill = _fill(NAVY)
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = BORDER_ALL
    ws.row_dimensions[header_row].height = 34
    # Freeze the header row AND the S.No column so both stay visible while
    # scrolling - reduces the feeling of "scrolling to see everything".
    ws.freeze_panes = ws.cell(row=header_row + 1, column=2).coordinate

    first_data_row = header_row + 1
    for i, q in enumerate(rec["final_questions"], start=1):
        r = header_row + i
        band = LIGHT_GREY if i % 2 == 0 else WHITE
        objective = rec.get("objective", "")
        evidence = q.get("evidence", "")
        policy_ref = rec.get("policy_reference", "")
        row_values = {
            1: i, 2: q["question"], 3: objective, 4: evidence,
            5: policy_ref, 6: "", 7: "", 8: "",
        }
        for c, v in row_values.items():
            cell = ws.cell(row=r, column=c, value=v)
            cell.border = BORDER_ALL
            cell.fill = _fill(band)
            if c in (2, 3, 4, 7):
                cell.alignment = Alignment(wrap_text=True, vertical="top")
            elif c == 5:
                cell.alignment = Alignment(wrap_text=True, vertical="center", horizontal="center")
            else:
                cell.alignment = Alignment(horizontal="center", vertical="center")
        texts_widths = [
            (q["question"], CONTROL_WRAP_COLS[2]),
            (objective, CONTROL_WRAP_COLS[3]),
            (evidence, CONTROL_WRAP_COLS[4]),
        ]
        ws.row_dimensions[r].height = _row_height_for_texts(texts_widths, base_line_pt=14,
                                                             min_height=32)
    last_data_row = header_row + len(rec["final_questions"])

    # Response dropdown (Yes / No / N/A)
    dv_last_row = max(last_data_row, first_data_row + 50)
    dv = DataValidation(type="list", formula1='"Yes,No,N/A"', allow_blank=True,
                         showDropDown=False)
    dv.error = "Please select Yes, No or N/A"
    dv.errorTitle = "Invalid entry"
    ws.add_data_validation(dv)
    dv.add(f"F{first_data_row}:F{dv_last_row}")

    _apply_professional_view(ws, zoom=80, landscape=True, fit_width=True)
    return ws, header_row, first_data_row, last_data_row


def build_summary_sheet(ws, controls, sheet_meta, system_name, assessed_by):
    """Populates the (already created, correctly positioned) Summary &
    Sign-off worksheet."""
    _set_col_widths(ws, [12, 34, 15, 9, 9, 9, 11, 20])

    row = 1
    row = _title_block(ws, row, "Summary & Sign-off", size=16, span=8)
    row += 1

    headers = ["Control No.", "Control Area", "Total Questions", "Yes", "No",
               "N/A", "Open Items", "Overall Status"]
    header_row = row
    for c, h in enumerate(headers, start=1):
        cell = ws.cell(row=header_row, column=c, value=h)
        cell.font = Font(bold=True, color=WHITE)
        cell.fill = _fill(NAVY)
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = BORDER_ALL
    ws.row_dimensions[header_row].height = 30
    ws.freeze_panes = ws.cell(row=header_row + 1, column=1).coordinate
    row += 1

    for idx, cid in enumerate(sorted(controls.keys())):
        rec = controls[cid]
        meta = sheet_meta[cid]
        sheet_name = _safe_sheet_name(cid)
        f_first, f_last = meta["first_data_row"], max(meta["last_data_row"], meta["first_data_row"] + 200)
        area = " - ".join([p for p in [rec.get("domain", ""), rec.get("sub_process", "")] if p])
        total_q = len(rec["final_questions"])

        r = row
        ws.cell(row=r, column=1, value=cid)
        ws.cell(row=r, column=2, value=area)
        ws.cell(row=r, column=3, value=total_q)
        yes_f = f"COUNTIF('{sheet_name}'!$F${f_first}:$F${f_last},\"Yes\")"
        no_f = f"COUNTIF('{sheet_name}'!$F${f_first}:$F${f_last},\"No\")"
        na_f = f"COUNTIF('{sheet_name}'!$F${f_first}:$F${f_last},\"N/A\")"
        ws.cell(row=r, column=4, value=f"={yes_f}")
        ws.cell(row=r, column=5, value=f"={no_f}")
        ws.cell(row=r, column=6, value=f"={na_f}")
        ws.cell(row=r, column=7, value=f"=C{r}-D{r}-F{r}")
        ws.cell(row=r, column=8,
                value=(f'=IF(C{r}=0,"N/A",IF(G{r}=0,"Complete",'
                       f'IF(D{r}=0,"In Progress","Open - Action Needed")))'))
        band = LIGHT_GREY if idx % 2 == 0 else WHITE
        for c in range(1, 9):
            cell = ws.cell(row=r, column=c)
            cell.border = BORDER_ALL
            cell.fill = _fill(band)
            cell.alignment = Alignment(horizontal="center", vertical="center") if c != 2 \
                else Alignment(horizontal="left", vertical="center", wrap_text=True)
        ws.row_dimensions[r].height = _row_height_for_texts([(area, 34)], base_line_pt=14, min_height=20)
        row += 1

    from openpyxl.formatting.rule import FormulaRule
    status_col = "H"
    rng = f"{status_col}{header_row+1}:{status_col}{row-1}"
    ws.conditional_formatting.add(
        rng, FormulaRule(formula=[f'{status_col}{header_row+1}="Complete"'],
                          fill=_fill("C6EFCE"), font=Font(color="006100")))
    ws.conditional_formatting.add(
        rng, FormulaRule(formula=[f'{status_col}{header_row+1}="Open - Action Needed"'],
                          fill=_fill("FFC7CE"), font=Font(color="9C0006")))
    ws.conditional_formatting.add(
        rng, FormulaRule(formula=[f'{status_col}{header_row+1}="In Progress"'],
                          fill=_fill("FFEB9C"), font=Font(color="9C6500")))

    # ------------------------------------------------------------------
    # Control Sign-off block - a single, simple sign-off record (NOT a
    # per-control list): Control Owner Name, System Name, Signature, Date.
    # ------------------------------------------------------------------
    row += 2
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=8)
    _style_range(ws, row, 1, row, 8, border=BORDER_ALL, fill=_fill(BLUE))
    hdr = ws.cell(row=row, column=1, value="Control Sign-off")
    hdr.font = Font(bold=True, size=12, color=WHITE)
    hdr.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[row].height = 22
    row += 1

    def signoff_field(label, value=""):
        nonlocal row
        # Left label block (Cols A-B)
        ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=2)
        _style_range(ws, row, 1, row, 2, border=BORDER_ALL, fill=_fill(TEAL))
        lc = ws.cell(row=row, column=1, value=label)
        lc.font = Font(bold=True, color=WHITE)
        lc.alignment = Alignment(vertical="center")

        # Right value block (Cols C-H)
        ws.merge_cells(start_row=row, start_column=3, end_row=row, end_column=8)
        _style_range(ws, row, 3, row, 8, border=BORDER_ALL, fill=_fill(WHITE))
        vc = ws.cell(row=row, column=3, value=value)
        vc.alignment = Alignment(vertical="center")

        ws.row_dimensions[row].height = 24
        row += 1

    signoff_field("Control Owner Name", "")
    signoff_field("System Name", system_name or "")
    signoff_field("Signature", "")
    signoff_field("Date", "")

    _apply_professional_view(ws, zoom=80, landscape=True, fit_width=True)
    return ws


def generate_workbook(controls, policy_info, system_name, assessed_by,
                       target_go_live, output_path):
    controls = build_assessment_dataset(controls)

    # Guarantee the Cover Page always has a meaningful Policy Summary, even
    # when the source PDF has no extractable text (e.g. scanned/rendered
    # pages) by falling back to a summary synthesised from the RCM content.
    if not policy_info.get("note") or len(policy_info["note"].strip()) < 30:
        policy_info = dict(policy_info)
        policy_info["note"] = synthesize_summary_from_controls(controls)

    wb = Workbook()
    build_cover_sheet(wb, policy_info, controls, system_name, assessed_by, target_go_live)

    # Create the Summary & Sign-off sheet as sheet #2 (right after the Cover
    # Page) so it appears second in the workbook tab order, even though its
    # contents (which reference every control sheet) are only populated
    # after all control sheets have been built.
    summary_ws = wb.create_sheet("Summary & Sign-off", index=1)

    sheet_meta = {}
    for cid in sorted(controls.keys()):
        rec = controls[cid]
        _, header_row, first_data_row, last_data_row = build_control_sheet(wb, cid, rec)
        sheet_meta[cid] = {"header_row": header_row, "first_data_row": first_data_row,
                            "last_data_row": last_data_row}

    build_summary_sheet(summary_ws, controls, sheet_meta, system_name, assessed_by)

    wb.active = 0
    wb.save(output_path)
    return output_path


# ============================================================================
#  PART C : PyQt5 GRAPHICAL USER INTERFACE
# ============================================================================

APP_STYLE = f"""
QMainWindow {{
    background-color: #0f1f3d;
}}
QWidget#centralWidget {{
    background-color: #eef2f9;
}}
QLabel#headerTitle {{
    color: white;
    font-size: 22px;
    font-weight: 800;
}}
QLabel#headerSubtitle {{
    color: #d7e2ff;
    font-size: 12px;
}}
QGroupBox {{
    background-color: white;
    border: 2px solid #{BLUE};
    border-radius: 10px;
    margin-top: 14px;
    font-weight: 700;
    color: #{NAVY};
    padding: 10px;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 12px;
    padding: 2px 8px;
    background-color: #{BLUE};
    color: white;
    border-radius: 6px;
}}
QPushButton {{
    background-color: #{BLUE};
    color: white;
    border-radius: 8px;
    padding: 8px 14px;
    font-weight: 600;
}}
QPushButton:hover {{
    background-color: #{TEAL};
}}
QPushButton#generateBtn {{
    background-color: #{GOLD};
    color: #1f2937;
    font-size: 15px;
    font-weight: 800;
    padding: 12px;
    border-radius: 10px;
}}
QPushButton#generateBtn:hover {{
    background-color: #ffcf4d;
}}
QPushButton#dangerBtn {{
    background-color: #{RED};
}}
QLineEdit, QComboBox, QDateEdit {{
    border: 1px solid #b9c4dd;
    border-radius: 6px;
    padding: 6px;
    background-color: white;
}}
QListWidget {{
    border: 1px solid #b9c4dd;
    border-radius: 6px;
    background-color: white;
}}
QTextEdit {{
    border: 1px solid #b9c4dd;
    border-radius: 6px;
    background-color: #10141f;
    color: #7CFC9C;
    font-family: Consolas, monospace;
}}
QLabel.fieldLabel {{
    font-weight: 600;
    color: #{NAVY};
}}
"""


class ITSoxAssessorWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("IT SOX Assessor")
        self.resize(1080, 720)
        self.policy_files = []   # list of full paths
        self.rcm_file = None

        self._build_ui()
        self.setStyleSheet(APP_STYLE)

    # ------------------------------------------------------------------
    def _build_ui(self):
        central = QWidget()
        central.setObjectName("centralWidget")
        self.setCentralWidget(central)
        outer = QVBoxLayout(central)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ---- Header banner ----
        header = QFrame()
        header.setStyleSheet(f"background-color: #{NAVY};")
        header.setFixedHeight(84)
        hl = QVBoxLayout(header)
        hl.setContentsMargins(24, 8, 24, 8)
        title = QLabel("IT SOX Assessor")
        title.setObjectName("headerTitle")
        subtitle = QLabel("Intelligent Pre-Deployment SOX Control Assessment Generator")
        subtitle.setObjectName("headerSubtitle")
        hl.addWidget(title)
        hl.addWidget(subtitle)
        outer.addWidget(header)

        body = QWidget()
        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(16, 16, 16, 16)
        body_layout.setSpacing(16)
        outer.addWidget(body)

        # ---------------- LEFT COLUMN : Uploads ----------------
        left = QVBoxLayout()
        left.setSpacing(14)

        policy_group = QGroupBox("Step 1 - Upload IT SOX Policy Document(s) (PDF)")
        pg = QVBoxLayout(policy_group)
        self.policy_list = QListWidget()
        self.policy_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        pg.addWidget(self.policy_list)
        pbtns = QHBoxLayout()
        add_policy_btn = QPushButton("Add Policy PDF(s)")
        add_policy_btn.clicked.connect(self.add_policy_files)
        remove_policy_btn = QPushButton("Remove Selected")
        remove_policy_btn.setObjectName("dangerBtn")
        remove_policy_btn.clicked.connect(self.remove_selected_policy)
        pbtns.addWidget(add_policy_btn)
        pbtns.addWidget(remove_policy_btn)
        pg.addLayout(pbtns)
        left.addWidget(policy_group)

        rcm_group = QGroupBox("Step 2 - Upload IT SOX Risk & Control Matrix (RCM) (Excel)")
        rg = QVBoxLayout(rcm_group)
        rcm_row = QHBoxLayout()
        self.rcm_path_edit = QLineEdit()
        self.rcm_path_edit.setReadOnly(True)
        self.rcm_path_edit.setPlaceholderText("No RCM file selected")
        browse_rcm_btn = QPushButton("Browse RCM (.xlsx)")
        browse_rcm_btn.clicked.connect(self.select_rcm_file)
        rcm_row.addWidget(self.rcm_path_edit)
        rcm_row.addWidget(browse_rcm_btn)
        rg.addLayout(rcm_row)
        left.addWidget(rcm_group)

        select_group = QGroupBox("Step 3 - Select Policy For This Assessment")
        sg = QVBoxLayout(select_group)
        self.policy_combo = QComboBox()
        self.policy_combo.addItem("(Upload a policy PDF first)")
        sg.addWidget(self.policy_combo)
        left.addWidget(select_group)

        details_group = QGroupBox("Step 4 - New System Deployment Details")
        dg = QGridLayout(details_group)
        self.system_name_edit = QLineEdit()
        self.assessed_by_edit = QLineEdit()
        self.golive_date = QDateEdit()
        self.golive_date.setCalendarPopup(True)
        self.golive_date.setDate(QDate.currentDate())
        dg.addWidget(self._label("New System / Application Name"), 0, 0)
        dg.addWidget(self.system_name_edit, 0, 1)
        dg.addWidget(self._label("Assessment Prepared By"), 1, 0)
        dg.addWidget(self.assessed_by_edit, 1, 1)
        dg.addWidget(self._label("Target Go-Live Date"), 2, 0)
        dg.addWidget(self.golive_date, 2, 1)
        left.addWidget(details_group)

        left.addStretch()
        body_layout.addLayout(left, 2)

        # ---------------- RIGHT COLUMN : Action + log ----------------
        right = QVBoxLayout()
        right.setSpacing(14)

        action_group = QGroupBox("Step 5 - Generate Assessment Workbook")
        ag = QVBoxLayout(action_group)
        info = QLabel(
            "The intelligence engine will read the selected policy and the "
            "uploaded RCM, match content to each SOX control number, and "
            "build one worksheet per control with auto-generated assessment "
            "questions, Yes/No/N/A response dropdowns, evidence references, "
            "comments and action-date fields - plus a Cover Page and a "
            "Summary & Sign-off sheet."
        )
        info.setWordWrap(True)
        info.setStyleSheet(f"color:#{NAVY};")
        ag.addWidget(info)

        self.generate_btn = QPushButton("\u2699  Generate IT SOX Assessment Workbook")
        self.generate_btn.setObjectName("generateBtn")
        self.generate_btn.clicked.connect(self.generate_assessment)
        ag.addWidget(self.generate_btn)
        right.addWidget(action_group)

        log_group = QGroupBox("Activity Log")
        lg = QVBoxLayout(log_group)
        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        lg.addWidget(self.log_box)
        right.addWidget(log_group, 1)

        body_layout.addLayout(right, 3)

        # footer
        footer = QLabel("IT SOX Assessor  |  Built for pre-deployment SOX ITGC readiness reviews")
        footer.setAlignment(Qt.AlignCenter)
        footer.setStyleSheet(f"background-color:#{NAVY}; color:#cdd8f5; padding:6px;")
        outer.addWidget(footer)

        self.log("Welcome to IT SOX Assessor. Upload your policy PDF(s) and RCM file to begin.")

    @staticmethod
    def _label(text):
        lbl = QLabel(text)
        lbl.setProperty("class", "fieldLabel")
        lbl.setStyleSheet(f"font-weight:600; color:#{NAVY};")
        return lbl

    # ------------------------------------------------------------------
    def log(self, msg):
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_box.append(f"[{ts}] {msg}")

    # ------------------------------------------------------------------
    def add_policy_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Select IT SOX Policy PDF file(s)", "", "PDF Files (*.pdf)")
        for f in files:
            if f not in self.policy_files:
                self.policy_files.append(f)
                self.policy_list.addItem(QListWidgetItem(os.path.basename(f)))
                self.policy_combo.addItem(os.path.basename(f))
        if files and self.policy_combo.itemText(0).startswith("(Upload"):
            self.policy_combo.removeItem(0)
        if files:
            self.log(f"Added {len(files)} policy file(s).")

    def remove_selected_policy(self):
        for item in self.policy_list.selectedItems():
            idx = self.policy_list.row(item)
            removed_path = self.policy_files.pop(idx)
            self.policy_list.takeItem(idx)
            combo_idx = self.policy_combo.findText(os.path.basename(removed_path))
            if combo_idx >= 0:
                self.policy_combo.removeItem(combo_idx)
            self.log(f"Removed policy file: {os.path.basename(removed_path)}")
        if self.policy_combo.count() == 0:
            self.policy_combo.addItem("(Upload a policy PDF first)")

    def select_rcm_file(self):
        f, _ = QFileDialog.getOpenFileName(
            self, "Select IT SOX RCM Excel file", "", "Excel Files (*.xlsx *.xlsm)")
        if f:
            self.rcm_file = f
            self.rcm_path_edit.setText(f)
            self.log(f"RCM file selected: {os.path.basename(f)}")

    # ------------------------------------------------------------------
    def generate_assessment(self):
        try:
            if not self.policy_files:
                QMessageBox.warning(self, "Missing Policy", "Please upload at least one IT SOX policy PDF.")
                return
            if not self.rcm_file:
                QMessageBox.warning(self, "Missing RCM", "Please upload the IT SOX Risk & Control Matrix (RCM) Excel file.")
                return
            combo_text = self.policy_combo.currentText()
            if combo_text.startswith("(Upload"):
                QMessageBox.warning(self, "Select Policy", "Please select which uploaded policy to assess.")
                return

            selected_path = None
            for p in self.policy_files:
                if os.path.basename(p) == combo_text:
                    selected_path = p
                    break
            if not selected_path:
                selected_path = self.policy_files[0]

            self.log(f"Reading policy document: {os.path.basename(selected_path)} ...")
            policy_info = parse_policy_pdf(selected_path)

            self.log(f"Reading RCM workbook: {os.path.basename(self.rcm_file)} ...")
            controls = parse_rcm(self.rcm_file)

            if not controls:
                QMessageBox.critical(self, "RCM Parsing Error",
                                      "No SOX controls with a 'Control ID' column could be found "
                                      "in the uploaded RCM file. Please check the file layout.")
                return

            self.log(f"Identified {len(controls)} SOX control(s): {', '.join(sorted(controls.keys()))}")
            self.log("Running intelligence engine to generate assessment questions per control ...")

            system_name = self.system_name_edit.text().strip()
            assessed_by = self.assessed_by_edit.text().strip()
            golive = self.golive_date.date().toString("dd-MMM-yyyy")

            default_name = f"IT_SOX_Assessment_{re.sub(r'[^A-Za-z0-9]+', '_', policy_info['title'])[:40]}.xlsx"
            out_path, _ = QFileDialog.getSaveFileName(
                self, "Save Assessment Workbook As", default_name, "Excel Workbook (*.xlsx)")
            if not out_path:
                self.log("Generation cancelled by user (no save location chosen).")
                return

            self.log("Building Cover Page, control worksheets and Summary & Sign-off sheet ...")
            generate_workbook(controls, policy_info, system_name, assessed_by, golive, out_path)

            self.log(f"SUCCESS: Assessment workbook saved to: {out_path}")
            QMessageBox.information(self, "Assessment Generated",
                                     f"The IT SOX Assessment workbook was generated successfully:\n\n{out_path}")
        except Exception as exc:
            self.log("ERROR: " + str(exc))
            self.log(traceback.format_exc())
            QMessageBox.critical(self, "Generation Failed", f"An error occurred:\n\n{exc}")


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    win = ITSoxAssessorWindow()
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
