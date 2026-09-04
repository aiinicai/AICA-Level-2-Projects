"""Calculation engine for Schedule III statutory analytical ratios."""
from dataclasses import dataclass, field
import math
from typing import Dict, List, Optional, Tuple, Any

from src.core.derivations import PeriodFinancials
from src.core.assumptions import AssumptionItem


@dataclass
class SingleRatioResult:
    id: int
    key: str
    name: str
    clause: str
    unit: str
    is_percentage: bool
    numerator_desc: str
    denominator_desc: str
    numerator_cy: Optional[float]
    denominator_cy: Optional[float]
    value_cy: Optional[float]
    value_cy_formatted: str
    numerator_py: Optional[float]
    denominator_py: Optional[float]
    value_py: Optional[float]
    value_py_formatted: str
    variance_pct: Optional[float]
    variance_pct_formatted: str
    is_flagged: bool
    status: str  # 'OK', 'Variance Flagged', 'Not meaningful' / 'NA'
    reason_generated: str = ""
    reason_final: str = ""
    is_reason_edited: bool = False
    footnote: str = ""
    workings_cy: Optional[Dict[str, Any]] = None
    workings_py: Optional[Dict[str, Any]] = None


@dataclass
class CalculationResultSet:
    cy_label: str
    py_label: str
    threshold_pct: float
    schedule_iii_ratios: List[SingleRatioResult]
    additional_ratios: List[SingleRatioResult] = field(default_factory=list)


def safe_divide(
    numerator: Optional[float],
    denominator: Optional[float],
    is_percentage: bool = False,
    decimals: int = 2,
    na_string: str = "NA"
) -> Tuple[Optional[float], str, str]:
    """Safely divide numerator by denominator with divide-by-zero protection."""
    if numerator is None or denominator is None:
        return None, na_string, "Data not available"
        
    if math.isnan(numerator) or math.isnan(denominator) or math.isinf(numerator) or math.isinf(denominator):
        return None, na_string, "Value is undefined"
        
    if abs(denominator) < 1e-6:
        return None, na_string, "Denominator is zero"
        
    if denominator < 0:
        return None, na_string, "Denominator is negative"
        
    val = (numerator / denominator) * (100.0 if is_percentage else 1.0)
    
    if is_percentage:
        fmt = f"{val:.{decimals}f}%"
    else:
        fmt = f"{val:.{decimals}f}"
        
    return val, fmt, ""


def compute_two_year_average(closing: float, opening: float) -> float:
    return (closing + opening) / 2.0


def compute_ratios(
    cy_closing: PeriodFinancials,
    cy_opening: PeriodFinancials,
    py_closing: Optional[PeriodFinancials],
    py_opening: Optional[PeriodFinancials],
    assumptions: Dict[str, AssumptionItem],
    threshold_pct: float = 25.0
) -> CalculationResultSet:
    """Compute all 11 Schedule III ratios for Current Year and Previous Year."""
    cy_label = getattr(cy_closing, "year_label", None) or getattr(cy_closing, "period_label", None) or "Current Year"
    py_label = getattr(py_closing, "year_label", None) or getattr(py_closing, "period_label", None) or "Previous Year"
    
    def _get_val(k: str, d: float) -> float:
        it = assumptions.get(k)
        if it is None:
            return d
        if hasattr(it, "current_value"):
            return it.current_value
        if hasattr(it, "value_cy"):
            return it.value_cy
        if isinstance(it, (int, float)):
            return float(it)
        return d

    raw_sales = _get_val("credit_sales_pct", 1.0)
    credit_sales_pct = raw_sales / 100.0 if raw_sales > 1.0 else raw_sales

    raw_purchases = _get_val("credit_purchases_pct", 1.0)
    credit_purchases_pct = raw_purchases / 100.0 if raw_purchases > 1.0 else raw_purchases
    pref_dividend = _get_val("preference_dividend", 0.0)
    lease_payments = _get_val("lease_payments", 0.0)
    principal_repay_cy = _get_val("principal_repayment_cy", 0.0)
    principal_repay_py = _get_val("principal_repayment_py", 0.0)
    include_st_repay = _get_val("include_st_repay", 0.0) == 1.0
    investment_income = _get_val("investment_income", 0.0)

    schedule_iii_results: List[SingleRatioResult] = []

    # 1. Current Ratio
    cr_num_cy, cr_den_cy = cy_closing.current_assets, cy_closing.current_liabilities
    cr_val_cy, cr_fmt_cy, cr_fn_cy = safe_divide(cr_num_cy, cr_den_cy, is_percentage=False)
    
    cr_num_py = py_closing.current_assets if py_closing else None
    cr_den_py = py_closing.current_liabilities if py_closing else None
    cr_val_py, cr_fmt_py, cr_fn_py = safe_divide(cr_num_py, cr_den_py, is_percentage=False)
    
    schedule_iii_results.append(
        _create_ratio_result(
            id=1, key="current_ratio", name="Current Ratio",
            clause="Clause 6(L)(i) of General Instructions to Schedule III", unit="x", is_pct=False,
            num_desc="Current Assets", den_desc="Current Liabilities",
            num_cy=cr_num_cy, den_cy=cr_den_cy, val_cy=cr_val_cy, fmt_cy=cr_fmt_cy, fn_cy=cr_fn_cy,
            num_py=cr_num_py, den_py=cr_den_py, val_py=cr_val_py, fmt_py=cr_fmt_py, fn_py=cr_fn_py,
            threshold_pct=threshold_pct
        )
    )

    # 2. Debt-Equity Ratio
    de_num_cy, de_den_cy = cy_closing.total_debt, cy_closing.shareholders_equity
    de_val_cy, de_fmt_cy, de_fn_cy = safe_divide(de_num_cy, de_den_cy, is_percentage=False)
    
    de_num_py = py_closing.total_debt if py_closing else None
    de_den_py = py_closing.shareholders_equity if py_closing else None
    de_val_py, de_fmt_py, de_fn_py = safe_divide(de_num_py, de_den_py, is_percentage=False)
    
    schedule_iii_results.append(
        _create_ratio_result(
            id=2, key="debt_equity_ratio", name="Debt-Equity Ratio",
            clause="Clause 6(L)(ii) of General Instructions to Schedule III", unit="x", is_pct=False,
            num_desc="Total Debt", den_desc="Shareholders' Equity",
            num_cy=de_num_cy, den_cy=de_den_cy, val_cy=de_val_cy, fmt_cy=de_fmt_cy, fn_cy=de_fn_cy,
            num_py=de_num_py, den_py=de_den_py, val_py=de_val_py, fmt_py=de_fmt_py, fn_py=de_fn_py,
            threshold_pct=threshold_pct
        )
    )

    # 3. Debt Service Coverage Ratio (DSCR)
    dscr_num_cy = cy_closing.eads
    interest_cy = abs(cy_closing.cf_interest_paid) if cy_closing.cf_interest_paid else cy_closing.finance_costs
    st_repay_cy = abs(cy_closing.cf_repayment_st_borrowings) if (include_st_repay and cy_closing.cf_repayment_st_borrowings) else 0.0
    dscr_den_cy = interest_cy + principal_repay_cy + lease_payments + st_repay_cy
    dscr_val_cy, dscr_fmt_cy, dscr_fn_cy = safe_divide(dscr_num_cy, dscr_den_cy, is_percentage=False)

    if py_closing:
        dscr_num_py = py_closing.eads
        interest_py = abs(py_closing.cf_interest_paid) if py_closing.cf_interest_paid else py_closing.finance_costs
        st_repay_py = abs(py_closing.cf_repayment_st_borrowings) if (include_st_repay and py_closing.cf_repayment_st_borrowings) else 0.0
        dscr_den_py = interest_py + principal_repay_py + lease_payments + st_repay_py
        dscr_val_py, dscr_fmt_py, dscr_fn_py = safe_divide(dscr_num_py, dscr_den_py, is_percentage=False)
    else:
        dscr_num_py, dscr_den_py, dscr_val_py, dscr_fmt_py, dscr_fn_py = None, None, None, "NA", ""

    schedule_iii_results.append(
        _create_ratio_result(
            id=3, key="dscr", name="Debt Service Coverage Ratio",
            clause="Clause 6(L)(iii) of General Instructions to Schedule III", unit="x", is_pct=False,
            num_desc="Earnings Available for Debt Service", den_desc="Debt Service",
            num_cy=dscr_num_cy, den_cy=dscr_den_cy, val_cy=dscr_val_cy, fmt_cy=dscr_fmt_cy, fn_cy=dscr_fn_cy,
            num_py=dscr_num_py, den_py=dscr_den_py, val_py=dscr_val_py, fmt_py=dscr_fmt_py, fn_py=dscr_fn_py,
            threshold_pct=threshold_pct
        )
    )

    # 4. Return on Equity (ROE)
    roe_num_cy = cy_closing.pat - pref_dividend
    roe_den_cy = compute_two_year_average(cy_closing.shareholders_equity, cy_opening.shareholders_equity)
    roe_val_cy, roe_fmt_cy, roe_fn_cy = safe_divide(roe_num_cy, roe_den_cy, is_percentage=True)

    if py_closing and py_opening:
        roe_num_py = py_closing.pat - pref_dividend
        roe_den_py = compute_two_year_average(py_closing.shareholders_equity, py_opening.shareholders_equity)
        roe_val_py, roe_fmt_py, roe_fn_py = safe_divide(roe_num_py, roe_den_py, is_percentage=True)
    else:
        roe_num_py, roe_den_py, roe_val_py, roe_fmt_py, roe_fn_py = None, None, None, "NA", ""

    schedule_iii_results.append(
        _create_ratio_result(
            id=4, key="return_on_equity", name="Return on Equity Ratio",
            clause="Clause 6(L)(iv) of General Instructions to Schedule III", unit="%", is_pct=True,
            num_desc="Net Profit after Tax − Preference Dividend", den_desc="Average Shareholders' Equity",
            num_cy=roe_num_cy, den_cy=roe_den_cy, val_cy=roe_val_cy, fmt_cy=roe_fmt_cy, fn_cy=roe_fn_cy,
            num_py=roe_num_py, den_py=roe_den_py, val_py=roe_val_py, fmt_py=roe_fmt_py, fn_py=roe_fn_py,
            threshold_pct=threshold_pct
        )
    )

    # 5. Inventory Turnover Ratio
    inv_num_cy = cy_closing.cogs
    inv_den_cy = compute_two_year_average(cy_closing.inventories, cy_opening.inventories)
    inv_val_cy, inv_fmt_cy, inv_fn_cy = safe_divide(inv_num_cy, inv_den_cy, is_percentage=False)

    if py_closing and py_opening:
        inv_num_py = py_closing.cogs
        inv_den_py = compute_two_year_average(py_closing.inventories, py_opening.inventories)
        inv_val_py, inv_fmt_py, inv_fn_py = safe_divide(inv_num_py, inv_den_py, is_percentage=False)
    else:
        inv_num_py, inv_den_py, inv_val_py, inv_fmt_py, inv_fn_py = None, None, None, "NA", ""

    schedule_iii_results.append(
        _create_ratio_result(
            id=5, key="inventory_turnover", name="Inventory Turnover Ratio",
            clause="Clause 6(L)(v) of General Instructions to Schedule III", unit="x", is_pct=False,
            num_desc="Cost of Goods Sold", den_desc="Average Inventory",
            num_cy=inv_num_cy, den_cy=inv_den_cy, val_cy=inv_val_cy, fmt_cy=inv_fmt_cy, fn_cy=inv_fn_cy,
            num_py=inv_num_py, den_py=inv_den_py, val_py=inv_val_py, fmt_py=inv_fmt_py, fn_py=inv_fn_py,
            threshold_pct=threshold_pct
        )
    )

    # 6. Trade Receivables Turnover Ratio
    rec_num_cy = cy_closing.revenue_net * credit_sales_pct
    rec_den_cy = compute_two_year_average(cy_closing.trade_receivables, cy_opening.trade_receivables)
    rec_val_cy, rec_fmt_cy, rec_fn_cy = safe_divide(rec_num_cy, rec_den_cy, is_percentage=False)

    if py_closing and py_opening:
        rec_num_py = py_closing.revenue_net * credit_sales_pct
        rec_den_py = compute_two_year_average(py_closing.trade_receivables, py_opening.trade_receivables)
        rec_val_py, rec_fmt_py, rec_fn_py = safe_divide(rec_num_py, rec_den_py, is_percentage=False)
    else:
        rec_num_py, rec_den_py, rec_val_py, rec_fmt_py, rec_fn_py = None, None, None, "NA", ""

    schedule_iii_results.append(
        _create_ratio_result(
            id=6, key="trade_receivables_turnover", name="Trade Receivables Turnover Ratio",
            clause="Clause 6(L)(vi) of General Instructions to Schedule III", unit="x", is_pct=False,
            num_desc="Net Credit Sales", den_desc="Average Trade Receivables",
            num_cy=rec_num_cy, den_cy=rec_den_cy, val_cy=rec_val_cy, fmt_cy=rec_fmt_cy, fn_cy=rec_fn_cy,
            num_py=rec_num_py, den_py=rec_den_py, val_py=rec_val_py, fmt_py=rec_fmt_py, fn_py=rec_fn_py,
            threshold_pct=threshold_pct
        )
    )

    # 7. Trade Payables Turnover Ratio
    pay_num_cy = (cy_closing.cost_of_materials + cy_closing.purchases_stock_in_trade) * credit_purchases_pct
    pay_den_cy = compute_two_year_average(cy_closing.trade_payables_total, cy_opening.trade_payables_total)
    pay_val_cy, pay_fmt_cy, pay_fn_cy = safe_divide(pay_num_cy, pay_den_cy, is_percentage=False)

    if py_closing and py_opening:
        pay_num_py = (py_closing.cost_of_materials + py_closing.purchases_stock_in_trade) * credit_purchases_pct
        pay_den_py = compute_two_year_average(py_closing.trade_payables_total, py_opening.trade_payables_total)
        pay_val_py, pay_fmt_py, pay_fn_py = safe_divide(pay_num_py, pay_den_py, is_percentage=False)
    else:
        pay_num_py, pay_den_py, pay_val_py, pay_fmt_py, pay_fn_py = None, None, None, "NA", ""

    schedule_iii_results.append(
        _create_ratio_result(
            id=7, key="trade_payables_turnover", name="Trade Payables Turnover Ratio",
            clause="Clause 6(L)(vii) of General Instructions to Schedule III", unit="x", is_pct=False,
            num_desc="Net Credit Purchases", den_desc="Average Trade Payables",
            num_cy=pay_num_cy, den_cy=pay_den_cy, val_cy=pay_val_cy, fmt_cy=pay_fmt_cy, fn_cy=pay_fn_cy,
            num_py=pay_num_py, den_py=pay_den_py, val_py=pay_val_py, fmt_py=pay_fmt_py, fn_py=pay_fn_py,
            threshold_pct=threshold_pct
        )
    )

    # 8. Net Capital Turnover Ratio
    nct_num_cy = cy_closing.revenue_net
    nct_den_cy = compute_two_year_average(cy_closing.working_capital, cy_opening.working_capital)
    nct_val_cy, nct_fmt_cy, nct_fn_cy = safe_divide(nct_num_cy, nct_den_cy, is_percentage=False)

    if py_closing and py_opening:
        nct_num_py = py_closing.revenue_net
        nct_den_py = compute_two_year_average(py_closing.working_capital, py_opening.working_capital)
        nct_val_py, nct_fmt_py, nct_fn_py = safe_divide(nct_num_py, nct_den_py, is_percentage=False)
    else:
        nct_num_py, nct_den_py, nct_val_py, nct_fmt_py, nct_fn_py = None, None, None, "NA", ""

    schedule_iii_results.append(
        _create_ratio_result(
            id=8, key="net_capital_turnover", name="Net Capital Turnover Ratio",
            clause="Clause 6(L)(viii) of General Instructions to Schedule III", unit="x", is_pct=False,
            num_desc="Net Revenue", den_desc="Average Working Capital",
            num_cy=nct_num_cy, den_cy=nct_den_cy, val_cy=nct_val_cy, fmt_cy=nct_fmt_cy, fn_cy=nct_fn_cy,
            num_py=nct_num_py, den_py=nct_den_py, val_py=nct_val_py, fmt_py=nct_fmt_py, fn_py=nct_fn_py,
            threshold_pct=threshold_pct
        )
    )

    # 9. Net Profit Ratio
    np_num_cy = cy_closing.pat
    np_den_cy = cy_closing.revenue_net
    np_val_cy, np_fmt_cy, np_fn_cy = safe_divide(np_num_cy, np_den_cy, is_percentage=True)

    if py_closing:
        np_num_py = py_closing.pat
        np_den_py = py_closing.revenue_net
        np_val_py, np_fmt_py, np_fn_py = safe_divide(np_num_py, np_den_py, is_percentage=True)
    else:
        np_num_py, np_den_py, np_val_py, np_fmt_py, np_fn_py = None, None, None, "NA", ""

    schedule_iii_results.append(
        _create_ratio_result(
            id=9, key="net_profit_ratio", name="Net Profit Ratio",
            clause="Clause 6(L)(ix) of General Instructions to Schedule III", unit="%", is_pct=True,
            num_desc="Profit After Tax", den_desc="Net Revenue",
            num_cy=np_num_cy, den_cy=np_den_cy, val_cy=np_val_cy, fmt_cy=np_fmt_cy, fn_cy=np_fn_cy,
            num_py=np_num_py, den_py=np_den_py, val_py=np_val_py, fmt_py=np_fmt_py, fn_py=np_fn_py,
            threshold_pct=threshold_pct
        )
    )

    # 10. Return on Capital Employed (ROCE)
    roce_num_cy = cy_closing.ebit
    roce_den_cy = cy_closing.capital_employed
    roce_val_cy, roce_fmt_cy, roce_fn_cy = safe_divide(roce_num_cy, roce_den_cy, is_percentage=True)

    if py_closing:
        roce_num_py = py_closing.ebit
        roce_den_py = py_closing.capital_employed
        roce_val_py, roce_fmt_py, roce_fn_py = safe_divide(roce_num_py, roce_den_py, is_percentage=True)
    else:
        roce_num_py, roce_den_py, roce_val_py, roce_fmt_py, roce_fn_py = None, None, None, "NA", ""

    schedule_iii_results.append(
        _create_ratio_result(
            id=10, key="roce", name="Return on Capital Employed",
            clause="Clause 6(L)(x) of General Instructions to Schedule III", unit="%", is_pct=True,
            num_desc="Earnings Before Interest & Tax", den_desc="Capital Employed",
            num_cy=roce_num_cy, den_cy=roce_den_cy, val_cy=roce_val_cy, fmt_cy=roce_fmt_cy, fn_cy=roce_fn_cy,
            num_py=roce_num_py, den_py=roce_den_py, val_py=roce_val_py, fmt_py=roce_fmt_py, fn_py=roce_fn_py,
            threshold_pct=threshold_pct
        )
    )

    # 11. Return on Investment (ROI) - Outputs 'NA' when no investments per user requirement
    roi_num_cy = investment_income
    roi_den_cy = compute_two_year_average(cy_closing.total_investments, cy_opening.total_investments)
    roi_val_cy, roi_fmt_cy, roi_fn_cy = safe_divide(roi_num_cy, roi_den_cy, is_percentage=True, na_string="NA")

    if py_closing and py_opening:
        roi_num_py = investment_income
        roi_den_py = compute_two_year_average(py_closing.total_investments, py_opening.total_investments)
        roi_val_py, roi_fmt_py, roi_fn_py = safe_divide(roi_num_py, roi_den_py, is_percentage=True, na_string="NA")
    else:
        roi_num_py, roi_den_py, roi_val_py, roi_fmt_py, roi_fn_py = None, None, None, "NA", ""

    # Force "NA" for ROI when investments are nil
    if roi_val_cy is None:
        roi_fmt_cy = "NA"
    if roi_val_py is None:
        roi_fmt_py = "NA"

    schedule_iii_results.append(
        _create_ratio_result(
            id=11, key="roi", name="Return on Investment",
            clause="Clause 6(L)(xi) of General Instructions to Schedule III", unit="%", is_pct=True,
            num_desc="Income from Investments", den_desc="Average Total Investments",
            num_cy=roi_num_cy, den_cy=roi_den_cy, val_cy=roi_val_cy, fmt_cy=roi_fmt_cy, fn_cy=roi_fn_cy,
            num_py=roi_num_py, den_py=roi_den_py, val_py=roi_val_py, fmt_py=roi_fmt_py, fn_py=roi_fn_py,
            threshold_pct=threshold_pct
        )
    )

    return CalculationResultSet(
        cy_label=cy_label,
        py_label=py_label,
        threshold_pct=threshold_pct,
        schedule_iii_ratios=schedule_iii_results,
    )


def _create_ratio_result(
    id: int,
    key: str,
    name: str,
    clause: str,
    unit: str,
    is_pct: bool,
    num_desc: str,
    den_desc: str,
    num_cy: Optional[float],
    den_cy: Optional[float],
    val_cy: Optional[float],
    fmt_cy: str,
    fn_cy: str,
    num_py: Optional[float],
    den_py: Optional[float],
    val_py: Optional[float],
    fmt_py: str,
    fn_py: str,
    threshold_pct: float
) -> SingleRatioResult:
    footnote = ""
    status = "OK"
    var_val = None
    var_fmt = "Minor variance"
    is_flagged = False

    if key == "roi" and (val_cy is None or fmt_cy == "NA"):
        status = "NA"
        var_fmt = "NA"
        footnote = "The entity holds no investments; return on investment is NA."
        return SingleRatioResult(
            id=id, key=key, name=name, clause=clause, unit=unit, is_percentage=is_pct,
            numerator_desc=num_desc, denominator_desc=den_desc,
            numerator_cy=num_cy, denominator_cy=den_cy, value_cy=val_cy, value_cy_formatted=fmt_cy,
            numerator_py=num_py, denominator_py=den_py, value_py=val_py, value_py_formatted=fmt_py,
            variance_pct=None, variance_pct_formatted=var_fmt, is_flagged=False,
            status=status, reason_generated="NA", reason_final="NA", footnote=footnote
        )

    if val_cy is None or val_py is None:
        status = "NA"
        var_fmt = "NA"
        footnote = f"Ratio cannot be computed for one or more periods ({fn_cy or fn_py})."
    else:
        if abs(val_py) < 1e-6:
            var_fmt = "NA"
            footnote = "Previous year ratio is zero; percentage variance is undefined."
        else:
            var_val = ((val_cy - val_py) / abs(val_py)) * 100.0
            sign = "+" if var_val > 0 else ""
            var_fmt = f"{sign}{var_val:.2f}%"
            if abs(var_val) >= threshold_pct:
                is_flagged = True
                status = "Variance Flagged"
            else:
                status = "OK"
                
    # Default unflagged reason is "Minor variance" per user requirement
    reason_init = "Minor variance" if not is_flagged else ""

    return SingleRatioResult(
        id=id,
        key=key,
        name=name,
        clause=clause,
        unit=unit,
        is_percentage=is_pct,
        numerator_desc=num_desc,
        denominator_desc=den_desc,
        numerator_cy=num_cy,
        denominator_cy=den_cy,
        value_cy=val_cy,
        value_cy_formatted=fmt_cy,
        numerator_py=num_py,
        denominator_py=den_py,
        value_py=val_py,
        value_py_formatted=fmt_py,
        variance_pct=var_val,
        variance_pct_formatted=var_fmt,
        is_flagged=is_flagged,
        status=status,
        reason_generated=reason_init,
        reason_final=reason_init,
        footnote=footnote
    )
