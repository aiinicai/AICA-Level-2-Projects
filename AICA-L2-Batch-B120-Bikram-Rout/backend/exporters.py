import io
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from typing import Dict, Any, List
from datetime import datetime
from .database import get_db
from .reconciliation import calculate_brs, to_decimal

def sanitize_cell(val: Any) -> Any:
    if val is None:
        return ""
    if isinstance(val, (int, float)):
        return val
    s = str(val).strip()
    if s and s[0] in ('=', '+', '-', '@', '\t', '\r'):
        return "'" + s
    return s

def export_brs_excel(account_id: str, period_id: str) -> io.BytesIO:
    """
    Generates multi-sheet Excel file with:
    - Summary & BRS
    - Matched Items
    - Ledger Outstanding
    - Bank Outstanding
    - Aging Analysis
    - Adjustments & Audit Trail
    """
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM bank_accounts WHERE id = ?", (account_id,))
    account = dict(cur.fetchone())

    cur.execute("SELECT * FROM companies WHERE id = ?", (account["company_id"],))
    company = dict(cur.fetchone())

    cur.execute("SELECT * FROM periods WHERE id = ?", (period_id,))
    period = dict(cur.fetchone())

    brs = calculate_brs(account_id, period_id)

    cur.execute("SELECT * FROM transactions WHERE account_id = ? AND period_id = ?", (account_id, period_id))
    all_txs = [dict(r) for r in cur.fetchall()]

    matched_txs = [t for t in all_txs if t["recon_status"] == "Matched"]
    ledger_outstanding = [t for t in all_txs if t["source"] == "Oracle Ledger" and t["recon_status"] in ("Unmatched", "Exception", "Suggested Match")]
    bank_outstanding = [t for t in all_txs if t["source"] == "Bank Statement" and t["recon_status"] in ("Unmatched", "Exception", "Suggested Match")]

    cur.execute("SELECT * FROM audit_logs ORDER BY timestamp DESC LIMIT 100")
    audit_logs = [dict(r) for r in cur.fetchall()]

    wb = openpyxl.Workbook()
    # Remove default sheet
    wb.remove(wb.active)

    # Styles
    navy_header = PatternFill(start_color="0F172A", end_color="0F172A", fill_type="solid")
    teal_sub = PatternFill(start_color="0D9488", end_color="0D9488", fill_type="solid")
    light_gray = PatternFill(start_color="F1F5F9", end_color="F1F5F9", fill_type="solid")
    amber_alert = PatternFill(start_color="FEF3C7", end_color="FEF3C7", fill_type="solid")

    white_bold = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    navy_bold_title = Font(name="Calibri", size=14, bold=True, color="0F172A")
    bold_font = Font(name="Calibri", size=11, bold=True)
    normal_font = Font(name="Calibri", size=10)
    thin_border = Border(
        left=Side(style='thin', color='CBD5E1'),
        right=Side(style='thin', color='CBD5E1'),
        top=Side(style='thin', color='CBD5E1'),
        bottom=Side(style='thin', color='CBD5E1')
    )

    # 1. SUMMARY SHEET
    ws_sum = wb.create_sheet(title="Summary & BRS")
    ws_sum.column_dimensions['A'].width = 35
    ws_sum.column_dimensions['B'].width = 25
    ws_sum.column_dimensions['C'].width = 30

    ws_sum["A1"] = "BANK RECONCILIATION STATEMENT"
    ws_sum["A1"].font = navy_bold_title

    ws_sum["A3"] = "Company Name:"
    ws_sum["B3"] = sanitize_cell(company["name"])
    ws_sum["A4"] = "Bank Name & Branch:"
    ws_sum["B4"] = f"{account['bank_name']} - {account.get('branch', 'Main')}"
    ws_sum["A5"] = "Bank Account (Masked):"
    ws_sum["B5"] = f"•••• {account['account_number'][-4:]}"
    ws_sum["A6"] = "Currency:"
    ws_sum["B6"] = account["currency"]
    ws_sum["A7"] = "Reconciliation Period:"
    ws_sum["B7"] = period["period_name"]
    ws_sum["A8"] = "Period Status:"
    ws_sum["B8"] = period["status"]

    for row in range(3, 9):
        ws_sum[f"A{row}"].font = bold_font
        ws_sum[f"B{row}"].font = normal_font

    ws_sum["A10"] = "Statement Item"
    ws_sum["B10"] = f"Amount ({account['currency']})"
    ws_sum["C10"] = "Notes / Calculation"
    for col in ["A", "B", "C"]:
        ws_sum[f"{col}10"].fill = navy_header
        ws_sum[f"{col}10"].font = white_bold

    brs_rows = [
        ("A. Bank Statement Closing Balance", brs["bank_closing_balance"], "Closing balance confirmed per bank statement"),
        ("Add / Less: Ledger-Only Movements (Outstanding)", brs["ledger_unmatched_sum"], "Timing items not yet cleared at bank"),
        ("   - Outstanding Cheques / Payments", brs["ledger_payments_in_transit"], "Unpresented cheques & outbound wires"),
        ("   - Deposits in Transit", brs["ledger_deposits_in_transit"], "Undeposited cash/cheque collections"),
        ("ADJUSTED BANK BALANCE (A + Movements)", brs["adjusted_bank_balance"], "Formula: Bank Closing + Ledger Movements"),
        ("", "", ""),
        ("B. Oracle General Ledger Closing Balance", brs["ledger_closing_balance"], "Closing balance per Oracle Cash GL"),
        ("Add / Less: Bank-Only Movements (Unrecorded)", brs["bank_unmatched_sum"], "Bank items not yet posted to Oracle"),
        ("   - Bank Charges / Fees", brs["bank_charges"], "Direct debits, fees & maintenance"),
        ("   - Interest / Direct Credits", brs["bank_interest_credits"], "Interest credits & inward transfers"),
        ("ADJUSTED LEDGER BALANCE (B + Movements)", brs["adjusted_ledger_balance"], "Formula: Ledger Closing + Bank Movements"),
        ("", "", ""),
        ("RESIDUAL UNRECONCILED DIFFERENCE", brs["residual_difference"], "Adjusted Bank Balance - Adjusted Ledger Balance"),
        ("RECONCILIATION RESULT", "RECONCILED" if brs["is_reconciled"] else "UNRESOLVED VARIANCE", "Zero residual required for approved lock")
    ]

    r_idx = 11
    for label, val, note in brs_rows:
        ws_sum[f"A{r_idx}"] = label
        ws_sum[f"B{r_idx}"] = sanitize_cell(val) if val != "" else ""
        ws_sum[f"C{r_idx}"] = note

        if "ADJUSTED" in label or "RESIDUAL" in label:
            ws_sum[f"A{r_idx}"].font = bold_font
            ws_sum[f"B{r_idx}"].font = bold_font
            ws_sum[f"A{r_idx}"].fill = light_gray
            ws_sum[f"B{r_idx}"].fill = light_gray
            if "RESIDUAL" in label and val != 0.0:
                ws_sum[f"B{r_idx}"].fill = amber_alert

        if isinstance(val, (int, float)):
            ws_sum[f"B{r_idx}"].number_format = "#,##0.00"

        r_idx += 1

    # Helper function for data tables
    def build_tx_sheet(sheet_title, tx_list):
        ws = wb.create_sheet(title=sheet_title)
        headers = ["Tx ID", "Date", "Source", "Description", "Reference", "Cheque #", "Signed Amount", "Status", "Match Group"]
        for c_idx, h in enumerate(headers, 1):
            cell = ws.cell(row=1, column=c_idx, value=h)
            cell.fill = navy_header
            cell.font = white_bold
            ws.column_dimensions[openpyxl.utils.get_column_letter(c_idx)].width = 18

        ws.column_dimensions['D'].width = 30 # Description wider

        for row_num, t in enumerate(tx_list, 2):
            ws.cell(row=row_num, column=1, value=sanitize_cell(t["id"])).font = normal_font
            ws.cell(row=row_num, column=2, value=sanitize_cell(t["tx_date"])).font = normal_font
            ws.cell(row=row_num, column=3, value=sanitize_cell(t["source"])).font = normal_font
            ws.cell(row=row_num, column=4, value=sanitize_cell(t["description"])).font = normal_font
            ws.cell(row=row_num, column=5, value=sanitize_cell(t.get("reference"))).font = normal_font
            ws.cell(row=row_num, column=6, value=sanitize_cell(t.get("cheque_number"))).font = normal_font
            amt_cell = ws.cell(row=row_num, column=7, value=float(t["signed_amount"]))
            amt_cell.font = normal_font
            amt_cell.number_format = "#,##0.00"
            ws.cell(row=row_num, column=8, value=sanitize_cell(t["recon_status"])).font = normal_font
            ws.cell(row=row_num, column=9, value=sanitize_cell(t.get("match_group_id"))).font = normal_font

    # 2. Matched Items
    build_tx_sheet("Matched Items", matched_txs)
    # 3. Ledger Outstanding
    build_tx_sheet("Ledger Outstanding", ledger_outstanding)
    # 4. Bank Outstanding
    build_tx_sheet("Bank Outstanding", bank_outstanding)

    # 5. Aging Analysis
    ws_age = wb.create_sheet(title="Aging Analysis")
    age_headers = ["Bucket", "Ledger Count", "Ledger Amount", "Bank Count", "Bank Amount", "Gross Exposure"]
    for c_idx, h in enumerate(age_headers, 1):
        c = ws_age.cell(row=1, column=c_idx, value=h)
        c.fill = navy_header
        c.font = white_bold
        ws_age.column_dimensions[openpyxl.utils.get_column_letter(c_idx)].width = 20

    buckets = [("0-30 Days", 0, 30), ("31-60 Days", 31, 60), ("61-90 Days", 61, 90), ("90+ Days", 91, 9999)]
    now_dt = datetime.now()

    for b_idx, (b_name, min_d, max_d) in enumerate(buckets, 2):
        l_subset = []
        for t in ledger_outstanding:
            try:
                days = (now_dt - datetime.strptime(t["tx_date"][:10], "%Y-%m-%d")).days
            except Exception:
                days = 0
            if min_d <= days <= max_d:
                l_subset.append(t)

        b_subset = []
        for t in bank_outstanding:
            try:
                days = (now_dt - datetime.strptime(t["tx_date"][:10], "%Y-%m-%d")).days
            except Exception:
                days = 0
            if min_d <= days <= max_d:
                b_subset.append(t)

        l_amt = sum((float(t["signed_amount"]) for t in l_subset), 0.0)
        b_amt = sum((float(t["signed_amount"]) for t in b_subset), 0.0)
        gross = abs(l_amt) + abs(b_amt)

        ws_age.cell(row=b_idx, column=1, value=b_name).font = bold_font
        ws_age.cell(row=b_idx, column=2, value=len(l_subset)).font = normal_font
        c3 = ws_age.cell(row=b_idx, column=3, value=l_amt)
        c3.number_format = "#,##0.00"
        ws_age.cell(row=b_idx, column=4, value=len(b_subset)).font = normal_font
        c5 = ws_age.cell(row=b_idx, column=5, value=b_amt)
        c5.number_format = "#,##0.00"
        c6 = ws_age.cell(row=b_idx, column=6, value=gross)
        c6.number_format = "#,##0.00"

    # 6. Audit Trail
    ws_aud = wb.create_sheet(title="Audit Trail")
    aud_headers = ["Timestamp", "User", "Action", "Entity Type", "Entity ID", "Reason"]
    for c_idx, h in enumerate(aud_headers, 1):
        c = ws_aud.cell(row=1, column=c_idx, value=h)
        c.fill = navy_header
        c.font = white_bold
        ws_aud.column_dimensions[openpyxl.utils.get_column_letter(c_idx)].width = 22

    for row_num, a in enumerate(audit_logs, 2):
        ws_aud.cell(row=row_num, column=1, value=sanitize_cell(a["timestamp"])).font = normal_font
        ws_aud.cell(row=row_num, column=2, value=sanitize_cell(a["user"])).font = normal_font
        ws_aud.cell(row=row_num, column=3, value=sanitize_cell(a["action"])).font = normal_font
        ws_aud.cell(row=row_num, column=4, value=sanitize_cell(a["entity_type"])).font = normal_font
        ws_aud.cell(row=row_num, column=5, value=sanitize_cell(a["entity_id"])).font = normal_font
        ws_aud.cell(row=row_num, column=6, value=sanitize_cell(a.get("reason"))).font = normal_font

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    conn.close()
    return output

def export_brs_pdf(account_id: str, period_id: str) -> io.BytesIO:
    """
    Generates professional PDF Bank Reconciliation Statement.
    """
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM bank_accounts WHERE id = ?", (account_id,))
    account = dict(cur.fetchone())
    cur.execute("SELECT * FROM companies WHERE id = ?", (account["company_id"],))
    company = dict(cur.fetchone())
    cur.execute("SELECT * FROM periods WHERE id = ?", (period_id,))
    period = dict(cur.fetchone())
    brs = calculate_brs(account_id, period_id)
    conn.close()

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()

    story = []

    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontSize=18,
        leading=22,
        textColor=colors.HexColor('#0F172A'),
        spaceAfter=10
    )

    sub_style = ParagraphStyle(
        'SubTitle',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#475569'),
        spaceAfter=15
    )

    story.append(Paragraph("Bank Reconciliation Statement", title_style))
    story.append(Paragraph(f"<b>Company:</b> {company['name']} &nbsp;|&nbsp; <b>Bank:</b> {account['bank_name']} &nbsp;|&nbsp; <b>Account:</b> •••• {account['account_number'][-4:]} ({account['currency']})<br/><b>Period:</b> {period['period_name']} &nbsp;|&nbsp; <b>Status:</b> {period['status']}", sub_style))

    data = [
        ["Reconciliation Line Item", f"Amount ({account['currency']})", "Explanation"],
        ["Bank Statement Closing Balance", f"{brs['bank_closing_balance']:,.2f}", "Confirmed closing statement balance"],
        ["Add: Ledger Deposits in Transit", f"{brs['ledger_deposits_in_transit']:,.2f}", "Uncredited cash / receipts"],
        ["Less: Outstanding Cheques / Payments", f"{brs['ledger_payments_in_transit']:,.2f}", "Unpresented payments / wires"],
        ["ADJUSTED BANK BALANCE", f"{brs['adjusted_bank_balance']:,.2f}", "Bank Closing + Ledger Unmatched Movements"],
        ["", "", ""],
        ["Oracle GL Closing Balance", f"{brs['ledger_closing_balance']:,.2f}", "Cash GL account closing balance"],
        ["Less: Unrecorded Bank Charges", f"{brs['bank_charges']:,.2f}", "Fees, debits not in Oracle"],
        ["Add: Unrecorded Bank Interest / Credits", f"{brs['bank_interest_credits']:,.2f}", "Direct credits, interest not in Oracle"],
        ["ADJUSTED LEDGER BALANCE", f"{brs['adjusted_ledger_balance']:,.2f}", "Ledger Closing + Bank Unmatched Movements"],
        ["", "", ""],
        ["RESIDUAL UNRECONCILED VARIANCE", f"{brs['residual_difference']:,.2f}", "Adjusted Bank - Adjusted Ledger"],
        ["AUDIT RESULT", "RECONCILED" if brs['is_reconciled'] else "UNRECONCILED VARIANCE", "Zero variance required for approval"]
    ]

    t = Table(data, colWidths=[240, 120, 180])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0F172A')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
        ('BACKGROUND', (0, 4), (-1, 4), colors.HexColor('#F1F5F9')),
        ('FONTNAME', (0, 4), (-1, 4), 'Helvetica-Bold'),
        ('BACKGROUND', (0, 9), (-1, 9), colors.HexColor('#F1F5F9')),
        ('FONTNAME', (0, 9), (-1, 9), 'Helvetica-Bold'),
        ('BACKGROUND', (0, 11), (-1, 11), colors.HexColor('#FEF3C7') if not brs['is_reconciled'] else colors.HexColor('#CCFBF1')),
        ('FONTNAME', (0, 11), (-1, 11), 'Helvetica-Bold'),
        ('FONTNAME', (0, 12), (-1, 12), 'Helvetica-Bold'),
        ('ALIGN', (1, 1), (1, -1), 'RIGHT'),
    ]))

    story.append(t)
    story.append(Spacer(1, 20))
    story.append(Paragraph("<b>Workflow & Certification:</b><br/>Preparer: " + (account.get('preparer') or 'Staff') + " &nbsp;&nbsp;&nbsp;&nbsp; Reviewer: " + (account.get('reviewer') or 'Senior Accountant') + " &nbsp;&nbsp;&nbsp;&nbsp; Approver: " + (account.get('approver') or 'Finance Controller'), sub_style))

    doc.build(story)
    buffer.seek(0)
    return buffer
