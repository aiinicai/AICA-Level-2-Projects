"""Discounted Cash Flow valuation engine — Module 7.

Every assumption is an explicit field on DCFAssumptions - nothing is a
hidden default baked into a formula. The full year-by-year build-up
(Revenue -> EBITDA -> EBIT -> Tax -> NOPAT -> +D&A -> -Capex -> -ΔWC ->
FCFF -> discounted) is returned in DCFResult.year_projections so every
number in the final per-share value is traceable back to its inputs,
per the spec's "every DCF assumption must be visible" requirement.

This module NEVER presents a DCF output as an objectively correct
price - DCFResult always carries the full assumption set alongside the
result, and scenarios.py is the expected way to present a range
(bear/base/bull) rather than a single point estimate.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, model_validator

from app.core.enums import DataStatus
from app.core.models import FinancialStatement, MetricResult


class DCFAssumptions(BaseModel):
    """Every input the DCF engine uses. Nothing is computed from a
    hidden default — if a field isn't set here, it isn't used."""

    projection_years: int = Field(default=5, ge=1, le=15)

    # Revenue growth: either one rate applied every year, or a list with
    # one entry per projection year (must match projection_years length).
    revenue_growth_rate: float | list[float] = Field(
        ..., description="Annual revenue growth rate(s), e.g. 0.12 for 12%"
    )
    ebitda_margin: float | list[float] = Field(
        ..., description="EBITDA margin(s) as a fraction of revenue, e.g. 0.25"
    )
    depreciation_pct_of_revenue: float | list[float] = Field(
        ..., description="D&A as a fraction of revenue"
    )
    capex_pct_of_revenue: float | list[float] = Field(
        ..., description="Capex as a fraction of revenue"
    )
    wc_change_pct_of_revenue_change: float | list[float] = Field(
        default=0.0,
        description="Incremental working capital investment as a fraction "
        "of the YoY change in revenue",
    )
    tax_rate: float = Field(..., ge=0.0, le=1.0)
    wacc: float = Field(..., gt=0.0, lt=1.0, description="Weighted Average Cost of Capital")
    terminal_growth_rate: float = Field(..., description="Perpetuity growth rate applied after the projection window")

    @model_validator(mode="after")
    def _wacc_must_exceed_terminal_growth(self) -> "DCFAssumptions":
        if self.wacc <= self.terminal_growth_rate:
            raise ValueError(
                f"WACC ({self.wacc}) must exceed terminal growth rate "
                f"({self.terminal_growth_rate}) - the Gordon Growth terminal "
                "value formula is undefined/negative otherwise."
            )
        return self

    def _expand(self, field: float | list[float]) -> list[float]:
        if isinstance(field, list):
            if len(field) != self.projection_years:
                raise ValueError(
                    f"List-valued assumption has {len(field)} entries but "
                    f"projection_years={self.projection_years}."
                )
            return field
        return [field] * self.projection_years


class DCFYearProjection(BaseModel):
    """One year of the DCF build-up — fully transparent line items."""

    year_index: int
    revenue: float
    ebitda: float
    ebit: float
    tax: float
    nopat: float
    depreciation: float
    capex: float
    wc_change: float
    fcff: float
    discount_factor: float
    pv_fcff: float


class DCFResult(BaseModel):
    """Full DCF output: every year's build-up plus the final valuation
    bridge (EV -> Equity Value -> Value Per Share)."""

    company: str
    base_period: str
    assumptions: DCFAssumptions
    year_projections: list[DCFYearProjection]
    terminal_value: float
    pv_terminal_value: float
    enterprise_value: float
    net_debt: float
    equity_value: float
    shares_outstanding: float
    value_per_share: float
    status: DataStatus = DataStatus.OK
    data_quality_notes: list[str] = Field(default_factory=list)

    DISCLAIMER: str = (
        "This DCF output is a decision-support estimate under the stated "
        "assumptions, not an objectively correct price or a guarantee of "
        "future value. Small changes in WACC or terminal growth materially "
        "change the result - see the sensitivity table before relying on "
        "a single figure."
    )


def run_dcf(
    base_statement: FinancialStatement,
    assumptions: DCFAssumptions,
    *,
    company_name: str | None = None,
) -> DCFResult | MetricResult:
    """Run a full DCF given a base-year FinancialStatement and explicit
    assumptions.

    Returns a DCFResult on success. Returns a MetricResult with
    status != OK (never a fabricated DCFResult) if required base-year
    inputs (sales, net debt components, share count) are missing.
    """
    company = company_name or base_statement.company

    if not base_statement.sales:
        return MetricResult(
            metric_name="DCF Value Per Share", formula="See DCFResult build-up",
            inputs={"base_revenue": base_statement.sales}, value=None,
            unit=base_statement.unit, period=base_statement.period,
            status=DataStatus.MISSING_INPUT,
            data_quality_notes=["Base-year Sales is required to run a DCF and is missing."],
        )
    if base_statement.num_equity_shares is None or base_statement.num_equity_shares <= 0:
        return MetricResult(
            metric_name="DCF Value Per Share", formula="See DCFResult build-up",
            inputs={"num_equity_shares": base_statement.num_equity_shares}, value=None,
            unit=base_statement.unit, period=base_statement.period,
            status=DataStatus.MISSING_INPUT,
            data_quality_notes=["Base-year share count is required and is missing/zero."],
        )

    borrowings = base_statement.borrowings or 0.0
    cash = base_statement.cash_and_bank or 0.0
    net_debt = borrowings - cash

    growth = assumptions._expand(assumptions.revenue_growth_rate)
    margin = assumptions._expand(assumptions.ebitda_margin)
    dep_pct = assumptions._expand(assumptions.depreciation_pct_of_revenue)
    capex_pct = assumptions._expand(assumptions.capex_pct_of_revenue)
    wc_pct = assumptions._expand(assumptions.wc_change_pct_of_revenue_change)

    projections: list[DCFYearProjection] = []
    prev_revenue = base_statement.sales

    for i in range(assumptions.projection_years):
        revenue = prev_revenue * (1.0 + growth[i])
        ebitda = revenue * margin[i]
        depreciation = revenue * dep_pct[i]
        ebit = ebitda - depreciation
        tax = max(ebit, 0.0) * assumptions.tax_rate  # no tax benefit on losses assumed
        nopat = ebit - tax
        capex = revenue * capex_pct[i]
        revenue_change = revenue - prev_revenue
        wc_change = revenue_change * wc_pct[i]
        fcff = nopat + depreciation - capex - wc_change

        year_index = i + 1
        discount_factor = 1.0 / ((1.0 + assumptions.wacc) ** year_index)
        pv_fcff = fcff * discount_factor

        projections.append(
            DCFYearProjection(
                year_index=year_index, revenue=round(revenue, 2), ebitda=round(ebitda, 2),
                ebit=round(ebit, 2), tax=round(tax, 2), nopat=round(nopat, 2),
                depreciation=round(depreciation, 2), capex=round(capex, 2),
                wc_change=round(wc_change, 2), fcff=round(fcff, 2),
                discount_factor=round(discount_factor, 6), pv_fcff=round(pv_fcff, 2),
            )
        )
        prev_revenue = revenue

    terminal_fcff = projections[-1].fcff * (1.0 + assumptions.terminal_growth_rate)
    terminal_value = terminal_fcff / (assumptions.wacc - assumptions.terminal_growth_rate)
    pv_terminal_value = terminal_value * projections[-1].discount_factor

    enterprise_value = sum(p.pv_fcff for p in projections) + pv_terminal_value
    equity_value = enterprise_value - net_debt
    value_per_share = (equity_value * 1e7) / base_statement.num_equity_shares  # crore -> INR

    notes = []
    if pv_terminal_value / enterprise_value > 0.75:
        notes.append(
            f"Terminal value represents {pv_terminal_value / enterprise_value:.0%} of "
            "enterprise value — the result is highly sensitive to the terminal growth "
            "and WACC assumptions; treat with proportionate caution."
        )

    return DCFResult(
        company=company, base_period=base_statement.period, assumptions=assumptions,
        year_projections=projections, terminal_value=round(terminal_value, 2),
        pv_terminal_value=round(pv_terminal_value, 2), enterprise_value=round(enterprise_value, 2),
        net_debt=round(net_debt, 2), equity_value=round(equity_value, 2),
        shares_outstanding=base_statement.num_equity_shares,
        value_per_share=round(value_per_share, 2), data_quality_notes=notes,
    )


def sensitivity_analysis(
    base_statement: FinancialStatement,
    base_assumptions: DCFAssumptions,
    *,
    wacc_range: list[float],
    terminal_growth_range: list[float],
) -> dict[str, dict[str, float | None]]:
    """Grid of value-per-share across WACC x terminal growth rate combinations.

    Returns a nested dict: {wacc_str: {terminal_growth_str: value_per_share}}.
    Combinations where WACC <= terminal growth are skipped (None) rather
    than silently clamped, since that combination is mathematically invalid
    for the Gordon Growth terminal value formula.
    """
    grid: dict[str, dict[str, float | None]] = {}
    for wacc in wacc_range:
        row: dict[str, float | None] = {}
        for tg in terminal_growth_range:
            if wacc <= tg:
                row[f"{tg:.1%}"] = None
                continue
            variant = base_assumptions.model_copy(update={"wacc": wacc, "terminal_growth_rate": tg})
            result = run_dcf(base_statement, variant)
            row[f"{tg:.1%}"] = result.value_per_share if isinstance(result, DCFResult) else None
        grid[f"{wacc:.1%}"] = row
    return grid


def revenue_margin_sensitivity(
    base_statement: FinancialStatement,
    base_assumptions: DCFAssumptions,
    *,
    revenue_growth_range: list[float],
    ebitda_margin_range: list[float],
) -> dict[str, dict[str, float | None]]:
    """Grid of value-per-share across (flat) revenue growth x EBITDA margin."""
    grid: dict[str, dict[str, float | None]] = {}
    for g in revenue_growth_range:
        row: dict[str, float | None] = {}
        for m in ebitda_margin_range:
            variant = base_assumptions.model_copy(
                update={"revenue_growth_rate": g, "ebitda_margin": m}
            )
            result = run_dcf(base_statement, variant)
            row[f"{m:.1%}"] = result.value_per_share if isinstance(result, DCFResult) else None
        grid[f"{g:.1%}"] = row
    return grid
