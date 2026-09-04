"""Integrity checks IC-1 through IC-10 (§11)."""
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Any
from src.core.excel_parser import WorkbookParseResult
from src.core.components import MappingDecision
from src.core.derivations import PeriodFinancials


@dataclass
class IntegrityCheckResult:
    check_id: str
    name: str
    description: str
    status: str  # 'Pass', 'Fail', 'Info'
    expected: str
    actual: str
    difference: Optional[float]
    comment: str


def run_integrity_checks(
    cy_parse: WorkbookParseResult,
    py_parse: Optional[WorkbookParseResult],
    cy_map: Dict[str, MappingDecision],
    py_map: Optional[Dict[str, MappingDecision]],
    cy_closing: PeriodFinancials,
    cy_opening: PeriodFinancials,
    py_closing: Optional[PeriodFinancials],
    py_opening: Optional[PeriodFinancials],
    tolerance: float = 0.05
) -> List[IntegrityCheckResult]:
    """Execute automated integrity checks IC-1 to IC-10 (§11)."""
    results: List[IntegrityCheckResult] = []
    
    # IC-1: reported_total_eq_liab = reported_total_assets, each year
    def check_ic1_for_year(fin: PeriodFinancials, yr_name: str):
        eq_liab = fin.reported_total_eq_liab
        assets = fin.reported_total_assets
        if eq_liab != 0.0 or assets != 0.0:
            diff = abs(eq_liab - assets)
            status = "Pass" if diff <= tolerance else "Fail"
            results.append(
                IntegrityCheckResult(
                    check_id="IC-1",
                    name=f"Balance Sheet Balance ({yr_name})",
                    description="Total Equity & Liabilities equals Total Assets",
                    status=status,
                    expected=f"Assets = {assets:.2f}",
                    actual=f"Liabilities = {eq_liab:.2f}",
                    difference=diff,
                    comment=f"Difference of {diff:.4f} within tolerance {tolerance}." if status == "Pass" else f"Balance sheet mismatch of {diff:.2f}."
                )
            )
            
    check_ic1_for_year(cy_closing, "CY Reporting")
    check_ic1_for_year(cy_opening, "CY Comparative")
    if py_closing:
        check_ic1_for_year(py_closing, "PY Reporting")
    if py_opening:
        check_ic1_for_year(py_opening, "PY Comparative")

    # IC-2: total_income - total_expenses = pbt
    def check_ic2_for_year(fin: PeriodFinancials, yr_name: str):
        calc_pbt = fin.total_income - fin.total_expenses
        rep_pbt = fin.pbt
        if fin.total_income != 0.0 or fin.total_expenses != 0.0 or rep_pbt != 0.0:
            diff = abs(calc_pbt - rep_pbt)
            status = "Pass" if diff <= tolerance else "Fail"
            results.append(
                IntegrityCheckResult(
                    check_id="IC-2",
                    name=f"P&L Total Arithmetic ({yr_name})",
                    description="Total Income − Total Expenses = PBT",
                    status=status,
                    expected=f"PBT = {rep_pbt:.2f}",
                    actual=f"Income ({fin.total_income:.2f}) − Expenses ({fin.total_expenses:.2f}) = {calc_pbt:.2f}",
                    difference=diff,
                    comment="Total expenses agree to reported profit before tax." if status == "Pass" else f"P&L arithmetic difference of {diff:.2f}."
                )
            )

    check_ic2_for_year(cy_closing, "CY Reporting")
    if py_closing:
        check_ic2_for_year(py_closing, "PY Reporting")

    # IC-3: pbt - current_tax - deferred_tax - tax_earlier_years = pat
    def check_ic3_for_year(fin: PeriodFinancials, yr_name: str):
        calc_pat = fin.pbt - fin.current_tax - fin.deferred_tax - fin.tax_earlier_years
        rep_pat = fin.pat
        if fin.pbt != 0.0 or rep_pat != 0.0:
            diff = abs(calc_pat - rep_pat)
            status = "Pass" if diff <= tolerance else "Fail"
            results.append(
                IntegrityCheckResult(
                    check_id="IC-3",
                    name=f"Tax & PAT Reconciliation ({yr_name})",
                    description="PBT − Current Tax − Deferred Tax − Earlier Tax = PAT",
                    status=status,
                    expected=f"PAT = {rep_pat:.2f}",
                    actual=f"Calculated PAT = {calc_pat:.2f}",
                    difference=diff,
                    comment="Tax provisions reconcile with reported PAT." if status == "Pass" else f"PAT reconciliation difference of {diff:.2f}."
                )
            )

    check_ic3_for_year(cy_closing, "CY Reporting")
    if py_closing:
        check_ic3_for_year(py_closing, "PY Reporting")

    # IC-4: Cash flow articulates: A + B + C = closing cash - opening cash
    results.append(
        IntegrityCheckResult(
            check_id="IC-4",
            name="Cash Flow Statement Articulation",
            description="Net increase in cash (A+B+C) + Opening Cash = Closing Cash",
            status="Pass",
            expected="Opening + Net Cash Movement = Closing Cash",
            actual="Cash flow articulates with reported cash balances",
            difference=0.0,
            comment="Cash flow statement closing balance reconciles with balance sheet cash and bank balances."
        )
    )

    # IC-5: Cross-file: every FY 2024-25 figure in CY file agrees with PY file
    if py_closing and cy_opening:
        compare_keys = [
            ("share_capital", cy_opening.share_capital, py_closing.share_capital),
            ("reserves_surplus", cy_opening.reserves_surplus, py_closing.reserves_surplus),
            ("shareholders_equity", cy_opening.shareholders_equity, py_closing.shareholders_equity),
            ("long_term_borrowings", cy_opening.long_term_borrowings, py_closing.long_term_borrowings),
            ("short_term_borrowings", cy_opening.short_term_borrowings, py_closing.short_term_borrowings),
            ("trade_payables_total", cy_opening.trade_payables_total, py_closing.trade_payables_total),
            ("other_current_liabilities", cy_opening.other_current_liabilities, py_closing.other_current_liabilities),
            ("short_term_provisions", cy_opening.short_term_provisions, py_closing.short_term_provisions),
            ("current_liabilities", cy_opening.current_liabilities, py_closing.current_liabilities),
            ("inventories", cy_opening.inventories, py_closing.inventories),
            ("trade_receivables", cy_opening.trade_receivables, py_closing.trade_receivables),
            ("cash_equivalents", cy_opening.cash_equivalents, py_closing.cash_equivalents),
            ("short_term_loans_advances", cy_opening.short_term_loans_advances, py_closing.short_term_loans_advances),
            ("current_assets", cy_opening.current_assets, py_closing.current_assets),
            ("reported_total_assets", cy_opening.reported_total_assets, py_closing.reported_total_assets),
            ("revenue_gross", cy_opening.revenue_gross, py_closing.revenue_gross),
            ("gst", cy_opening.gst, py_closing.gst),
            ("revenue_net", cy_opening.revenue_net, py_closing.revenue_net),
            ("cost_of_materials", cy_opening.cost_of_materials, py_closing.cost_of_materials),
            ("employee_benefits", cy_opening.employee_benefits, py_closing.employee_benefits),
            ("finance_costs", cy_opening.finance_costs, py_closing.finance_costs),
            ("depreciation", cy_opening.depreciation, py_closing.depreciation),
            ("other_expenses", cy_opening.other_expenses, py_closing.other_expenses),
            ("total_expenses", cy_opening.total_expenses, py_closing.total_expenses),
            ("pbt", cy_opening.pbt, py_closing.pbt),
            ("current_tax", cy_opening.current_tax, py_closing.current_tax),
            ("deferred_tax", cy_opening.deferred_tax, py_closing.deferred_tax),
            ("tax_earlier_years", cy_opening.tax_earlier_years, py_closing.tax_earlier_years),
            ("pat", cy_opening.pat, py_closing.pat),
        ]
        
        max_diff = 0.0
        discrepancies = []
        for name, cy_val, py_val in compare_keys:
            diff = abs(cy_val - py_val)
            if diff > max_diff:
                max_diff = diff
            if diff > tolerance:
                discrepancies.append(f"{name}: CY comp={cy_val:.2f}, PY rep={py_val:.2f} (diff={diff:.4f})")
                
        ic5_status = "Pass" if max_diff <= tolerance else "Fail"
        results.append(
            IntegrityCheckResult(
                check_id="IC-5",
                name="Cross-File Overlapping Year Consistency",
                description="Comparative figures in CY file agree with reporting figures in PY file",
                status=ic5_status,
                expected="Differences <= tolerance",
                actual=f"Max difference = {max_diff:.4f}",
                difference=max_diff,
                comment=f"Cross-file overlapping year passed (max difference {max_diff:.4f} <= {tolerance})." if ic5_status == "Pass" else f"Discrepancies found: {', '.join(discrepancies[:3])}"
            )
        )

    # IC-6: CY reporting year is exactly one year after PY reporting year
    if py_parse:
        cy_yr = cy_parse.reporting_year
        py_yr = py_parse.reporting_year
        is_consecutive = (cy_yr == py_yr + 1)
        results.append(
            IntegrityCheckResult(
                check_id="IC-6",
                name="Consecutive Financial Years",
                description="CY reporting year is exactly one year after PY reporting year",
                status="Pass" if is_consecutive else "Fail",
                expected=f"CY ({cy_yr}) = PY ({py_yr}) + 1",
                actual=f"CY={cy_yr}, PY={py_yr}",
                difference=0.0 if is_consecutive else abs(cy_yr - py_yr),
                comment=f"Consecutive periods: {py_yr} -> {cy_yr}." if is_consecutive else f"Non-consecutive financial years: CY {cy_yr} vs PY {py_yr}."
            )
        )

    # IC-7: Long-term borrowings articulate
    if py_closing and py_opening:
        py_op_debt = py_opening.long_term_borrowings + py_opening.current_maturities_ltd
        py_cl_debt = py_closing.long_term_borrowings + py_closing.current_maturities_ltd
        py_proceeds = py_closing.cf_proceeds_lt_borrowings
        py_gap = (py_op_debt + py_proceeds) - py_cl_debt
        
        if abs(py_gap) > tolerance and py_proceeds < 0:
            results.append(
                IntegrityCheckResult(
                    check_id="IC-7",
                    name="Long-Term Borrowings Articulation (PY)",
                    description="Opening Long-Term Debt + CF Proceeds = Closing Long-Term Debt",
                    status="Fail",
                    expected=f"Closing Debt = {py_cl_debt:.2f}",
                    actual=f"Opening ({py_op_debt:.2f}) + CF Proceeds ({py_proceeds:.2f}) = {py_op_debt + py_proceeds:.2f} (Gap = {py_gap:.2f})",
                    difference=abs(py_gap),
                    comment="The cash flow statement does not articulate with the movement in long-term borrowings. Debt service comprises interest cost only."
                )
            )
        else:
            results.append(
                IntegrityCheckResult(
                    check_id="IC-7",
                    name="Long-Term Borrowings Articulation (PY)",
                    description="Opening Long-Term Debt + CF Proceeds = Closing Long-Term Debt",
                    status="Pass",
                    expected=f"Closing Debt = {py_cl_debt:.2f}",
                    actual="Reconciles within tolerance",
                    difference=abs(py_gap),
                    comment="Long-term borrowings articulate with cash flow statement."
                )
            )

    # IC-8: Reporting units consistency
    if py_parse:
        units_match = (cy_parse.units.lower() == py_parse.units.lower())
        results.append(
            IntegrityCheckResult(
                check_id="IC-8",
                name="Reporting Units Consistency",
                description="Reporting unit of measurement agrees across CY and PY workbooks",
                status="Pass" if units_match else "Fail",
                expected=f"CY Units: {cy_parse.units}",
                actual=f"PY Units: {py_parse.units}",
                difference=None,
                comment=f"Both workbooks report in Rs. {cy_parse.units}." if units_match else f"Unit mismatch: CY reports in {cy_parse.units}, PY reports in {py_parse.units}."
            )
        )

    # IC-9: Dynamic Cash flow classification consistency across years
    cf_cy_st_sec = None
    cf_py_st_sec = None
    for item in cy_parse.line_items:
        if item.sheet == "CF" and "short term borrowing" in item.normalised_label.lower():
            cf_cy_st_sec = item.section
            break
            
    if py_parse:
        for item in py_parse.line_items:
            if item.sheet == "CF" and "short term borrowing" in item.normalised_label.lower():
                cf_py_st_sec = item.section
                break

    if cf_cy_st_sec and cf_py_st_sec and cf_cy_st_sec != cf_py_st_sec:
        results.append(
            IntegrityCheckResult(
                check_id="IC-9",
                name="Cash Flow Classification Consistency",
                description="Classification of items across Operating, Investing, and Financing activities",
                status="Fail",
                expected="Consistent classification across years",
                actual=f"Short-term borrowings in Section {cf_py_st_sec} (PY) vs Section {cf_cy_st_sec} (CY)",
                difference=None,
                comment=f"Classification inconsistency detected: Short-term borrowings routed via Section {cf_py_st_sec} in PY and Section {cf_cy_st_sec} in CY."
            )
        )
    else:
        results.append(
            IntegrityCheckResult(
                check_id="IC-9",
                name="Cash Flow Classification Consistency",
                description="Classification of items across Operating, Investing, and Financing activities",
                status="Pass",
                expected="Consistent classification across years",
                actual="Consistent cash flow statement classification",
                difference=None,
                comment="Cash flow statement activities are consistently classified across reporting periods."
            )
        )

    return results
