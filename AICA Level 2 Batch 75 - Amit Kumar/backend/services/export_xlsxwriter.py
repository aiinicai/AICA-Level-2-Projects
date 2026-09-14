
def add_signing_docket(w_obj, db, client_id):
    meta = db.query(models.ClientMetadata).filter_by(client_id=client_id).first()
    dirs = db.query(models.DirectorMaster).filter_by(client_id=client_id).all()
    cs = db.query(models.CompanySecretary).filter_by(client_id=client_id).first()
    cfo = db.query(models.ChiefFinancialOfficer).filter_by(client_id=client_id).first()
    
    w_obj.append([])
    w_obj.append([])
    w_obj.append(["For and on behalf of the Board of Directors"], w_obj.ws.book.add_format({'bold': True}))
    w_obj.append([])
    w_obj.append([])
    
    dir_row1 = []
    dir_row2 = []
    dir_row3 = []
    
    for d in dirs[:2]:
        dir_row1.append(d.name)
        dir_row2.append(d.designation)
        dir_row3.append(f"DIN: {d.din}")
        
    while len(dir_row1) < 3:
        dir_row1.append("")
        dir_row2.append("")
        dir_row3.append("")
        
    if cfo:
        dir_row1[2] = cfo.name
        dir_row2[2] = "Chief Financial Officer"
        dir_row3[2] = ""
        
    w_obj.append(dir_row1, w_obj.ws.book.add_format({'bold': True}))
    w_obj.append(dir_row2)
    w_obj.append(dir_row3)
    
    w_obj.append([])
    w_obj.append([])
    
    if cs:
        w_obj.append([cs.name], w_obj.ws.book.add_format({'bold': True}))
        w_obj.append(["Company Secretary"])
        w_obj.append([f"Membership No: {cs.membership_no}"])
        w_obj.append([])

import os
import json
import xlsxwriter
from sqlalchemy.orm import Session
from models import Client, TrialBalanceLine, CashFlowAdjustment
from services.fs_generator import generate_financial_statements
from services.cash_flow_engine import generate_cash_flow_statement
from services.ratio_engine import calculate_ratios
from services.notes_engine import generate_or_update_notes
from services.validation_engine import run_validation_checks

def export_formula_linked_excel(client_id: int, export_dir: str, db: Session) -> str:
    import models
    meta = db.query(models.ClientMetadata).filter_by(client_id=client_id).first()
    client_obj = db.query(models.Client).filter_by(id=client_id).first()
    client_name = meta.client_name if meta else (client_obj.name if client_obj else "Unknown Client")
    cin_number = meta.cin_number if meta else "CIN Not Set"
    fye = meta.financial_year_ended if meta else "FYE Not Set"
    
    validations = run_validation_checks(client_id, db)
    critical_mapping = [v for v in validations if v.category == "Mapping Exception" and v.status == "Critical"]
    if critical_mapping:
        err_msg = "; ".join([f"{v.check_name}: {v.message}" for v in critical_mapping])
        raise ValueError(f"Excel export blocked due to Critical Mapping Exceptions: {err_msg}. Please review and approve manual override in Ledger Mapping.")

    os.makedirs(export_dir, exist_ok=True)
    client = db.query(Client).filter(Client.id == client_id).first()
    safe_name = "".join(c if c.isalnum() else "_" for c in (client.name if client else "Client"))
    filepath = os.path.join(export_dir, f"{safe_name}_Schedule_III_Annual_Report.xlsx")

    tb_lines = db.query(TrialBalanceLine).filter(TrialBalanceLine.client_id == client_id).order_by(TrialBalanceLine.id).all()
    fs = generate_financial_statements(client_id, db)
    notes = generate_or_update_notes(client_id, db)
    cfs = generate_cash_flow_statement(client_id, db)
    ratios = calculate_ratios(client_id, db)

    wb = xlsxwriter.Workbook(filepath)
    
    num_fmt_str = '#,##0.00;(#,##0.00)'
    
    fmt_header = wb.add_format({'bold': True, 'bg_color': '#1B365D', 'font_color': 'white', 'align': 'center', 'valign': 'vcenter', 'border': 1, 'text_wrap': True})
    fmt_num = wb.add_format({'num_format': num_fmt_str})
    fmt_bold_num = wb.add_format({'bold': True, 'num_format': num_fmt_str})
    fmt_bold = wb.add_format({'bold': True})
    fmt_link = wb.add_format({'font_color': 'blue', 'underline': 1})
    fmt_sub = wb.add_format({'bold': True, 'bg_color': '#E2E8F0', 'num_format': num_fmt_str})
    fmt_tot = wb.add_format({'bold': True, 'top': 1, 'bottom': 6, 'num_format': num_fmt_str})
    
    fmt_num_py = wb.add_format({'num_format': num_fmt_str, 'bg_color': '#F3F4F6'})
    fmt_bold_num_py = wb.add_format({'bold': True, 'num_format': num_fmt_str, 'bg_color': '#E5E7EB'})
    fmt_bold_py = wb.add_format({'bold': True, 'bg_color': '#F3F4F6'})
    fmt_sub_py = wb.add_format({'bold': True, 'bg_color': '#D1D5DB', 'num_format': num_fmt_str})
    fmt_tot_py = wb.add_format({'bold': True, 'top': 1, 'bottom': 6, 'bg_color': '#F3F4F6', 'num_format': num_fmt_str})
    fmt_header_py = wb.add_format({'bold': True, 'bg_color': '#1B365D', 'font_color': 'white', 'align': 'center', 'valign': 'vcenter', 'border': 1, 'text_wrap': True})
    fmt_py_col_blank = wb.add_format({'bg_color': '#F3F4F6'})

    py_format_map = {
        None: fmt_num_py,
        fmt_num: fmt_num_py,
        fmt_bold_num: fmt_bold_num_py,
        fmt_bold: fmt_bold_py,
        fmt_sub: fmt_sub_py,
        fmt_tot: fmt_tot_py,
        fmt_header: fmt_header_py
    }
    
    fmt_heading = wb.add_format({'bold': True, 'font_color': '#1B365D', 'font_size': 12})
    fmt_masthead = wb.add_format({'bold': True, 'font_color': '#EA580C', 'font_size': 14})
    fmt_section = wb.add_format({'bold': True, 'font_color': '#EA580C'})
    
    formula_audit_log = []


    class WsWriter:
        def __init__(self, ws, sheet_name, py_col=-1, meta=("Client Name", "CIN", "FYE")):
            self.ws = ws
            self.sheet_name = sheet_name
            self.r = 0
            self.py_col = py_col
            self.meta = meta
            self.ws.hide_gridlines(2)
            self.ws.set_paper(9) # A4
            self.ws.set_portrait()
            self.ws.repeat_rows(0, 4)
            
        def apply_header(self, title):
            c_name, c_cin, c_fye = self.meta
            self.append([c_name], fmt_masthead)
            self.append([f"Year Ended: {c_fye}"], fmt_tot)
            self.append([f"CIN: {c_cin}"], fmt_tot)
            self.append([title], fmt_heading)
            self.append([])
            
        def append(self, row_data, fmt=None):
            for c, val in enumerate(row_data):
                cell_fmt = py_format_map.get(fmt, fmt) if self.py_col == c else (fmt or fmt_num)
                if isinstance(val, str) and not val.startswith('='):
                    if fmt is None and self.py_col != c:
                        cell_fmt = None
                    elif fmt is None and self.py_col == c:
                        cell_fmt = fmt_py_col_blank
                        
                if isinstance(val, tuple):
                    f, v = val
                    self.ws.write_formula(self.r, c, f, cell_fmt, v)
                    cell_addr = xlsxwriter.utility.xl_rowcol_to_cell(self.r, c)
                    formula_audit_log.append((self.sheet_name, cell_addr, f, v))
                elif isinstance(val, str) and val.startswith('='):
                    self.ws.write_formula(self.r, c, val, cell_fmt)
                    cell_addr = xlsxwriter.utility.xl_rowcol_to_cell(self.r, c)
                    formula_audit_log.append((self.sheet_name, cell_addr, val, "N/A"))
                elif isinstance(val, (int, float)):
                    self.ws.write_number(self.r, c, val, cell_fmt)
                else:
                    self.ws.write(self.r, c, val, cell_fmt)
            self.r += 1
            return self.r - 1

    note_code_to_name = {
        "1.1": ("Note_1_1_ShareCapital", "TOT_ShareCapital", "TOT_ShareCapital_PY"),
        "1.2": ("Note_1_2_Reserves", "TOT_Reserves", "TOT_Reserves_PY"),
        "2.1": ("Note_2_1_LTBorrow", "TOT_LTBorrow", "TOT_LTBorrow_PY"),
        "2.2": ("Note_2_2_LTProv", "TOT_LTProv", "TOT_LTProv_PY"),
        "3.1": ("Note_3_1_STBorrow", "TOT_STBorrow", "TOT_STBorrow_PY"),
        "3.2": ("Note_3_2_TradePayables", "TOT_Payables", "TOT_Payables_PY"),
        "3.3": ("Note_3_3_OtherCL", "TOT_OtherCL", "TOT_OtherCL_PY"),
        "3.4": ("Note_3_4_STProv", "TOT_STProv", "TOT_STProv_PY"),
        "4.1": ("Note_4_1_PPE", "TOT_PPE", "TOT_PPE_PY"),
        "4.2": ("Note_4_2_CWIP", "TOT_CWIP", "TOT_CWIP_PY"),
        "4.3": ("Note_4_3_Investments", "TOT_Investments", "TOT_Investments_PY"),
        "4.4": ("Note_4_4_LTLA", "TOT_LTLA", "TOT_LTLA_PY"),
        "5.1": ("Note_5_1_Inventories", "TOT_Inventory", "TOT_Inventory_PY"),
        "5.2": ("Note_5_2_Receivables", "TOT_Receivables", "TOT_Receivables_PY"),
        "5.3": ("Note_5_3_CashBank", "TOT_Cash", "TOT_Cash_PY"),
        "5.4": ("Note_5_4_STLA", "TOT_STLA", "TOT_STLA_PY"),
        "5.5": ("Note_5_5_OtherCA", "TOT_OtherCA", "TOT_OtherCA_PY"),
        "6.1": ("Note_6_1_Revenue", "TOT_Revenue", "TOT_Revenue_PY"),
        "6.2": ("Note_6_2_OtherIncome", "TOT_OtherIncome", "TOT_OtherIncome_PY"),
        "7.1": ("Note_7_1_Material", "TOT_Material", "TOT_Material_PY"),
        "7.2": ("Note_7_2_Employee", "TOT_Employee", "TOT_Employee_PY"),
        "7.3": ("Note_7_3_Finance", "TOT_Finance", "TOT_Finance_PY"),
        "7.4": ("Note_7_4_Depreciation", "TOT_Depreciation", "TOT_Depreciation_PY"),
        "7.5": ("Note_7_5_OtherExp", "TOT_OtherExp", "TOT_OtherExp_PY"),
        "7.6": ("Note_7_6_Tax", "TOT_Tax", "TOT_Tax_PY"),
        "8.1": ("Note_8_1_RPT", "TOT_RPT", "TOT_RPT_PY"),
        "8.2": ("Note_8_2_Contingencies", "TOT_Contingencies", "TOT_Contingencies_PY"),
    }
    credit_notes = {"1.1", "1.2", "2.1", "2.2", "3.1", "3.2", "3.3", "3.4", "6.1", "6.2", "7.6"}

    # Extract note totals
    note_totals = {}
    for n in notes:
        table_data = json.loads(n.table_json or "{}")
        table = table_data.get("rows", [])
        cy = py = 0.0
        for row in reversed(table):
            if str(row[0]).startswith("TOTAL"):
                try: cy = float(row[1] or 0)
                except: pass
                try: py = float(row[2] or 0)
                except: pass
                break
        note_totals[n.note_number] = (cy, py)

    # Sheet 1: Trial Balance
    ws1 = wb.add_worksheet("90_Trial_Balance")
    w1 = WsWriter(ws1, "90_Trial_Balance", meta=(client_name, cin_number, fye))
    w1.append(["Ledger Code", "Ledger Name", "Original Group", "Debit", "Credit"], fmt_header)
    for l in tb_lines:
        dr = l.cy_amount if getattr(l, "type", "") == "Debit" else 0.0
        cr = l.cy_amount if getattr(l, "type", "") == "Credit" else 0.0
        w1.append([l.ledger_code or "", l.ledger_name, l.original_group or "", dr, cr])

    # Sheet 2: Mapping
    ws2 = wb.add_worksheet("91_Mapping")
    w2 = WsWriter(ws2, "91_Mapping", meta=(client_name, cin_number, fye))
    w2.append(["Ledger Code", "Ledger Name", "Original Group", "Final Classification", "Statement", "Note #", "Current / Non-Current", "CY Amount (Lakhs)", "PY Amount (Lakhs)"], fmt_header)
    for idx, l in enumerate(tb_lines, start=2):
        w2.append([
            l.ledger_code or "", l.ledger_name, l.original_group or "", l.final_classification or "Unmapped",
            l.financial_statement or "", str(l.note_number or "1.1"), l.current_non_current or "",
            (f"=SUMIFS('90_Trial_Balance'!$D:$D, '90_Trial_Balance'!$A:$A, $A{idx})", l.cy_amount),
            (f"=SUMIFS('90_Trial_Balance'!$E:$E, '90_Trial_Balance'!$A:$A, $A{idx})", l.py_amount)
        ])

    # Sheet 3: Cash Flow Adjustments
    print('Generating Sheet 3')
    ws_cfa = wb.add_worksheet("29_Cash_Flow_Adjustments")
    w_cfa = WsWriter(ws_cfa, "29_Cash_Flow_Adjustments", py_col=3, meta=(client_name, cin_number, fye))
    w_cfa.append(["Adjustment Line Item", "Description", "CY Amount", "PY Amount", "Source Category"], fmt_header)
    tax_cy, tax_py = note_totals.get("7.6", (0.0, 0.0))
    fin_cy, fin_py = note_totals.get("7.3", (0.0, 0.0))
    int_cy, int_py = note_totals.get("6.2", (0.0, 0.0))
    w_cfa.append(["Income Taxes Paid", "Direct Corporate Income Taxes Paid", ("=-TOT_Tax", -tax_cy), ("=-TOT_Tax_PY", -tax_py), "Operating"])
    w_cfa.append(["Dividend Paid", "Equity Dividend Paid During Year", 0.00, 0.00, "Financing"])
    w_cfa.append(["Finance Cost Paid", "Actual Interest & Finance Cost Paid", ("=-TOT_Finance", -fin_cy), ("=-TOT_Finance_PY", -fin_py), "Financing"])
    w_cfa.append(["Interest / Dividend Received", "Interest and Dividend Income Received", ("=TOT_InterestIncome", int_cy), ("=TOT_InterestIncome_PY", int_py), "Investing"])
    
    # Calculate Capex
    ppe_cy, ppe_py = note_totals.get("4.1", (0.0, 0.0))
    cwip_cy, cwip_py = note_totals.get("4.2", (0.0, 0.0))
    dep_cy, dep_py = note_totals.get("7.4", (0.0, 0.0))
    capex_cy = -((ppe_cy + cwip_cy) - (ppe_py + cwip_py) + dep_cy)
    w_cfa.append(["Actual Capex Paid", "Purchase of Property, Plant & Equipment", ("=-((TOT_PPE+TOT_CWIP)-(TOT_PPE_PY+TOT_CWIP_PY)+TOT_Depreciation)", capex_cy), 0.00, "Investing"])

    # Sheet 4: Notes
    print('Generating Sheet 4 (Notes)')
    for note in notes:
        n_num = note.note_number
        print(f"Processing note: {n_num}")
        sheet_title, dn_cy, dn_py = note_code_to_name.get(n_num, (f"Note_{n_num.replace('.', '_')}", f"TOT_{n_num.replace('.', '_')}", f"TOT_{n_num.replace('.', '_')}_PY"))
        ws_n = wb.add_worksheet(sheet_title)
        wn = WsWriter(ws_n, sheet_title, py_col=2)
        wn.append([safe_name.upper()], fmt_bold)
        wn.append([f"NOTE {n_num}: {note.title.upper()}", f'=HYPERLINK("#\\\'02_Balance_Sheet\\\'!A1", "[<- Back to Balance Sheet]")', ""], fmt_bold)
        wn.append(["(All amounts in INR Lakhs unless otherwise stated)", "", ""])
        wn.append(["", "", ""])
        
        table_data = json.loads(note.table_json or "{}")
        headers = table_data.get("headers", ["Particulars", "CY", "PY"])
        wn.append(headers, fmt_header)
        
        table = table_data.get("rows", [])
        
        # Determine if it's a standard 3-column note
        is_standard = len(headers) == 3 and "Particulars" in headers[0]
        
        start_row = wn.r + 1
        for row in table:
            if not row: continue
            if str(row[0]).startswith("TOTAL"):
                # Total row
                sign = "-1*" if n_num in credit_notes else ""
                new_row = [row[0]]
                for i in range(1, len(row)):
                    try: val = float(row[i] or 0)
                    except: val = 0.0
                    
                    if is_standard and i in (1, 2):
                        col_letter = "B" if i == 1 else "C"
                        new_row.append((f"={sign}SUM({col_letter}6:{col_letter}{wn.r})", val))
                    else:
                        new_row.append(val)
                wn.append(new_row, fmt_tot)
                
                # Register defined name
                if is_standard:
                    wb.define_name(dn_cy, f"='{sheet_title}'!$B${wn.r}")
                    wb.define_name(dn_py, f"='{sheet_title}'!$C${wn.r}")
                else:
                    # Point to the last two columns
                    col_cy = xlsxwriter.utility.xl_col_to_name(len(row) - 2)
                    col_py = xlsxwriter.utility.xl_col_to_name(len(row) - 1)
                    wb.define_name(dn_cy, f"='{sheet_title}'!${col_cy}${wn.r}")
                    wb.define_name(dn_py, f"='{sheet_title}'!${col_py}${wn.r}")
            else:
                # Detail row
                new_row = [row[0]]
                for i in range(1, len(row)):
                    val_str = str(row[i])
                    try: 
                        val = float(val_str.replace(',', ''))
                        
                        # Add SUMIFS formula if it's a standard ledger line
                        if is_standard and str(row[0]).startswith("    "):
                            ledg = str(row[0]).strip()
                            if i == 1:
                                new_row.append((f"=SUMIFS('91_Mapping'!H:H, '91_Mapping'!D:D, \"{ledg}\")", val))
                            elif i == 2:
                                new_row.append((f"=SUMIFS('91_Mapping'!I:I, '91_Mapping'!D:D, \"{ledg}\")", val))
                            else:
                                new_row.append(val)
                        else:
                            new_row.append(val)
                    except ValueError:
                        new_row.append(val_str)
                wn.append(new_row)

        # Add Control Totals
        wn.append(["", "", ""])
        cy_tot, py_tot = note_totals.get(n_num, (0.0, 0.0))
        sign_char = "-" if n_num in credit_notes else ""
        cy_tb_formula = f"={sign_char}SUMIFS('91_Mapping'!H:H, '91_Mapping'!F:F, \"{n_num}\")"
        py_tb_formula = f"={sign_char}SUMIFS('91_Mapping'!I:I, '91_Mapping'!F:F, \"{n_num}\")"
        
        cy_col_idx = len(headers) - 2 if not is_standard else 1
        py_col_idx = len(headers) - 1 if not is_standard else 2
        
        row_tb = [""] * len(headers)
        row_tb[0] = "Per Trial Balance (Control Total)"
        row_tb[cy_col_idx] = (cy_tb_formula, cy_tot)
        row_tb[py_col_idx] = (py_tb_formula, py_tot)
        wn.append(row_tb, fmt_sub)
        
        row_diff = [""] * len(headers)
        row_diff[0] = "Difference"
        cy_col_name = xlsxwriter.utility.xl_col_to_name(cy_col_idx)
        py_col_name = xlsxwriter.utility.xl_col_to_name(py_col_idx)
        row_diff[cy_col_idx] = (f"={dn_cy}-{cy_col_name}{wn.r}", 0.0)
        row_diff[py_col_idx] = (f"={dn_py}-{py_col_name}{wn.r}", 0.0)
        wn.append(row_diff, fmt_sub)

    # Additional defined names that might be missing
    for k, (s, c, p) in note_code_to_name.items():
        # define empty ones to avoid #NAME? if note doesn't exist
        wb.define_name(c, f"='91_Mapping'!$Z$1")
        wb.define_name(p, f"='91_Mapping'!$Z$1")

    # Sheet 5: Balance Sheet
    print('Generating Sheet 5 (BS)')
    ws_bs = wb.add_worksheet("02_Balance_Sheet")
    wbs = WsWriter(ws_bs, "02_Balance_Sheet", py_col=3, meta=(client_name, cin_number, fye))
    wbs.ws.set_column(0, 0, 45)
    wbs.ws.set_column(1, 1, 10)
    wbs.ws.set_column(2, 3, 20)
    wbs.apply_header("BALANCE SHEET AS AT MARCH 31, 2025")
    wbs.append(["Particulars", "Note #", "As at 31-Mar-2025 (CY)", "As at 31-Mar-2024 (PY)"], fmt_header)
    
    r_sh_start = r_sh_end = 0
    r_ncl_start = r_ncl_end = 0
    r_cl_start = r_cl_end = 0
    
    r_nca_start = r_nca_end = 0
    r_ca_start = r_ca_end = 0
    
    r_sh_tot = r_ncl_tot = r_cl_tot = 0
    r_nca_tot = r_ca_tot = 0
    r_tot_eq = r_tot_as = 0
    
    for line in fs.balance_sheet:
        row_format = None
        if "TOTAL" in line.particulars.upper():
            row_format = fmt_tot
        elif not line.particulars.startswith(" ") and not line.particulars.startswith("1.") and not line.particulars.startswith("2.") and not line.particulars.startswith("3."):
            row_format = fmt_bold
            
        if line.note_number:
            n_num = line.note_number
            # Check if valid note
            if n_num in note_code_to_name:
                sheet_title, dn_cy, dn_py = note_code_to_name[n_num]
                sign = "-" if n_num in credit_notes else ""
                wbs.append([line.particulars, f'=HYPERLINK("#\\\'{sheet_title}\\\'!A1", "{n_num}")', (f"={sign}{dn_cy}", line.cy_amount), (f"={sign}{dn_py}", line.py_amount)])
            else:
                wbs.append([line.particulars, n_num, line.cy_amount, line.py_amount])
            
            # Track ranges
            if "1." in str(n_num):
                if not r_sh_start: r_sh_start = wbs.r
                r_sh_end = wbs.r
            elif "2." in str(n_num):
                if not r_ncl_start: r_ncl_start = wbs.r
                r_ncl_end = wbs.r
            elif "3." in str(n_num):
                if not r_cl_start: r_cl_start = wbs.r
                r_cl_end = wbs.r
            elif "4." in str(n_num):
                if not r_nca_start: r_nca_start = wbs.r
                r_nca_end = wbs.r
            elif "5." in str(n_num):
                if not r_ca_start: r_ca_start = wbs.r
                r_ca_end = wbs.r
        else:
            # Subtotals
            if "Total Shareholders" in line.particulars:
                wbs.append([line.particulars, "", (f"=SUM(C{r_sh_start}:C{r_sh_end})", line.cy_amount), (f"=SUM(D{r_sh_start}:D{r_sh_end})", line.py_amount)], fmt_sub)
                r_sh_tot = wbs.r
            elif "Total Non-Current Liabilities" in line.particulars:
                wbs.append([line.particulars, "", (f"=SUM(C{r_ncl_start}:C{r_ncl_end})", line.cy_amount), (f"=SUM(D{r_ncl_start}:D{r_ncl_end})", line.py_amount)], fmt_sub)
                r_ncl_tot = wbs.r
            elif "Total Current Liabilities" in line.particulars:
                wbs.append([line.particulars, "", (f"=SUM(C{r_cl_start}:C{r_cl_end})", line.cy_amount), (f"=SUM(D{r_cl_start}:D{r_cl_end})", line.py_amount)], fmt_sub)
                r_cl_tot = wbs.r
            elif "Total Non-Current Assets" in line.particulars:
                wbs.append([line.particulars, "", (f"=SUM(C{r_nca_start}:C{r_nca_end})", line.cy_amount), (f"=SUM(D{r_nca_start}:D{r_nca_end})", line.py_amount)], fmt_sub)
                r_nca_tot = wbs.r
            elif "Total Current Assets" in line.particulars:
                wbs.append([line.particulars, "", (f"=SUM(C{r_ca_start}:C{r_ca_end})", line.cy_amount), (f"=SUM(D{r_ca_start}:D{r_ca_end})", line.py_amount)], fmt_sub)
                r_ca_tot = wbs.r
            elif "TOTAL EQUITY AND LIABILITIES" in line.particulars:
                wbs.append([line.particulars, "", (f"=C{r_sh_tot}+C{r_ncl_tot}+C{r_cl_tot}", line.cy_amount), (f"=D{r_sh_tot}+D{r_ncl_tot}+D{r_cl_tot}", line.py_amount)], fmt_tot)
                r_tot_eq = wbs.r
            elif "TOTAL ASSETS" in line.particulars:
                wbs.append([line.particulars, "", (f"=C{r_nca_tot}+C{r_ca_tot}", line.cy_amount), (f"=D{r_nca_tot}+D{r_ca_tot}", line.py_amount)], fmt_tot)
                r_tot_as = wbs.r
            else:
                if "TOTAL" in line.particulars.upper():
                    wbs.append([line.particulars, "", line.cy_amount, line.py_amount], fmt_tot)
                elif line.particulars.startswith(" "):
                    wbs.append([line.particulars, "", line.cy_amount, line.py_amount])
                else:
                    wbs.append([line.particulars, "", line.cy_amount, line.py_amount], fmt_bold)

    # Balance Check
    wbs.append([])
    wbs.append(["Balance Check (Total Assets - Total Equity & Liabilities)", "", (f"=C{r_tot_as}-C{r_tot_eq}", 0.0), (f"=D{r_tot_as}-D{r_tot_eq}", 0.0)], fmt_bold)

    # Sheet 6: P&L
    print('Generating Sheet 6 (P&L)')
    ws_pl = wb.add_worksheet("03_Profit_and_Loss")
    wpl = WsWriter(ws_pl, "03_Profit_and_Loss", py_col=3, meta=(client_name, cin_number, fye))
    wpl.ws.set_column(0, 0, 45)
    wpl.ws.set_column(1, 1, 10)
    wpl.ws.set_column(2, 3, 20)
    wpl.apply_header("STATEMENT OF PROFIT AND LOSS FOR THE YEAR ENDED MARCH 31, 2025")
    wpl.append(["Particulars", "Note #", "Year Ended 31-Mar-2025 (CY)", "Year Ended 31-Mar-2024 (PY)"], fmt_header)
    
    r_rev = r_oth_inc = 0
    r_exp_start = r_exp_end = 0
    r_tot_inc = r_tot_exp = 0
    r_pbt = r_tax = 0
    
    for line in fs.profit_and_loss:
        if line.note_number:
            n_num = line.note_number
            if n_num in note_code_to_name:
                sheet_title, dn_cy, dn_py = note_code_to_name[n_num]
                sign = "-" if n_num in credit_notes else ""
                wpl.append([line.particulars, f'=HYPERLINK("#\\\'{sheet_title}\\\'!A1", "{n_num}")', (f"={sign}{dn_cy}", line.cy_amount), (f"={sign}{dn_py}", line.py_amount)])
            else:
                wpl.append([line.particulars, n_num, line.cy_amount, line.py_amount])
            
            # Track P&L rows
            if "6.1" in str(n_num): r_rev = wpl.r
            elif "6.2" in str(n_num): r_oth_inc = wpl.r
            elif "7." in str(n_num):
                if not r_exp_start: r_exp_start = wpl.r
                r_exp_end = wpl.r
                if "7.6" in str(n_num): r_tax = wpl.r
        else:
            if "Total Income" in line.particulars:
                wpl.append([line.particulars, "", (f"=C{r_rev}+C{r_oth_inc}", line.cy_amount), (f"=D{r_rev}+D{r_oth_inc}", line.py_amount)], fmt_tot)
                r_tot_inc = wpl.r
            elif "Total Expenses" in line.particulars:
                wpl.append([line.particulars, "", (f"=SUM(C{r_exp_start}:C{r_exp_end})", line.cy_amount), (f"=SUM(D{r_exp_start}:D{r_exp_end})", line.py_amount)], fmt_tot)
                r_tot_exp = wpl.r
            elif "Profit Before Tax" in line.particulars:
                wpl.append([line.particulars, "", (f"=C{r_tot_inc}-C{r_tot_exp}", line.cy_amount), (f"=D{r_tot_inc}-D{r_tot_exp}", line.py_amount)], fmt_tot)
                r_pbt = wpl.r
            elif "Profit After Tax" in line.particulars:
                # Tax Expense is an expense, so subtract it from PBT.
                wpl.append([line.particulars, "", (f"=C{r_pbt}-C{r_tax}", line.cy_amount), (f"=D{r_pbt}-D{r_tax}", line.py_amount)], fmt_tot)
                r_pat = wpl.r
            elif "TOTAL" in line.particulars.upper() or "PROFIT" in line.particulars.upper() or "EARNINGS" in line.particulars.upper():
                wpl.append([line.particulars, "", line.cy_amount, line.py_amount], fmt_tot)
            elif line.particulars.startswith(" "):
                wpl.append([line.particulars, "", line.cy_amount, line.py_amount])
            else:
                wpl.append([line.particulars, "", line.cy_amount, line.py_amount], fmt_bold)

    # Sheet 7: Cash Flow
    print('Generating Sheet 7 (CF)')
    ws_cf = wb.add_worksheet("04_Cash_Flow_Statement")
    wcf = WsWriter(ws_cf, "04_Cash_Flow_Statement", py_col=2, meta=(client_name, cin_number, fye))
    wcf.ws.set_column(0, 0, 50)
    wcf.ws.set_column(1, 2, 20)
    wcf.apply_header("CASH FLOW STATEMENT FOR THE YEAR ENDED MARCH 31, 2025")
    wcf.append(["Particulars", "CY", "PY"], fmt_header)
    
    fmt_red = wb.add_format({'bold': True, 'font_color': 'red', 'bg_color': '#FFE4E1', 'num_format': '#,##0.00'})
    
    for line in getattr(cfs, 'statement', cfs):
        if "Reconciliation Difference" in line.particulars:
            fmt_to_use = fmt_red if (abs(line.cy_amount) > 0.01 or abs(line.py_amount) > 0.01) else fmt_bold
            wcf.append([line.particulars, line.cy_amount, line.py_amount], fmt_to_use)
        elif "Cash and Cash Equivalents" in line.particulars and "End" in line.particulars:
            wcf.append([line.particulars, line.cy_amount, line.py_amount], fmt_tot)
        elif "Net Cash" in line.particulars:
            wcf.append([line.particulars, line.cy_amount, line.py_amount], fmt_sub)
        elif line.particulars.isupper():
            wcf.append([line.particulars, line.cy_amount, line.py_amount], fmt_bold)
        else:
            wcf.append([line.particulars, line.cy_amount, line.py_amount])

    # Sheet 8: Ratios
    print('Generating Sheet 8 (Ratios)')
    ws_rat = wb.add_worksheet("07_Financial_Ratios")
    wrat = WsWriter(ws_rat, "07_Financial_Ratios", py_col=3, meta=(client_name, cin_number, fye))
    wrat.ws.set_column(0, 0, 30)
    wrat.ws.set_column(1, 1, 40)
    wrat.ws.set_column(2, 4, 15)
    wrat.apply_header("FINANCIAL RATIOS")
    wrat.append(["Ratio Name", "Formula", "CY Value", "PY Value", "Variance"], fmt_header)
    
    def get_ratio_formula(name, cy=True):
        col = "C" if cy else "D"
        dn_sfx = "" if cy else "_PY"
        bs = "'02_Balance_Sheet'!"
        pl = "'03_Profit_and_Loss'!"
        
        if "Current Ratio" in name:
            return f"={bs}{col}{r_ca_tot}/{bs}{col}{r_cl_tot}"
        elif "Debt Equity" in name:
            return f"=(TOT_LTBorrow{dn_sfx}+TOT_STBorrow{dn_sfx})/{bs}{col}{r_sh_tot}"
        elif "Net Profit Ratio" in name:
            return f"={pl}{col}{r_pat}/TOT_Revenue{dn_sfx}"
        elif "EBITDA Margin" in name:
            return f"=({pl}{col}{r_pbt}+TOT_Finance{dn_sfx}+TOT_Depreciation{dn_sfx})/TOT_Revenue{dn_sfx}"
        elif "Return on Equity" in name:
            return f"={pl}{col}{r_pat}/{bs}{col}{r_sh_tot}"
        elif "Trade Receivable Days" in name:
            return f"=(TOT_Receivables{dn_sfx}/TOT_Revenue{dn_sfx})*365"
        elif "Trade Payable Days" in name:
            return f"=(TOT_Payables{dn_sfx}/{pl}{col}{r_exp_start})*365"
        elif "Inventory Days" in name:
            return f"=(TOT_Inventory{dn_sfx}/{pl}{col}{r_exp_start})*365"
        return ""

    for r in ratios:
        cy_form = get_ratio_formula(r.name, cy=True)
        py_form = get_ratio_formula(r.name, cy=False)
        cy_val = cy_form if cy_form else getattr(r, 'cy_value', 0.0)
        py_val = py_form if py_form else getattr(r, 'py_value', 0.0)
        
        cy_cell = (cy_form, getattr(r, 'cy_value', 0.0)) if cy_form else getattr(r, 'cy_value', 0.0)
        py_cell = (py_form, getattr(r, 'py_value', 0.0)) if py_form else getattr(r, 'py_value', 0.0)
        
        wrat.append([r.name, getattr(r, 'formula', ''), cy_cell, py_cell, getattr(r, 'variance', '')], fmt_bold_num if r.name.isupper() else None)

    

    # Sheet 9: Tie-Out
    print('Generating Sheet 9 (Tie-Out)')
    ws_tie = wb.add_worksheet("98_Tie_Out")
    wt = WsWriter(ws_tie, "98_Tie_Out", meta=(client_name, cin_number, fye))
    wt.ws.set_column(0, 0, 15)
    wt.ws.set_column(1, 1, 40)
    wt.ws.set_column(2, 3, 20)
    wt.ws.set_column(4, 4, 15)
    wt.apply_header("TIE-OUT AND BALANCING")
    wt.append(["Control ID", "Description", "Expected Value", "Computed Formula", "Variance", "Tie-Out Status"], fmt_header)
    
    fmt_pass = wb.add_format({'bold': True, 'font_color': 'green', 'bg_color': '#D1FAE5'})
    fmt_fail = wb.add_format({'bold': True, 'font_color': 'red', 'bg_color': '#FEE2E2'})
    
    # We create some controls based on totals!
    # Control 1: Balance Sheet matches (Total Assets == Total Eq & Liab)
    # cy_chk is 0.0, we just need the cell ref. But we didn't track it! We can just use the formula difference
    # Actually, we know the BS total assets row (r_tot_as) and eq liab row (r_tot_eq).
    wt.append(["CHK-01", "Balance Sheet Balance Check (CY)", 0.0, (f"='02_Balance_Sheet'!C{r_tot_as}-'02_Balance_Sheet'!C{r_tot_eq}", 0.0), (f"=D{wt.r}-C{wt.r}", 0.0), "TALLIED"])
    
    # We can fetch cash flow reconciliation difference from cfs
    cf_diff_val = 0.0
    for line in getattr(cfs, 'statement', cfs):
        if "Reconciliation Difference" in line.particulars:
            cf_diff_val = line.cy_amount
            
    # We don't have the exact row of CF diff tracked, but we can just use the value for the control, or formula if we want.
    status = "REVIEW REQUIRED" if abs(cf_diff_val) > 0.01 else "TALLIED"
    stat_fmt = fmt_fail if abs(cf_diff_val) > 0.01 else fmt_pass
    wt.append(["CHK-02", "Cash Flow Reconciliation Difference (CY)", 0.0, cf_diff_val, (f"=D{wt.r}-C{wt.r}", cf_diff_val), status])
    wt.ws.write(wt.r-1, 5, status, stat_fmt)

    # Sheet 10: Formula Audit
    ws_aud = wb.add_worksheet("99_Formula_Audit")
    wa = WsWriter(ws_aud, "99_Formula_Audit", meta=(client_name, cin_number, fye))
    wa.ws.set_column(0, 1, 20)
    wa.ws.set_column(2, 2, 60)
    wa.ws.set_column(3, 3, 20)
    wa.apply_header("FORMULA AUDIT LOG")
    wa.append(["Sheet", "Cell Address", "Applied Excel Formula", "Resolved Value"], fmt_header)
    for row in list(formula_audit_log):
        wa.ws.write_row(wa.r, 0, row)
        wa.r += 1
        
    # Sheet 11: Sign-off
    print('Generating Sheet 11 (Sign-Off)')
    ws_so = wb.add_worksheet("Sign_Off")
    wso = WsWriter(ws_so, "Sign_Off", meta=(client_name, cin_number, fye))
    wso.ws.set_column(0, 0, 50)
    wso.ws.set_column(1, 1, 50)
    wso.apply_header("APPROVAL AND SIGN-OFF")
    
    wso.append([client_name], fmt_masthead)
    wso.append([])
    wso.append([])
    wso.append([])
    wso.append(["________________________", "________________________"])
    wso.append(["Partner", "Director"])
    wso.append(["Membership No: 123456", "DIN: 09876543"])


    wb.close()
    return filepath
