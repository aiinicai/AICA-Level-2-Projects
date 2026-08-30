"""
Evidence Requisition List PDF Generator using ReportLab.
Produces a formal client-addressed document detailing specific evidentiary records required,
justified by the specific red flags that actually fired during analysis.
"""
import io
import datetime
from typing import Dict, List, Any, Optional
import pandas as pd
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from engine.coverage import load_methods_registry

def generate_requisition_pdf(
    scoring_result: Dict[str, Any],
    client_name: str = "The Board of Directors / Management",
    engagement_ref: str = "FORENSIC-ENG-01",
    firm_name: str = "",
    operator: str = "Lead Forensic Auditor",
    predication_note: str = "",
    response_days: int = 14,
) -> bytes:
    """
    Generate client evidence requisition list PDF based on fired flags.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36
    )
    
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=colors.HexColor('#1F497D'),
        spaceAfter=6
    )
    
    subtitle_style = ParagraphStyle(
        'DocSubTitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#555555'),
        spaceAfter=12
    )
    
    section_style = ParagraphStyle(
        'SectionHeader',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=colors.HexColor('#1F497D'),
        spaceBefore=10,
        spaceAfter=6
    )
    
    body_style = ParagraphStyle(
        'BodyDark',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=colors.HexColor('#222222')
    )
    
    bold_body_style = ParagraphStyle(
        'BoldBody',
        parent=body_style,
        fontName='Helvetica-Bold'
    )
    
    callout_style = ParagraphStyle(
        'Callout',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor('#771111')
    )

    story = []

    # 0. Firm letterhead line
    if firm_name:
        firm_style = ParagraphStyle(
            'FirmLine', parent=styles['Normal'], fontName='Times-Bold', fontSize=13,
            leading=16, textColor=colors.HexColor('#000099'), alignment=1, spaceAfter=2)
        story.append(Paragraph(firm_name, firm_style))
        story.append(HRFlowable(width="100%", thickness=0.8, color=colors.black,
                                spaceBefore=2, spaceAfter=12))

    # 1. Header & Formal Addressee
    story.append(Paragraph("FORENSIC AUDIT EVIDENCE REQUISITION LIST", title_style))
    story.append(Paragraph("Formal Request for Information & Records under SA 240 / FAIS 130", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#1F497D'), spaceBefore=2, spaceAfter=10))
    
    meta_text = f"""
    <b>To:</b> {client_name}<br/>
    <b>Date of Issue:</b> {datetime.date.today().strftime('%d %B %Y')}<br/>
    <b>Engagement Ref:</b> {engagement_ref}<br/>
    <b>Response Required By:</b> {(datetime.date.today() + datetime.timedelta(days=response_days)).strftime('%d %B %Y')}<br/>
    <b>Risk Classification:</b> <font color="{'red' if scoring_result.get('bucket') == 'RED' else ('#B8860B' if scoring_result.get('bucket') == 'YELLOW' else '#1E8449')}"><b>{scoring_result.get('bucket')} — entity risk score {scoring_result.get('entity_score')} of 100</b></font>
    """
    story.append(Paragraph(meta_text, body_style))
    story.append(Spacer(1, 10))
    
    # Notice & Statutory Framework
    intro_text = (
        "<b>Confidential & Privileged Audit Requisition:</b><br/>"
        "Following initial analytical review and preliminary risk scoring across the financial years under review, "
        "the following specific books, registers, vouchers, electronic databases, and third-party records are required to be "
        "produced to the audit team. These requisitions correspond directly to specific statistical exceptions, structural red flags, "
        "and analytical variances identified during the automated review."
    )
    story.append(Paragraph(intro_text, body_style))
    story.append(Spacer(1, 8))

    if predication_note:
        story.append(Paragraph("<b>Predication for this review:</b>", bold_body_style))
        story.append(Paragraph(f"<i>{predication_note}</i>", body_style))
        story.append(Spacer(1, 10))

    story.append(Paragraph("<b>Records requisitioned</b>", section_style))
    
    # 2. Extract Requisitions from Fired Exceptions
    scored_df = scoring_result.get("scored_exceptions", pd.DataFrame())
    
    # Map rule categories to evidence requests
    requisition_items = []
    
    if not scored_df.empty:
        fired_rules = set(scored_df["rule_id"].unique())
        
        # General vouchers / day book if suspense, turnover or circular trades fired
        daybook_reasons = []
        if "TB-03" in fired_rules:
            susp_rows = scored_df[scored_df["rule_id"] == "TB-03"]
            daybook_reasons.append(f"closing balance in {susp_rows.iloc[0]['subject']} ({susp_rows.iloc[0]['fy']})")
        if "TB-07" in fired_rules or "LG-07" in fired_rules or "TB-14" in fired_rules:
            circ_rows = scored_df[scored_df["rule_id"].isin(["TB-07", "LG-07", "TB-14"])]
            daybook_reasons.append(f"high-turnover squaring to nil in {circ_rows.iloc[0]['subject']}")
        if daybook_reasons:
            requisition_items.append((
                "General Day Book & Electronic Voucher Register",
                "Full period transaction dumps with voucher numbers, narrations, posting timestamps, and contra ledgers.",
                f"In connection with {'; and '.join(daybook_reasons)}."
            ))
            
        # Vendor / Creditor onboarding files if duplicate creditors or personal names fired
        if any(r in fired_rules for r in ["TB-06", "TB-08", "LG-01"]):
            dup_rows = scored_df[scored_df["rule_id"].isin(["TB-06", "TB-08", "LG-01"])]
            subjects = ", ".join(dup_rows["subject"].head(3).tolist())
            requisition_items.append((
                "Vendor Master Files, PAN/GSTIN Records & Contracts",
                "Vendor onboarding documentation, GST registration certificates, bank confirmation letters, and signed agreements.",
                f"Required in relation to {subjects} (Rules: {', '.join(dup_rows['rule_id'].unique())})."
            ))
            
        # Debtor confirmations & dispatch proofs if receivables inflated or stagnant
        if any(r in fired_rules for r in ["FS-04", "LG-05", "MS-01", "LG-10"]):
            rec_rows = scored_df[scored_df["rule_id"].isin(["FS-04", "LG-05", "MS-01", "LG-10"])]
            requisition_items.append((
                "Trade Receivables Ageing, E-Way Bills & Delivery Proofs",
                "Itemised invoice-wise debtor ageing report, proof of dispatch (transporter lorry receipts, e-Way bills), and post-period collection records.",
                f"Motivated by {rec_rows.iloc[0]['detail']} (Rules: {', '.join(rec_rows['rule_id'].unique())})."
            ))
            
        # CWIP / Fixed Asset inspection & contractor bills
        if any(r in fired_rules for r in ["FS-08", "FS-09", "FS-10"]):
            fa_rows = scored_df[scored_df["rule_id"].isin(["FS-08", "FS-09", "FS-10"])]
            requisition_items.append((
                "Fixed Asset Register, Project Progress Reports & Valuer Certificates",
                "Itemised physical fixed asset register, architect / engineer completion certificates for CWIP, and equipment purchase invoices.",
                f"Motivated by capex additions / CWIP growth: {fa_rows.iloc[0]['detail']}."
            ))
            
        # Cash count sheets & bank statements
        if any(r in fired_rules for r in ["TB-10", "TB-02", "FS-01", "MS-03"]):
            cash_rows = scored_df[scored_df["rule_id"].isin(["TB-10", "TB-02", "FS-01", "MS-03"])]
            requisition_items.append((
                "Physical Cash Verification Certificates & Bank Statements",
                "Certified surprise cash count sheets as of balance sheet date, bank reconciliation statements (BRS), and direct bank confirmation letters.",
                f"Required in connection with {cash_rows.iloc[0]['detail']}."
            ))
            
        # Related party register & board approvals
        if any(r in fired_rules for r in ["TB-11", "FS-11"]):
            rp_rows = scored_df[scored_df["rule_id"].isin(["TB-11", "FS-11"])]
            requisition_items.append((
                "Register of Contracts / Related Parties (Sec 189) & Transfer Pricing Docs",
                "Board and Audit Committee approval resolutions, transfer pricing study, and arm's length benchmarking reports.",
                f"Motivated by {rp_rows.iloc[0]['detail']}."
            ))
    else:
        requisition_items.append((
            "Standard General Ledger & Trial Balance Backing",
            "Routine transaction listings for annual statutory audit verification.",
            "Standard procedural sampling."
        ))

    # Build Requisition Table
    table_data = [
        [
            Paragraph("<b>#</b>", bold_body_style),
            Paragraph("<b>Document / Record Category</b>", bold_body_style),
            Paragraph("<b>Detailed Description & Scope</b>", bold_body_style),
            Paragraph("<b>Motivating Forensic Finding</b>", bold_body_style)
        ]
    ]
    
    for idx, (doc_name, scope, motive) in enumerate(requisition_items, 1):
        table_data.append([
            Paragraph(str(idx), body_style),
            Paragraph(f"<b>{doc_name}</b>", body_style),
            Paragraph(scope, body_style),
            Paragraph(f"<i>{motive}</i>", callout_style)
        ])
        
    t = Table(table_data, colWidths=[20, 140, 180, 180])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#EAEFF5')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#1F497D')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CCCCCC')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#FBFBFB')]),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    
    story.append(t)
    story.append(Spacer(1, 15))
    
    # Mandatory disclaimer banner
    disclaimer = (
        "<b>IMPORTANT NOTICE:</b> Indicators are not evidence. This requisition establishes predication "
        "for further examination; it does not conclude that fraud has occurred."
    )
    story.append(Paragraph(disclaimer, callout_style))
    story.append(Spacer(1, 15))
    
    # Signature block
    story.append(HRFlowable(width="100%", thickness=0.6, color=colors.HexColor('#CCCCCC'),
                            spaceBefore=4, spaceAfter=14))

    sig_data = [[
        Paragraph(
            "<b>Requisitioned by</b><br/><br/><br/>"
            "_______________________________<br/>"
            f"{operator}<br/>"
            f"{firm_name or 'Engagement Team'}<br/>"
            "Authorised Signatory",
            body_style),
        Paragraph(
            "<b>Received on behalf of the entity</b><br/><br/><br/>"
            "_______________________________<br/>"
            "Name &amp; Designation<br/>"
            "Date: ____ / ____ / ________<br/>"
            "Entity seal",
            body_style),
    ]]
    sig_tbl = Table(sig_data, colWidths=[260, 260])
    sig_tbl.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(sig_tbl)
    
    def _footer(canvas, doc_):
        canvas.saveState()
        canvas.setFont('Helvetica', 7.5)
        canvas.setFillColor(colors.HexColor('#777777'))
        canvas.drawString(36, 22, f"Evidence Requisition List  |  {engagement_ref}  |  Confidential & Privileged")
        canvas.drawRightString(A4[0] - 36, 22, f"Page {doc_.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buffer.getvalue()
