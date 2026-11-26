"""
report_generator.py
Generates the consolidated Excel workbook (TenderIQ_Tender_Report.xlsx)
and PDF management report (TenderIQ_Management_Report.pdf).
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional
from xml.sax.saxutils import escape

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from document_analyser import AnalysisStats
from tender_extractor import NOT_AVAILABLE, TenderRecord

EXCEL_FILENAME = "TenderIQ_Tender_Report.xlsx"
PDF_FILENAME = "TenderIQ_Management_Report.pdf"

MASTER_HEADERS = [
    "Tender Reference",
    "Tender Title",
    "Organisation",
    "Department",
    "Location",
    "Published Date",
    "Closing Date",
    "Estimated Value",
    "EMD",
    "Tender Fee",
    "Document Download Status",
    "Tender URL",
    "Document Folder",
]

MASTER_WIDTHS = [22, 42, 28, 24, 20, 16, 16, 20, 18, 16, 26, 38, 34]

AI_HEADERS = [
    "Tender Reference",
    "Scope of Work",
    "Product / Service",
    "Turnover Requirement",
    "Experience Requirement",
    "Technical Requirements",
    "EMD",
    "Important Deadlines",
    "Required Certificates",
    "Commercial Conditions",
    "Risk Observations",
    "Overall Summary",
]

AI_WIDTHS = [22, 38, 30, 28, 30, 36, 20, 28, 30, 32, 34, 46]

DATE_FORMATS = (
    "%Y-%m-%d",
    "%d-%m-%Y",
    "%d/%m/%Y",
    "%Y/%m/%d",
    "%d-%b-%Y",
    "%d %b %Y",
    "%d-%B-%Y",
    "%d %B %Y",
    "%b %d, %Y",
    "%B %d, %Y",
)


def _parse_date_value(raw: str):
    """Attempt to convert a date string to a datetime.date for Excel date formatting."""
    if not raw or raw == NOT_AVAILABLE:
        return raw
    candidate = raw.strip()
    # Strip trailing time component if present (e.g. "2026-12-15 17:00")
    date_part = candidate.split(" ")[0].strip(",")
    for target in (candidate, date_part):
        for fmt in DATE_FORMATS:
            try:
                return datetime.strptime(target, fmt).date()
            except ValueError:
                continue
    return raw


def _style_worksheet(ws, headers: list[str], widths: list[int], date_col_indices: tuple[int, ...] = ()) -> None:
    """Apply consistent headers, widths, filters, freeze panes, wrap text, and date format."""
    header_fill = PatternFill(start_color="1F3864", end_color="1F3864", fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    body_font = Font(name="Calibri", size=10, color="111111")
    thin_side = Side(style="thin", color="D0D7DE")
    cell_border = Border(left=thin_side, right=thin_side, top=thin_side, bottom=thin_side)

    ws.freeze_panes = "A2"
    ws.row_dimensions[1].height = 28

    for col_idx, (title, width) in enumerate(zip(headers, widths), start=1):
        cell = ws.cell(row=1, column=col_idx, value=title)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = cell_border
        ws.column_dimensions[get_column_letter(col_idx)].width = width

    max_row = ws.max_row
    max_col = len(headers)
    if max_row >= 1:
        ws.auto_filter.ref = f"A1:{get_column_letter(max_col)}{max_row}"

    alt_fill = PatternFill(start_color="F6F8FA", end_color="F6F8FA", fill_type="solid")

    for row_idx in range(2, max_row + 1):
        max_lines = 1
        for col_idx in range(1, max_col + 1):
            cell = ws.cell(row=row_idx, column=col_idx)
            cell.font = body_font
            cell.border = cell_border
            if row_idx % 2 == 1:
                cell.fill = alt_fill

            if col_idx in date_col_indices and hasattr(cell.value, "year"):
                cell.number_format = "yyyy-mm-dd"
                cell.alignment = Alignment(horizontal="center", vertical="top", wrap_text=True)
            else:
                cell.alignment = Alignment(horizontal="left", vertical="top", wrap_text=True)

            val_str = str(cell.value or "")
            width = widths[col_idx - 1]
            est_lines = max(1, (len(val_str) // max(width - 3, 10)) + val_str.count("\n") + 1)
            if est_lines > max_lines:
                max_lines = est_lines

        ws.row_dimensions[row_idx].height = min(max(20, max_lines * 15), 220)


def generate_excel_report(tenders: list[TenderRecord], output_dir: Path) -> Path:
    """Create TenderIQ_Tender_Report.xlsx with TENDER MASTER and AI TENDER SUMMARY sheets."""
    output_dir.mkdir(parents=True, exist_ok=True)
    excel_path = output_dir / EXCEL_FILENAME

    wb = Workbook()

    # Worksheet 1: TENDER MASTER
    ws_master = wb.active
    ws_master.title = "TENDER MASTER"
    ws_master.append(MASTER_HEADERS)

    for t in tenders:
        ws_master.append(
            [
                t.tender_id,
                t.title,
                t.organisation,
                t.department,
                t.location,
                _parse_date_value(t.published_date),
                _parse_date_value(t.closing_date),
                t.estimated_value,
                t.emd_amount,
                t.tender_fee,
                t.document_download_status,
                t.detail_url,
                t.document_folder,
            ]
        )

    _style_worksheet(ws_master, MASTER_HEADERS, MASTER_WIDTHS, date_col_indices=(6, 7))

    # Worksheet 2: AI TENDER SUMMARY
    ws_ai = wb.create_sheet(title="AI TENDER SUMMARY")
    ws_ai.append(AI_HEADERS)

    for t in tenders:
        ai = t.ai_summary or {}
        ws_ai.append(
            [
                t.tender_id,
                ai.get("scope_of_work", NOT_AVAILABLE),
                ai.get("products_services", NOT_AVAILABLE),
                ai.get("turnover_requirement", NOT_AVAILABLE),
                ai.get("experience_requirement", NOT_AVAILABLE),
                ai.get("technical_specifications", NOT_AVAILABLE),
                ai.get("emd_requirement", t.emd_amount),
                ai.get("important_deadlines", t.closing_date),
                ai.get("required_certificates", NOT_AVAILABLE),
                ai.get("commercial_conditions", NOT_AVAILABLE),
                ai.get("risk_observations", NOT_AVAILABLE),
                ai.get("overall_summary", NOT_AVAILABLE),
            ]
        )

    _style_worksheet(ws_ai, AI_HEADERS, AI_WIDTHS)

    wb.save(excel_path)
    return excel_path


def _p(text: str, style: ParagraphStyle) -> Paragraph:
    """Safely XML-escape text and preserve line breaks inside a ReportLab Paragraph."""
    safe = escape(str(text or NOT_AVAILABLE)).replace("\n", "<br/>")
    return Paragraph(safe, style)


def _add_page_number(canvas, doc) -> None:
    """Draw footer with page number on every PDF page."""
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#6B7280"))
    canvas.drawString(18 * mm, 10 * mm, "TenderIQ - AI-Powered Tender Intelligence Report")
    canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, f"Page {doc.page}")
    canvas.restoreState()


def generate_pdf_report(
    tenders: list[TenderRecord],
    source_url: str,
    total_documents_downloaded: int,
    analysis_stats: AnalysisStats,
    output_dir: Path,
) -> Path:
    """Create TenderIQ_Management_Report.pdf with Executive Summary and per-tender briefs."""
    output_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = output_dir / PDF_FILENAME

    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=A4,
        leftMargin=16 * mm,
        rightMargin=16 * mm,
        topMargin=16 * mm,
        bottomMargin=18 * mm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "TenderIQTitle",
        parent=styles["Heading1"],
        fontSize=19,
        leading=23,
        textColor=colors.HexColor("#1F3864"),
        spaceAfter=4,
    )
    subtitle_style = ParagraphStyle(
        "TenderIQSub",
        parent=styles["Normal"],
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#4B5563"),
        spaceAfter=10,
    )
    section_hdr = ParagraphStyle(
        "SectionHdr",
        parent=styles["Heading2"],
        fontSize=12.5,
        leading=16,
        textColor=colors.HexColor("#1F3864"),
        spaceBefore=10,
        spaceAfter=6,
    )
    body_style = ParagraphStyle(
        "BodyTextClean",
        parent=styles["Normal"],
        fontSize=9.2,
        leading=13,
        textColor=colors.HexColor("#111827"),
    )
    label_style = ParagraphStyle(
        "LabelClean",
        parent=styles["Normal"],
        fontSize=9.2,
        leading=13,
        fontName="Helvetica-Bold",
        textColor=colors.HexColor("#1F3864"),
    )

    story = []

    # --- PAGE 1: EXECUTIVE SUMMARY ---
    story.append(_p("TENDERIQ - MANAGEMENT INTELLIGENCE REPORT", title_style))
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    story.append(_p(f"Generated: {generated_at} | Source URL: {source_url}", subtitle_style))

    story.append(_p("1. Executive Summary", section_hdr))

    metrics_data = [
        [_p("Metric", label_style), _p("Count", label_style)],
        [_p("Total Tenders Identified", body_style), _p(str(len(tenders)), body_style)],
        [_p("Total Documents Downloaded", body_style), _p(str(total_documents_downloaded), body_style)],
        [_p("Total Tenders Analysed by AI", body_style), _p(str(analysis_stats.tenders_analysed), body_style)],
        [
            _p("Documents That Could Not Be Analysed", body_style),
            _p(str(analysis_stats.documents_unanalysed), body_style),
        ],
    ]
    metrics_table = Table(metrics_data, colWidths=[125 * mm, 53 * mm])
    metrics_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E8EEF7")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story.append(metrics_table)
    story.append(Spacer(1, 8))

    # Important Upcoming Deadlines
    story.append(_p("2. Important Upcoming Deadlines", section_hdr))
    deadline_rows = [
        [
            _p("Tender Ref", label_style),
            _p("Tender Title", label_style),
            _p("Closing Date", label_style),
            _p("Est. Value", label_style),
        ]
    ]
    for t in tenders[:15]:
        deadline_rows.append(
            [
                _p(t.tender_id, body_style),
                _p(t.title[:95], body_style),
                _p(t.closing_date, body_style),
                _p(t.estimated_value, body_style),
            ]
        )
    dl_table = Table(deadline_rows, colWidths=[34 * mm, 82 * mm, 32 * mm, 30 * mm], repeatRows=1)
    dl_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E8EEF7")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CBD5E1")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(dl_table)
    story.append(Spacer(1, 8))

    # Key Observations
    story.append(_p("3. Key Observations", section_hdr))
    observations: list[str] = []
    if not analysis_stats.api_key_configured:
        observations.append(
            "OpenAI API key was not configured in .env; AI document analysis was skipped while "
            "tender metadata and document downloads were captured."
        )
    for t in tenders:
        ai = t.ai_summary or {}
        risk = ai.get("risk_observations", "")
        if risk and risk not in (NOT_AVAILABLE, "Not Specified in Document"):
            observations.append(f"{t.tender_id}: {risk}")
        if len(observations) >= 6:
            break

    if not observations:
        observations.append(
            f"Identified {len(tenders)} tender(s) and downloaded {total_documents_downloaded} document(s). "
            "Review individual tender pages below for extracted details."
        )
    for w in analysis_stats.warnings[:4]:
        observations.append(f"Notice: {w}")

    for obs in observations:
        story.append(_p(f"• {obs}", body_style))
        story.append(Spacer(1, 3))

    # --- SUBSEQUENT PAGES: INDIVIDUAL TENDER BRIEFS ---
    for idx, t in enumerate(tenders, start=1):
        story.append(PageBreak())
        ai = t.ai_summary or {}

        story.append(_p(f"Tender {idx}: {t.tender_id} — {t.title}", title_style))
        story.append(_p(f"Source URL: {t.detail_url}", subtitle_style))

        meta_rows = [
            [_p("Tender Reference", label_style), _p(t.tender_id, body_style), _p("Organisation", label_style), _p(t.organisation, body_style)],
            [_p("Location", label_style), _p(t.location, body_style), _p("Department", label_style), _p(t.department, body_style)],
            [_p("Published Date", label_style), _p(t.published_date, body_style), _p("Closing Date", label_style), _p(t.closing_date, body_style)],
            [_p("Estimated Value", label_style), _p(t.estimated_value, body_style), _p("EMD", label_style), _p(t.emd_amount, body_style)],
            [_p("Tender Fee", label_style), _p(t.tender_fee, body_style), _p("Download Status", label_style), _p(t.document_download_status, body_style)],
        ]
        meta_table = Table(meta_rows, colWidths=[32 * mm, 57 * mm, 32 * mm, 57 * mm])
        meta_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F1F5F9")),
                    ("BACKGROUND", (2, 0), (2, -1), colors.HexColor("#F1F5F9")),
                    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CBD5E1")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        story.append(meta_table)
        story.append(Spacer(1, 8))

        eligibility_text = (
            f"Turnover: {ai.get('turnover_requirement', NOT_AVAILABLE)}\n"
            f"Experience: {ai.get('experience_requirement', NOT_AVAILABLE)}\n"
            f"Capability: {ai.get('capability_requirement', NOT_AVAILABLE)}\n"
            f"Certificates: {ai.get('required_certificates', NOT_AVAILABLE)}"
        )
        conditions_text = (
            f"Tender Fee: {ai.get('tender_fee', t.tender_fee)}\n"
            f"Performance Security: {ai.get('performance_security', NOT_AVAILABLE)}\n"
            f"Deadlines: {ai.get('important_deadlines', t.closing_date)}\n"
            f"Commercial Terms: {ai.get('commercial_conditions', NOT_AVAILABLE)}\n"
            f"Disqualification Triggers: {ai.get('disqualification_conditions', NOT_AVAILABLE)}\n"
            f"Risks & Observations: {ai.get('risk_observations', NOT_AVAILABLE)}"
        )
        ai_summary_text = (
            f"Purpose: {ai.get('purpose', NOT_AVAILABLE)}\n"
            f"Products/Services: {ai.get('products_services', NOT_AVAILABLE)}\n\n"
            f"{ai.get('overall_summary', NOT_AVAILABLE)}"
        )

        detail_rows = [
            [_p("Scope of Work", label_style), _p(ai.get("scope_of_work", NOT_AVAILABLE), body_style)],
            [_p("Eligibility Requirements", label_style), _p(eligibility_text, body_style)],
            [_p("Technical Requirements", label_style), _p(ai.get("technical_specifications", NOT_AVAILABLE), body_style)],
            [_p("Important Conditions & Risks", label_style), _p(conditions_text, body_style)],
            [_p("AI-Generated Summary", label_style), _p(ai_summary_text, body_style)],
            [_p("Relevant Documents", label_style), _p(ai.get("document_references", ", ".join(t.downloaded_files) or NOT_AVAILABLE), body_style)],
        ]
        detail_table = Table(detail_rows, colWidths=[46 * mm, 132 * mm])
        detail_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#E8EEF7")),
                    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CBD5E1")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        story.append(detail_table)

    doc.build(story, onFirstPage=_add_page_number, onLaterPages=_add_page_number)
    return pdf_path
