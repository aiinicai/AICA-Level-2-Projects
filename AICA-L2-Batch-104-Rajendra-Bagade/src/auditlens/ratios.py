"""
The eleven ratios whose disclosure is mandated by Schedule III to the
Companies Act, 2013, as amended by the Ministry of Corporate Affairs
notification G.S.R. 207(E) dated 24 March 2021, applicable from the
financial year commencing 1 April 2021.

Schedule III also requires an explanation in the notes wherever a ratio
moves by more than 25 per cent against the preceding year.  The engine
computes the movement and flags the ones that must be explained; the
explanation itself is drafted separately and always reviewed by the
auditor.

Turnover ratios use average balances where a prior-year figure is
available, and the closing balance otherwise; which basis was used is
recorded on every result so the working is defensible.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .financials import Figures

VARIANCE_THRESHOLD = 0.25  # Schedule III: explain movements above 25 per cent


@dataclass
class RatioResult:
    key: str
    name: str
    numerator_label: str
    denominator_label: str
    numerator: float
    denominator: float
    unit: str                       # "times" | "%" | "days"
    value: float | None = None
    prior_value: float | None = None
    variance: float | None = None   # proportion, e.g. 0.31 for +31%
    basis: str = "closing balances"
    note: str = ""

    @property
    def computable(self) -> bool:
        return self.value is not None

    @property
    def requires_explanation(self) -> bool:
        """Schedule III note requirement: movement beyond 25 per cent."""
        return self.variance is not None and abs(self.variance) > VARIANCE_THRESHOLD

    @property
    def direction(self) -> str:
        if self.variance is None:
            return "n/a"
        return "increase" if self.variance > 0 else "decrease"

    def formatted(self) -> str:
        if self.value is None:
            return "Not computable"
        if self.unit == "%":
            return f"{self.value:.2f}%"
        return f"{self.value:.2f} {self.unit}"


def _safe_divide(numerator: float, denominator: float) -> float | None:
    if denominator is None or abs(denominator) < 1e-9:
        return None
    return numerator / denominator


def _average(current: float, prior: float | None) -> tuple[float, str]:
    if prior is None:
        return current, "closing balance (no comparative available)"
    return (current + prior) / 2.0, "average of opening and closing balances"


def compute_ratios(current: Figures, prior: Figures | None = None) -> list[RatioResult]:
    """Compute all eleven Schedule III ratios for the current year."""
    results: list[RatioResult] = []

    def add(
        key: str,
        name: str,
        num_label: str,
        den_label: str,
        num: float,
        den: float,
        unit: str = "times",
        basis: str = "closing balances",
        note: str = "",
    ) -> None:
        raw = _safe_divide(num, den)
        value = None if raw is None else round(raw * (100 if unit == "%" else 1), 2)
        results.append(
            RatioResult(
                key=key,
                name=name,
                numerator_label=num_label,
                denominator_label=den_label,
                numerator=round(num, 2),
                denominator=round(den, 2),
                unit=unit,
                value=value,
                basis=basis,
                note=note,
            )
        )

    avg_inventory, inv_basis = _average(
        current.inventories, prior.inventories if prior else None
    )
    avg_receivables, rec_basis = _average(
        current.trade_receivables, prior.trade_receivables if prior else None
    )
    avg_payables, pay_basis = _average(
        current.trade_payables, prior.trade_payables if prior else None
    )
    avg_equity, eq_basis = _average(
        current.shareholders_equity, prior.shareholders_equity if prior else None
    )

    # (a) Current Ratio
    add(
        "current_ratio", "Current Ratio",
        "Current assets", "Current liabilities",
        current.current_assets, current.current_liabilities,
    )
    # (b) Debt-Equity Ratio
    add(
        "debt_equity", "Debt-Equity Ratio",
        "Total debt (long-term + short-term borrowings)", "Shareholders' equity",
        current.total_debt, current.shareholders_equity,
    )
    # (c) Debt Service Coverage Ratio
    add(
        "dscr", "Debt Service Coverage Ratio",
        "Earnings available for debt service (PAT + depreciation + finance costs)",
        "Debt service (finance costs + principal repayments)",
        current.earnings_for_debt_service, current.debt_service,
        note="" if current.principal_repayments else
             "Principal repayments not supplied; debt service reflects finance costs only.",
    )
    # (d) Return on Equity
    add(
        "roe", "Return on Equity Ratio",
        "Profit after tax", "Average shareholders' equity",
        current.profit_after_tax, avg_equity, unit="%", basis=eq_basis,
    )
    # (e) Inventory Turnover Ratio
    add(
        "inventory_turnover", "Inventory Turnover Ratio",
        "Cost of goods sold", "Average inventory",
        current.cogs, avg_inventory, basis=inv_basis,
    )
    # (f) Trade Receivables Turnover Ratio
    add(
        "receivables_turnover", "Trade Receivables Turnover Ratio",
        "Net credit sales", "Average trade receivables",
        current.net_credit_sales, avg_receivables, basis=rec_basis,
    )
    # (g) Trade Payables Turnover Ratio
    add(
        "payables_turnover", "Trade Payables Turnover Ratio",
        "Net credit purchases", "Average trade payables",
        current.net_credit_purchases, avg_payables, basis=pay_basis,
    )
    # (h) Net Capital Turnover Ratio
    add(
        "net_capital_turnover", "Net Capital Turnover Ratio",
        "Net sales", "Working capital (current assets less current liabilities)",
        current.revenue_from_operations, current.working_capital,
        note="Working capital is negative; the ratio is not meaningful."
        if current.working_capital < 0 else "",
    )
    # (i) Net Profit Ratio
    add(
        "net_profit", "Net Profit Ratio",
        "Profit after tax", "Net sales",
        current.profit_after_tax, current.revenue_from_operations, unit="%",
    )
    # (j) Return on Capital Employed
    add(
        "roce", "Return on Capital Employed",
        "Earnings before interest and tax",
        "Capital employed (net worth + total debt + deferred tax liability)",
        current.ebit, current.capital_employed, unit="%",
    )
    # (k) Return on Investment
    add(
        "roi", "Return on Investment",
        "Income from investments", "Cost of investments",
        current.income_from_investments, current.total_investments, unit="%",
        note="No investments held during the year."
        if current.total_investments == 0 else "",
    )

    if prior is not None:
        prior_results = {r.key: r for r in compute_ratios(prior, None)}
        for r in results:
            pv = prior_results.get(r.key)
            if pv and pv.value is not None and r.value is not None and abs(pv.value) > 1e-9:
                r.prior_value = pv.value
                r.variance = round((r.value - pv.value) / abs(pv.value), 4)

    return results


@dataclass
class RatioSchedule:
    """The disclosure note, ready for the financial statements."""

    financial_year: str
    results: list[RatioResult] = field(default_factory=list)

    @property
    def to_explain(self) -> list[RatioResult]:
        return [r for r in self.results if r.requires_explanation]

    @property
    def not_computable(self) -> list[RatioResult]:
        return [r for r in self.results if not r.computable]

    def as_rows(self) -> list[dict]:
        rows = []
        for r in self.results:
            rows.append(
                {
                    "Ratio": r.name,
                    "Numerator": r.numerator_label,
                    "Denominator": r.denominator_label,
                    "Current year": r.value,
                    "Previous year": r.prior_value,
                    "% Variance": None if r.variance is None else round(r.variance * 100, 2),
                    "Unit": r.unit,
                    "Explanation required": "Yes" if r.requires_explanation else "No",
                    "Basis": r.basis,
                    "Auditor note": r.note,
                }
            )
        return rows


def build_schedule(current: Figures, prior: Figures | None = None) -> RatioSchedule:
    return RatioSchedule(current.financial_year, compute_ratios(current, prior))
