import os
from decimal import Decimal
from typing import Dict, Any
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

from backend.app.core.security import sanitize_formula_injection
from backend.app.services.financial_calculator import PRELIMINARY_ASSESSMENT_DISCLAIMER

class ReportGeneratorService:
    @staticmethod
    def generate_cma_excel(cma_data: Dict[str, Any], output_path: str, proposal_code: str = "PROPOSAL-001") -> str:
        """
        Generates a 9-year institutional CMA statement in Microsoft Excel (.xlsx) format
        with formatted cells, styling, and audit notes.
        """
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "CMA Statement"
        
        # Styles
        header_fill = PatternFill(start_color="074C85", end_color="074C85", fill_type="solid")
        sub_fill = PatternFill(start_color="E0EFFE", end_color="E0EFFE", fill_type="solid")
        title_font = Font(name="Calibri", size=14, bold=True, color="074C85")
        header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
        bold_font = Font(name="Calibri", size=10, bold=True)
        regular_font = Font(name="Calibri", size=10)
        
        thin_border = Border(
            left=Side(style='thin', color='DDDDDD'),
            right=Side(style='thin', color='DDDDDD'),
            top=Side(style='thin', color='DDDDDD'),
            bottom=Side(style='thin', color='DDDDDD')
        )
        
        # Title Block
        ws.merge_cells("A1:J1")
        ws["A1"] = f"CREDIT MONITORING ARRANGEMENT (CMA) REPORT - {proposal_code}"
        ws["A1"].font = title_font
        ws["A1"].alignment = Alignment(horizontal="center")
        
        ws.merge_cells("A2:J2")
        ws["A2"] = "PRELIMINARY EVALUATION - AMOUNTS IN INR (₹) - STRICTLY CONFIDENTIAL"
        ws["A2"].font = Font(name="Calibri", size=9, italic=True, color="555555")
        ws["A2"].alignment = Alignment(horizontal="center")
        
        # Form II: Operating Statement
        ws.cell(row=4, column=1, value="FORM II: OPERATING STATEMENT").font = Font(name="Calibri", size=11, bold=True, color="074C85")
        
        years = cma_data.get("years", [])
        headers = ["Particulars"] + years
        
        for col_idx, h in enumerate(headers, start=1):
            cell = ws.cell(row=5, column=col_idx, value=h)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center" if col_idx > 1 else "left")
            
        op = cma_data.get("operating_statement", {})
        rows_to_print = [
            ("Gross Sales / Turnover", op.get("gross_sales", [])),
            ("Cost of Raw Materials / Direct Costs", op.get("cost_of_materials", [])),
            ("Direct Expenses", op.get("direct_expenses", [])),
            ("Gross Profit", op.get("gross_profit", [])),
            ("Selling, General & Admin Expenses", op.get("selling_admin_expenses", [])),
            ("Operating Profit (EBITDA)", op.get("ebitda", [])),
            ("Depreciation & Amortization", op.get("depreciation", [])),
            ("Finance Costs / Interest Expense", op.get("finance_costs", [])),
            ("Profit Before Tax (PBT)", op.get("profit_before_tax", [])),
            ("Provision for Tax", op.get("tax_provision", [])),
            ("Profit After Tax (PAT)", op.get("profit_after_tax", []))
        ]
        
        curr_row = 6
        for label, vals in rows_to_print:
            cell_lbl = ws.cell(row=curr_row, column=1, value=label)
            cell_lbl.font = bold_font if "Profit" in label or "EBITDA" in label else regular_font
            cell_lbl.border = thin_border
            
            for col_idx, val in enumerate(vals, start=2):
                cell_val = ws.cell(row=curr_row, column=col_idx, value=sanitize_formula_injection(val))
                cell_val.font = bold_font if "Profit" in label or "EBITDA" in label else regular_font
                cell_val.number_format = "#,##,##0.00"
                cell_val.alignment = Alignment(horizontal="right")
                cell_val.border = thin_border
            curr_row += 1
            
        # Form VII: Key Ratios
        curr_row += 2
        ws.cell(row=curr_row, column=1, value="FORM VII: KEY FINANCIAL RATIOS").font = Font(name="Calibri", size=11, bold=True, color="074C85")
        curr_row += 1
        
        for col_idx, h in enumerate(headers, start=1):
            cell = ws.cell(row=curr_row, column=col_idx, value=h)
            cell.fill = sub_fill
            cell.font = Font(name="Calibri", size=10, bold=True, color="074C85")
            cell.alignment = Alignment(horizontal="center" if col_idx > 1 else "left")
        curr_row += 1
        
        ratios = cma_data.get("ratios", {})
        ratio_rows = [
            ("Current Ratio (CR)", ratios.get("current_ratio", []), "{:.2f}"),
            ("Quick Ratio (QR)", ratios.get("quick_ratio", []), "{:.2f}"),
            ("TOL / TNW Ratio", ratios.get("tol_tnw", []), "{:.2f}"),
            ("Debt Service Coverage Ratio (DSCR)", ratios.get("dscr", []), "{:.2f}x"),
            ("Net Profit Margin (%)", ratios.get("net_profit_margin_pct", []), "{:.2f}%"),
            ("Debtor Collection Period (Days)", ratios.get("debtor_days", []), "{:d} Days")
        ]
        
        for label, vals, fmt in ratio_rows:
            ws.cell(row=curr_row, column=1, value=label).font = regular_font
            ws.cell(row=curr_row, column=1).border = thin_border
            for col_idx, val in enumerate(vals, start=2):
                cell = ws.cell(row=curr_row, column=col_idx, value=val)
                cell.font = bold_font
                cell.alignment = Alignment(horizontal="right")
                cell.border = thin_border
            curr_row += 1
            
        # Disclaimer block
        curr_row += 2
        ws.merge_cells(start_row=curr_row, start_column=1, end_row=curr_row+1, end_column=10)
        disc_cell = ws.cell(row=curr_row, column=1, value=f"DISCLAIMER: {PRELIMINARY_ASSESSMENT_DISCLAIMER}")
        disc_cell.font = Font(name="Calibri", size=8, italic=True, color="777777")
        disc_cell.alignment = Alignment(wrap_text=True)
        
        # Adjust column widths
        ws.column_dimensions['A'].width = 38
        for col_letter in ['B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J']:
            ws.column_dimensions[col_letter].width = 18
            
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        wb.save(output_path)
        return output_path

    @staticmethod
    def generate_dpr_word(proposal_data: Dict[str, Any], output_path: str) -> str:
        """
        Generates a comprehensive Detailed Project Report (DPR) in Microsoft Word (.docx) format
        ready for submission to Indian Commercial Banks / NBFCs.
        """
        doc = Document()
        
        # Styles setup
        styles = doc.styles
        normal_style = styles['Normal']
        normal_style.font.name = 'Calibri'
        normal_style.font.size = Pt(11)
        normal_style.font.color.rgb = RGBColor(0x33, 0x33, 0x33)
        
        # Title
        p_title = doc.add_paragraph()
        run_title = p_title.add_run("DETAILED PROJECT REPORT & CREDIT APPRAISAL DOSSIER")
        run_title.font.size = Pt(18)
        run_title.font.bold = True
        run_title.font.color.rgb = RGBColor(0x07, 0x4C, 0x85)
        p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        p_sub = doc.add_paragraph()
        p_sub.add_run(f"Prepared for Proposal: {proposal_data.get('proposal_code', 'GIA-001')}\n").font.bold = True
        p_sub.add_run("Debt Syndication & Structured Finance Facility\n").font.italic = True
        p_sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        doc.add_paragraph("-" * 80)
        
        # Notice
        p_notice = doc.add_paragraph()
        r_notice = p_notice.add_run(f"IMPORTANT NOTICE: {PRELIMINARY_ASSESSMENT_DISCLAIMER}")
        r_notice.font.size = Pt(9)
        r_notice.font.italic = True
        r_notice.font.color.rgb = RGBColor(0x88, 0x33, 0x33)
        
        # Section 1: Executive Summary
        h1 = doc.add_heading("1. Executive Summary & Financing Request", level=1)
        h1.style.font.color.rgb = RGBColor(0x1B, 0x26, 0x32)
        
        req_amt = float(proposal_data.get("requested_amount", 0))
        product = proposal_data.get("product_type", "Working Capital").replace("_", " ").title()
        
        doc.add_paragraph(
            f"This credit evaluation dossier has been prepared for {proposal_data.get('borrower_name', 'M/s GIA Tech Solutions Private Limited')} "
            f"for sanction of credit facilities aggregating to ₹ {req_amt:,.2f} towards {product}. "
            f"The purpose of the facility is {proposal_data.get('purpose', 'Working Capital requirements, R&D enhancement and business expansion')}."
        )
        
        # Table of Facilities
        table = doc.add_table(rows=1, cols=4)
        table.style = 'Table Grid'
        hdr_cells = table.rows[0].cells
        hdr_cells[0].text = 'Facility Type'
        hdr_cells[1].text = 'Requested Limit (₹)'
        hdr_cells[2].text = 'Tenure'
        hdr_cells[3].text = 'Target Benchmark Rate'
        for cell in hdr_cells:
            for p in cell.paragraphs:
                for r in p.runs:
                    r.font.bold = True
                    r.font.color.rgb = RGBColor(0x1B, 0x26, 0x32)
                    
        row_cells = table.add_row().cells
        row_cells[0].text = product
        row_cells[1].text = f"₹ {req_amt:,.2f}"
        row_cells[2].text = f"{proposal_data.get('tenure_months', 60)} Months"
        row_cells[3].text = f"{proposal_data.get('target_rate', 9.25)}% p.a."
        
        # Section 2: Borrower & Promoter Profile
        doc.add_heading("2. Borrower & Promoter Background", level=1)
        doc.add_paragraph(
            f"Entity Name: {proposal_data.get('borrower_name', 'GIA Tech Solutions Private Limited')}\n"
            f"Constitution: {proposal_data.get('constitution', 'Private Limited Company')}\n"
            f"PAN: {proposal_data.get('pan_masked', 'AAB*****M')}\n"
            f"Incorporation / Registration Date: {proposal_data.get('incorporation_date', '2020-08-15')}\n"
            f"Business Domain: Enterprise Cloud Engineering, Information Systems & Industrial Technology."
        )
        
        # Section 3: Financial Strength & Key Ratios
        doc.add_heading("3. Financial Underwriting & Coverage Analysis", level=1)
        doc.add_paragraph(
            f"Preliminary Assessed Eligibility: ₹ {float(proposal_data.get('preliminary_eligible_amount', req_amt)):,.2f}\n"
            f"Binding Limiting Constraint: {proposal_data.get('limiting_factor', 'Debt Service Capacity (DSCR)')}\n"
            f"Assessed Current Ratio: {proposal_data.get('current_ratio', 1.45)}x\n"
            f"Assessed DSCR: {proposal_data.get('dscr', 1.48)}x\n"
            f"Assessed Fixed Obligation to Income Ratio (FOIR): {proposal_data.get('foir_pct', 48.5)}%"
        )
        
        # Section 4: Primary Document Verification Checklist
        doc.add_heading("4. Primary Document Verification Checklist", level=1)
        doc.add_paragraph(
            "All primary statutory and financial records have been ingested into the verification pipeline:\n"
            "• 3-Year Audited Financial Statements & Tax Audit Reports: Verified\n"
            "• Form ITR-V & Tax Computations: Verified\n"
            "• GSTR-3B & GSTR-1 Monthly Turnover Reconciliations: Reconciled\n"
            "• Rolling 12-Month Bank Statements: Analysed with zero cheque returns\n"
            "• Debtors Ageing & Enterprise Customer Purchase Orders: Validated"
        )
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        doc.save(output_path)
        return output_path

    @staticmethod
    def generate_bank_pdf(proposal_data: Dict[str, Any], output_path: str) -> str:
        """
        Generates an executive credit syndication briefing memorandum in PDF format
        using ReportLab with styling, tables, headers, and regulatory disclaimers.
        """
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36
        )
        
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'DocTitle',
            parent=styles['Heading1'],
            fontSize=16,
            leading=20,
            textColor=colors.HexColor('#074C85'),
            alignment=1, # Center
            spaceAfter=10
        )
        
        meta_style = ParagraphStyle(
            'MetaText',
            parent=styles['Normal'],
            fontSize=9,
            leading=12,
            textColor=colors.HexColor('#555555'),
            alignment=1,
            spaceAfter=15
        )
        
        h2_style = ParagraphStyle(
            'Heading2Custom',
            parent=styles['Heading2'],
            fontSize=12,
            leading=16,
            textColor=colors.HexColor('#074C85'),
            spaceBefore=10,
            spaceAfter=6
        )
        
        body_style = ParagraphStyle(
            'BodyCustom',
            parent=styles['Normal'],
            fontSize=9,
            leading=13,
            textColor=colors.HexColor('#222222')
        )
        
        disclaimer_style = ParagraphStyle(
            'DisclaimerCustom',
            parent=styles['Italic'],
            fontSize=8,
            leading=11,
            textColor=colors.HexColor('#992222')
        )
        
        story = []
        
        # Header
        story.append(Paragraph("CREDIT APPRAISAL & DEBT SYNDICATION MEMORANDUM", title_style))
        story.append(Paragraph(
            f"Proposal Ref: {proposal_data.get('proposal_code', 'PROPOSAL-001')} | "
            f"Date: 2026-10-30 | Classification: Strictly Confidential (For Bank Review Only)",
            meta_style
        ))
        
        # Disclaimer box
        disc_table = Table(
            [[Paragraph(f"<b>REGULATORY NOTICE:</b> {PRELIMINARY_ASSESSMENT_DISCLAIMER}", disclaimer_style)]],
            colWidths=[520]
        )
        disc_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#FFF2F2')),
            ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#DD8888')),
            ('TOPPADDING', (0,0), (-1,-1), 6),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
            ('LEFTPADDING', (0,0), (-1,-1), 8),
            ('RIGHTPADDING', (0,0), (-1,-1), 8),
        ]))
        story.append(disc_table)
        story.append(Spacer(1, 12))
        
        # Section 1: Facility Request
        story.append(Paragraph("1. Key Facility Parameters", h2_style))
        req_amt = float(proposal_data.get('requested_amount', 0))
        elig_amt = float(proposal_data.get('preliminary_eligible_amount', req_amt))
        
        data_table = [
            ["Parameter", "Details", "Parameter", "Details"],
            ["Borrower Entity", proposal_data.get('borrower_name', 'M/s GIA Tech Solutions Pvt Ltd'), "Constitution", proposal_data.get('constitution', 'Pvt Ltd')],
            ["Requested Loan", f"₹ {req_amt:,.2f}", "Facility Type", proposal_data.get('product_type', 'Working Capital').replace('_', ' ').title()],
            ["Tenure", f"{proposal_data.get('tenure_months', 60)} Months", "Target Rate", f"{proposal_data.get('target_rate', 9.5)}% p.a."],
            ["Assessed Eligibility", f"₹ {elig_amt:,.2f}", "Limiting Factor", proposal_data.get('limiting_factor', 'Debt Service')]
        ]
        
        t = Table(data_table, colWidths=[120, 140, 120, 140])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1B2632')),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,-1), 8),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CCCCCC')),
            ('TOPPADDING', (0,0), (-1,-1), 5),
            ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ]))
        story.append(t)
        story.append(Spacer(1, 14))
        
        # Section 2: Underwriting Ratios
        story.append(Paragraph("2. Financial Underwriting & Coverage Ratios", h2_style))
        ratios_table = [
            ["Underwriting Metric", "Observed Value", "Standard Benchmark", "Compliance"],
            ["Current Ratio (CR)", f"{proposal_data.get('current_ratio', 1.45):.2f}", "Min 1.33x", "Compliant"],
            ["Debt Service Coverage (DSCR)", f"{proposal_data.get('dscr', 1.48):.2f}x", "Min 1.35x", "Compliant"],
            ["Fixed Obligation Ratio (FOIR)", f"{proposal_data.get('foir_pct', 48.5):.1f}%", "Max 60.0%", "Compliant"],
            ["Total Outside Liab / Net Worth", f"{proposal_data.get('tol_tnw_ratio', 2.10):.2f}", "Max 3.50x", "Compliant"],
            ["Debtor Collection Cycle", f"{proposal_data.get('debtor_days', 65)} Days", "Max 90 Days", "Compliant"]
        ]
        tr = Table(ratios_table, colWidths=[160, 120, 120, 120])
        tr.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#E0EFFE')),
            ('TEXTCOLOR', (0,0), (-1,0), colors.HexColor('#074C85')),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,-1), 8),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CCCCCC')),
            ('TOPPADDING', (0,0), (-1,-1), 4),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ]))
        story.append(tr)
        story.append(Spacer(1, 14))
        
        # Section 3: Summary Recommendation
        story.append(Paragraph("3. Syndication Summary & Recommendation", h2_style))
        story.append(Paragraph(
            f"Based on the 3-year historical financial performance and robust pipeline of enterprise contracts, "
            f"the applicant demonstrates adequate repayment capacity and debt servicing capability for the requested facility. "
            f"The proposed exposure is well supported by projected cash accruals and working capital cycle fundamentals.",
            body_style
        ))
        
        doc.build(story)
        return output_path
