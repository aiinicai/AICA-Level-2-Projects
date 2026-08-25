"""PDF Report Generator for Bank Statement Analysis.
Uses ReportLab to generate a clean, letterhead-styled CA audit report.
"""

import os
import pandas as pd
from typing import Dict, Any, Optional

from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas

PRIMARY_COLOR = colors.HexColor("#1F4E78")
SECONDARY_COLOR = colors.HexColor("#2E75B6")
LIGHT_BG = colors.HexColor("#F2F4F7")
ACCENT_RED = colors.HexColor("#C00000")
SOFT_RED_BG = colors.HexColor("#FCE4D6")
TEXT_DARK = colors.HexColor("#262626")

class NumberedCanvas(canvas.Canvas):
    """Canvas for adding page numbers and running header/footer."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#595959"))
        
        # Header (pages > 1)
        if self._pageNumber > 1:
            self.drawString(54, 11 * inch - 36, "Dharmjeet & Associates — Bank Statement Audit Report")
            self.setStrokeColor(colors.HexColor("#D9D9D9"))
            self.setLineWidth(0.5)
            self.line(54, 11 * inch - 40, 8.5 * inch - 54, 11 * inch - 40)
            
        # Footer
        footer_text = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(8.5 * inch - 54, 36, footer_text)
        self.drawString(54, 36, "Strictly Confidential — Prepared for Income Tax / GST Scrutiny & Compliance")
        self.setStrokeColor(colors.HexColor("#D9D9D9"))
        self.setLineWidth(0.5)
        self.line(54, 46, 8.5 * inch - 54, 46)
        self.restoreState()

def build_pdf_table(
    data: list,
    col_widths: Optional[list] = None,
    header_color=PRIMARY_COLOR,
    font_size: int = 8,
    is_red_flag: bool = False
) -> Table:
    """Build a styled Table with zebra stripes."""
    style = [
        ('BACKGROUND', (0, 0), (-1, 0), header_color),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), font_size),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 4),
        ('TOPPADDING', (0, 0), (-1, 0), 4),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#D9D9D9")),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]

    for i in range(1, len(data)):
        if is_red_flag:
            bg = SOFT_RED_BG if i % 2 == 1 else colors.white
        else:
            bg = LIGHT_BG if i % 2 == 1 else colors.white
        style.append(('BACKGROUND', (0, i), (-1, i), bg))
        style.append(('TOPPADDING', (0, i), (-1, i), 3))
        style.append(('BOTTOMPADDING', (0, i), (-1, i), 3))

    table = Table(data, colWidths=col_widths)
    table.setStyle(TableStyle(style))
    return table

def export_pdf_report(
    df: pd.DataFrame,
    output_path: str,
    client_name: str = "Client"
) -> str:
    """Generate standalone PDF report using ReportLab."""
    from analysis.summaries import (
        generate_executive_summary, generate_month_wise_summary,
        generate_nature_wise_summary, generate_party_wise_summary,
        generate_top_and_extrema_transactions, generate_cash_summary
    )
    from analysis.red_flags import detect_red_flags
    from analysis.presumptive_tax import analyze_presumptive_tax
    from analysis.reconciliation import validate_running_balances

    exec_sum = generate_executive_summary(df)
    m_sum = generate_month_wise_summary(df)
    nat_cr, nat_dr = generate_nature_wise_summary(df)
    pty_cr, pty_dr = generate_party_wise_summary(df)
    top_ext = generate_top_and_extrema_transactions(df)
    cash_sum = generate_cash_summary(df)
    df_flagged, red_flag_sum = detect_red_flags(df, client_name=client_name)
    presump_sum = analyze_presumptive_tax(df)
    df_recon, recon_sum = validate_running_balances(df)

    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54
    )

    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'FirmTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=16,
        leading=20,
        textColor=PRIMARY_COLOR
    )
    subtitle_style = ParagraphStyle(
        'FirmSubTitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#595959")
    )
    heading_style = ParagraphStyle(
        'SecHeading',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=PRIMARY_COLOR,
        spaceBefore=10,
        spaceAfter=4
    )
    subheading_style = ParagraphStyle(
        'SubSecHeading',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=14,
        textColor=SECONDARY_COLOR,
        spaceBefore=6,
        spaceAfter=3
    )
    cell_style = ParagraphStyle(
        'CellText',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=10,
        textColor=TEXT_DARK
    )
    bold_cell_style = ParagraphStyle(
        'BoldCellText',
        parent=cell_style,
        fontName='Helvetica-Bold'
    )

    story = []

    # 1. Letterhead Banner
    story.append(Paragraph("DHARMJEET & ASSOCIATES", title_style))
    story.append(Paragraph("CHARTERED ACCOUNTANTS | TAXATION & AUDIT COMPLIANCE PRACTICE", subtitle_style))
    story.append(Spacer(1, 4))
    story.append(HRFlowable(width="100%", thickness=1.5, color=PRIMARY_COLOR, spaceAfter=8))

    # Report Title
    story.append(Paragraph(f"BANK STATEMENT AUDIT & SUMMARY REPORT — {client_name.upper()}", heading_style))
    story.append(Paragraph(
        f"<b>Period:</b> {exec_sum['start_date']} to {exec_sum['end_date']} | "
        f"<b>Transactions:</b> {exec_sum['total_transactions']:,} | "
        f"<b>Accounts:</b> {exec_sum['accounts_count']} | "
        f"<b>Status:</b> {recon_sum['status']}",
        subtitle_style
    ))
    story.append(Spacer(1, 8))

    # 2. Executive KPI Summary Table
    story.append(Paragraph("1. Financial Summary & Overview", heading_style))
    kpi_table_data = [
        [
            Paragraph("<b>Total Credits (Receipts)</b>", cell_style),
            Paragraph(f"<b>₹{exec_sum['total_credits']:,.2f}</b>", bold_cell_style),
            Paragraph(f"{exec_sum['credit_count']:,} txns", cell_style),
            Paragraph("<b>Total Debits (Payments)</b>", cell_style),
            Paragraph(f"<b>₹{exec_sum['total_debits']:,.2f}</b>", bold_cell_style),
            Paragraph(f"{exec_sum['debit_count']:,} txns", cell_style)
        ],
        [
            Paragraph("<b>Net Movement</b>", cell_style),
            Paragraph(f"₹{exec_sum['net_movement']:,.2f}", bold_cell_style),
            Paragraph("—", cell_style),
            Paragraph("<b>Cash Deposits Total</b>", cell_style),
            Paragraph(f"₹{cash_sum['total_cash_deposits']:,.2f}", bold_cell_style),
            Paragraph(f"{cash_sum['cash_deposit_count']:,} txns", cell_style)
        ],
        [
            Paragraph("<b>Cash Withdrawals Total</b>", cell_style),
            Paragraph(f"₹{cash_sum['total_cash_withdrawals']:,.2f}", bold_cell_style),
            Paragraph(f"{cash_sum['cash_withdrawal_count']:,} txns", cell_style),
            Paragraph("<b>Scrutiny Red Flags</b>", cell_style),
            Paragraph(f"<font color='#C00000'><b>{red_flag_sum['total_flagged_transactions']} Flagged</b></font>", bold_cell_style),
            Paragraph(f"₹{red_flag_sum['total_flagged_amount']:,.2f}", cell_style)
        ]
    ]
    t_kpi = Table(kpi_table_data, colWidths=[1.4*inch, 1.2*inch, 0.8*inch, 1.4*inch, 1.2*inch, 0.8*inch])
    t_kpi.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), LIGHT_BG),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#D9D9D9")),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(t_kpi)
    story.append(Spacer(1, 8))

    # 3. Presumptive Taxation (Section 44AD / 44ADA)
    story.append(Paragraph("2. Presumptive Taxation (Section 44AD / 44ADA) Analysis", heading_style))
    presump_rows = [
        ["Turnover / Gross Receipts", f"₹{presump_sum['total_turnover']:,.2f}", "Digital Receipts Proportion", f"{presump_sum['digital_percentage']:.1f}%"],
        ["Sec 44AD Limit Applicable", f"₹{presump_sum['sec_44ad_limit_applicable']/10000000:.1f} Crore", "44AD Audit Requirement", "AUDIT REQUIRED" if presump_sum['audit_required_44ad'] else "NO (Eligible)"],
        ["Sec 44ADA Limit Applicable", f"₹{presump_sum['sec_44ada_limit_applicable']/100000:.1f} Lakhs", "Min 44AD Deemed Profit", f"₹{presump_sum['min_presumptive_income_44ad']:,.2f}"]
    ]
    story.append(build_pdf_table(
        [["Parameter", "Value", "Parameter", "Value"]] + presump_rows,
        col_widths=[1.7*inch, 1.6*inch, 1.9*inch, 1.6*inch],
        header_color=SECONDARY_COLOR
    ))
    story.append(Spacer(1, 8))

    # 4. Month-wise Summary Table
    story.append(Paragraph("3. Month-wise Summary", heading_style))
    m_headers = ["Month", "FY Quarter", "Receipts (Cr)", "Payments (Dr)", "Net Movement", "Cash In", "Txns"]
    m_rows = [m_headers]
    for _, r in m_sum.iterrows():
        m_rows.append([
            str(r["Month"]),
            str(r["FY Quarter"]),
            f"₹{r['Receipts (Cr)']:,.2f}",
            f"₹{r['Payments (Dr)']:,.2f}",
            f"₹{r['Net Movement']:,.2f}",
            f"₹{r['Cash Deposits']:,.2f}",
            str(r["Txn Count"])
        ])
    story.append(build_pdf_table(m_rows, col_widths=[1.0*inch, 1.1*inch, 1.2*inch, 1.2*inch, 1.1*inch, 0.7*inch, 0.5*inch]))
    story.append(Spacer(1, 8))

    # 5. Nature-wise Summary
    story.append(Paragraph("4. Nature-wise Categorization", heading_style))
    story.append(Paragraph("4.1 Top Receipts by Category", subheading_style))
    cr_rows = [["Nature Category", "Total Amount (INR)", "Txn Count", "% Share"]]
    for _, r in nat_cr.head(8).iterrows():
        cr_rows.append([str(r["Nature Category"]), f"₹{r['Total Amount (INR)']:,.2f}", str(r["Txn Count"]), f"{r['% Share']:.1f}%"])
    story.append(build_pdf_table(cr_rows, col_widths=[2.8*inch, 1.8*inch, 1.1*inch, 1.1*inch], header_color=SECONDARY_COLOR))
    story.append(Spacer(1, 6))

    story.append(Paragraph("4.2 Top Payments by Category", subheading_style))
    dr_rows = [["Nature Category", "Total Amount (INR)", "Txn Count", "% Share"]]
    for _, r in nat_dr.head(8).iterrows():
        dr_rows.append([str(r["Nature Category"]), f"₹{r['Total Amount (INR)']:,.2f}", str(r["Txn Count"]), f"{r['% Share']:.1f}%"])
    story.append(build_pdf_table(dr_rows, col_widths=[2.8*inch, 1.8*inch, 1.1*inch, 1.1*inch], header_color=PRIMARY_COLOR))
    story.append(Spacer(1, 8))

    # 6. Top Counterparties
    story.append(Paragraph("5. Top Counterparties", heading_style))
    story.append(Paragraph("5.1 Top Inward Parties (Receipts)", subheading_style))
    pcr_rows = [["Party Name", "Amount (INR)", "Txns", "Dominant Nature", "Mode"]]
    for _, r in pty_cr.head(6).iterrows():
        pcr_rows.append([str(r["Party Name"])[:25], f"₹{r['Total Amount (INR)']:,.2f}", str(r["Txn Count"]), str(r["Dominant Nature"])[:20], str(r["Primary Mode"])])
    story.append(build_pdf_table(pcr_rows, col_widths=[2.2*inch, 1.3*inch, 0.6*inch, 1.8*inch, 0.9*inch], header_color=SECONDARY_COLOR))
    story.append(Spacer(1, 6))

    story.append(Paragraph("5.2 Top Outward Parties (Payments)", subheading_style))
    pdr_rows = [["Party Name", "Amount (INR)", "Txns", "Dominant Nature", "Mode"]]
    for _, r in pty_dr.head(6).iterrows():
        pdr_rows.append([str(r["Party Name"])[:25], f"₹{r['Total Amount (INR)']:,.2f}", str(r["Txn Count"]), str(r["Dominant Nature"])[:20], str(r["Primary Mode"])])
    story.append(build_pdf_table(pdr_rows, col_widths=[2.2*inch, 1.3*inch, 0.6*inch, 1.8*inch, 0.9*inch], header_color=PRIMARY_COLOR))
    story.append(Spacer(1, 8))

    # 7. Red Flags & Scrutiny Signals Annexure
    story.append(Paragraph("6. Tax Scrutiny Red Flags & Compliance Signals", heading_style))
    flagged_df = df_flagged[df_flagged["is_flagged"]].copy() if "is_flagged" in df_flagged.columns else pd.DataFrame()
    if not flagged_df.empty:
        f_rows = [["Date", "Counterparty / Narration", "Amount (INR)", "Flag Reason / Rule Trigger"]]
        for _, r in flagged_df.head(20).iterrows():
            amt = max(float(r["credit_amount"] or 0.0), float(r["debit_amount"] or 0.0))
            reasons_text = "; ".join(r["flag_reasons"])
            f_rows.append([
                str(r["transaction_date"]),
                str(r["counterparty_name"])[:20],
                f"₹{amt:,.2f}",
                Paragraph(reasons_text, cell_style)
            ])
        story.append(build_pdf_table(f_rows, col_widths=[0.9*inch, 1.8*inch, 1.2*inch, 2.9*inch], header_color=ACCENT_RED, is_red_flag=True))
    else:
        story.append(Paragraph("No scrutiny red flags detected under active thresholds.", cell_style))

    # Build Document with NumberedCanvas
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    doc.build(story, canvasmaker=NumberedCanvas)
    return output_path
