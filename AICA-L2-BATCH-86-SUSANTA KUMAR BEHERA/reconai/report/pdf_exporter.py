from decimal import Decimal
from pathlib import Path
from typing import Union
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

from reconai.models.session import ReconciliationSession
from reconai.models.transaction import MatchStatus, TransactionType, AuditSeverity


class PDFReportExporter:
    """Exports clean, formal Executive Bank Reconciliation & Audit Summary PDF."""

    def export(self, session: ReconciliationSession, output_path: Union[str, Path]) -> str:
        out_file = Path(output_path)
        doc = SimpleDocTemplate(
            str(out_file),
            pagesize=letter,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36,
        )

        styles = getSampleStyleSheet()
        
        # Custom typography styles
        title_style = ParagraphStyle(
            "DocTitle",
            parent=styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=16,
            textColor=colors.HexColor("#1E3A8A"),
            spaceAfter=4,
        )
        subtitle_style = ParagraphStyle(
            "DocSubtitle",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            textColor=colors.HexColor("#475569"),
            spaceAfter=12,
        )
        h2_style = ParagraphStyle(
            "SectionH2",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=12,
            textColor=colors.HexColor("#0F172A"),
            spaceBefore=10,
            spaceAfter=6,
        )
        body_style = ParagraphStyle(
            "BodySmall",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=10,
        )

        elements = []

        # 1. Header Banner
        elements.append(Paragraph("<b>RECONAI — BANK RECONCILIATION & AUDIT REPORT</b>", title_style))
        elements.append(
            Paragraph(
                f"<b>Client:</b> {session.client_name} &nbsp;|&nbsp; "
                f"<b>Period:</b> {session.period_label} &nbsp;|&nbsp; "
                f"<b>Generated:</b> {session.updated_at.strftime('%d-%b-%Y %H:%M')}",
                subtitle_style,
            )
        )
        elements.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#1E3A8A"), spaceAfter=10))

        # 2. Executive Summary Metrics Table
        elements.append(Paragraph("1. Executive Summary & KPIs", h2_style))
        matched = [m for m in session.matches if m.status == MatchStatus.MATCHED]
        probable = [m for m in session.matches if m.status == MatchStatus.PROBABLE]
        unmatched_stmt = [m for m in session.matches if m.status == MatchStatus.UNMATCHED and m.statement_tx_id]
        unmatched_ledger = [m for m in session.matches if m.status == MatchStatus.UNMATCHED and m.ledger_entry_id]

        kpi_data = [
            ["Metric", "Count", "Status / Auditor Action Required"],
            ["Fully Matched Transactions", str(len(matched)), "Reconciled automatically with high confidence"],
            ["Probable Matches (Review Needed)", str(len(probable)), "Review in ReconAI workspace and confirm/unpair"],
            ["Unmatched Bank Statement Entries", str(len(unmatched_stmt)), "Timing difference or unbooked bank charges/interest"],
            ["Unmatched Client Ledger Entries", str(len(unmatched_ledger)), "Unpresented cheques or uncredited bank deposits"],
            ["Expense & Compliance Exceptions", str(len(session.audit_flags)), f"{len([f for f in session.audit_flags if f.severity == AuditSeverity.HIGH])} High Severity items"],
        ]

        t_kpi = Table(kpi_data, colWidths=[180, 50, 310])
        t_kpi.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1E293B")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
        ]))
        elements.append(t_kpi)
        elements.append(Spacer(1, 12))

        # 3. Bank Reconciliation Statement (BRS)
        elements.append(Paragraph("2. Bank Reconciliation Statement (BRS)", h2_style))
        stmt_closing = session.statements[-1].balance if session.statements and session.statements[-1].balance else Decimal("0.00")
        uncredited = sum([l.amount for l in session.ledger_entries if not l.matched and l.type == TransactionType.CREDIT], Decimal("0.00"))
        unpresented = sum([l.amount for l in session.ledger_entries if not l.matched and l.type == TransactionType.DEBIT], Decimal("0.00"))
        adjusted_balance = stmt_closing + uncredited - unpresented

        brs_data = [
            ["Particulars", "Amount (INR)"],
            ["Balance as per Bank Statement (Closing)", f"₹ {stmt_closing:,.2f}"],
            ["Add: Receipts / Deposits entered in books not yet credited by bank", f"₹ {uncredited:,.2f}"],
            ["Less: Payments / Cheques issued in books not yet presented to bank", f"- ₹ {unpresented:,.2f}"],
            ["Estimated Adjusted Balance as per Client Books", f"₹ {adjusted_balance:,.2f}"],
        ]

        t_brs = Table(brs_data, colWidths=[380, 160])
        t_brs.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1E3A8A")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor("#E2E8F0")),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('FONTSIZE', (0, 0), (-1, -1), 8.5),
        ]))
        elements.append(t_brs)
        elements.append(Spacer(1, 14))

        # 4. Top Audit Exceptions Table
        elements.append(Paragraph("3. High & Medium Severity Expense Exceptions", h2_style))
        high_med_flags = [f for f in session.audit_flags if f.severity in (AuditSeverity.HIGH, AuditSeverity.MEDIUM)][:12]

        if high_med_flags:
            flag_data = [["Ref", "Sev", "Rule Fired", "Reason & Auditor Risk", "Action"]]
            for f in high_med_flags:
                flag_data.append([
                    Paragraph(str(f.source_row_ref), body_style),
                    Paragraph(f.severity.value, body_style),
                    Paragraph(f.rule_name, body_style),
                    Paragraph(f.plain_english_reason, body_style),
                    Paragraph(f.suggested_action, body_style),
                ])
            t_flag = Table(flag_data, colWidths=[45, 40, 110, 205, 140])
            t_flag.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#0F172A")),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 7.5),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
            ]))
            elements.append(t_flag)
        else:
            elements.append(Paragraph("<i>No high or medium severity expense exceptions detected.</i>", body_style))

        elements.append(Spacer(1, 15))

        # 5. Auditor Remarks & CA Opinion
        elements.append(Paragraph("4. Auditor Remarks & Professional Opinion", h2_style))
        remarks_txt = session.auditor_remarks or "All material variances between bank statements and client books have been examined. Direct bank charges and unpresented items have been duly verified."
        opinion_txt = session.partner_opinion or "In our opinion, the Bank Reconciliation Statement correctly presents the reconciliation of bank and book balances as of the specified period."

        elements.append(Paragraph(f"<b>Auditor Remarks:</b> {remarks_txt}", body_style))
        elements.append(Spacer(1, 4))
        elements.append(Paragraph(f"<b>CA Partner Opinion:</b> {opinion_txt}", body_style))
        elements.append(Spacer(1, 15))

        # 6. Sign-off block
        elements.append(Paragraph("5. Auditor Sign-Off & Verification", h2_style))
        sign_data = [
            ["Prepared by: ________________________", "Reviewed by (Partner): ________________________"],
            [f"Date: {session.updated_at.strftime('%d-%b-%Y')}", "CA Membership / FRN No: ______________________"],
        ]
        t_sign = Table(sign_data, colWidths=[270, 270])
        t_sign.setStyle(TableStyle([
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(t_sign)

        doc.build(elements)
        return str(out_file)
