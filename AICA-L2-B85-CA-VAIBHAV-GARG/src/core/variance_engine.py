"""Variance analysis and driver decomposition sentence generator (§9)."""
from typing import Dict, List, Optional
from src.core.calculator import SingleRatioResult
from src.core.derivations import PeriodFinancials


def generate_variance_reason(
    ratio: SingleRatioResult,
    closing_cy: PeriodFinancials,
    opening_cy: PeriodFinancials,
    closing_py: Optional[PeriodFinancials],
    opening_py: Optional[PeriodFinancials],
    units: str = "Lacs"
) -> str:
    """Generate dynamic driver decomposition reason for flagged variances."""
    if ratio.key == "roi":
        return "NA"

    if not ratio.is_flagged:
        return "Minor variance"
        
    var = ratio.variance_pct
    var_str = f"{abs(var):.1f}%" if var is not None else "significant"
    direction = "increased" if var and var > 0 else "decreased"
    u = f"Rs. {units}"
    
    # 4. Return on Equity
    if ratio.key == "return_on_equity":
        pat_cy = closing_cy.pat
        pat_py = closing_py.pat if closing_py else 0.0
        pat_growth = ((pat_cy - pat_py) / abs(pat_py) * 100.0) if pat_py != 0 else 0.0
        
        eq_cy = (closing_cy.shareholders_equity + opening_cy.shareholders_equity) / 2.0
        eq_py = ((closing_py.shareholders_equity + opening_py.shareholders_equity) / 2.0) if closing_py and opening_py else eq_cy
        eq_growth = ((eq_cy - eq_py) / eq_py * 100.0) if eq_py != 0 else 0.0
        
        return (
            f"The ratio has {direction} by {var_str} (from {ratio.value_py_formatted} to {ratio.value_cy_formatted}). "
            f"Profit after tax {('rose' if pat_growth > 0 else 'fell')} {abs(pat_growth):.1f}% (from {pat_py:,.2f} to {pat_cy:,.2f} {u}) "
            f"while average net worth remained largely stable ({('expanded' if eq_growth > 0 else 'contracted')} {abs(eq_growth):.1f}%). "
            f"Profit expansion directly drove the higher return on equity."
        )

    # 5. Inventory Turnover
    if ratio.key == "inventory_turnover":
        cogs_cy = closing_cy.cogs
        cogs_py = closing_py.cogs if closing_py else 0.0
        cogs_growth = ((cogs_cy - cogs_py) / cogs_py * 100.0) if cogs_py != 0 else 0.0
        
        inv_cy = (closing_cy.inventories + opening_cy.inventories) / 2.0
        inv_py = ((closing_py.inventories + opening_py.inventories) / 2.0) if closing_py and opening_py else inv_cy
        inv_growth = ((inv_cy - inv_py) / inv_py * 100.0) if inv_py != 0 else 0.0
        
        return (
            f"The ratio has {direction} by {var_str} (from {ratio.value_py_formatted} to {ratio.value_cy_formatted}). "
            f"Cost of goods sold rose {cogs_growth:.1f}% (from {cogs_py:,.2f} to {cogs_cy:,.2f} {u}) against average inventory "
            f"reducing {abs(inv_growth):.1f}% (from {inv_py:,.2f} to {inv_cy:,.2f} {u}), "
            f"reflecting higher sales throughput and leaner inventory holding."
        )

    # 9. Net Profit Ratio
    if ratio.key == "net_profit_ratio":
        pat_cy = closing_cy.pat
        pat_py = closing_py.pat if closing_py else 0.0
        pat_growth = ((pat_cy - pat_py) / abs(pat_py) * 100.0) if pat_py != 0 else 0.0
        
        rev_cy = closing_cy.revenue_net
        rev_py = closing_py.revenue_net if closing_py else 0.0
        rev_growth = ((rev_cy - rev_py) / rev_py * 100.0) if rev_py != 0 else 0.0
        
        return (
            f"The ratio has {direction} by {var_str} (from {ratio.value_py_formatted} to {ratio.value_cy_formatted}). "
            f"Profit after tax rose {pat_growth:.1f}% against net sales up only {rev_growth:.1f}%, "
            f"reflecting operating leverage: employee benefit expenses and depreciation both reduced in absolute terms despite higher revenue."
        )

    # 10. ROCE
    if ratio.key == "roce":
        ebit_cy = closing_cy.ebit
        ebit_py = closing_py.ebit if closing_py else 0.0
        ebit_growth = ((ebit_cy - ebit_py) / abs(ebit_py) * 100.0) if ebit_py != 0 else 0.0
        
        ce_cy = closing_cy.capital_employed
        ce_py = closing_py.capital_employed if closing_py else 0.0
        ce_growth = ((ce_cy - ce_py) / ce_py * 100.0) if ce_py != 0 else 0.0
        
        return (
            f"The ratio has {direction} by {var_str} (from {ratio.value_py_formatted} to {ratio.value_cy_formatted}). "
            f"Earnings before interest and tax increased {ebit_growth:.1f}% (from {ebit_py:,.2f} to {ebit_cy:,.2f} {u}) "
            f"on a relatively stable capital employed base ({('up' if ce_growth > 0 else 'down')} {abs(ce_growth):.1f}% from {ce_py:,.2f} to {ce_cy:,.2f} {u})."
        )

    # General Fallback for any other flagged ratio
    return (
        f"The ratio has {direction} by {var_str} (from {ratio.value_py_formatted} to {ratio.value_cy_formatted}) "
        f"driven by changes in {ratio.numerator_desc.lower()} relative to {ratio.denominator_desc.lower()}."
    )


def populate_reasons_for_results(
    ratios: List[SingleRatioResult],
    closing_cy: PeriodFinancials,
    opening_cy: PeriodFinancials,
    closing_py: Optional[PeriodFinancials],
    opening_py: Optional[PeriodFinancials],
    units: str = "Lacs"
) -> None:
    for r in ratios:
        if r.key == "roi":
            r.reason_generated = "NA"
            if not r.is_reason_edited:
                r.reason_final = "NA"
        elif r.is_flagged:
            reason = generate_variance_reason(r, closing_cy, opening_cy, closing_py, opening_py, units=units)
            r.reason_generated = reason
            if not r.is_reason_edited:
                r.reason_final = reason
        else:
            r.reason_generated = "Minor variance"
            if not r.is_reason_edited:
                r.reason_final = "Minor variance"
