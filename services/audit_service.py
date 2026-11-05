"""
LexSecure India Pro - Audit Defense Dossier & Cryptographic Chain Service
Generates tamper-evident audit verification certificates and compliance dossiers
"""

import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List
from database.db_engine import DatabaseEngine
from models.entities import TamperAuditLog, StatutoryCalendarEvent, ComplianceTask, Document

class AuditDefenseService:
    def __init__(self, db_engine: DatabaseEngine = None):
        self.db = db_engine or DatabaseEngine.get_instance()

    def verify_audit_integrity(self, organization_id: int = 1) -> Dict[str, Any]:
        """
        Validates the SHA-256 chained hash for all audit logs.
        """
        is_valid, count, broken_id = self.db.verify_audit_chain(organization_id)
        last_hash = self.db.get_last_audit_hash(organization_id)
        return {
            "is_valid": is_valid,
            "total_records": count,
            "broken_at_id": broken_id,
            "latest_head_hash": last_hash,
            "verified_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

    def generate_defense_dossier_pdf(self, output_path: str, organization_id: int = 1) -> str:
        """
        Generates a formal, printable Legal & Regulatory Compliance Defense Dossier PDF.
        """
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.lib import colors
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

            doc = SimpleDocTemplate(
                output_path,
                pagesize=letter,
                rightMargin=36,
                leftMargin=36,
                topMargin=36,
                bottomMargin=36
            )

            styles = getSampleStyleSheet()
            title_style = ParagraphStyle(
                'TitleStyle',
                parent=styles['Heading1'],
                fontSize=20,
                leading=24,
                textColor=colors.HexColor("#0F172A"),
                spaceAfter=6
            )
            subtitle_style = ParagraphStyle(
                'SubStyle',
                parent=styles['Normal'],
                fontSize=10,
                leading=14,
                textColor=colors.HexColor("#475569"),
                spaceAfter=15
            )
            heading_style = ParagraphStyle(
                'HeadStyle',
                parent=styles['Heading2'],
                fontSize=13,
                leading=16,
                textColor=colors.HexColor("#0D9488"),
                spaceBefore=12,
                spaceAfter=6
            )
            body_style = ParagraphStyle(
                'BodyStyle',
                parent=styles['Normal'],
                fontSize=9,
                leading=12,
                textColor=colors.HexColor("#1E293B")
            )
            hash_style = ParagraphStyle(
                'HashStyle',
                parent=styles['Normal'],
                fontSize=7,
                leading=9,
                fontName="Courier",
                textColor=colors.HexColor("#0284C7")
            )

            story = []

            # Header
            story.append(Paragraph("<b>LEXSECURE INDIA PRO — REGULATORY COMPLIANCE DEFENSE DOSSIER</b>", title_style))
            story.append(Paragraph(
                f"Generated for Board & Statutory Regulators (MCA / RBI / DGFT / DPDPB) | Generated: {datetime.now().strftime('%d %B %Y, %H:%M:%S IST')}",
                subtitle_style
            ))
            story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0D9488"), spaceAfter=12))

            # Cryptographic Integrity Certificate
            integrity = self.verify_audit_integrity(organization_id)
            status_text = "<font color='#10B981'><b>VERIFIED [CRYPTOGRAPHIC CHAIN INTACT]</b></font>" if integrity["is_valid"] else "<font color='#EF4444'><b>TAMPER DETECTED</b></font>"

            cert_data = [
                [Paragraph("<b>Cryptographic Verification Status</b>", body_style), Paragraph(status_text, body_style)],
                [Paragraph("<b>Audit Trail Chain Algorithm</b>", body_style), Paragraph("SHA-256 Chained Event Hashing", body_style)],
                [Paragraph("<b>Total Immutable Event Records</b>", body_style), Paragraph(str(integrity["total_records"]), body_style)],
                [Paragraph("<b>Current Chain Head Hash</b>", body_style), Paragraph(f"<code>{integrity['latest_head_hash']}</code>", hash_style)],
            ]
            cert_table = Table(cert_data, colWidths=[200, 340])
            cert_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
                ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#CBD5E1")),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
            ]))
            story.append(cert_table)
            story.append(Spacer(1, 14))

            # Statutory Calendar Obligations
            story.append(Paragraph("<b>1. Statutory Compliance Filings & Deadlines (MCA, RBI, Labour, Tax)</b>", heading_style))
            events = StatutoryCalendarEvent.get_by_entity(1)
            event_data = [["Authority", "Statutory Filing", "Due Date", "Frequency", "Statutory Penalty Risk"]]
            for ev in events[:6]:
                event_data.append([
                    ev.statutory_body,
                    ev.compliance_name,
                    ev.due_date,
                    ev.recurring_freq,
                    ev.penalty_clause[:50] + "..." if len(ev.penalty_clause) > 50 else ev.penalty_clause
                ])
            event_table = Table(event_data, colWidths=[65, 145, 75, 65, 190])
            event_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#0F172A")),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTSIZE', (0, 0), (-1, 0), 8),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                ('FONTSIZE', (0, 1), (-1, -1), 7.5),
            ]))
            story.append(event_table)
            story.append(Spacer(1, 14))

            # Immutable Chained Audit Logs Sample
            story.append(Paragraph("<b>2. Tamper-Evident SHA-256 Audit Trail (Most Recent Events)</b>", heading_style))
            logs = TamperAuditLog.get_all(organization_id)[:8]
            log_data = [["Timestamp", "Actor", "Event Type", "Target", "Current SHA-256 Hash"]]
            for log in logs:
                log_data.append([
                    log.timestamp[:19],
                    log.actor_name or "System",
                    log.event_type,
                    f"{log.target_model} #{log.target_id}",
                    Paragraph(f"<code>{log.current_hash[:24]}...</code>", hash_style)
                ])
            log_table = Table(log_data, colWidths=[100, 90, 100, 80, 170])
            log_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1E293B")),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTSIZE', (0, 0), (-1, 0), 8),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                ('FONTSIZE', (0, 1), (-1, -1), 7),
            ]))
            story.append(log_table)

            doc.build(story)
            return output_path
        except Exception as e:
            # Fallback to rich HTML/Text format if PDF generation has issues
            txt_path = str(Path(output_path).with_suffix(".html"))
            return self._generate_html_fallback(txt_path, organization_id)

    def _generate_html_fallback(self, output_path: str, organization_id: int = 1) -> str:
        integrity = self.verify_audit_integrity(organization_id)
        logs = TamperAuditLog.get_all(organization_id)[:10]
        events = StatutoryCalendarEvent.get_by_entity(1)

        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>LexSecure India Pro - Audit Defense Dossier</title>
    <style>
        body {{ font-family: 'Segoe UI', Arial, sans-serif; background: #0F172A; color: #F8FAFC; padding: 24px; }}
        .header {{ border-bottom: 2px solid #0D9488; padding-bottom: 12px; margin-bottom: 20px; }}
        h1 {{ color: #10B981; margin: 0; font-size: 24px; }}
        .card {{ background: #1E293B; border-radius: 8px; padding: 16px; margin-bottom: 20px; border: 1px solid #334155; }}
        table {{ width: 100%; border-collapse: collapse; font-size: 13px; margin-top: 10px; }}
        th, td {{ border: 1px solid #334155; padding: 8px 12px; text-align: left; }}
        th {{ background: #0B1120; color: #38BDF8; }}
        .hash {{ font-family: monospace; color: #38BDF8; font-size: 11px; }}
        .badge {{ background: #10B981; color: white; padding: 4px 8px; border-radius: 4px; font-weight: bold; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>LEXSECURE INDIA PRO — REGULATORY DEFENSE DOSSIER</h1>
        <p>Verified Tamper-Evident Compliance Dossier | Generated {datetime.now().strftime('%d %B %Y, %H:%M:%S IST')}</p>
    </div>
    <div class="card">
        <h3>Cryptographic Chain Certificate</h3>
        <p>Status: <span class="badge">{'VERIFIED & INTACT' if integrity['is_valid'] else 'TAMPER DETECTED'}</span></p>
        <p>Total Cryptographically Chained Events: <b>{integrity['total_records']}</b></p>
        <p>Latest Head SHA-256 Hash: <span class="hash">{integrity['latest_head_hash']}</span></p>
    </div>
    <div class="card">
        <h3>Statutory Obligations</h3>
        <table>
            <tr><th>Authority</th><th>Filing</th><th>Due Date</th><th>Penalty Clause</th></tr>
            {"".join(f"<tr><td>{e.statutory_body}</td><td>{e.compliance_name}</td><td>{e.due_date}</td><td>{e.penalty_clause}</td></tr>" for e in events)}
        </table>
    </div>
    <div class="card">
        <h3>Audit Logs</h3>
        <table>
            <tr><th>Timestamp</th><th>Actor</th><th>Event</th><th>Hash</th></tr>
            {"".join(f"<tr><td>{l.timestamp}</td><td>{l.actor_name}</td><td>{l.event_type}</td><td class='hash'>{l.current_hash[:32]}...</td></tr>" for l in logs)}
        </table>
    </div>
</body>
</html>"""
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html)
        return output_path
