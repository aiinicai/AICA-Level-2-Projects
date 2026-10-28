"""
memo.py
Professional PDF Audit Conclusion Memo Generator using ReportLab.
Adheres to ICAI SA 240, SA 315, SA 330 and CARO 2020 standards.
Includes auditor conclusion choices, exception analysis, running header/footer,
and sign-off blocks.
"""

from datetime import datetime
import io
import math
from typing import Any, Dict, List, Optional
import numpy as np
import reportlab
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


class NumberedCanvas(canvas.Canvas):
    """
    Two-pass canvas to dynamically compute and print 'Page X of Y'
    along with running CA firm confidentiality header.
    """
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

    def draw_page_decorations(self, total_pages):
        self.saveState()
        self.setFont("Helvetica-Bold", 8)
        self.setFillColor(colors.HexColor("#1B365D"))

        # Running Header
        self.drawString(40, A4[1] - 30, "CONFIDENTIAL & PRIVILEGED | AUDIT WORKING PAPER")
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#666666"))
        self.drawRightString(A4[0] - 40, A4[1] - 30, "SA 240 / SA 330 / CARO 2020 COMPLIANCE")
        self.setStrokeColor(colors.HexColor("#CCCCCC"))
        self.setLineWidth(0.5)
        self.line(40, A4[1] - 34, A4[0] - 40, A4[1] - 34)

        # Running Footer
        self.line(40, 36, A4[0] - 40, 36)
        self.setFont("Helvetica-Oblique", 7.5)
        self.drawString(40, 24, "Strictly for Internal Audit File Records. Not for external circulation.")
        page_str = f"Page {self._pageNumber} of {total_pages}"
        self.setFont("Helvetica", 8)
        self.drawRightString(A4[0] - 40, 24, page_str)
        self.restoreState()


def generate_pdf_conclusion_memo(
    engagement_info: Dict[str, Any],
    diagnostics: Dict[str, Any],
    flags_df,
    sample_df,
    benford_result: Dict[str, Any],
    conclusion_choice: str = "Satisfactory",
    auditor_final_memo: str = "",
    caro_implications: str = "No reportable matters noted under CARO 2020 Clause 3(ix) or 3(xi) based on tested sample.",
    unresolved_matters: str = "None outstanding.",
    financial_impact: str = "No material misstatement quantified."
) -> bytes:
    """
    Generate professional PDF Audit Conclusion Memo adhering to Indian Standards on Auditing.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=40,
        rightMargin=40,
        topMargin=50,
        bottomMargin=50
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=15,
        leading=19,
        textColor=colors.HexColor("#1B365D"),
        spaceAfter=4
    )

    h1_style = ParagraphStyle(
        "Heading1_Custom",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=15,
        textColor=colors.HexColor("#1B365D"),
        spaceBefore=10,
        spaceAfter=4,
        keepWithNext=True
    )

    body_style = ParagraphStyle(
        "Body_Custom",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#222222"),
        spaceAfter=4
    )

    bold_body = ParagraphStyle(
        "Bold_Body",
        parent=body_style,
        fontName="Helvetica-Bold"
    )

    callout_style = ParagraphStyle(
        "Callout_Style",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor("#1B365D")
    )

    story = []

    # Title & Memo Header
    story.append(Paragraph("AUDIT CONCLUSION MEMORANDUM", title_style))
    story.append(Paragraph("<b>Subject:</b> Journal Entry & Non-Standard Voucher Testing under SA 240, SA 315 & SA 330", bold_body))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#1B365D"), spaceAfter=8, spaceBefore=4))

    # Engagement Info Box Table
    co_name = engagement_info.get("company_name", "N/A")
    eng_name = engagement_info.get("engagement_name", "Statutory Audit")
    fy_str = engagement_info.get("financial_year", "FY 2023-24")
    prep_by = engagement_info.get("prepared_by", "Audit Senior")
    rev_by = engagement_info.get("reviewed_by", "Engagement Partner")
    om_val = engagement_info.get("om", 0.0)
    pm_val = engagement_info.get("pm", 0.0)
    ctt_val = engagement_info.get("ctt", 0.0)

    header_table_data = [
        [
            Paragraph(f"<b>Client / Entity:</b> {co_name}", body_style),
            Paragraph(f"<b>Financial Year:</b> {fy_str}", body_style)
        ],
        [
            Paragraph(f"<b>Engagement:</b> {eng_name}", body_style),
            Paragraph(f"<b>Date of Memo:</b> {datetime.now().strftime('%d-%b-%Y')}", body_style)
        ],
        [
            Paragraph(f"<b>Prepared By:</b> {prep_by}", body_style),
            Paragraph(f"<b>Reviewed By:</b> {rev_by}", body_style)
        ],
        [
            Paragraph(f"<b>Overall Materiality (OM):</b> ₹ {om_val:,.2f}", body_style),
            Paragraph(f"<b>Performance Materiality (PM):</b> ₹ {pm_val:,.2f} | <b>CTT:</b> ₹ {ctt_val:,.2f}", body_style)
        ]
    ]

    t_header = Table(header_table_data, colWidths=[260, 255])
    t_header.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F4F6F9")),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CCCCCC")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E0E0E0")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(t_header)
    story.append(Spacer(1, 10))

    # 1. Objective and Scope
    story.append(Paragraph("1. Objective and Regulatory Scope", h1_style))
    scope_text = (
        "In accordance with <b>SA 240</b> (<i>The Auditor's Responsibilities Relating to Fraud in an Audit of Financial Statements</i>), "
        "management is in a unique position to perpetrate fraud because of its ability to manipulate accounting records and prepare "
        "fraudulent financial statements by overriding controls that otherwise appear to be operating effectively. "
        "Pursuant to paragraphs 32(a) of SA 240 and <b>SA 330</b> (<i>The Auditor's Responses to Assessed Risks</i>), we designed and "
        "executed automated analytical routines and risk-targeted testing on the entire general ledger journal voucher population "
        f"of {co_name} for the period under audit."
    )
    story.append(Paragraph(scope_text, body_style))

    # 2. Population & Reconciliation
    story.append(Paragraph("2. Population Integrity and Reconciliation", h1_style))
    tot_rows = diagnostics.get("total_rows", 0)
    tot_dr = diagnostics.get("total_debit", 0.0)
    tot_cr = diagnostics.get("total_credit", 0.0)
    diff = diagnostics.get("difference", 0.0)
    unbal = diagnostics.get("unbalanced_vouchers_count", 0)

    recon_summary = (
        f"• <b>Total Records Examined:</b> {tot_rows:,} journal lines imported from client accounting records.<br/>"
        f"• <b>Total Debits:</b> ₹ {tot_dr:,.2f} | <b>Total Credits:</b> ₹ {tot_cr:,.2f}<br/>"
        f"• <b>Net Population Balance Difference:</b> ₹ {diff:,.2f} (Status: {'BALANCED' if abs(diff) < 0.01 else 'UNBALANCED EXCEPTION'})<br/>"
        f"• <b>Vouchers with Debit-Credit Discrepancies:</b> {unbal} vouchers identified."
    )
    story.append(Paragraph(recon_summary, body_style))

    # 3. Analytics & Red-Flag Results
    story.append(Paragraph("3. Summary of Journal Entry Red-Flag Tests Executed", h1_style))
    flags_count = len(flags_df) if not flags_df.empty else 0
    high_count = len(flags_df[flags_df["risk_level"] == "High"]) if flags_count > 0 else 0
    med_count = len(flags_df[flags_df["risk_level"] == "Medium"]) if flags_count > 0 else 0
    low_count = len(flags_df[flags_df["risk_level"] == "Low"]) if flags_count > 0 else 0

    results_table_data = [
        ["Audit Risk Level", "Flag Count", "Testing Stratum / Mandated Treatment"],
        ["High Risk (Cutoff, Structuring, PM, SoD)", str(high_count), "100% Substantive Vouching to External Third-Party Docs"],
        ["Medium Risk (Sunday, Off-hours, Blank Narr)", str(med_count), "Inquiry & Sample Verification of Supporting Vouchers"],
        ["Low Risk (Round Multiples)", str(low_count), "Exploratory Scrutiny & Contract Rate Verification"],
        ["Total Identified Exceptions", str(flags_count), "Investigated per Audit Plan"]
    ]

    t_res = Table(results_table_data, colWidths=[180, 75, 260])
    t_res.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1B365D")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ALIGN", (1, 0), (1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CCCCCC")),
        ("BACKGROUND", (0, 1), (0, 1), colors.HexColor("#FCE8E6")),
        ("BACKGROUND", (0, 2), (0, 2), colors.HexColor("#FEF7E0")),
        ("BACKGROUND", (0, 3), (0, 3), colors.HexColor("#E6F4EA")),
        ("BACKGROUND", (0, 4), (-1, 4), colors.HexColor("#E8EEF5")),
        ("FONTNAME", (0, 4), (-1, 4), "Helvetica-Bold"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(t_res)
    story.append(Spacer(1, 8))

    # 4. Benford's Law Analytical Assessment
    story.append(Paragraph("4. Benford's Law First-Digit Analysis", h1_style))
    chi2 = benford_result.get("chi2_stat")
    pval = benford_result.get("p_value")
    conforms = benford_result.get("conforms", False)
    
    chi_str = f"χ² = {chi2:.3f}" if chi2 is not None and not np.isnan(chi2) else "N/A"
    p_str = f"p-value = {pval:.4f}" if pval is not None and not np.isnan(pval) else "N/A"
    conf_str = "conforms to" if conforms else "statistically deviates from"

    ben_text = (
        f"A first-digit Benford distribution test was performed on {benford_result.get('sample_size', 0):,} monetary values ({chi_str}, {p_str}, df=8). "
        f"The observed population {conf_str} the expected logarithmic distribution at α = 0.05. "
        "<i>Important ICAI Audit Note:</i> A statistical deviation under Benford's Law does NOT constitute proof of fraud or error, "
        "as regular operational dynamics (such as fixed rate tariffs, round allowances, or regulatory caps) routinely generate digit concentrations."
    )
    story.append(Paragraph(ben_text, body_style))

    # 5. CARO 2020 Reporting Considerations
    story.append(Paragraph("5. CARO 2020 Specific Considerations", h1_style))
    caro_box_text = (
        f"<b>Auditor CARO Assessment:</b> {caro_implications}<br/>"
        "• <i>Clause 3(ix):</i> Verified whether any funds raised have been diverted or applied for purposes other than intended.<br/>"
        "• <i>Clause 3(viii):</i> Verified that no unrecorded transactions were surrendered or disclosed as income during tax assessments.<br/>"
        "• <i>Clause 3(xi):</i> Considered whether any whistle-blower complaints or fraud instances were uncovered during JE testing."
    )
    t_caro = Table([[Paragraph(caro_box_text, callout_style)]], colWidths=[515])
    t_caro.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F0F4F8")),
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#1B365D")),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(t_caro)
    story.append(Spacer(1, 8))

    # 6. Unresolved Matters & Financial Statement Impact
    story.append(Paragraph("6. Unresolved Matters & Financial Statement Impact", h1_style))
    matters_p = (
        f"• <b>Unresolved Matters:</b> {unresolved_matters}<br/>"
        f"• <b>Quantified Financial Statement Impact:</b> {financial_impact}"
    )
    story.append(Paragraph(matters_p, body_style))

    # 7. Audit Conclusion & Decision Choice
    story.append(Paragraph("7. Auditor Conclusion & Recommendation", h1_style))

    conclusion_colors = {
        "Satisfactory": "#0F5132",
        "Unresolved Exceptions": "#856404",
        "Potential Material Misstatement": "#721C24",
        "Inconclusive": "#383D41"
    }
    badge_color = conclusion_colors.get(conclusion_choice, "#1B365D")

    conclusion_summary_box = [
        [
            Paragraph(f"<b>FINAL AUDIT CONCLUSION:</b> <font color='{badge_color}'><b>{conclusion_choice.upper()}</b></font>", h1_style)
        ],
        [
            Paragraph(
                f"<b>Auditor Evaluation & Narrative:</b><br/>"
                f"{auditor_final_memo if auditor_final_memo else 'The audit team has tested representative and risk-targeted journal entries. Based on the documentation reviewed and management explanations evaluated, the procedures performed provide sufficient appropriate audit evidence under SA 330.'}",
                body_style
            )
        ]
    ]
    t_concl = Table(conclusion_summary_box, colWidths=[515])
    t_concl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FAFAFA")),
        ("BOX", (0, 0), (-1, -1), 1.5, colors.HexColor(badge_color)),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(t_concl)
    story.append(Spacer(1, 14))

    # 8. Sign-Off Section
    story.append(Paragraph("8. Audit File Sign-Off & Review Approval", h1_style))
    story.append(Spacer(1, 10))

    sign_data = [
        ["PREPARED BY (AUDIT SENIOR)", "REVIEWED BY (ENGAGEMENT PARTNER)"],
        ["\n\n___________________________________\nSignature", "\n\n___________________________________\nSignature"],
        [f"Name: {prep_by}", f"Name: {rev_by}"],
        ["Designation: Audit Senior / Assistant", "Designation: Engagement Partner"],
        [f"Date: {datetime.now().strftime('%d-%b-%Y')}", f"Date: {datetime.now().strftime('%d-%b-%Y')}"]
    ]

    t_sign = Table(sign_data, colWidths=[250, 265])
    t_sign.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
    ]))
    story.append(KeepTogether(t_sign))

    # Build document with NumberedCanvas
    doc.build(story, canvasmaker=NumberedCanvas)
    buffer.seek(0)
    return buffer.getvalue()
