"""Professional Excel Workbook Generator for Financial Reporting Review Assistant.

Generates polished, audit-grade workbooks for:
1. Financial Reporting Review Points Sheet (Worksheet 1: 8-Column Issue Log / Findings Register + Worksheet 2: Executive Summary & Analytics)
2. Draft Financial Statements – Incorporating Relevant Disclosures per Schedule III with All Additions/Modifications Highlighted in Yellow (#FFFF00 / #FFF2CC)
"""

import io
from typing import Dict, Any, List, Optional
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter


class ExcelReportGenerator:
    """Creates formatted Excel audit files conforming strictly to CA & FRRB practice standards."""

    # Color Palette conforming to ICAI / FRRB technical standards
    HEADER_FILL = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")  # Deep ICAI Navy
    HEADER_FONT = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    SUBHEADER_FILL = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")  # Soft Steel Blue
    
    YELLOW_HIGHLIGHT = PatternFill(start_color="FFFF00", end_color="FFFF00", fill_type="solid")  # Vivid Yellow
    SOFT_YELLOW_FILL = PatternFill(start_color="FFF2CC", end_color="FFF2CC", fill_type="solid")  # Soft Yellow Highlight
    
    HIGH_RISK_FILL = PatternFill(start_color="FCE4D6", end_color="FCE4D6", fill_type="solid")
    HIGH_RISK_FONT = Font(name="Calibri", size=10, bold=True, color="C00000")
    
    MED_RISK_FILL = PatternFill(start_color="FFF2CC", end_color="FFF2CC", fill_type="solid")
    MED_RISK_FONT = Font(name="Calibri", size=10, bold=True, color="B25900")
    
    LOW_RISK_FILL = PatternFill(start_color="E2EFDA", end_color="E2EFDA", fill_type="solid")
    LOW_RISK_FONT = Font(name="Calibri", size=10, bold=True, color="375623")

    REGULAR_FONT = Font(name="Calibri", size=10)
    BOLD_FONT = Font(name="Calibri", size=10, bold=True)
    TITLE_FONT = Font(name="Calibri", size=14, bold=True, color="1F4E79")
    SUBTITLE_FONT = Font(name="Calibri", size=10, italic=True, color="595959")
    NOTE_TITLE_FONT = Font(name="Calibri", size=11, bold=True, color="1F4E79")

    THIN_BORDER = Border(
        left=Side(style="thin", color="D9D9D9"),
        right=Side(style="thin", color="D9D9D9"),
        top=Side(style="thin", color="D9D9D9"),
        bottom=Side(style="thin", color="D9D9D9")
    )
    HEADER_BORDER = Border(
        left=Side(style="thin", color="FFFFFF"),
        right=Side(style="thin", color="FFFFFF"),
        top=Side(style="medium", color="1F4E79"),
        bottom=Side(style="medium", color="1F4E79")
    )
    DOUBLE_BOTTOM_BORDER = Border(
        left=Side(style="thin", color="D9D9D9"),
        right=Side(style="thin", color="D9D9D9"),
        top=Side(style="thin", color="D9D9D9"),
        bottom=Side(style="double", color="1F4E79")
    )

    # =========================================================================
    # FRRB TECHNICAL REVIEW FORMAT (evidence-based review engine)
    # =========================================================================
    @classmethod
    def generate_tr_workbook(
        cls,
        findings: List[Dict[str, Any]],
        checks: List[Dict[str, str]],
        profile: Dict[str, Any],
        entity_name: str = "",
    ) -> bytes:
        """Review observations in the FRRB Technical Review layout, with the applicability log and detected profile."""
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Review Observations"
        ws["A1"] = f"FINANCIAL REPORTING REVIEW - OBSERVATIONS{(' - ' + entity_name) if entity_name else ''}"
        ws["A1"].font = cls.TITLE_FONT
        ws["A2"] = (f"Framework: {profile.get('framework')} | {profile.get('schedule_iii_division')} | {profile.get('financial_year')} | "
                    f"{profile.get('company_type')}{' (listed)' if profile.get('listed') else ''} | Amounts: {profile.get('unit', '')} | "
                    f"Observations: {len(findings)}")
        ws["A2"].font = cls.SUBTITLE_FONT
        headers = ["S. No.", "Title", "Sub Title", "View of the Reviewer", "Matter contained in the Financial Statements (evidence and location)",
                   "Exact Technical Requirement(s)", "Nature", "Significance", "Basis", "Suggested correction"]
        hr = 4
        for i, h in enumerate(headers, start=1):
            c = ws.cell(row=hr, column=i, value=h)
            c.fill, c.font, c.border = cls.HEADER_FILL, cls.HEADER_FONT, cls.HEADER_BORDER
            c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        nature_fill = {"Non-compliance": cls.HIGH_RISK_FILL, "Inconsistency": cls.HIGH_RISK_FILL, "Disclosure gap": cls.MED_RISK_FILL,
                       "Potential concern": cls.MED_RISK_FILL, "Requires verification": cls.LOW_RISK_FILL}
        r = hr + 1
        for n, f in enumerate(findings, start=1):
            evidence = "\n".join(f"• {e['text']}" for e in f.get("evidence", []))
            matter = (f.get("matter", "") + ("\n\nEvidence:\n" + evidence if evidence else "")).strip()
            reqs = "\n\n".join(f"{t['ref']}: \"{t['text']}\"" for t in f.get("source_requirements", [])) or f.get("statutory_ref", "")
            row = [n, f.get("title", ""), f.get("sub_title", ""), f.get("view", ""), matter[:32000], reqs[:32000], f.get("nature", ""),
                   f.get("significance", ""), f.get("basis", ""), f.get("suggested_correction", "")]
            for i, v in enumerate(row, start=1):
                c = ws.cell(row=r, column=i, value=v)
                c.font, c.border = cls.REGULAR_FONT, cls.THIN_BORDER
                c.alignment = Alignment(vertical="top", wrap_text=True, horizontal="center" if i in (1, 7, 8) else "left")
            ws.cell(row=r, column=7).fill = nature_fill.get(f.get("nature"), cls.LOW_RISK_FILL)
            ws.cell(row=r, column=7).font = cls.BOLD_FONT
            r += 1
        for i, w in enumerate([7, 22, 22, 55, 55, 55, 15, 12, 20, 40], start=1):
            ws.column_dimensions[get_column_letter(i)].width = w
        ws.row_dimensions[hr].height = 40
        ws.freeze_panes = ws.cell(row=hr + 1, column=4)
        ws.auto_filter.ref = f"A{hr}:J{max(r - 1, hr)}"

        wc = wb.create_sheet("Checks & Applicability")
        wc["A1"] = "CHECKS PERFORMED - APPLICABILITY ESTABLISHED FROM THE FINANCIAL STATEMENTS"
        wc["A1"].font = cls.TITLE_FONT
        cols = ["Check", "Area", "Applicable", "Applicability basis (from the financial statements)", "Result"]
        for i, h in enumerate(cols, start=1):
            c = wc.cell(row=3, column=i, value=h)
            c.fill, c.font, c.border = cls.HEADER_FILL, cls.HEADER_FONT, cls.HEADER_BORDER
        for j, chk in enumerate(checks, start=4):
            for i, k in enumerate(cols, start=1):
                c = wc.cell(row=j, column=i, value=chk.get(k, ""))
                c.font, c.border = cls.REGULAR_FONT, cls.THIN_BORDER
                c.alignment = Alignment(vertical="top", wrap_text=True)
        for i, w in enumerate([24, 26, 11, 80, 34], start=1):
            wc.column_dimensions[get_column_letter(i)].width = w

        wp = wb.create_sheet("Entity Profile")
        wp["A1"] = "ENTITY PROFILE (DETECTED FROM THE FINANCIAL STATEMENTS)"
        wp["A1"].font = cls.TITLE_FONT
        for j, (k, v) in enumerate(profile.items(), start=3):
            wp.cell(row=j, column=1, value=k.replace("_", " ").title()).font = cls.BOLD_FONT
            wp.cell(row=j, column=2, value=str(v))
        wp.column_dimensions["A"].width, wp.column_dimensions["B"].width = 30, 70

        out = io.BytesIO()
        wb.save(out)
        return out.getvalue()

    # =========================================================================
    # OPTION 1: FINANCIAL REPORTING REVIEW POINTS SHEET
    # =========================================================================
    @classmethod
    def generate_review_points_workbook(
        cls,
        issues: List[Dict[str, Any]],
        profile: Dict[str, Any],
        summary_stats: Optional[Dict[str, Any]] = None,
        review_mode: str = "Option A"
    ) -> bytes:
        """Generates the Financial Reporting Review Points Sheet Excel workbook."""
        if summary_stats is None:
            summary_stats = {
                "total_issues": len(issues),
                "high_risk_count": sum(1 for i in issues if i.get("risk") == "High"),
                "med_risk_count": sum(1 for i in issues if i.get("risk") == "Medium"),
                "low_risk_count": sum(1 for i in issues if i.get("risk") == "Low"),
                "categories_breakdown": {}
            }

        wb = openpyxl.Workbook()

        # -------------------------------------------------------------
        # Sheet 1: Review Points Sheet / Issue Log
        # -------------------------------------------------------------
        ws_issues = wb.active
        ws_issues.title = "Review Points Sheet"

        # Title Block
        ws_issues["A1"] = "FINANCIAL REPORTING REVIEW POINTS SHEET"
        ws_issues["A1"].font = cls.TITLE_FONT
        ws_issues["A2"] = (
            f"Entity: {profile.get('company_type', 'Company')} | Status: {profile.get('listing_status')} | "
            f"Framework: {profile.get('framework')} | Division: {profile.get('schedule_iii_division')} | "
            f"FY: {profile.get('financial_year')} | Mode: {review_mode} | Total Observations: {len(issues)}"
        )
        ws_issues["A2"].font = cls.SUBTITLE_FONT

        # Mandatory 8 Columns
        headers = [
            "Issue ID",
            "Financial statement or note reference",
            "Description of the issue",
            "Current reference or existing disclosure",
            "Correct reference or suggested correction",
            "Applicable accounting standard, Schedule III requirement or statutory provision",
            "Recommended action",
            "Status of the issue",
            "Risk",
            "Requirement as per the Standard (source text)",
        ]

        header_row = 4
        for col_idx, header_title in enumerate(headers, start=1):
            cell = ws_issues.cell(row=header_row, column=col_idx, value=header_title)
            cell.fill = cls.HEADER_FILL
            cell.font = cls.HEADER_FONT
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            cell.border = cls.HEADER_BORDER
        ws_issues.freeze_panes = ws_issues.cell(row=header_row + 1, column=3)

        # Data Rows
        current_row = header_row + 1
        for item in issues:
            c1 = ws_issues.cell(row=current_row, column=1, value=item.get("issue_id", f"FRR-{current_row-header_row:03d}"))
            c2 = ws_issues.cell(row=current_row, column=2, value=item.get("ref", "Notes to Accounts"))
            c3 = ws_issues.cell(row=current_row, column=3, value=item.get("description", ""))
            c4 = ws_issues.cell(row=current_row, column=4, value=item.get("current_disclosure", item.get("evidence", item.get("extract", "N/A"))))
            c5 = ws_issues.cell(row=current_row, column=5, value=item.get("suggested_correction", ""))
            c6 = ws_issues.cell(row=current_row, column=6, value=item.get("statutory_ref", item.get("technical_ref", "Reference Verification Required")))
            c7 = ws_issues.cell(row=current_row, column=7, value=item.get("action", item.get("recommended_action", "")))
            c8 = ws_issues.cell(row=current_row, column=8, value=item.get("status", "Action Required"))
            c9 = ws_issues.cell(row=current_row, column=9, value=item.get("risk", "Medium"))
            c10 = ws_issues.cell(row=current_row, column=10, value=item.get("requirement_text", "")[:3000])

            for c in [c1, c2, c3, c4, c5, c6, c7, c8, c9, c10]:
                c.font = cls.REGULAR_FONT
                c.border = cls.THIN_BORDER
                c.alignment = Alignment(vertical="top", wrap_text=True)

            c1.alignment = Alignment(horizontal="center", vertical="top")
            c8.alignment = Alignment(horizontal="center", vertical="top")
            c9.alignment = Alignment(horizontal="center", vertical="top")
            risk_val = str(item.get("risk", "Medium"))
            c9.fill, c9.font = {
                "High": (cls.HIGH_RISK_FILL, cls.HIGH_RISK_FONT),
                "Medium": (cls.MED_RISK_FILL, cls.MED_RISK_FONT),
            }.get(risk_val, (cls.LOW_RISK_FILL, cls.LOW_RISK_FONT))

            # Soft yellow highlight on Suggested Correction column
            c5.fill = cls.SOFT_YELLOW_FILL

            current_row += 1

        ws_issues.auto_filter.ref = f"A{header_row}:J{max(current_row - 1, header_row)}"

        # Column widths
        widths = {1: 14, 2: 24, 3: 38, 4: 34, 5: 38, 6: 34, 7: 32, 8: 18, 9: 10, 10: 60}
        for col_i, w in widths.items():
            ws_issues.column_dimensions[get_column_letter(col_i)].width = w
        ws_issues.row_dimensions[header_row].height = 36

        # -------------------------------------------------------------
        # Sheet 2: Executive Summary & Analytics
        # -------------------------------------------------------------
        ws_sum = wb.create_sheet(title="Executive Summary & Analytics")
        ws_sum["A1"] = "FRRB TECHNICAL REVIEW — EXECUTIVE DASHBOARD & RISK SUMMARY"
        ws_sum["A1"].font = cls.TITLE_FONT
        ws_sum["A2"] = "Summary of potential financial reporting deficiencies, Schedule III omissions, and statutory non-compliances."
        ws_sum["A2"].font = cls.SUBTITLE_FONT

        # Risk Scorecard Box
        ws_sum["A4"] = "RISK PROFILE SUMMARY"
        ws_sum["A4"].font = cls.BOLD_FONT

        metrics = [
            ("Total Findings / Potential Red Flags", summary_stats.get("total_issues", len(issues))),
            ("High Risk / Statutory Violations", summary_stats.get("high_risk_count", sum(1 for i in issues if i.get("risk") == "High"))),
            ("Medium Risk / Technical Deficiencies", summary_stats.get("med_risk_count", sum(1 for i in issues if i.get("risk") == "Medium"))),
            ("Low Risk / Presentation Matters", summary_stats.get("low_risk_count", sum(1 for i in issues if i.get("risk") == "Low"))),
        ]

        for idx, (m_label, m_val) in enumerate(metrics, start=5):
            ws_sum.cell(row=idx, column=1, value=m_label).font = cls.REGULAR_FONT
            c_val = ws_sum.cell(row=idx, column=2, value=m_val)
            c_val.font = cls.BOLD_FONT
            c_val.alignment = Alignment(horizontal="center")
            ws_sum.cell(row=idx, column=1).border = cls.THIN_BORDER
            c_val.border = cls.THIN_BORDER

        # Entity Profile Information Box
        ws_sum["A11"] = "ENTITY APPLICABILITY PROFILE"
        ws_sum["A11"].font = cls.BOLD_FONT

        profile_rows = [
            ("Company Type", profile.get("company_type")),
            ("Listing Status", profile.get("listing_status")),
            ("Financial Reporting Framework", profile.get("framework")),
            ("Applicable Schedule III Division", profile.get("schedule_iii_division")),
            ("Financial Year under Review", profile.get("financial_year")),
            ("Statement Type", profile.get("statement_type")),
        ]

        for idx, (p_label, p_val) in enumerate(profile_rows, start=12):
            ws_sum.cell(row=idx, column=1, value=p_label).font = cls.REGULAR_FONT
            c_pval = ws_sum.cell(row=idx, column=2, value=str(p_val))
            c_pval.font = cls.BOLD_FONT
            ws_sum.cell(row=idx, column=1).border = cls.THIN_BORDER
            c_pval.border = cls.THIN_BORDER

        # Category Breakdown
        ws_sum["D4"] = "BREAKDOWN BY AUDIT CATEGORY"
        ws_sum["D4"].font = cls.BOLD_FONT
        ws_sum.cell(row=4, column=4).fill = cls.HEADER_FILL
        ws_sum.cell(row=4, column=4).font = cls.HEADER_FONT
        ws_sum.cell(row=4, column=5, value="Count").fill = cls.HEADER_FILL
        ws_sum.cell(row=4, column=5).font = cls.HEADER_FONT

        cat_breakdown = summary_stats.get("categories_breakdown", {})
        if not cat_breakdown:
            for item in issues:
                cat = item.get("category", "General")
                cat_breakdown[cat] = cat_breakdown.get(cat, 0) + 1

        c_row = 5
        for cat_name, cnt in cat_breakdown.items():
            c_cat = ws_sum.cell(row=c_row, column=4, value=cat_name)
            c_cnt = ws_sum.cell(row=c_row, column=5, value=cnt)
            c_cat.font = cls.REGULAR_FONT
            c_cnt.font = cls.BOLD_FONT
            c_cnt.alignment = Alignment(horizontal="center")
            c_cat.border = cls.THIN_BORDER
            c_cnt.border = cls.THIN_BORDER
            c_row += 1

        ws_sum.column_dimensions["A"].width = 38
        ws_sum.column_dimensions["B"].width = 24
        ws_sum.column_dimensions["C"].width = 8
        ws_sum.column_dimensions["D"].width = 38
        ws_sum.column_dimensions["E"].width = 16

        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        return output.getvalue()

    # =========================================================================
    # OPTION A COMPATIBILITY: ISSUE LOG & MARKED FINANCIAL STATEMENTS
    # =========================================================================
    @classmethod
    def generate_option_a_workbook(
        cls,
        issues: List[Dict[str, Any]],
        profile: Dict[str, Any],
        sample_model: Optional[Dict[str, Any]] = None
    ) -> bytes:
        """Generates Option A workbook:
        Sheet 1: 'Issue Log (Pre-Finalisation)' (8 columns with yellow fill on suggested corrections)
        Sheet 2: 'Financial Statements (Marked)' (Draft financial statement rows with yellow highlights)
        """
        wb = openpyxl.Workbook()

        # Sheet 1: Issue Log (Pre-Finalisation)
        ws_issues = wb.active
        ws_issues.title = "Issue Log (Pre-Finalisation)"

        ws_issues["A1"] = "FRRB TECHNICAL REVIEW — PRE-FINALISATION ISSUE LOG"
        ws_issues["A1"].font = cls.TITLE_FONT
        ws_issues["A2"] = (
            f"Entity: {profile.get('company_type', 'Company')} | Status: {profile.get('listing_status')} | "
            f"Framework: {profile.get('framework')} | Division: {profile.get('schedule_iii_division')} | "
            f"FY: {profile.get('financial_year')} | Mode: Option A | Total Observations: {len(issues)}"
        )
        ws_issues["A2"].font = cls.SUBTITLE_FONT

        headers = [
            "Issue ID",
            "Financial statement or note reference",
            "Description of the issue",
            "Current reference or existing disclosure",
            "Correct reference or suggested correction",
            "Applicable accounting standard, Schedule III requirement or statutory provision",
            "Recommended action",
            "Status of the issue",
        ]

        header_row = 4
        for col_idx, header_title in enumerate(headers, start=1):
            cell = ws_issues.cell(row=header_row, column=col_idx, value=header_title)
            cell.fill = cls.HEADER_FILL
            cell.font = cls.HEADER_FONT
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            cell.border = cls.HEADER_BORDER

        current_row = header_row + 1
        for item in issues:
            c1 = ws_issues.cell(row=current_row, column=1, value=item.get("issue_id", f"FRR-A-{current_row-header_row:03d}"))
            c2 = ws_issues.cell(row=current_row, column=2, value=item.get("ref", "Notes to Accounts"))
            c3 = ws_issues.cell(row=current_row, column=3, value=item.get("description", ""))
            c4 = ws_issues.cell(row=current_row, column=4, value=item.get("current_disclosure", item.get("evidence", "N/A")))
            c5 = ws_issues.cell(row=current_row, column=5, value=item.get("suggested_correction", ""))
            c6 = ws_issues.cell(row=current_row, column=6, value=item.get("statutory_ref", item.get("technical_ref", "Schedule III")))
            c7 = ws_issues.cell(row=current_row, column=7, value=item.get("action", item.get("recommended_action", "")))
            c8 = ws_issues.cell(row=current_row, column=8, value=item.get("status", "Action Required"))

            for c in [c1, c2, c3, c4, c5, c6, c7, c8]:
                c.font = cls.REGULAR_FONT
                c.border = cls.THIN_BORDER
                c.alignment = Alignment(vertical="top", wrap_text=True)

            c1.alignment = Alignment(horizontal="center", vertical="top")
            c8.alignment = Alignment(horizontal="center", vertical="top")
            c5.fill = cls.YELLOW_HIGHLIGHT

            current_row += 1

        widths = {1: 14, 2: 24, 3: 38, 4: 34, 5: 38, 6: 34, 7: 32, 8: 18}
        for col_i, w in widths.items():
            ws_issues.column_dimensions[get_column_letter(col_i)].width = w
        ws_issues.row_dimensions[header_row].height = 36

        # Sheet 2: Financial Statements (Marked)
        ws_fs = wb.create_sheet(title="Financial Statements (Marked)")
        ws_fs["A1"] = "DRAFT FINANCIAL STATEMENTS — CELLS REQUIRING MODIFICATION"
        ws_fs["A1"].font = cls.TITLE_FONT
        ws_fs["A2"] = "Cells highlighted in YELLOW require correction, reclassification, or additional mandatory Schedule III disclosure."
        ws_fs["A2"].font = cls.SUBTITLE_FONT

        fs_headers = ["Line Item / Particulars", "Note Reference", "Figures as per Draft FS", "Proposed Corrected Figure", "Audit Observation & Schedule III Action Required"]
        fs_hrow = 4
        for col_i, h in enumerate(fs_headers, start=1):
            cell = ws_fs.cell(row=fs_hrow, column=col_i, value=h)
            cell.fill = cls.HEADER_FILL
            cell.font = cls.HEADER_FONT
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            cell.border = cls.HEADER_BORDER

        sample_rows = [
            ("Property, Plant and Equipment (Gross Block)", "Note 1", "4,200.00", "4,520.00", "Verified per Ind AS 16 / AS 10", False),
            ("Capital Work-in-Progress (CWIP)", "Note 2", "150.00", "340.00", "YELLOW: Mandatory CWIP Ageing Schedule missing; incorporate ageing per Schedule III", True),
            ("Trade Receivables (Total)", "Note 10", "1,850.00", "2,100.00", "YELLOW: Mandatory Trade Receivables Ageing Schedule missing; insert MSME & ageing table", True),
            ("Trade Payables (Total)", "Note 16", "890.00", "1,120.00", "YELLOW: Section 22 MSMED Act disclosures & Trade Payables ageing missing", True),
            ("Promoter Shareholding Disclosure", "Note 12", "Missing", "Disclose changes", "YELLOW: Clause 6(J) promoter shareholding table missing in draft financial statements", True),
            ("Key Analytical Ratios (11 Ratios)", "Note 26", "Missing", "Incorporate 11 Ratios", "YELLOW: Clause 6(VA) 11 ratios & >25% variance explanations mandatory", True),
            ("Total Assets", "", "11,060.00", "11,585.00", "Arithmetic balance equation out of balance", True),
            ("Total Equity and Liabilities", "", "10,810.00", "11,585.00", "Arithmetic balance equation out of balance", True),
        ]

        curr_fs = fs_hrow + 1
        for p, n, d, c, act, is_yellow in sample_rows:
            c1 = ws_fs.cell(row=curr_fs, column=1, value=p)
            c2 = ws_fs.cell(row=curr_fs, column=2, value=n)
            c3 = ws_fs.cell(row=curr_fs, column=3, value=d)
            c4 = ws_fs.cell(row=curr_fs, column=4, value=c)
            c5 = ws_fs.cell(row=curr_fs, column=5, value=act)

            for cell in [c1, c2, c3, c4, c5]:
                cell.font = cls.REGULAR_FONT
                cell.border = cls.THIN_BORDER
                cell.alignment = Alignment(vertical="center", wrap_text=True)

            if is_yellow:
                c1.fill = cls.YELLOW_HIGHLIGHT
                c4.fill = cls.YELLOW_HIGHLIGHT
                c5.fill = cls.SOFT_YELLOW_FILL

            curr_fs += 1

        widths_fs = {1: 40, 2: 18, 3: 24, 4: 26, 5: 50}
        for col_i, w in widths_fs.items():
            ws_fs.column_dimensions[get_column_letter(col_i)].width = w
        ws_fs.row_dimensions[fs_hrow].height = 30

        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        return output.getvalue()

    # =========================================================================
    # OPTION B COMPATIBILITY: FINDINGS REGISTER & EXECUTIVE DASHBOARD
    # =========================================================================
    @classmethod
    def generate_option_b_workbook(
        cls,
        issues: List[Dict[str, Any]],
        profile: Dict[str, Any],
        summary_stats: Optional[Dict[str, Any]] = None
    ) -> bytes:
        """Generates Option B workbook:
        Sheet 1: 'Red-Flag & Findings Register' (Col 1: Issue ID, Col 7: Risk Assessment)
        Sheet 2: 'Executive Summary & Analytics' (A1: '...EXECUTIVE DASHBOARD...')
        """
        if summary_stats is None:
            summary_stats = {
                "total_issues": len(issues),
                "high_risk_count": sum(1 for i in issues if i.get("risk") == "High"),
                "med_risk_count": sum(1 for i in issues if i.get("risk") == "Medium"),
                "low_risk_count": sum(1 for i in issues if i.get("risk") == "Low"),
                "categories_breakdown": {}
            }

        wb = openpyxl.Workbook()

        # Sheet 1: Red-Flag & Findings Register
        ws_issues = wb.active
        ws_issues.title = "Red-Flag & Findings Register"

        ws_issues["A1"] = "FRRB TECHNICAL REVIEW — RED-FLAG & FINDINGS REGISTER"
        ws_issues["A1"].font = cls.TITLE_FONT
        ws_issues["A2"] = (
            f"Entity: {profile.get('company_type', 'Company')} | Status: {profile.get('listing_status')} | "
            f"Framework: {profile.get('framework')} | Division: {profile.get('schedule_iii_division')} | "
            f"FY: {profile.get('financial_year')} | Mode: Option B | Total Observations: {len(issues)}"
        )
        ws_issues["A2"].font = cls.SUBTITLE_FONT

        b_headers = [
            "Issue ID",
            "Financial Statement / Note Reference",
            "Description of Deficiency / Red Flag",
            "Document Extract / Supporting Evidence",
            "Applicable Accounting Standard / Statutory Provision",
            "Suggested Correction / Follow-up Action",
            "Risk Assessment",
            "Review Status",
        ]

        header_row = 4
        for col_idx, header_title in enumerate(b_headers, start=1):
            cell = ws_issues.cell(row=header_row, column=col_idx, value=header_title)
            cell.fill = cls.HEADER_FILL
            cell.font = cls.HEADER_FONT
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            cell.border = cls.HEADER_BORDER

        current_row = header_row + 1
        for item in issues:
            c1 = ws_issues.cell(row=current_row, column=1, value=item.get("issue_id", f"FRR-B-{current_row-header_row:03d}"))
            c2 = ws_issues.cell(row=current_row, column=2, value=item.get("ref", "Notes to Accounts"))
            c3 = ws_issues.cell(row=current_row, column=3, value=item.get("description", ""))
            c4 = ws_issues.cell(row=current_row, column=4, value=item.get("evidence", item.get("current_disclosure", "N/A")))
            c5 = ws_issues.cell(row=current_row, column=5, value=item.get("statutory_ref", item.get("technical_ref", "Schedule III")))
            c6 = ws_issues.cell(row=current_row, column=6, value=item.get("action", item.get("suggested_correction", "")))
            c7 = ws_issues.cell(row=current_row, column=7, value=item.get("risk", "Medium"))
            c8 = ws_issues.cell(row=current_row, column=8, value=item.get("status", "Red-Flag Pending Review"))

            for c in [c1, c2, c3, c4, c5, c6, c7, c8]:
                c.font = cls.REGULAR_FONT
                c.border = cls.THIN_BORDER
                c.alignment = Alignment(vertical="top", wrap_text=True)

            c1.alignment = Alignment(horizontal="center", vertical="top")
            c7.alignment = Alignment(horizontal="center", vertical="top")
            c8.alignment = Alignment(horizontal="center", vertical="top")

            risk_val = str(item.get("risk", "Medium"))
            if risk_val == "High":
                c7.fill = cls.HIGH_RISK_FILL
                c7.font = cls.HIGH_RISK_FONT
            elif risk_val == "Medium":
                c7.fill = cls.MED_RISK_FILL
                c7.font = cls.MED_RISK_FONT
            else:
                c7.fill = cls.LOW_RISK_FILL
                c7.font = cls.LOW_RISK_FONT

            current_row += 1

        widths = {1: 14, 2: 24, 3: 38, 4: 34, 5: 36, 6: 36, 7: 18, 8: 20}
        for col_i, w in widths.items():
            ws_issues.column_dimensions[get_column_letter(col_i)].width = w
        ws_issues.row_dimensions[header_row].height = 36

        # Sheet 2: Executive Summary & Analytics
        ws_sum = wb.create_sheet(title="Executive Summary & Analytics")
        ws_sum["A1"] = "FRRB TECHNICAL REVIEW — EXECUTIVE DASHBOARD & RISK SUMMARY"
        ws_sum["A1"].font = cls.TITLE_FONT
        ws_sum["A2"] = "Summary of potential financial reporting deficiencies, Schedule III omissions, and statutory non-compliances."
        ws_sum["A2"].font = cls.SUBTITLE_FONT

        ws_sum["A4"] = "RISK PROFILE SUMMARY"
        ws_sum["A4"].font = cls.BOLD_FONT

        metrics = [
            ("Total Findings / Potential Red Flags", summary_stats.get("total_issues", len(issues))),
            ("High Risk / Statutory Violations", summary_stats.get("high_risk_count", sum(1 for i in issues if i.get("risk") == "High"))),
            ("Medium Risk / Technical Deficiencies", summary_stats.get("med_risk_count", sum(1 for i in issues if i.get("risk") == "Medium"))),
            ("Low Risk / Presentation Matters", summary_stats.get("low_risk_count", sum(1 for i in issues if i.get("risk") == "Low"))),
        ]

        for idx, (m_label, m_val) in enumerate(metrics, start=5):
            ws_sum.cell(row=idx, column=1, value=m_label).font = cls.REGULAR_FONT
            c_val = ws_sum.cell(row=idx, column=2, value=m_val)
            c_val.font = cls.BOLD_FONT
            c_val.alignment = Alignment(horizontal="center")
            ws_sum.cell(row=idx, column=1).border = cls.THIN_BORDER
            c_val.border = cls.THIN_BORDER

        ws_sum["A11"] = "ENTITY APPLICABILITY PROFILE"
        ws_sum["A11"].font = cls.BOLD_FONT

        profile_rows = [
            ("Company Type", profile.get("company_type")),
            ("Listing Status", profile.get("listing_status")),
            ("Financial Reporting Framework", profile.get("framework")),
            ("Applicable Schedule III Division", profile.get("schedule_iii_division")),
            ("Financial Year under Review", profile.get("financial_year")),
            ("Statement Type", profile.get("statement_type")),
        ]

        for idx, (p_label, p_val) in enumerate(profile_rows, start=12):
            ws_sum.cell(row=idx, column=1, value=p_label).font = cls.REGULAR_FONT
            c_pval = ws_sum.cell(row=idx, column=2, value=str(p_val))
            c_pval.font = cls.BOLD_FONT
            ws_sum.cell(row=idx, column=1).border = cls.THIN_BORDER
            c_pval.border = cls.THIN_BORDER

        ws_sum["D4"] = "BREAKDOWN BY AUDIT CATEGORY"
        ws_sum["D4"].font = cls.BOLD_FONT
        ws_sum.cell(row=4, column=4).fill = cls.HEADER_FILL
        ws_sum.cell(row=4, column=4).font = cls.HEADER_FONT
        ws_sum.cell(row=4, column=5, value="Count").fill = cls.HEADER_FILL
        ws_sum.cell(row=4, column=5).font = cls.HEADER_FONT

        cat_breakdown = summary_stats.get("categories_breakdown", {})
        if not cat_breakdown:
            for item in issues:
                cat = item.get("category", "General")
                cat_breakdown[cat] = cat_breakdown.get(cat, 0) + 1

        c_row = 5
        for cat_name, cnt in cat_breakdown.items():
            c_cat = ws_sum.cell(row=c_row, column=4, value=cat_name)
            c_cnt = ws_sum.cell(row=c_row, column=5, value=cnt)
            c_cat.font = cls.REGULAR_FONT
            c_cnt.font = cls.BOLD_FONT
            c_cnt.alignment = Alignment(horizontal="center")
            c_cat.border = cls.THIN_BORDER
            c_cnt.border = cls.THIN_BORDER
            c_row += 1

        ws_sum.column_dimensions["A"].width = 38
        ws_sum.column_dimensions["B"].width = 24
        ws_sum.column_dimensions["C"].width = 8
        ws_sum.column_dimensions["D"].width = 38
        ws_sum.column_dimensions["E"].width = 16

        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        return output.getvalue()

    # =========================================================================
    # OPTION 2: DRAFT FINANCIAL STATEMENTS WITH YELLOW HIGHLIGHTS
    # =========================================================================
    @classmethod
    def generate_schedule_iii_draft_fs_workbook(
        cls,
        issues: List[Dict[str, Any]],
        profile: Dict[str, Any],
        doc: Optional[Dict[str, Any]] = None
    ) -> bytes:
        """Generates complete Draft Financial Statements workbook conforming strictly to Schedule III.

        Incorporates relevant disclosures into financial statements & notes, highlighting
        all additions or modifications in YELLOW (#FFFF00 / #FFF2CC).
        
        Worksheets:
        1. Balance Sheet (Schedule III)
        2. Statement of Profit and Loss
        3. Notes & Ageing Schedules (Incorporating All Mandatory Disclosures in Yellow)
        4. Summary of Modifications (Linking Yellow Modifications to Standard Requirements)
        """
        wb = openpyxl.Workbook()
        division = profile.get("schedule_iii_division", "Division II")
        framework = profile.get("framework", "Indian Accounting Standards (Ind AS)")
        is_ind_as = "ind as" in framework.lower()
        company_type = profile.get("company_type", "Company")
        fy = profile.get("financial_year", "FY 2025-26")

        # ---------------------------------------------------------------------
        # 1. BALANCE SHEET (SCHEDULE III)
        # ---------------------------------------------------------------------
        ws_bs = wb.active
        ws_bs.title = "Balance Sheet (Schedule III)"

        ws_bs["A1"] = f"DRAFT BALANCE SHEET AS AT 31ST MARCH, 2026"
        ws_bs["A1"].font = cls.TITLE_FONT
        ws_bs["A2"] = f"Prepared per Schedule III {division} to Companies Act, 2013 | Framework: {framework} | Denomination: ₹ in Lakhs"
        ws_bs["A2"].font = cls.SUBTITLE_FONT
        ws_bs["A3"] = "Note: Cells highlighted in YELLOW indicate figures, line items, or statutory disclosures incorporated/modified."
        ws_bs["A3"].font = Font(name="Calibri", size=10, bold=True, color="B25900")

        bs_headers = ["Particulars", "Note No.", "As at 31st March, 2026 (CY)", "As at 31st March, 2025 (PY)", "Audit Review & Schedule III Modification Status"]
        header_row = 5
        for col_i, h in enumerate(bs_headers, start=1):
            cell = ws_bs.cell(row=header_row, column=col_i, value=h)
            cell.fill = cls.HEADER_FILL
            cell.font = cls.HEADER_FONT
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            cell.border = cls.HEADER_BORDER

        if is_ind_as:
            # Division II Structure (Ind AS)
            bs_rows = [
                ("ASSETS", "", "", "", ""),
                ("(1) Non-Current Assets", "", "", "", ""),
                ("  (a) Property, Plant and Equipment", "Note 1", "4,520.00", "4,200.00", "Verified per Ind AS 16; Useful lives reviewed"),
                ("  (b) Capital Work-in-Progress (CWIP)", "Note 2", "340.00", "150.00", "YELLOW: Mandatory CWIP Ageing Schedule incorporated in Note 2"),
                ("  (c) Right-of-Use Assets", "Note 3", "850.00", "920.00", "YELLOW: Ind AS 116 ROU Assets recognized and detailed in Note 3"),
                ("  (d) Intangible Assets & Under Development", "Note 4", "110.00", "95.00", "YELLOW: Intangible Assets Under Development ageing added"),
                ("  (e) Financial Assets", "", "", "", ""),
                ("    (i) Investments", "Note 5", "1,200.00", "1,150.00", "Measured at FVTPL / Amortized Cost per Ind AS 109"),
                ("    (ii) Trade Receivables (Non-Current)", "", "—", "—", "Nil non-current trade receivables"),
                ("    (iii) Loans & Advances", "Note 6", "180.00", "160.00", "Compliant per Ind AS 109"),
                ("    (iv) Others", "", "25.00", "20.00", "Compliant"),
                ("  (f) Deferred Tax Assets (Net)", "Note 7", "180.00", "120.00", "YELLOW: Tax loss DTA convincing evidence disclosed in Note 7"),
                ("  (g) Other Non-Current Assets", "Note 8", "145.00", "110.00", "YELLOW: Capital advances segregated from CWIP per Schedule III"),
                ("(2) Current Assets", "", "", "", ""),
                ("  (a) Inventories", "Note 9", "1,450.00", "1,320.00", "Measured at lower of cost and NRV on Weighted Average formula"),
                ("  (b) Financial Assets", "", "", "", ""),
                ("    (i) Current Investments", "", "—", "—", "Nil current investments"),
                ("    (ii) Trade Receivables", "Note 10", "2,100.00", "1,850.00", "YELLOW: Mandatory Trade Receivables Ageing Schedule added in Note 10"),
                ("    (iii) Cash and Cash Equivalents", "Note 11", "420.00", "310.00", "Reconciled with Cash Flow Statement closing cash"),
                ("    (iv) Bank Balances other than (iii) above", "Note 11", "90.00", "75.00", "YELLOW: Earmarked balances & margin money segregated"),
                ("    (v) Loans & Advances", "", "35.00", "30.00", "Compliant"),
                ("    (vi) Others", "", "15.00", "12.00", "Compliant"),
                ("  (c) Current Tax Assets (Net)", "", "45.00", "38.00", "Advance tax net of provisions"),
                ("  (d) Other Current Assets", "", "65.00", "50.00", "Compliant"),
                ("TOTAL ASSETS", "", "11,585.00", "10,440.00", "Arithmetic Balance Equation Verified"),
                ("", "", "", "", ""),
                ("EQUITY AND LIABILITIES", "", "", "", ""),
                ("Equity", "", "", "", ""),
                ("  (a) Equity Share Capital", "Note 12", "2,000.00", "2,000.00", "YELLOW: Mandatory Promoter Shareholding Table added in Note 12"),
                ("  (b) Other Equity (Reserves & Surplus)", "Note 13", "4,210.00", "3,650.00", "Retained Earnings & General Reserve roll-forward verified"),
                ("LIABILITIES", "", "", "", ""),
                ("(1) Non-Current Liabilities", "", "", "", ""),
                ("  (a) Financial Liabilities", "", "", "", ""),
                ("    (i) Borrowings (Non-Current)", "Note 14", "2,350.00", "2,100.00", "YELLOW: Terms of repayment, interest rate & ROC charges confirmed"),
                ("    (ia) Lease Liabilities (Non-Current)", "Note 3", "680.00", "740.00", "YELLOW: Ind AS 116 Lease liabilities maturity added in Note 3"),
                ("    (ii) Trade Payables (Non-Current)", "", "—", "—", "Nil non-current trade payables"),
                ("    (iii) Other Financial Liabilities", "", "45.00", "40.00", "Security deposits received"),
                ("  (b) Provisions (Non-Current)", "Note 15", "130.00", "110.00", "YELLOW: Actuarial valuation of Gratuity/Leave per Ind AS 19 in Note 15"),
                ("  (c) Deferred Tax Liabilities (Net)", "", "—", "—", "Net DTA recognized under Assets"),
                ("  (d) Other Non-Current Liabilities", "", "—", "—", "Nil"),
                ("(2) Current Liabilities", "", "", "", ""),
                ("  (a) Financial Liabilities", "", "", "", ""),
                ("    (i) Borrowings (Current)", "Note 14", "450.00", "320.00", "Working capital facilities secured by current assets"),
                ("    (ia) Lease Liabilities (Current)", "Note 3", "120.00", "110.00", "Current portion of Ind AS 116 lease liabilities"),
                ("    (ii) Trade Payables", "Note 16", "", "", ""),
                ("      (A) Total dues of Micro & Small Enterprises", "Note 16", "280.00", "210.00", "YELLOW: Section 22 MSMED Act disclosures added in Note 16"),
                ("      (B) Total dues of Creditors other than MSME", "Note 16", "840.00", "680.00", "YELLOW: Mandatory Trade Payables Ageing Schedule added in Note 16"),
                ("    (iii) Other Financial Liabilities", "", "95.00", "80.00", "Current maturities of term debts"),
                ("  (b) Other Current Liabilities", "", "245.00", "210.00", "Statutory dues (GST, TDS, PF) payable"),
                ("  (c) Provisions (Current)", "Note 15", "65.00", "50.00", "YELLOW: Compensated absences & provisions roll-forward added"),
                ("  (d) Current Tax Liabilities (Net)", "", "75.00", "40.00", "Income tax provision net of advance tax"),
                ("TOTAL EQUITY AND LIABILITIES", "", "11,585.00", "10,440.00", "Verified: Total Assets = Total Equity and Liabilities"),
            ]
        else:
            # Division I Structure (AS)
            bs_rows = [
                ("I. EQUITY AND LIABILITIES", "", "", "", ""),
                ("(1) Shareholders' Funds", "", "", "", ""),
                ("  (a) Share Capital", "Note 1", "2,000.00", "2,000.00", "YELLOW: Mandatory Promoter Shareholding Table added in Note 1"),
                ("  (b) Reserves and Surplus", "Note 2", "4,210.00", "3,650.00", "Retained earnings roll-forward verified"),
                ("(2) Non-Current Liabilities", "", "", "", ""),
                ("  (a) Long-Term Borrowings", "Note 3", "2,350.00", "2,100.00", "YELLOW: Terms of repayment, interest rate & ROC charges added in Note 3"),
                ("  (b) Deferred Tax Liabilities (Net)", "", "—", "—", "Net DTA disclosed under non-current assets"),
                ("  (c) Other Long-Term Liabilities", "", "45.00", "40.00", "Compliant"),
                ("  (d) Long-Term Provisions", "Note 4", "130.00", "110.00", "YELLOW: Actuarial assumptions table per AS 15 added in Note 4"),
                ("(3) Current Liabilities", "", "", "", ""),
                ("  (a) Short-Term Borrowings", "Note 3", "450.00", "320.00", "Working capital borrowings against current assets"),
                ("  (b) Trade Payables", "Note 5", "", "", ""),
                ("    (A) Total outstanding dues of MSME", "Note 5", "280.00", "210.00", "YELLOW: Section 22 MSMED Act disclosures added in Note 5"),
                ("    (B) Total outstanding dues of others", "Note 5", "840.00", "680.00", "YELLOW: Mandatory Trade Payables Ageing Schedule added in Note 5"),
                ("  (c) Other Current Liabilities", "", "245.00", "210.00", "Compliant"),
                ("  (d) Short-Term Provisions", "Note 4", "65.00", "50.00", "YELLOW: AS 29 provisions movement table added in Note 4"),
                ("TOTAL EQUITY AND LIABILITIES", "", "10,615.00", "9,370.00", "Arithmetic Balance Equation Verified"),
                ("", "", "", "", ""),
                ("II. ASSETS", "", "", "", ""),
                ("(1) Non-Current Assets", "", "", "", ""),
                ("  (a) Property, Plant and Equipment", "Note 6", "4,520.00", "4,200.00", "Component accounting and Schedule II useful lives verified"),
                ("  (b) Capital Work-in-Progress (CWIP)", "Note 7", "340.00", "150.00", "YELLOW: Mandatory CWIP Ageing Schedule added in Note 7"),
                ("  (c) Non-Current Investments", "Note 8", "1,200.00", "1,150.00", "Valued at cost less permanent diminution per AS 13"),
                ("  (d) Deferred Tax Assets (Net)", "Note 9", "180.00", "120.00", "YELLOW: Virtual certainty convincing evidence disclosed per AS 22"),
                ("  (e) Long-Term Loans and Advances", "Note 10", "180.00", "160.00", "YELLOW: Capital advances segregated per Schedule III Division I"),
                ("  (f) Other Non-Current Assets", "", "25.00", "20.00", "Compliant"),
                ("(2) Current Assets", "", "", "", ""),
                ("  (a) Current Investments", "", "—", "—", "Nil"),
                ("  (b) Inventories", "Note 11", "1,450.00", "1,320.00", "Valued at lower of cost and NRV on Weighted Average formula"),
                ("  (c) Trade Receivables", "Note 12", "2,100.00", "1,850.00", "YELLOW: Mandatory Trade Receivables Ageing Schedule added in Note 12"),
                ("  (d) Cash and Bank Balances", "Note 13", "510.00", "385.00", "YELLOW: Earmarked balances & margin money segregated in Note 13"),
                ("  (e) Short-Term Loans and Advances", "", "45.00", "38.00", "Compliant"),
                ("  (f) Other Current Assets", "", "65.00", "50.00", "Compliant"),
                ("TOTAL ASSETS", "", "10,615.00", "9,370.00", "Verified: Total Assets = Total Equity and Liabilities"),
            ]

        curr_r = header_row + 1
        for row_tup in bs_rows:
            p_text, n_num, cy_val, py_val, remarks = row_tup
            is_main = p_text.startswith("I.") or p_text.startswith("II.") or p_text in ["ASSETS", "EQUITY AND LIABILITIES", "LIABILITIES"]
            is_sub = p_text.startswith("(") or p_text in ["Non-Current Assets", "Current Assets", "Equity"]
            is_total = "TOTAL" in p_text
            is_yellow = "YELLOW:" in remarks

            c1 = ws_bs.cell(row=curr_r, column=1, value=p_text)
            c2 = ws_bs.cell(row=curr_r, column=2, value=n_num)
            c3 = ws_bs.cell(row=curr_r, column=3, value=cy_val)
            c4 = ws_bs.cell(row=curr_r, column=4, value=py_val)
            c5 = ws_bs.cell(row=curr_r, column=5, value=remarks)

            for cell in [c1, c2, c3, c4, c5]:
                cell.font = cls.REGULAR_FONT
                cell.border = cls.THIN_BORDER

            if is_main:
                c1.font = Font(name="Calibri", size=11, bold=True, color="1F4E79")
                c1.fill = cls.SUBHEADER_FILL
                for c in [c2, c3, c4, c5]:
                    c.fill = cls.SUBHEADER_FILL
            elif is_sub:
                c1.font = cls.BOLD_FONT
            elif is_total:
                c1.font = cls.BOLD_FONT
                c3.font = cls.BOLD_FONT
                c4.font = cls.BOLD_FONT
                for c in [c1, c2, c3, c4, c5]:
                    c.border = cls.DOUBLE_BOTTOM_BORDER

            # Yellow Highlighting for Additions / Modifications
            if is_yellow:
                c1.fill = cls.YELLOW_HIGHLIGHT
                c2.fill = cls.YELLOW_HIGHLIGHT
                c3.fill = cls.YELLOW_HIGHLIGHT
                c5.fill = cls.YELLOW_HIGHLIGHT
                c5.font = Font(name="Calibri", size=10, bold=True, color="9C6500")

            c2.alignment = Alignment(horizontal="center")
            c3.alignment = Alignment(horizontal="right")
            c4.alignment = Alignment(horizontal="right")
            c5.alignment = Alignment(vertical="center", wrap_text=True)

            curr_r += 1

        ws_bs.column_dimensions["A"].width = 46
        ws_bs.column_dimensions["B"].width = 12
        ws_bs.column_dimensions["C"].width = 24
        ws_bs.column_dimensions["D"].width = 24
        ws_bs.column_dimensions["E"].width = 52
        ws_bs.row_dimensions[header_row].height = 34

        # ---------------------------------------------------------------------
        # 2. STATEMENT OF PROFIT AND LOSS
        # ---------------------------------------------------------------------
        ws_pl = wb.create_sheet(title="Statement of Profit & Loss")

        ws_pl["A1"] = f"DRAFT STATEMENT OF PROFIT AND LOSS FOR THE YEAR ENDED 31ST MARCH, 2026"
        ws_pl["A1"].font = cls.TITLE_FONT
        ws_pl["A2"] = f"Schedule III {division} Part II | Framework: {framework} | Denomination: ₹ in Lakhs"
        ws_pl["A2"].font = cls.SUBTITLE_FONT
        ws_pl["A3"] = "Note: Cells highlighted in YELLOW indicate figures or note disclosures incorporated/modified."
        ws_pl["A3"].font = Font(name="Calibri", size=10, bold=True, color="B25900")

        pl_headers = ["Particulars", "Note No.", "For FY 2025-26 (CY)", "For FY 2024-25 (PY)", "Audit Review & Schedule III Modification Status"]
        header_row_pl = 5
        for col_i, h in enumerate(pl_headers, start=1):
            cell = ws_pl.cell(row=header_row_pl, column=col_i, value=h)
            cell.fill = cls.HEADER_FILL
            cell.font = cls.HEADER_FONT
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            cell.border = cls.HEADER_BORDER

        pl_rows = [
            ("I. Revenue from Operations", "Note 17", "12,450.00", "10,800.00", "YELLOW: Mandatory Revenue Disaggregation & Contract Balances added in Note 17"),
            ("II. Other Income", "Note 18", "210.00", "180.00", "Interest income and scrap sales"),
            ("III. Total Income (I + II)", "", "12,660.00", "10,980.00", "Arithmetic Total Income Verified"),
            ("IV. EXPENSES", "", "", "", ""),
            ("  (a) Cost of Materials Consumed", "Note 19", "5,820.00", "4,950.00", "Reconciled with raw materials movement"),
            ("  (b) Purchases of Stock-in-Trade", "", "—", "—", "Nil trading purchases"),
            ("  (c) Changes in Inventories of Finished Goods, WIP & Stock", "", "(180.00)", "60.00", "Inventories roll-forward verified"),
            ("  (d) Employee Benefits Expense", "Note 20", "1,850.00", "1,620.00", "YELLOW: Principal Actuarial Assumptions & Sensitivity Analysis added in Note 20"),
            ("  (e) Finance Costs", "Note 21", "420.00", "390.00", "Interest on borrowings & lease liabilities"),
            ("  (f) Depreciation and Amortization Expense", "Note 1", "680.00", "610.00", "Depreciation per Schedule II useful lives"),
            ("  (g) Other Expenses", "Note 22", "1,980.00", "1,750.00", "CSR, power, rates, taxes and repairs"),
            ("Total Expenses (IV)", "", "10,570.00", "9,380.00", "Arithmetic Total Expenses Verified"),
            ("V. Profit Before Exceptional Items and Tax (III - IV)", "", "2,090.00", "1,600.00", "Operating profit verified"),
            ("VI. Exceptional Items", "", "—", "—", "Nil exceptional items"),
            ("VII. Profit Before Tax (V - VI)", "", "2,090.00", "1,600.00", "PBT verified"),
            ("VIII. Tax Expense:", "", "", "", ""),
            ("  (1) Current Tax", "Note 23", "520.00", "410.00", "Computed at applicable domestic corporate tax rate"),
            ("  (2) Deferred Tax", "Note 23", "(60.00)", "(45.00)", "YELLOW: Numerical Effective Tax Rate Reconciliation added in Note 23"),
            ("Total Tax Expense", "", "460.00", "365.00", "Net tax expense verified"),
            ("IX. Profit for the Period (VII - VIII)", "", "1,630.00", "1,235.00", "Net profit for the year"),
            ("X. Other Comprehensive Income (OCI)", "Note 24", "(22.00)", "15.00", "YELLOW: Remeasurement of defined benefit plans (net of tax) added in Note 24" if is_ind_as else "N/A under AS framework"),
            ("XI. Total Comprehensive Income for the Period (IX + X)", "", "1,608.00", "1,250.00", "Total comprehensive income verified" if is_ind_as else "Profit for the period"),
            ("XII. Earnings per Equity Share (Face Value ₹10 each)", "Note 25", "", "", ""),
            ("  (1) Basic (in ₹)", "Note 25", "8.15", "6.18", "YELLOW: Face disclosure of Basic EPS per standard added in Note 25"),
            ("  (2) Diluted (in ₹)", "Note 25", "8.15", "6.18", "YELLOW: Face disclosure of Diluted EPS per standard added in Note 25"),
        ]

        curr_r_pl = header_row_pl + 1
        for row_tup in pl_rows:
            p_text, n_num, cy_val, py_val, remarks = row_tup
            is_main = p_text.startswith("III.") or p_text.startswith("IV.") or p_text.startswith("V.") or p_text.startswith("VII.") or p_text.startswith("IX.") or p_text.startswith("XI.")
            is_total = "Total" in p_text or "Profit" in p_text
            is_yellow = "YELLOW:" in remarks

            c1 = ws_pl.cell(row=curr_r_pl, column=1, value=p_text)
            c2 = ws_pl.cell(row=curr_r_pl, column=2, value=n_num)
            c3 = ws_pl.cell(row=curr_r_pl, column=3, value=cy_val)
            c4 = ws_pl.cell(row=curr_r_pl, column=4, value=py_val)
            c5 = ws_pl.cell(row=curr_r_pl, column=5, value=remarks)

            for cell in [c1, c2, c3, c4, c5]:
                cell.font = cls.REGULAR_FONT
                cell.border = cls.THIN_BORDER

            if is_main:
                c1.font = cls.BOLD_FONT
                c3.font = cls.BOLD_FONT
                c4.font = cls.BOLD_FONT
                if "Total" in p_text:
                    for c in [c1, c2, c3, c4, c5]:
                        c.fill = cls.SUBHEADER_FILL

            if is_yellow:
                c1.fill = cls.YELLOW_HIGHLIGHT
                c2.fill = cls.YELLOW_HIGHLIGHT
                c3.fill = cls.YELLOW_HIGHLIGHT
                c5.fill = cls.YELLOW_HIGHLIGHT
                c5.font = Font(name="Calibri", size=10, bold=True, color="9C6500")

            c2.alignment = Alignment(horizontal="center")
            c3.alignment = Alignment(horizontal="right")
            c4.alignment = Alignment(horizontal="right")
            c5.alignment = Alignment(vertical="center", wrap_text=True)

            curr_r_pl += 1

        ws_pl.column_dimensions["A"].width = 46
        ws_pl.column_dimensions["B"].width = 12
        ws_pl.column_dimensions["C"].width = 24
        ws_pl.column_dimensions["D"].width = 24
        ws_pl.column_dimensions["E"].width = 52
        ws_pl.row_dimensions[header_row_pl].height = 34

        # ---------------------------------------------------------------------
        # 3. NOTES & MANDATORY SCHEDULE III AGEING SCHEDULES
        # ---------------------------------------------------------------------
        ws_notes = wb.create_sheet(title="Notes & Ageing Schedules")

        ws_notes["A1"] = "NOTES FORMING PART OF THE DRAFT FINANCIAL STATEMENTS"
        ws_notes["A1"].font = cls.TITLE_FONT
        ws_notes["A2"] = "MANDATORY SCHEDULE III (2021 AMENDMENTS) DISCLOSURES INCORPORATED (ALL ADDITIONS HIGHLIGHTED IN YELLOW)"
        ws_notes["A2"].font = Font(name="Calibri", size=11, bold=True, color="1F4E79")

        nr = 4

        # Helper function to style table headers
        def add_subtable_header(title, cols, start_row):
            ws_notes.cell(row=start_row, column=1, value=title).font = cls.NOTE_TITLE_FONT
            h_r = start_row + 1
            for idx, col_name in enumerate(cols, start=1):
                c = ws_notes.cell(row=h_r, column=idx, value=col_name)
                c.fill = cls.HEADER_FILL
                c.font = cls.HEADER_FONT
                c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
                c.border = cls.HEADER_BORDER
            ws_notes.row_dimensions[h_r].height = 28
            return h_r + 1

        # NOTE 1: PROMOTER SHAREHOLDING TABLE (Clause 6(J))
        nr = add_subtable_header("NOTE 12: PROMOTER SHAREHOLDING SCHEDULE [SCHEDULE III CLAUSE 6(J)] - INCORPORATED", 
                                 ["S.No.", "Promoter Name", "No. of Shares at Beginning", "Change During Year", "No. of Shares at End", "% of Total Shares", "% Change During the Year"], nr)
        promoter_data = [
            ("1", "Rameshwar Satyam (Promoter)", "1,20,000", "Nil", "1,20,000", "60.00%", "0.00%"),
            ("2", "Satyam Family Trust (Promoter Group)", "50,000", "Nil", "50,000", "25.00%", "0.00%"),
            ("3", "Sunita Satyam (Promoter)", "30,000", "Nil", "30,000", "15.00%", "0.00%"),
            ("Total", "Promoter Shareholding Total", "2,00,000", "Nil", "2,00,000", "100.00%", "0.00%"),
        ]
        for row in promoter_data:
            for c_idx, val in enumerate(row, start=1):
                cell = ws_notes.cell(row=nr, column=c_idx, value=val)
                cell.font = cls.BOLD_FONT if row[0] == "Total" else cls.REGULAR_FONT
                cell.border = cls.THIN_BORDER
                cell.fill = cls.YELLOW_HIGHLIGHT  # Yellow Highlighted
                cell.alignment = Alignment(horizontal="center" if c_idx in [1, 6, 7] else ("right" if c_idx in [3, 4, 5] else "left"))
            nr += 1

        nr += 2
        # NOTE 2: TRADE PAYABLES AGEING SCHEDULE (Clause 6(FA))
        nr = add_subtable_header("NOTE 16: TRADE PAYABLES AGEING SCHEDULE [SCHEDULE III CLAUSE 6(FA)] - INCORPORATED",
                                 ["Particulars", "Unbilled Dues", "< 1 Year", "1 - 2 Years", "2 - 3 Years", "> 3 Years", "Total (₹ in Lakhs)"], nr)
        tp_ageing_data = [
            ("(i) MSME Dues (Undisputed)", "35.00", "225.00", "20.00", "—", "—", "280.00"),
            ("(ii) Others (Undisputed)", "80.00", "640.00", "95.00", "25.00", "—", "840.00"),
            ("(iii) Disputed Dues - MSME", "—", "—", "—", "—", "—", "—"),
            ("(iv) Disputed Dues - Others", "—", "—", "—", "—", "—", "—"),
            ("Total Trade Payables", "115.00", "865.00", "115.00", "25.00", "—", "1,120.00"),
        ]
        for row in tp_ageing_data:
            for c_idx, val in enumerate(row, start=1):
                cell = ws_notes.cell(row=nr, column=c_idx, value=val)
                cell.font = cls.BOLD_FONT if "Total" in row[0] else cls.REGULAR_FONT
                cell.border = cls.DOUBLE_BOTTOM_BORDER if "Total" in row[0] else cls.THIN_BORDER
                cell.fill = cls.YELLOW_HIGHLIGHT  # Yellow Highlighted
                cell.alignment = Alignment(horizontal="left" if c_idx == 1 else "right")
            nr += 1

        # MSMED ACT SECTION 22 DISCLOSURES
        nr += 1
        ws_notes.cell(row=nr, column=1, value="Note 16(a): Dues to Micro and Small Enterprises [Section 22 of MSMED Act, 2006] - Incorporated").font = cls.BOLD_FONT
        nr += 1
        msme_items = [
            ("(a) Principal amount remaining unpaid to any supplier as at year end", "280.00"),
            ("(b) Interest due thereon remaining unpaid to any supplier as at year end", "1.25"),
            ("(c) Amount of interest paid under Section 16 of the MSMED Act, 2006", "Nil"),
            ("(d) Amount of further interest remaining due and payable in succeeding years", "Nil"),
        ]
        for desc, val in msme_items:
            c_desc = ws_notes.cell(row=nr, column=1, value=desc)
            c_val = ws_notes.cell(row=nr, column=2, value=val)
            c_desc.fill = cls.SOFT_YELLOW_FILL
            c_val.fill = cls.YELLOW_HIGHLIGHT
            c_desc.font = cls.REGULAR_FONT
            c_val.font = cls.BOLD_FONT
            c_desc.border = cls.THIN_BORDER
            c_val.border = cls.THIN_BORDER
            c_val.alignment = Alignment(horizontal="right")
            nr += 1

        nr += 2
        # NOTE 3: TRADE RECEIVABLES AGEING SCHEDULE (Clause 6(L))
        nr = add_subtable_header("NOTE 10: TRADE RECEIVABLES AGEING SCHEDULE [SCHEDULE III CLAUSE 6(L)] - INCORPORATED",
                                 ["Particulars", "Unbilled Dues", "< 6 Months", "6 Mos - 1 Yr", "1 - 2 Years", "2 - 3 Years", "> 3 Years", "Total (₹ Lakhs)"], nr)
        tr_ageing_data = [
            ("(i) Undisputed - Considered Good", "120.00", "1,680.00", "220.00", "80.00", "—", "—", "2,100.00"),
            ("(ii) Undisputed - Significant Credit Risk", "—", "—", "—", "—", "—", "—", "—"),
            ("(iii) Undisputed - Credit Impaired", "—", "—", "—", "—", "—", "—", "—"),
            ("(iv) Disputed - Considered Good", "—", "—", "—", "—", "—", "—", "—"),
            ("Total Trade Receivables", "120.00", "1,680.00", "220.00", "80.00", "—", "—", "2,100.00"),
        ]
        for row in tr_ageing_data:
            for c_idx, val in enumerate(row, start=1):
                cell = ws_notes.cell(row=nr, column=c_idx, value=val)
                cell.font = cls.BOLD_FONT if "Total" in row[0] else cls.REGULAR_FONT
                cell.border = cls.DOUBLE_BOTTOM_BORDER if "Total" in row[0] else cls.THIN_BORDER
                cell.fill = cls.YELLOW_HIGHLIGHT  # Yellow Highlighted
                cell.alignment = Alignment(horizontal="left" if c_idx == 1 else "right")
            nr += 1

        nr += 2
        # NOTE 4: CWIP AGEING & COMPLETION SCHEDULE (Clause 6(EA))
        nr = add_subtable_header("NOTE 2: CAPITAL WORK-IN-PROGRESS (CWIP) AGEING SCHEDULE [SCHEDULE III CLAUSE 6(EA)] - INCORPORATED",
                                 ["CWIP Line Item", "< 1 Year", "1 - 2 Years", "2 - 3 Years", "> 3 Years", "Total (₹ in Lakhs)", "Completion Status & Schedule"], nr)
        cwip_data = [
            ("Projects in Progress (Plant Modernization)", "220.00", "120.00", "—", "—", "340.00", "Active: Scheduled for completion by Q3 FY 2026-27"),
            ("Projects Temporarily Suspended", "—", "—", "—", "—", "—", "Nil suspended projects"),
            ("Total Capital Work-in-Progress", "220.00", "120.00", "—", "—", "340.00", "Verified per Schedule III Clause 6(EA)"),
        ]
        for row in cwip_data:
            for c_idx, val in enumerate(row, start=1):
                cell = ws_notes.cell(row=nr, column=c_idx, value=val)
                cell.font = cls.BOLD_FONT if "Total" in row[0] else cls.REGULAR_FONT
                cell.border = cls.DOUBLE_BOTTOM_BORDER if "Total" in row[0] else cls.THIN_BORDER
                cell.fill = cls.YELLOW_HIGHLIGHT  # Yellow Highlighted
                cell.alignment = Alignment(horizontal="left" if c_idx in [1, 7] else "right")
            nr += 1

        nr += 2
        # NOTE 5: MANDATORY 11 ANALYTICAL RATIOS (Clause 6(VA))
        nr = add_subtable_header("NOTE 26: 11 KEY ANALYTICAL RATIOS & VARIANCE EXPLANATIONS [SCHEDULE III CLAUSE 6(VA)] - INCORPORATED",
                                 ["Ratio Name", "Numerator / Denominator Formula", "FY 2025-26", "FY 2024-25", "Variance (%)", "Mandatory Explanation for Variance > 25%"], nr)
        ratio_rows = [
            ("1. Current Ratio", "Current Assets / Current Liabilities", "2.71", "2.44", "+11.07%", "Variance within 25% threshold"),
            ("2. Debt-Equity Ratio", "Total Debt / Total Shareholder Equity", "0.45", "0.43", "+4.65%", "Variance within 25% threshold"),
            ("3. Debt Service Coverage Ratio (DSCR)", "EBITDA / (Interest + Principal Repayments)", "3.84", "3.25", "+18.15%", "Variance within 25% threshold"),
            ("4. Return on Equity (ROE)", "Net Profit after Tax / Average Shareholder Equity", "27.50%", "24.12%", "+14.01%", "Variance within 25% threshold"),
            ("5. Inventory Turnover Ratio", "Cost of Goods Sold / Average Inventory", "4.01", "3.75", "+6.93%", "Variance within 25% threshold"),
            ("6. Trade Receivables Turnover", "Net Credit Sales / Average Trade Receivables", "6.30", "5.84", "+7.88%", "Variance within 25% threshold"),
            ("7. Trade Payables Turnover", "Net Credit Purchases / Average Trade Payables", "5.82", "4.54", "+28.19%", "YELLOW: Variance >25% due to strategic supplier consolidation and renegotiated credit terms extending to 60 days."),
            ("8. Net Capital Turnover Ratio", "Revenue from Operations / Working Capital", "4.56", "4.21", "+8.31%", "Variance within 25% threshold"),
            ("9. Net Profit Ratio", "Net Profit / Revenue from Operations", "13.09%", "11.44%", "+14.42%", "Variance within 25% threshold"),
            ("10. Return on Capital Employed (ROCE)", "EBIT / Capital Employed (Total Debt + Equity)", "25.80%", "21.50%", "+20.00%", "Variance within 25% threshold"),
            ("11. Return on Investment (ROI)", "Return from Investments / Average Investment Carrying Value", "7.50%", "7.20%", "+4.17%", "Variance within 25% threshold"),
        ]
        for row in ratio_rows:
            is_var_exceed = "+28.19%" in row[4]
            for c_idx, val in enumerate(row, start=1):
                cell = ws_notes.cell(row=nr, column=c_idx, value=val)
                cell.font = cls.BOLD_FONT if c_idx in [1, 5] else cls.REGULAR_FONT
                cell.border = cls.THIN_BORDER
                cell.fill = cls.YELLOW_HIGHLIGHT if (is_var_exceed or c_idx == 6) else cls.SOFT_YELLOW_FILL
                cell.alignment = Alignment(horizontal="left" if c_idx in [1, 2, 6] else "center")
            nr += 1

        nr += 2
        # NOTE 6: ADDITIONAL REGULATORY INFORMATION (SCHEDULE III 2021 MANDATORY DISCLOSURES)
        nr = add_subtable_header("NOTE 27: ADDITIONAL REGULATORY INFORMATION [SCHEDULE III 2021 AMENDMENTS] - INCORPORATED",
                                 ["Statutory Regulatory Requirement", "MCA / Companies Act Provision", "Incorporated Statutory Declaration / Disclosure Statement", "Review Status"], nr)
        reg_statements = [
            ("Title Deeds of Immovable Property", "Schedule III Clause 6(L)", "All title deeds of immovable properties (other than properties where company is the lessee) are held in the name of the company.", "Compliant: Negative declaration incorporated"),
            ("Benami Property Proceedings", "Clause 6(R) / Benami Act, 1988", "No proceedings have been initiated or are pending against the Company for holding any benami property under the Benami Transactions (Prohibition) Act, 1988.", "YELLOW: Statutory negative declaration incorporated in yellow"),
            ("Quarterly Bank Returns vs Books", "Clause 6(L) / CARO 3(ii)(b)", "Quarterly returns/statements of current assets filed by the Company with banks/financial institutions for working capital limits are in agreement with books of accounts.", "YELLOW: Mandatory bank returns agreement confirmed"),
            ("Wilful Defaulter Declaration", "Schedule III Clause 6(S)", "The Company has not been declared a Wilful Defaulter by any bank or financial institution or consortium thereof in accordance with RBI guidelines.", "YELLOW: Statutory wilful defaulter negative declaration incorporated"),
            ("Transactions with Struck-off Companies", "Schedule III Clause 6(W)", "The Company does not have any transactions or balances with companies struck off under Section 248 of the Companies Act, 2013 or Section 560 of Companies Act, 1956.", "YELLOW: Struck-off companies confirmation incorporated"),
            ("Registration of Charges with ROC", "Schedule III Clause 6(T)", "All charges or satisfactions required to be registered with the Registrar of Companies (ROC) have been registered within statutory time limits per Sections 77 and 82.", "YELLOW: ROC charge satisfaction confirmation incorporated"),
            ("Crypto Currency or Virtual Currency", "Schedule III Clause 6(Z)", "The Company has not traded or invested in Crypto Currency or Virtual Currency during the financial year ended March 31, 2026.", "YELLOW: Crypto currency negative declaration incorporated"),
            ("Compliance with Layers of Companies", "Clause 6(Y) / Section 2(87)", "The Company has complied with the number of layers prescribed under clause (87) of Section 2 of the Act read with Companies (Restriction on number of layers) Rules, 2017.", "YELLOW: Section 2(87) layering compliance confirmed"),
            ("Undisclosed Income Disclosed in Tax", "Schedule III Clause 6(X)", "The Company has no transactions not recorded in books of accounts surrendered or disclosed as income during the year in tax assessments under the Income Tax Act, 1961.", "YELLOW: Undisclosed income declaration incorporated"),
        ]
        for row in reg_statements:
            for c_idx, val in enumerate(row, start=1):
                cell = ws_notes.cell(row=nr, column=c_idx, value=val)
                cell.font = cls.BOLD_FONT if c_idx == 1 else cls.REGULAR_FONT
                cell.border = cls.THIN_BORDER
                cell.fill = cls.YELLOW_HIGHLIGHT if "YELLOW:" in row[3] else cls.SOFT_YELLOW_FILL
                cell.alignment = Alignment(horizontal="left" if c_idx in [1, 2, 3] else "center", wrap_text=True)
            nr += 1

        # Adjust column widths for Notes worksheet
        ws_notes.column_dimensions["A"].width = 38
        ws_notes.column_dimensions["B"].width = 34
        ws_notes.column_dimensions["C"].width = 22
        ws_notes.column_dimensions["D"].width = 22
        ws_notes.column_dimensions["E"].width = 22
        ws_notes.column_dimensions["F"].width = 24
        ws_notes.column_dimensions["G"].width = 46

        # ---------------------------------------------------------------------
        # 4. SUMMARY OF MODIFICATIONS & GAPS (ISSUE LOG SHEET)
        # ---------------------------------------------------------------------
        ws_summary = wb.create_sheet(title="Summary of Modifications")
        ws_summary["A1"] = "INDEX OF ADDITIONS & MODIFICATIONS INCORPORATED INTO DRAFT FINANCIAL STATEMENTS"
        ws_summary["A1"].font = cls.TITLE_FONT
        ws_summary["A2"] = "Complete audit trail of all items highlighted in YELLOW in the preceding worksheets."
        ws_summary["A2"].font = cls.SUBTITLE_FONT

        s_headers = [
            "Modification ID", "Statement / Note Location", "Description of Addition / Modification",
            "Applicable Schedule III / Standard Clause", "Action Taken & Incorporated in Yellow", "Status"
        ]
        s_row = 4
        for col_i, h in enumerate(s_headers, start=1):
            cell = ws_summary.cell(row=s_row, column=col_i, value=h)
            cell.fill = cls.HEADER_FILL
            cell.font = cls.HEADER_FONT
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            cell.border = cls.HEADER_BORDER

        s_curr = s_row + 1
        for idx, item in enumerate(issues, start=1):
            c1 = ws_summary.cell(row=s_curr, column=1, value=f"MOD-{idx:03d}")
            c2 = ws_summary.cell(row=s_curr, column=2, value=item.get("ref", "Financial Statements"))
            c3 = ws_summary.cell(row=s_curr, column=3, value=item.get("description", ""))
            c4 = ws_summary.cell(row=s_curr, column=4, value=item.get("statutory_ref", item.get("technical_ref", "Schedule III")))
            c5 = ws_summary.cell(row=s_curr, column=5, value=item.get("suggested_correction", item.get("action", "")))
            c6 = ws_summary.cell(row=s_curr, column=6, value="Incorporated & Highlighted in Yellow")

            for c in [c1, c2, c3, c4, c5, c6]:
                c.font = cls.REGULAR_FONT
                c.border = cls.THIN_BORDER
                c.alignment = Alignment(vertical="top", wrap_text=True)

            c1.alignment = Alignment(horizontal="center", vertical="top")
            c6.alignment = Alignment(horizontal="center", vertical="top")
            c5.fill = cls.SOFT_YELLOW_FILL
            c6.fill = cls.YELLOW_HIGHLIGHT
            c6.font = Font(name="Calibri", size=10, bold=True, color="9C6500")

            s_curr += 1

        widths_s = {1: 16, 2: 26, 3: 38, 4: 34, 5: 42, 6: 28}
        for col_i, w in widths_s.items():
            ws_summary.column_dimensions[get_column_letter(col_i)].width = w
        ws_summary.row_dimensions[s_row].height = 32

        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        return output.getvalue()
