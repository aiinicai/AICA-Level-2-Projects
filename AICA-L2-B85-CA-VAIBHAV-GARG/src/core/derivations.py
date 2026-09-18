"""Derived financial sub-totals and fallback derivations (§5.4)."""
from dataclasses import dataclass
from typing import Dict, Optional
from src.core.components import MappingDecision


@dataclass
class PeriodFinancials:
    # Mapped core components
    share_capital: float = 0.0
    preference_share_capital: float = 0.0
    reserves_surplus: float = 0.0
    long_term_borrowings: float = 0.0
    deferred_tax_liability: float = 0.0
    other_lt_liabilities: float = 0.0
    long_term_provisions: float = 0.0
    short_term_borrowings: float = 0.0
    current_maturities_ltd: float = 0.0
    trade_payables_msme: float = 0.0
    trade_payables_other: float = 0.0
    trade_payables: float = 0.0
    other_current_liabilities: float = 0.0
    short_term_provisions: float = 0.0
    reported_total_eq_liab: float = 0.0
    ppe: float = 0.0
    intangible_assets: float = 0.0
    cwip: float = 0.0
    non_current_investments: float = 0.0
    current_investments: float = 0.0
    deferred_tax_asset: float = 0.0
    other_non_current_assets: float = 0.0
    inventories: float = 0.0
    trade_receivables: float = 0.0
    cash_equivalents: float = 0.0
    short_term_loans_advances: float = 0.0
    other_current_assets: float = 0.0
    reported_total_assets: float = 0.0
    revenue_gross: float = 0.0
    gst: float = 0.0
    revenue_net: float = 0.0
    other_income: float = 0.0
    total_income: float = 0.0
    cost_of_materials: float = 0.0
    purchases_stock_in_trade: float = 0.0
    changes_in_inventories: float = 0.0
    employee_benefits: float = 0.0
    finance_costs: float = 0.0
    depreciation: float = 0.0
    other_expenses: float = 0.0
    total_expenses: float = 0.0
    pbt: float = 0.0
    current_tax: float = 0.0
    deferred_tax: float = 0.0
    tax_earlier_years: float = 0.0
    pat: float = 0.0
    cf_proceeds_lt_borrowings: float = 0.0
    cf_repayment_lt_borrowings: float = 0.0
    cf_repayment_st_borrowings: float = 0.0
    cf_movement_st_borrowings: float = 0.0
    cf_increase_share_capital: float = 0.0
    cf_interest_paid: float = 0.0
    cf_interest_income: float = 0.0
    cf_depreciation: float = 0.0
    cf_misc_written_off: float = 0.0
    cf_purchase_fixed_assets: float = 0.0
    cf_dividend_income: float = 0.0
    cf_profit_sale_investments: float = 0.0
    cf_margin_money: float = 0.0

    # Derived sub-totals
    trade_payables_total: float = 0.0
    current_assets: float = 0.0
    current_liabilities: float = 0.0
    shareholders_equity: float = 0.0
    total_debt: float = 0.0
    working_capital: float = 0.0
    tangible_net_worth: float = 0.0
    capital_employed: float = 0.0
    total_investments: float = 0.0
    cogs: float = 0.0
    ebit: float = 0.0
    eads: float = 0.0

    # Metadata
    year_label: str = ""
    is_derived_revenue_net: bool = False
    is_derived_pat: bool = False
    is_derived_pbt: bool = False


def extract_period_financials(
    mappings: Dict[str, MappingDecision],
    period: str = "reporting",  # 'reporting' or 'comparative'
    year_label: str = ""
) -> PeriodFinancials:
    """Extract and derive all financial figures for a single period."""
    raw: Dict[str, float] = {}
    for k, decision in mappings.items():
        if decision.is_manual:
            if period == "reporting":
                val = decision.manual_amount_reporting if decision.manual_amount_reporting is not None else decision.amount_reporting
            else:
                val = decision.manual_amount_comparative if decision.manual_amount_comparative is not None else decision.amount_comparative
        else:
            val = decision.amount_reporting if period == "reporting" else decision.amount_comparative
        raw[k] = val or 0.0

    fin = PeriodFinancials(year_label=year_label)
    
    # Assign raw values
    for field_name in PeriodFinancials.__dataclass_fields__:
        if field_name in raw:
            setattr(fin, field_name, raw[field_name])

    # Fallback derivations (§5.4)
    if fin.revenue_net == 0.0 and fin.revenue_gross != 0.0:
        fin.revenue_net = fin.revenue_gross - fin.gst
        fin.is_derived_revenue_net = True

    if fin.pbt == 0.0 and (fin.total_income != 0.0 or fin.total_expenses != 0.0):
        fin.pbt = fin.total_income - fin.total_expenses
        fin.is_derived_pbt = True

    if fin.pat == 0.0 and fin.pbt != 0.0:
        fin.pat = fin.pbt - fin.current_tax - fin.deferred_tax - fin.tax_earlier_years
        fin.is_derived_pat = True

    # Derived sub-totals (§5.4)
    # Trade Payables Total
    # If sub-lines MSME / other exist, sum them. Otherwise use parent trade_payables.
    msme_sum = fin.trade_payables_msme + fin.trade_payables_other
    if msme_sum != 0.0:
        fin.trade_payables_total = msme_sum
    else:
        fin.trade_payables_total = fin.trade_payables

    fin.current_assets = (
        fin.inventories
        + fin.trade_receivables
        + fin.cash_equivalents
        + fin.short_term_loans_advances
        + fin.other_current_assets
        + fin.current_investments
    )

    fin.current_liabilities = (
        fin.short_term_borrowings
        + fin.trade_payables_total
        + fin.other_current_liabilities
        + fin.short_term_provisions
    )

    fin.shareholders_equity = fin.share_capital + fin.reserves_surplus
    fin.total_debt = fin.long_term_borrowings + fin.short_term_borrowings + fin.current_maturities_ltd
    fin.working_capital = fin.current_assets - fin.current_liabilities
    fin.tangible_net_worth = fin.shareholders_equity - fin.intangible_assets
    fin.capital_employed = fin.tangible_net_worth + fin.total_debt + fin.deferred_tax_liability
    fin.total_investments = fin.non_current_investments + fin.current_investments
    fin.cogs = fin.cost_of_materials + fin.purchases_stock_in_trade + fin.changes_in_inventories
    fin.ebit = fin.pbt + fin.finance_costs
    fin.eads = fin.pat + fin.depreciation + fin.finance_costs + fin.cf_misc_written_off

    return fin
