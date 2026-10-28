"""
workpapers.py
Professional Chartered Accountant Excel Work Paper Generator (openpyxl)
Outputs WP_JE_Testing_FY202X-XX.xlsx with 5 structured sheets, CA styling,
freeze panes, autofit, formulas, tick-mark legends, and INR number formats.
"""

from datetime import datetime
import io
import math
from typing import Any, Dict, List, Optional
import numpy as np
import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

# CA Firm Workpaper Theme Colors
HEADER_FILL = PatternFill(start_color="1B365D", end_color="1B365D", fill_type="solid")  # Deep Navy Blue
HEADER_FONT = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
SUBHEADER_FILL = PatternFill(start_color="E8EEF5", end_color="E8EEF5", fill_type="solid") # Soft Ice Blue
SUBHEADER_FONT = Font(name="Calibri", size=11, bold=True, color="1B365D")
TITLE_FONT = Font(name="Calibri", size=15, bold=True, color="1B365D")
BOLD_FONT = Font(name="Calibri", size=10, bold=True)
REGULAR_FONT = Font(name="Calibri", size=10)
ITALIC_FONT = Font(name="Calibri", size=9, italic=True, color="555555")

# Risk conditional fills
HIGH_RISK_FILL = PatternFill(start_color="FCE8E6", end_color="FCE8E6", fill_type="solid")  # Soft Red
MED_RISK_FILL = PatternFill(start_color="FEF7E0", end_color="FEF7E0", fill_type="solid")   # Soft Amber
LOW_RISK_FILL = PatternFill(start_color="E6F4EA", end_color="E6F4EA", fill_type="solid")   # Soft Green

# Borders
THIN_SIDE = Side(border_style="thin", color="CCCCCC")
THICK_BOTTOM = Side(border_style="double", color="1B365D")
CELL_BORDER = Border(left=THIN_SIDE, right=THIN_SIDE, top=THIN_SIDE, bottom=THIN_SIDE)
TOTAL_BORDER = Border(top=THIN_SIDE, bottom=THICK_BOTTOM)

# Indian Currency Format in Excel
INR_FORMAT = '₹ #,##,##0.00;[Red](₹ #,##,##0.00);"-"'


def style_range(ws, min_col, min_row, max_col, max_row, font=None, fill=None, border=None, alignment=None):
    for row in ws.iter_rows(min_row=min_row, max_row=max_row, min_col=min_col, max_col=max_col):
        for cell in row:
            if font: cell.font = font
            if fill: cell.fill = fill
            if border: cell.border = border
            if alignment: cell.alignment = alignment


def autofit_columns(ws, min_col=1, max_col=None, max_len_cap=50):
    if max_col is None:
        max_col = ws.max_column
    for col in range(min_col, max_col + 1):
        col_letter = get_column_letter(col)
        max_len = 0
        for cell in ws[col_letter]:
            if cell.value is not None:
                val_str = str(cell.value)
                if len(val_str) > max_len and not val_str.startswith("="):
                    max_len = len(val_str)
        ws.column_dimensions[col_letter].width = min(max(max_len + 3, 12), max_len_cap)


def build_excel_workpaper(
    engagement_info: Dict[str, Any],
    diagnostics: Dict[str, Any],
    flags_df,
    sample_df,
    benford_result: Dict[str, Any],
    review_data: Optional[List[Dict[str, Any]]] = None
) -> bytes:
    """
    Generate the complete, audit-grade multi-sheet Excel Work Paper package.
    """
    wb = openpyxl.Workbook()
    
    # -------------------------------------------------------------
    # Sheet 1: Index & Objective
    # -------------------------------------------------------------
    ws_index = wb.active
    ws_index.title = "Index & Objective"
    ws_index.views.sheetView[0].showGridLines = True

    # Title Banner
    ws_index["B2"] = "AUDIT WORKING PAPER: JOURNAL ENTRY & VOUCHER TESTING"
    ws_index["B2"].font = TITLE_FONT
    ws_index["B3"] = f"Reference Standards: ICAI SA 240, SA 315, SA 330, SA 500, SA 530 | CARO 2020"
    ws_index["B3"].font = ITALIC_FONT

    # Engagement Meta Table
    meta_rows = [
        ("Entity / Client Name:", engagement_info.get("company_name", "N/A")),
        ("Engagement Name:", engagement_info.get("engagement_name", "Statutory Audit")),
        ("Financial Year:", engagement_info.get("financial_year", "FY 2023-24")),
        ("Audit Period:", engagement_info.get("audit_period", "01-Apr-2023 to 31-Mar-2024")),
        ("Prepared By (Audit Senior):", engagement_info.get("prepared_by", "Audit Team")),
        ("Reviewed By (Audit Partner/Manager):", engagement_info.get("reviewed_by", "Engagement Partner")),
        ("Date of Preparation:", datetime.now().strftime("%d-%b-%Y")),
        ("Workpaper Code / Index:", "WP-JE-01")
    ]

    curr_row = 5
    ws_index.cell(row=curr_row, column=2, value="A. ENGAGEMENT METADATA & CONTROL INFORMATION").font = SUBHEADER_FONT
    ws_index.cell(row=curr_row, column=2).fill = SUBHEADER_FILL
    ws_index.merge_cells(start_row=curr_row, start_column=2, end_row=curr_row, end_column=5)
    curr_row += 1

    for label, val in meta_rows:
        ws_index.cell(row=curr_row, column=2, value=label).font = BOLD_FONT
        ws_index.cell(row=curr_row, column=3, value=val).font = REGULAR_FONT
        ws_index.cell(row=curr_row, column=2).border = CELL_BORDER
        ws_index.cell(row=curr_row, column=3).border = CELL_BORDER
        curr_row += 1

    # Materiality Thresholds Table
    curr_row += 1
    ws_index.cell(row=curr_row, column=2, value="B. AUDIT MATERIALITY BENCHMARKS (SA 320 / SA 450)").font = SUBHEADER_FONT
    ws_index.cell(row=curr_row, column=2).fill = SUBHEADER_FILL
    ws_index.merge_cells(start_row=curr_row, start_column=2, end_row=curr_row, end_column=5)
    curr_row += 1

    mat_rows = [
        ("Overall Materiality (OM)", engagement_info.get("om", 0.0), "Basis: Planning materiality for financial statements as a whole."),
        ("Performance Materiality (PM)", engagement_info.get("pm", 0.0), "Basis: Haircut threshold for targeted JE substantive testing (SA 320.11)."),
        ("Clearly Trivial Threshold (CTT)", engagement_info.get("ctt", 0.0), "Basis: Threshold below which misstatements are clearly inconsequential (SA 450.A2).")
    ]

    ws_index.cell(row=curr_row, column=2, value="Materiality Metric").font = HEADER_FONT
    ws_index.cell(row=curr_row, column=2).fill = HEADER_FILL
    ws_index.cell(row=curr_row, column=3, value="Amount (INR)").font = HEADER_FONT
    ws_index.cell(row=curr_row, column=3).fill = HEADER_FILL
    ws_index.cell(row=curr_row, column=4, value="Audit Rationale / Statutory Basis").font = HEADER_FONT
    ws_index.cell(row=curr_row, column=4).fill = HEADER_FILL
    curr_row += 1

    for label, amt, note in mat_rows:
        ws_index.cell(row=curr_row, column=2, value=label).font = BOLD_FONT
        c_amt = ws_index.cell(row=curr_row, column=3, value=amt)
        c_amt.font = BOLD_FONT
        c_amt.number_format = INR_FORMAT
        c_amt.alignment = Alignment(horizontal="right")
        ws_index.cell(row=curr_row, column=4, value=note).font = REGULAR_FONT
        ws_index.cell(row=curr_row, column=2).border = CELL_BORDER
        ws_index.cell(row=curr_row, column=3).border = CELL_BORDER
        ws_index.cell(row=curr_row, column=4).border = CELL_BORDER
        curr_row += 1

    # Audit Scope & Objective narrative
    curr_row += 1
    ws_index.cell(row=curr_row, column=2, value="C. OBJECTIVE, MANDATE & AUDIT METHODOLOGY").font = SUBHEADER_FONT
    ws_index.cell(row=curr_row, column=2).fill = SUBHEADER_FILL
    ws_index.merge_cells(start_row=curr_row, start_column=2, end_row=curr_row, end_column=5)
    curr_row += 1

    narratives = [
        "1. Standard on Auditing (SA) 240 Mandate:",
        "   Per SA 240 (The Auditor's Responsibilities Relating to Fraud in an Audit of Financial Statements), management is in a unique",
        "   position to perpetrate fraud because of its ability to manipulate accounting records and prepare fraudulent financial statements",
        "   by overriding controls. The auditor is mandatorily required to design and perform procedures to test the appropriateness of journal entries.",
        "",
        "2. Scope of Population Examined:",
        "   The population encompasses all journal entries and non-standard ledger vouchers recorded in the General Ledger throughout the reporting FY,",
        "   including closing entries, post-cutoff adjustments, round transactions, and entries affecting sensitive/suspense accounts.",
        "",
        "3. Tick Mark Standards & Legend (ICAI Standard Audit Practice):",
        "   [^] Reconciled with Trial Balance and general ledger master totals.",
        "   [V] Vouched with underlying external third-party invoice, contract, or challan.",
        "   [B] Traced and verified against bank statements / direct bank confirmations.",
        "   [A] Verified Delegation of Authority (DOA) compliance and independent approval.",
        "   [C] Cut-off verified against goods inward/outward registers and subsequent period logs.",
        "   [T] Statutory deduction / TDS / GST compliance verified."
    ]

    for line in narratives:
        ws_index.cell(row=curr_row, column=2, value=line).font = BOLD_FONT if line.endswith(":") else REGULAR_FONT
        curr_row += 1

    autofit_columns(ws_index, min_col=2, max_col=5)

    # -------------------------------------------------------------
    # Sheet 2: Methodology & Criteria
    # -------------------------------------------------------------
    ws_meth = wb.create_sheet(title="Methodology & Criteria")
    ws_meth.views.sheetView[0].showGridLines = True

    ws_meth["A1"] = "JOURNAL ENTRY TESTING: AUDIT CRITERIA & RED-FLAG CATALOG"
    ws_meth["A1"].font = TITLE_FONT
    ws_meth["A2"] = "Criteria formulated under ICAI SA 240, SA 315 & CARO 2020"
    ws_meth["A2"].font = ITALIC_FONT

    meth_headers = ["Test ID", "Audit Risk / Criterion", "Risk Level", "Detection Logic & Threshold", "Mandated Audit Procedure (SA 240/330)"]
    for c_idx, h in enumerate(meth_headers, 1):
        cell = ws_meth.cell(row=4, column=c_idx, value=h)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    criteria_list = [
        ("TEST_01", "Sunday Postings", "Medium", "Entries dated or keyed on Sunday.", "Inspect physical vouchers and overtime logs; evaluate why entries were processed on weekly rest days."),
        ("TEST_02", "Off-Hours Postings", "Medium", "Entries keyed outside business hours (09:00 - 19:00).", "Review IT access control logs and user authentication stamps to confirm authorization."),
        ("TEST_03", "Post-Year-End Backdated Cutoff", "High", "Entries dated <= 31 March posted in subsequent period.", "Perform cutoff testing per SA 560; ensure entries do not smooth earnings or conceal liabilities."),
        ("TEST_04", "Round-Value Transactions", "Low", "Amounts in exact multiples of ₹1,00,000 / ₹5,00,000.", "Review commercial contracts and vendor billing to confirm whether round values represent estimates."),
        ("TEST_05", "Below Authorization Threshold", "High", "Amounts within 5% below approval limits.", "Investigate structuring / smurfing designed to circumvent DOA board approval limits."),
        ("TEST_06", "Blank / Generic Narration", "Medium", "Narrations blank or 'Being entry passed', etc.", "Obtain commercial substantiation and underlying contracts from management."),
        ("TEST_07", "Audit Keyword in Narration", "High", "Keywords: 'adjustment', 'rectification', 'dummy', 'urgent'.", "Examine root cause of entry per SA 240; evaluate for management override of controls."),
        ("TEST_08", "Exceeding Performance Materiality", "High", "Single entries exceeding PM threshold.", "Perform 100% substantive vouching of third-party documents, tax returns, and bank advices."),
        ("TEST_09", "Sensitive / Suspense Accounts", "High", "Touches Cash, Bank, Suspense, Director loan/advance.", "Verify reconciliation of suspense items and check CARO 2020 Clause (ix) fund diversion."),
        ("TEST_10", "Admin / Maker-Checker Anomaly", "High", "User is 'admin' or Maker equals Checker.", "Inspect ITGC access controls, segregation of duties (SoD), and dual-control compliance.")
    ]

    r_idx = 5
    for tid, name, rlevel, logic, proc in criteria_list:
        ws_meth.cell(row=r_idx, column=1, value=tid).alignment = Alignment(horizontal="center")
        ws_meth.cell(row=r_idx, column=2, value=name).font = BOLD_FONT
        
        c_risk = ws_meth.cell(row=r_idx, column=3, value=rlevel)
        c_risk.alignment = Alignment(horizontal="center")
        if rlevel == "High": c_risk.fill = HIGH_RISK_FILL
        elif rlevel == "Medium": c_risk.fill = MED_RISK_FILL
        else: c_risk.fill = LOW_RISK_FILL

        ws_meth.cell(row=r_idx, column=4, value=logic)
        ws_meth.cell(row=r_idx, column=5, value=proc)

        for col in range(1, 6):
            ws_meth.cell(row=r_idx, column=col).border = CELL_BORDER
            ws_meth.cell(row=r_idx, column=col).font = REGULAR_FONT if col != 2 else BOLD_FONT
        r_idx += 1

    autofit_columns(ws_meth, min_col=1, max_col=5)

    # -------------------------------------------------------------
    # Sheet 3: Testing Summary
    # -------------------------------------------------------------
    ws_summ = wb.create_sheet(title="Testing Summary")
    ws_summ.views.sheetView[0].showGridLines = True

    ws_summ["A1"] = "POPULATION RECONCILIATION & RISK EXCEPTION SUMMARY"
    ws_summ["A1"].font = TITLE_FONT

    # Population Diagnostic Table
    ws_summ["A3"] = "1. Data Integrity & Debit/Credit Reconciliation"
    ws_summ["A3"].font = SUBHEADER_FONT

    diag_headers = ["Metric / Parameter", "Value", "Status / Audit Implication"]
    for c, h in enumerate(diag_headers, 1):
        cell = ws_summ.cell(row=4, column=c, value=h)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL

    pop_data = [
        ("Total Records Imported", diagnostics.get("total_rows", 0), "Complete population loaded without silent omission."),
        ("Total Debit Amount (INR)", diagnostics.get("total_debit", 0.0), "Sum of all debit journal legs."),
        ("Total Credit Amount (INR)", diagnostics.get("total_credit", 0.0), "Sum of all credit journal legs."),
        ("Net Trial Balance Difference", diagnostics.get("difference", 0.0), "Balanced" if diagnostics.get("is_balanced", True) else "RECONCILIATION EXCEPTION"),
        ("Unbalanced Vouchers Count", diagnostics.get("unbalanced_vouchers_count", 0), "Vouchers where Dr != Cr."),
        ("Invalid / Unparseable Dates", diagnostics.get("invalid_dates_count", 0), "Records with corrupted date strings."),
        ("Duplicate Records Identified", diagnostics.get("duplicate_rows_count", 0), "Duplicate voucher lines identified."),
        ("Records Outside Financial Year", diagnostics.get("out_of_fy_count", 0), "Vouchers dated outside reporting period.")
    ]

    r_idx = 5
    for label, val, imp in pop_data:
        ws_summ.cell(row=r_idx, column=1, value=label).font = BOLD_FONT
        c_val = ws_summ.cell(row=r_idx, column=2, value=val)
        if "Amount" in label or "Difference" in label:
            c_val.number_format = INR_FORMAT
            c_val.alignment = Alignment(horizontal="right")
        else:
            c_val.number_format = "#,##0"
            c_val.alignment = Alignment(horizontal="right")
        ws_summ.cell(row=r_idx, column=3, value=imp).font = REGULAR_FONT
        for col in range(1, 4):
            ws_summ.cell(row=r_idx, column=col).border = CELL_BORDER
        r_idx += 1

    # Exception Risk Level Breakdown
    r_idx += 2
    ws_summ.cell(row=r_idx, column=1, value="2. Flagged Journal Exceptions by Risk Level").font = SUBHEADER_FONT
    r_idx += 1

    risk_headers = ["Risk Classification", "Number of Flags", "Total Amount (INR)", "% of Total Population Value"]
    for c, h in enumerate(risk_headers, 1):
        cell = ws_summ.cell(row=r_idx, column=c, value=h)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL

    r_idx += 1
    start_risk_row = r_idx

    total_pop_amt = diagnostics.get("total_debit", 1.0)
    if total_pop_amt <= 0: total_pop_amt = 1.0

    if not flags_df.empty:
        for r_name in ["High", "Medium", "Low"]:
            sub = flags_df[flags_df["risk_level"] == r_name]
            cnt = len(sub)
            amt = float(sub["amount"].sum()) if cnt > 0 else 0.0
            pct = (amt / total_pop_amt) * 100

            ws_summ.cell(row=r_idx, column=1, value=f"{r_name} Risk").font = BOLD_FONT
            ws_summ.cell(row=r_idx, column=2, value=cnt).alignment = Alignment(horizontal="right")
            c_amt = ws_summ.cell(row=r_idx, column=3, value=amt)
            c_amt.number_format = INR_FORMAT
            c_amt.alignment = Alignment(horizontal="right")
            ws_summ.cell(row=r_idx, column=4, value=f"{pct:.2f}%").alignment = Alignment(horizontal="right")

            for col in range(1, 5):
                ws_summ.cell(row=r_idx, column=col).border = CELL_BORDER
            r_idx += 1
    else:
        ws_summ.cell(row=r_idx, column=1, value="No flags identified").font = REGULAR_FONT
        r_idx += 1

    autofit_columns(ws_summ, min_col=1, max_col=4)

    # -------------------------------------------------------------
    # Sheet 4: Sample Testing Schedule
    # -------------------------------------------------------------
    ws_sample = wb.create_sheet(title="Sample Testing Schedule")
    ws_sample.views.sheetView[0].showGridLines = True
    ws_sample.freeze_panes = "A4"

    ws_sample["A1"] = "SAMPLE AUDIT TESTING SCHEDULE & VOUCHING WORK SHEET"
    ws_sample["A1"].font = TITLE_FONT
    ws_sample["A2"] = "Distinguishing Targeted Testing (Stratum 1 & 2) from Representative Sampling (Stratum 3)"
    ws_sample["A2"].font = ITALIC_FONT

    sched_headers = [
        "Source Row Ref", "Voucher No", "Voucher Date", "Account / Ledger Head",
        "Debit (INR)", "Credit (INR)", "Amount (INR)", "Narration",
        "Selection Stratum & Method", "Risk Level",
        "Auditor Observations", "Management Explanation", "Supporting Document Ref",
        "Audit Tick Marks", "Reviewer Comments", "Final Disposition", "Review Status"
    ]

    for c_idx, h in enumerate(sched_headers, 1):
        cell = ws_sample.cell(row=3, column=c_idx, value=h)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    r_idx = 4
    if not sample_df.empty:
        # Build quick review lookup if provided
        review_dict = {}
        if review_data:
            for r in review_data:
                review_dict[r.get("source_row_index")] = r

        for _, item in sample_df.iterrows():
            s_idx = int(item["source_row_index"])
            rev = review_dict.get(s_idx, {})

            ws_sample.cell(row=r_idx, column=1, value=s_idx).alignment = Alignment(horizontal="center")
            ws_sample.cell(row=r_idx, column=2, value=str(item["voucher_number"]))
            ws_sample.cell(row=r_idx, column=3, value=str(item["voucher_date"])).alignment = Alignment(horizontal="center")
            ws_sample.cell(row=r_idx, column=4, value=str(item["account_name"]))

            c_dr = ws_sample.cell(row=r_idx, column=5, value=float(item.get("debit", 0.0)))
            c_dr.number_format = INR_FORMAT
            c_cr = ws_sample.cell(row=r_idx, column=6, value=float(item.get("credit", 0.0)))
            c_cr.number_format = INR_FORMAT
            c_amt = ws_sample.cell(row=r_idx, column=7, value=float(item["amount"]))
            c_amt.number_format = INR_FORMAT

            ws_sample.cell(row=r_idx, column=8, value=str(item["narration"]))
            ws_sample.cell(row=r_idx, column=9, value=str(item["selection_method"]))
            
            c_risk = ws_sample.cell(row=r_idx, column=10, value=str(item["risk_level"]))
            c_risk.alignment = Alignment(horizontal="center")
            if str(item["risk_level"]) == "High": c_risk.fill = HIGH_RISK_FILL
            elif str(item["risk_level"]) == "Medium": c_risk.fill = MED_RISK_FILL

            # Review fields
            ws_sample.cell(row=r_idx, column=11, value=rev.get("auditor_observations", ""))
            ws_sample.cell(row=r_idx, column=12, value=rev.get("management_explanation", ""))
            ws_sample.cell(row=r_idx, column=13, value=rev.get("supporting_document_ref", ""))
            ws_sample.cell(row=r_idx, column=14, value=rev.get("audit_tick_marks", "^, V, B"))
            ws_sample.cell(row=r_idx, column=15, value=rev.get("reviewer_comments", ""))
            ws_sample.cell(row=r_idx, column=16, value=rev.get("final_disposition", "Pending Review"))
            ws_sample.cell(row=r_idx, column=17, value=rev.get("review_status", "Open"))

            for col in range(1, 18):
                ws_sample.cell(row=r_idx, column=col).border = CELL_BORDER
                ws_sample.cell(row=r_idx, column=col).font = REGULAR_FONT
            r_idx += 1

        # Add Excel Formula for Total Sample Amount
        ws_sample.cell(row=r_idx, column=4, value="TOTAL SAMPLE TESTED:").font = BOLD_FONT
        tot_cell = ws_sample.cell(row=r_idx, column=7, value=f"=SUM(G4:G{r_idx - 1})")
        tot_cell.font = BOLD_FONT
        tot_cell.number_format = INR_FORMAT
        tot_cell.border = TOTAL_BORDER

    # Enable Excel Auto-Filter on Table Headers
    ws_sample.auto_filter.ref = f"A3:Q{r_idx}"
    autofit_columns(ws_sample, min_col=1, max_col=17, max_len_cap=35)

    # -------------------------------------------------------------
    # Sheet 5: Benford Analysis
    # -------------------------------------------------------------
    ws_ben = wb.create_sheet(title="Benford Analysis")
    ws_ben.views.sheetView[0].showGridLines = True

    ws_ben["A1"] = "BENFORD'S LAW FIRST-DIGIT DISTRIBUTION ANALYSIS"
    ws_ben["A1"].font = TITLE_FONT
    ws_ben["A2"] = "Analytical procedure to evaluate digit frequency against logarithmic distribution (SA 240 / SA 520)"
    ws_ben["A2"].font = ITALIC_FONT

    ben_headers = [
        "First Digit (d)", "Observed Count", "Expected Count",
        "Observed Freq (%)", "Expected Freq (%)", "Deviation (%)", "Z-Score"
    ]

    for c_idx, h in enumerate(ben_headers, 1):
        cell = ws_ben.cell(row=4, column=c_idx, value=h)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = Alignment(horizontal="center", vertical="center")

    summary_df = benford_result.get("summary_df")
    r_idx = 5
    if summary_df is not None and not summary_df.empty:
        for _, row in summary_df.iterrows():
            ws_ben.cell(row=r_idx, column=1, value=int(row["Digit"])).alignment = Alignment(horizontal="center")
            ws_ben.cell(row=r_idx, column=2, value=int(row["Observed Count"])).alignment = Alignment(horizontal="right")
            ws_ben.cell(row=r_idx, column=3, value=float(row["Expected Count"])).alignment = Alignment(horizontal="right")
            ws_ben.cell(row=r_idx, column=4, value=float(row["Observed Proportion (%)"])).alignment = Alignment(horizontal="right")
            ws_ben.cell(row=r_idx, column=5, value=float(row["Expected Proportion (%)"])).alignment = Alignment(horizontal="right")
            
            c_dev = ws_ben.cell(row=r_idx, column=6, value=float(row["Deviation (%)"]))
            c_dev.alignment = Alignment(horizontal="right")
            if abs(float(row["Deviation (%)"])) > 5.0:
                c_dev.font = Font(name="Calibri", size=10, bold=True, color="9C0006")
                c_dev.fill = HIGH_RISK_FILL

            ws_ben.cell(row=r_idx, column=7, value=float(row["Z-Score"])).alignment = Alignment(horizontal="right")

            for col in range(1, 8):
                ws_ben.cell(row=r_idx, column=col).border = CELL_BORDER
                if col != 6 or abs(float(row["Deviation (%)"])) <= 5.0:
                    ws_ben.cell(row=r_idx, column=col).font = REGULAR_FONT
            r_idx += 1

    # Statistical Test Summary
    r_idx += 2
    ws_ben.cell(row=r_idx, column=1, value="Statistical Test Parameters:").font = SUBHEADER_FONT
    r_idx += 1
    
    chi2_val = benford_result.get("chi2_stat")
    p_val = benford_result.get("p_value")
    n_size = benford_result.get("sample_size", 0)

    stats_meta = [
        ("Total Records Tested (N):", f"{n_size:,}"),
        ("Degrees of Freedom (k - 1):", "8"),
        ("Chi-Square Statistic (χ²):", f"{chi2_val:.3f}" if chi2_val is not None and not np.isnan(chi2_val) else "N/A"),
        ("p-value:", f"{p_val:.4f}" if p_val is not None and not np.isnan(p_val) else "N/A"),
        ("Statistical Conclusion (at α=0.05):", "Conforms to Benford's Law (H0 not rejected)" if benford_result.get("conforms") else "Deviates from Benford's Law (H0 rejected)")
    ]

    for label, val in stats_meta:
        ws_ben.cell(row=r_idx, column=1, value=label).font = BOLD_FONT
        ws_ben.cell(row=r_idx, column=2, value=val).font = REGULAR_FONT
        r_idx += 1

    r_idx += 1
    ws_ben.cell(row=r_idx, column=1, value="Auditor Cautionary Note & Limitations (SA 240 / ICAI Guidance):").font = BOLD_FONT
    r_idx += 1
    notes = [
        "• Benford's Law is applicable only to naturally occurring, scale-invariant populations spanning several orders of magnitude.",
        "• Non-conformance does NOT establish fraud or error. Operational factors such as uniform contract prices, statutory limits, and petty cash ceilings naturally cause spikes.",
        "• Results must be interpreted in conjunction with qualitative understanding of the client's business model."
    ]
    for n_line in notes:
        ws_ben.cell(row=r_idx, column=1, value=n_line).font = ITALIC_FONT
        r_idx += 1

    autofit_columns(ws_ben, min_col=1, max_col=7)

    # Save to in-memory bytes
    output_stream = io.BytesIO()
    wb.save(output_stream)
    output_stream.seek(0)
    return output_stream.getvalue()
