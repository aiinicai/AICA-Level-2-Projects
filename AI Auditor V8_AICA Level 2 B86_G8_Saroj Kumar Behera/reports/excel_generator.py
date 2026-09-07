"""
AI Auditor V8 - Professional Excel Report Generator
Produces a multi-tab, formatted financial analysis and audit-support workbook.
"""

import os
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from core.models import FinancialModel
from config.constants import APP_NAME, APP_VERSION, DISCLAIMER_TEXT
from analysis.trend_engine import TrendEngine

class ExcelReportGenerator:

    def __init__(self, model: FinancialModel):
        self.model = model
        self.wb = openpyxl.Workbook()
        # Styling Palette
        self.font_title = Font(name="Segoe UI", size=14, bold=True, color="FFFFFF")
        self.font_subtitle = Font(name="Segoe UI", size=10, italic=True, color="FFFFFF")
        self.font_header = Font(name="Segoe UI", size=10, bold=True, color="FFFFFF")
        self.font_sub_header = Font(name="Segoe UI", size=10, bold=True, color="1A365D")
        self.font_bold = Font(name="Segoe UI", size=9.5, bold=True, color="000000")
        self.font_regular = Font(name="Segoe UI", size=9.5, color="000000")
        self.font_disclaimer = Font(name="Segoe UI", size=8.5, italic=True, color="4A5568")

        self.fill_navy = PatternFill(start_color="1A365D", end_color="1A365D", fill_type="solid")
        self.fill_steel = PatternFill(start_color="2B6CB0", end_color="2B6CB0", fill_type="solid")
        self.fill_gray_header = PatternFill(start_color="EDF2F7", end_color="EDF2F7", fill_type="solid")
        self.fill_highlight = PatternFill(start_color="FEFCBF", end_color="FEFCBF", fill_type="solid")
        self.fill_alert_red = PatternFill(start_color="FED7D7", end_color="FED7D7", fill_type="solid")
        self.fill_alert_green = PatternFill(start_color="C6F6D5", end_color="C6F6D5", fill_type="solid")

        self.align_center = Alignment(horizontal="center", vertical="center", wrap_text=True)
        self.align_left = Alignment(horizontal="left", vertical="center", wrap_text=True)
        self.align_right = Alignment(horizontal="right", vertical="center")

        thin = Side(border_style="thin", color="CBD5E0")
        self.border_cell = Border(left=thin, right=thin, top=thin, bottom=thin)
        self.border_top_bottom = Border(top=thin, bottom=Side(border_style="double", color="1A365D"))

    def generate(self, output_path: str) -> str:
        """Constructs all 12 worksheets and saves workbook."""
        # Remove default sheet
        default_sheet = self.wb.active
        self.wb.remove(default_sheet)

        self._build_executive_summary()
        self._build_statement_sheet("Balance Sheet", self.model.balance_sheet)
        self._build_statement_sheet("Profit & Loss", self.model.profit_loss)
        self._build_statement_sheet("Cash Flow", self.model.cash_flow)
        self._build_ratio_sheet()
        self._build_trend_sheet()
        self._build_variance_sheet()
        self._build_possible_reasons_sheet()
        self._build_audit_verification_sheet()
        self._build_risk_sheet()
        self._build_limitations_sheet()

        # Save workbook
        self.wb.save(output_path)
        return output_path

    def _apply_sheet_header(self, ws, title: str, subtitle: str, num_cols: int):
        """Standardized banner at the top of every worksheet."""
        ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=num_cols)
        c1 = ws.cell(row=1, column=1, value=f"{APP_NAME} - {title.upper()}")
        c1.font = self.font_title
        c1.fill = self.fill_navy
        c1.alignment = self.align_center
        ws.row_dimensions[1].height = 28

        ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=num_cols)
        c2 = ws.cell(row=2, column=1, value=f"Company: {self.model.company_info.name} | {subtitle} | Unit: {self.model.company_info.unit_label}")
        c2.font = self.font_subtitle
        c2.fill = self.fill_steel
        c2.alignment = self.align_center
        ws.row_dimensions[2].height = 18

    def _auto_fit_columns(self, ws, min_width=12, max_width=60):
        for col in ws.columns:
            col_letter = get_column_letter(col[0].column)
            max_len = 0
            for cell in col:
                # skip merged banner
                if cell.row in [1, 2]: continue
                if cell.value:
                    val_str = str(cell.value)
                    max_len = max(max_len, len(val_str))
            ws.column_dimensions[col_letter].width = max(min_width, min(max_len + 3, max_width))

    # --- 1. Executive Summary ---
    def _build_executive_summary(self):
        ws = self.wb.create_sheet(title="Executive Summary")
        self._apply_sheet_header(ws, "Executive Summary", f"Analysis Date: {self.model.company_info.analysis_date}", 6)

        # Engagement Info Table
        ws.cell(row=4, column=1, value="Company / Entity Name:").font = self.font_bold
        ws.cell(row=4, column=2, value=self.model.company_info.name).font = self.font_regular
        ws.cell(row=4, column=4, value="Engagement Type:").font = self.font_bold
        ws.cell(row=4, column=5, value=self.model.company_info.engagement_type).font = self.font_regular

        ws.cell(row=5, column=1, value="Primary Financial Year:").font = self.font_bold
        ws.cell(row=5, column=2, value=self.model.company_info.financial_year_current).font = self.font_regular
        ws.cell(row=5, column=4, value="Comparative Year:").font = self.font_bold
        ws.cell(row=5, column=5, value=self.model.company_info.financial_year_previous).font = self.font_regular

        ws.cell(row=6, column=1, value="Reporting Unit:").font = self.font_bold
        ws.cell(row=6, column=2, value=self.model.company_info.unit_label).font = self.font_regular
        ws.cell(row=6, column=4, value="Source File:").font = self.font_bold
        ws.cell(row=6, column=5, value=self.model.company_info.source_file).font = self.font_regular

        # Key Financial Highlights
        ws.cell(row=8, column=1, value="KEY FINANCIAL HIGHLIGHTS & SUMMARY METRICS").font = self.font_sub_header
        
        headers = ["Metric / Line Item", "Current Period", "Previous Period", "Absolute Change", "YoY % Change", "Health Tag"]
        for c_idx, h in enumerate(headers, 1):
            cell = ws.cell(row=9, column=c_idx, value=h)
            cell.font = self.font_header
            cell.fill = self.fill_steel
            cell.alignment = self.align_center
            cell.border = self.border_cell

        # Pull key figures
        p_curr = self.model.periods[0] if self.model.periods else ""
        p_prev = self.model.periods[1] if len(self.model.periods) > 1 else ""

        def get_rev(p): return self.model.profit_loss.get_value_by_key("revenue_operations", p, 0.0)
        def get_pat(p): return self.model.profit_loss.get_value_by_key("profit_after_tax", p, 0.0)
        def get_ebitda(p):
            pbt = self.model.profit_loss.get_value_by_key("profit_before_tax", p, 0.0)
            fin = self.model.profit_loss.get_value_by_key("finance_costs", p, 0.0)
            dep = self.model.profit_loss.get_value_by_key("depreciation_amortisation", p, 0.0)
            return pbt + fin + dep

        kpis = [
            ("Revenue from Operations", get_rev(p_curr), get_rev(p_prev)),
            ("EBITDA", get_ebitda(p_curr), get_ebitda(p_prev)),
            ("Profit After Tax (PAT)", get_pat(p_curr), get_pat(p_prev))
        ]

        curr_row = 10
        for name, v_cy, v_py in kpis:
            diff = v_cy - v_py
            pct = (diff / abs(v_py) * 100) if v_py != 0 else 0
            tag = "Growth" if diff > 0 else ("Decline" if diff < 0 else "Neutral")

            ws.cell(row=curr_row, column=1, value=name).font = self.font_bold
            
            c_cy = ws.cell(row=curr_row, column=2, value=v_cy)
            c_cy.number_format = '#,##0.00'
            c_cy.alignment = self.align_right

            c_py = ws.cell(row=curr_row, column=3, value=v_py)
            c_py.number_format = '#,##0.00'
            c_py.alignment = self.align_right

            c_df = ws.cell(row=curr_row, column=4, value=diff)
            c_df.number_format = '#,##0.00'
            c_df.alignment = self.align_right

            c_pc = ws.cell(row=curr_row, column=5, value=pct / 100.0)
            c_pc.number_format = '0.0%'
            c_pc.alignment = self.align_right

            c_tg = ws.cell(row=curr_row, column=6, value=tag)
            c_tg.alignment = self.align_center
            c_tg.font = self.font_bold

            for col in range(1, 7):
                ws.cell(row=curr_row, column=col).border = self.border_cell
            curr_row += 1

        # Summary of Risk & Variance Findings
        curr_row += 2
        ws.cell(row=curr_row, column=1, value="AUDIT SUMMARY FINDINGS").font = self.font_sub_header
        curr_row += 1
        
        num_vars = len(self.model.variations)
        num_risks = len(self.model.risks)
        
        ws.cell(row=curr_row, column=1, value=f"• Significant Variations (>= 5% threshold): {num_vars} items identified.").font = self.font_regular
        curr_row += 1
        ws.cell(row=curr_row, column=1, value=f"• Potential Risk / Attention Areas: {num_risks} alerts flagged.").font = self.font_regular
        curr_row += 1
        ws.cell(row=curr_row, column=1, value="• Offline Rule Engine: Comprehensive CA Possible Reasons and Audit Documents generated.").font = self.font_regular

        # Mandatory Disclaimer
        curr_row += 3
        ws.merge_cells(start_row=curr_row, start_column=1, end_row=curr_row+2, end_column=6)
        disc_cell = ws.cell(row=curr_row, column=1, value=DISCLAIMER_TEXT)
        disc_cell.font = self.font_disclaimer
        disc_cell.alignment = self.align_left

        self._auto_fit_columns(ws)

    # --- 2/3/4. Statements (BS, P&L, CFS) ---
    def _build_statement_sheet(self, title: str, stmt):
        ws = self.wb.create_sheet(title=title)
        periods = stmt.periods if stmt.periods else self.model.periods
        num_cols = 2 + len(periods)
        self._apply_sheet_header(ws, title, "Standardized Financial Statement", num_cols)

        headers = ["Line Item / Particulars", "Classification Category"] + periods
        for c_idx, h in enumerate(headers, 1):
            cell = ws.cell(row=4, column=c_idx, value=h)
            cell.font = self.font_header
            cell.fill = self.fill_steel
            cell.alignment = self.align_center
            cell.border = self.border_cell

        r_idx = 5
        for item in stmt.line_items:
            ws.cell(row=r_idx, column=1, value=item.original_name).font = self.font_bold if item.is_subtotal else self.font_regular
            ws.cell(row=r_idx, column=2, value=item.category).font = self.font_regular

            for p_idx, p in enumerate(periods, 3):
                val = item.get_value(p, 0.0)
                cell = ws.cell(row=r_idx, column=p_idx, value=val)
                cell.number_format = '#,##0.00'
                cell.alignment = self.align_right
                cell.font = self.font_bold if item.is_subtotal else self.font_regular

            for c in range(1, num_cols + 1):
                ws.cell(row=r_idx, column=c).border = self.border_cell
            r_idx += 1

        self._auto_fit_columns(ws)

    # --- 5. Ratio Analysis ---
    def _build_ratio_sheet(self):
        ws = self.wb.create_sheet(title="Ratio Analysis")
        self._apply_sheet_header(ws, "Financial Ratio Analysis", "Liquidity, Profitability, Solvency, Activity & Cash Ratios", 8)

        headers = ["Category", "Ratio Name", "Formula", "Current Period", "Previous Period", "YoY Change", "Benchmark", "Status"]
        for c_idx, h in enumerate(headers, 1):
            cell = ws.cell(row=4, column=c_idx, value=h)
            cell.font = self.font_header
            cell.fill = self.fill_steel
            cell.alignment = self.align_center
            cell.border = self.border_cell

        r_idx = 5
        for cat, r_list in self.model.ratios.items():
            for r in r_list:
                ws.cell(row=r_idx, column=1, value=cat).font = self.font_bold
                ws.cell(row=r_idx, column=2, value=r["name"]).font = self.font_bold
                ws.cell(row=r_idx, column=3, value=r["formula"]).font = self.font_regular

                c_cy = ws.cell(row=r_idx, column=4, value=r["current_value"])
                c_cy.alignment = self.align_right
                if r["current_value"] is not None:
                    c_cy.number_format = '0.00' if r["unit"] == "x" else ('#,##0.00' if r["unit"] != "%" else '0.00"%"')

                c_py = ws.cell(row=r_idx, column=5, value=r["previous_value"])
                c_py.alignment = self.align_right
                if r["previous_value"] is not None:
                    c_py.number_format = '0.00' if r["unit"] == "x" else ('#,##0.00' if r["unit"] != "%" else '0.00"%"')

                c_chg = ws.cell(row=r_idx, column=6, value=r["absolute_change"])
                c_chg.alignment = self.align_right
                if r["absolute_change"] is not None:
                    c_chg.number_format = '0.00'

                ws.cell(row=r_idx, column=7, value=r["benchmark"]).font = self.font_regular
                
                c_st = ws.cell(row=r_idx, column=8, value=r["status"])
                c_st.alignment = self.align_center
                c_st.font = self.font_bold
                if r["status"] == "Healthy":
                    c_st.fill = self.fill_alert_green
                elif r["status"] in ["Attention", "Critical"]:
                    c_st.fill = self.fill_alert_red

                for c in range(1, 9):
                    ws.cell(row=r_idx, column=c).border = self.border_cell
                r_idx += 1

        self._auto_fit_columns(ws)

    # --- 6. Trend Analysis ---
    def _build_trend_sheet(self):
        ws = self.wb.create_sheet(title="Trend Analysis")
        self._apply_sheet_header(ws, "Horizontal & Common-Size Trend Analysis", "YoY Variances and % Contribution", 8)

        headers = ["Statement", "Particulars", "Current Period", "Previous Period", "YoY Abs Change", "YoY % Change", "Common-Size %", "Trend Direction"]
        for c_idx, h in enumerate(headers, 1):
            cell = ws.cell(row=4, column=c_idx, value=h)
            cell.font = self.font_header
            cell.fill = self.fill_steel
            cell.alignment = self.align_center
            cell.border = self.border_cell

        trends = TrendEngine.analyze_trends(self.model)
        r_idx = 5
        for stmt_name, rows in [
            ("Balance Sheet", trends.get("balance_sheet_trends", [])),
            ("Profit & Loss", trends.get("profit_loss_trends", [])),
            ("Cash Flow", trends.get("cash_flow_trends", []))
        ]:
            for row in rows:
                ws.cell(row=r_idx, column=1, value=stmt_name).font = self.font_bold
                ws.cell(row=r_idx, column=2, value=row["particulars"]).font = self.font_regular
                
                c_cy = ws.cell(row=r_idx, column=3, value=row["cy_value"])
                c_cy.number_format = '#,##0.00'
                c_cy.alignment = self.align_right

                c_py = ws.cell(row=r_idx, column=4, value=row["py_value"])
                c_py.number_format = '#,##0.00'
                c_py.alignment = self.align_right

                c_df = ws.cell(row=r_idx, column=5, value=row["abs_change"])
                c_df.number_format = '#,##0.00'
                c_df.alignment = self.align_right

                c_pc = ws.cell(row=r_idx, column=6, value=(row["pct_change"] / 100.0) if row["pct_change"] is not None else None)
                if c_pc.value is not None:
                    c_pc.number_format = '0.0%'
                c_pc.alignment = self.align_right

                c_cs = ws.cell(row=r_idx, column=7, value=(row["common_size_cy"] / 100.0) if row["common_size_cy"] is not None else None)
                if c_cs.value is not None:
                    c_cs.number_format = '0.0%'
                c_cs.alignment = self.align_right

                ws.cell(row=r_idx, column=8, value=row["trend_direction"]).alignment = self.align_center

                for c in range(1, 9):
                    ws.cell(row=r_idx, column=c).border = self.border_cell
                r_idx += 1

        self._auto_fit_columns(ws)

    # --- 7. Significant Variations ---
    def _build_variance_sheet(self):
        ws = self.wb.create_sheet(title="Significant Variations")
        self._apply_sheet_header(ws, "Significant Variations (>= 5%)", "Material Line Item Movements", 8)

        headers = ["Statement", "Particulars", "Previous Period", "Current Period", "Absolute Change", "Percentage Change", "Movement", "Risk Level"]
        for c_idx, h in enumerate(headers, 1):
            cell = ws.cell(row=4, column=c_idx, value=h)
            cell.font = self.font_header
            cell.fill = self.fill_steel
            cell.alignment = self.align_center
            cell.border = self.border_cell

        r_idx = 5
        for v in self.model.variations:
            ws.cell(row=r_idx, column=1, value=v["statement"]).font = self.font_bold
            ws.cell(row=r_idx, column=2, value=v["particulars"]).font = self.font_bold

            c_py = ws.cell(row=r_idx, column=3, value=v["previous_period_amount"])
            c_py.number_format = '#,##0.00'
            c_py.alignment = self.align_right

            c_cy = ws.cell(row=r_idx, column=4, value=v["current_period_amount"])
            c_cy.number_format = '#,##0.00'
            c_cy.alignment = self.align_right

            c_df = ws.cell(row=r_idx, column=5, value=v["absolute_change"])
            c_df.number_format = '#,##0.00'
            c_df.alignment = self.align_right

            c_pc = ws.cell(row=r_idx, column=6, value=v["percentage_change"] / 100.0)
            c_pc.number_format = '0.0%'
            c_pc.alignment = self.align_right

            c_dir = ws.cell(row=r_idx, column=7, value=v["direction"])
            c_dir.alignment = self.align_center
            c_dir.font = self.font_bold

            c_rk = ws.cell(row=r_idx, column=8, value=v["risk_level"])
            c_rk.alignment = self.align_center
            c_rk.font = self.font_bold
            if v["risk_level"] == "High":
                c_rk.fill = self.fill_alert_red

            for c in range(1, 9):
                ws.cell(row=r_idx, column=c).border = self.border_cell
            r_idx += 1

        self._auto_fit_columns(ws)

    # --- 8. Possible Reasons ---
    def _build_possible_reasons_sheet(self):
        ws = self.wb.create_sheet(title="Possible Reasons")
        self._apply_sheet_header(ws, "Chartered Accountant Possible Reasons", "Contextual Explanations for Significant Variances", 4)

        headers = ["Statement", "Particulars & Movement", "YoY Change", "POSSIBLE REASONS (Professional Hypotheses)"]
        for c_idx, h in enumerate(headers, 1):
            cell = ws.cell(row=4, column=c_idx, value=h)
            cell.font = self.font_header
            cell.fill = self.fill_steel
            cell.alignment = self.align_center
            cell.border = self.border_cell

        r_idx = 5
        for v in self.model.variations:
            ws.cell(row=r_idx, column=1, value=v["statement"]).font = self.font_bold
            ws.cell(row=r_idx, column=2, value=f"{v['particulars']} ({v['direction']})").font = self.font_bold
            ws.cell(row=r_idx, column=3, value=f"{v['percentage_change']:+.1f}%").alignment = self.align_center

            reasons_formatted = "\n• " + "\n• ".join(v["possible_reasons"])
            c_rs = ws.cell(row=r_idx, column=4, value=f"Possible reasons may include:{reasons_formatted}")
            c_rs.font = self.font_regular
            c_rs.alignment = Alignment(horizontal="left", vertical="top", wrap_text=True)

            for c in range(1, 5):
                ws.cell(row=r_idx, column=c).border = self.border_cell
            r_idx += 1

        self._auto_fit_columns(ws, max_width=80)

    # --- 9. Audit Verification ---
    def _build_audit_verification_sheet(self):
        ws = self.wb.create_sheet(title="Audit Verification")
        self._apply_sheet_header(ws, "Audit Verification Checklist", "Required Audit Documents & Justification (Why Required)", 4)

        headers = ["Line Item / Particulars", "Movement", "Required Audit Document / Evidence", "WHY Document is Required (Audit Purpose)"]
        for c_idx, h in enumerate(headers, 1):
            cell = ws.cell(row=4, column=c_idx, value=h)
            cell.font = self.font_header
            cell.fill = self.fill_steel
            cell.alignment = self.align_center
            cell.border = self.border_cell

        r_idx = 5
        for v in self.model.variations:
            for item in v["audit_verification"]:
                ws.cell(row=r_idx, column=1, value=v["particulars"]).font = self.font_bold
                ws.cell(row=r_idx, column=2, value=f"{v['direction']} ({v['percentage_change']:+.1f}%)").alignment = self.align_center
                ws.cell(row=r_idx, column=3, value=item["doc"]).font = self.font_bold
                
                c_why = ws.cell(row=r_idx, column=4, value=item["why"])
                c_why.font = self.font_regular
                c_why.alignment = Alignment(horizontal="left", vertical="top", wrap_text=True)

                for c in range(1, 5):
                    ws.cell(row=r_idx, column=c).border = self.border_cell
                r_idx += 1

        self._auto_fit_columns(ws, max_width=80)

    # --- 10. Risk Areas ---
    def _build_risk_sheet(self):
        ws = self.wb.create_sheet(title="Potential Risk Areas")
        self._apply_sheet_header(ws, "Potential Risk & Attention Areas", "Identified Financial Anomalies & Risk Signals", 5)

        headers = ["Risk Category", "Severity", "Risk Alert Title", "Detailed Description", "Audit & Practical Implications"]
        for c_idx, h in enumerate(headers, 1):
            cell = ws.cell(row=4, column=c_idx, value=h)
            cell.font = self.font_header
            cell.fill = self.fill_steel
            cell.alignment = self.align_center
            cell.border = self.border_cell

        r_idx = 5
        for r in self.model.risks:
            ws.cell(row=r_idx, column=1, value=r["category"]).font = self.font_bold
            
            c_sev = ws.cell(row=r_idx, column=2, value=r["severity"])
            c_sev.alignment = self.align_center
            c_sev.font = self.font_bold
            if r["severity"] == "High":
                c_sev.fill = self.fill_alert_red
            elif r["severity"] == "Medium":
                c_sev.fill = self.fill_highlight

            ws.cell(row=r_idx, column=3, value=r["title"]).font = self.font_bold
            ws.cell(row=r_idx, column=4, value=r["description"]).font = self.font_regular
            ws.cell(row=r_idx, column=5, value=r["audit_implication"]).font = self.font_regular

            for c in range(1, 6):
                ws.cell(row=r_idx, column=c).border = self.border_cell
            r_idx += 1

        self._auto_fit_columns(ws, max_width=70)

    # --- 11. Limitations & Disclaimer ---
    def _build_limitations_sheet(self):
        ws = self.wb.create_sheet(title="Data Limitations")
        self._apply_sheet_header(ws, "Data Limitations & Disclaimer", "Technical Scope & Mandatory Professional Disclaimers", 3)

        ws.cell(row=4, column=1, value="IDENTIFIED DATA & EXTRACTION LIMITATIONS").font = self.font_sub_header
        
        r_idx = 5
        if not self.model.data_limitations:
            ws.cell(row=r_idx, column=1, value="No extraction anomalies or data limitations flagged.").font = self.font_regular
            r_idx += 1
        else:
            for lim in self.model.data_limitations:
                ws.cell(row=r_idx, column=1, value=f"• {lim}").font = self.font_regular
                r_idx += 1

        r_idx += 2
        ws.cell(row=r_idx, column=1, value="PROFESSIONAL DISCLAIMER").font = self.font_sub_header
        r_idx += 1
        
        ws.merge_cells(start_row=r_idx, start_column=1, end_row=r_idx+3, end_column=3)
        c_disc = ws.cell(row=r_idx, column=1, value=DISCLAIMER_TEXT)
        c_disc.font = self.font_disclaimer
        c_disc.alignment = self.align_left

        self._auto_fit_columns(ws)
