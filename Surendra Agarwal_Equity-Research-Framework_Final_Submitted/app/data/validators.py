"""Data validation rules — Module 1.

Every function here is pure: takes data in, returns a list of
ValidationIssue, never raises on a data-quality problem and never
mutates its input. Calling code (typically app/main.py or a pipeline
orchestrator) decides what to do with BLOCKING-severity issues.

This separation matters: a validator that silently "fixed" bad data
would violate Principle 10 (fail safely rather than silently) and
Principle 9 (handle missing data explicitly).
"""

from __future__ import annotations

from app.core.enums import ValidationSeverity
from app.core.models import FinancialStatement, ValidationIssue

# Tolerance for balance-sheet tie-out, in INR crore. Real filings can be
# off by rounding of a few lakh; anything beyond this is flagged.
_BALANCE_SHEET_TOLERANCE_CR = 0.5

# Fields where a negative value is a plausible, valid state (e.g. net
# cash flow, or gains/losses) — negativity elsewhere is flagged.
_FIELDS_WHERE_NEGATIVE_IS_NORMAL = {
    "dividend_amount",  # can be blank/None but never itself flagged negative here
    "net_cash_flow",
    "cash_from_investing",
    "cash_from_financing",
}

_FIELDS_THAT_SHOULD_NOT_BE_NEGATIVE = {
    "sales",
    "total_assets",
    "total_liabilities",
    "net_block",
    "investments",
    "receivables",
    "inventory",
    "cash_and_bank",
    "num_equity_shares",
    "face_value",
}


def check_missing_values(statements: list[FinancialStatement]) -> list[ValidationIssue]:
    """Flag statements where core P&L fields are entirely absent.

    Does not flag every None field individually (that would be noisy —
    a company may genuinely not report a line item); flags only when
    the core trio (sales, net_profit, total_assets) needed for most
    downstream ratios is missing, since that materially limits what
    Module 2 can compute for that period.
    """
    issues: list[ValidationIssue] = []
    for stmt in statements:
        missing_core = [
            f for f in ("sales", "net_profit", "total_assets") if getattr(stmt, f) is None
        ]
        if missing_core:
            issues.append(
                ValidationIssue(
                    rule="missing_core_values",
                    severity=ValidationSeverity.WARNING,
                    message=(
                        f"{stmt.period}: core field(s) missing: {', '.join(missing_core)}. "
                        "Ratios depending on these will report status=missing_input."
                    ),
                    period=stmt.period,
                    context={"missing_fields": missing_core},
                )
            )
    return issues


def check_duplicate_periods(statements: list[FinancialStatement]) -> list[ValidationIssue]:
    """Flag more than one statement claiming the same period label."""
    issues: list[ValidationIssue] = []
    seen: dict[str, int] = {}
    for stmt in statements:
        seen[stmt.period] = seen.get(stmt.period, 0) + 1
    for period, count in seen.items():
        if count > 1:
            issues.append(
                ValidationIssue(
                    rule="duplicate_period",
                    severity=ValidationSeverity.BLOCKING,
                    message=f"Period {period} appears {count} times in the input data.",
                    period=period,
                    context={"count": count},
                )
            )
    return issues


def check_impossible_values(statements: list[FinancialStatement]) -> list[ValidationIssue]:
    """Flag values that are structurally impossible regardless of business context.

    E.g. face value of 0, share count of 0 with a non-null price implied
    elsewhere, tax paid exceeding profit before tax by an implausible
    margin (allowed in principle — deferred tax adjustments happen — but
    flagged as a WARNING for analyst review, not silently accepted).
    """
    issues: list[ValidationIssue] = []
    for stmt in statements:
        if stmt.face_value is not None and stmt.face_value <= 0:
            issues.append(
                ValidationIssue(
                    rule="impossible_face_value",
                    severity=ValidationSeverity.BLOCKING,
                    message=f"{stmt.period}: face value is {stmt.face_value} (must be > 0).",
                    period=stmt.period,
                )
            )
        if stmt.num_equity_shares is not None and stmt.num_equity_shares <= 0:
            issues.append(
                ValidationIssue(
                    rule="impossible_share_count",
                    severity=ValidationSeverity.BLOCKING,
                    message=f"{stmt.period}: equity share count is {stmt.num_equity_shares}.",
                    period=stmt.period,
                )
            )
        if stmt.tax is not None and stmt.profit_before_tax is not None and stmt.profit_before_tax > 0:
            effective_rate = stmt.tax / stmt.profit_before_tax
            if effective_rate > 0.5 or effective_rate < -0.2:
                issues.append(
                    ValidationIssue(
                        rule="unusual_effective_tax_rate",
                        severity=ValidationSeverity.WARNING,
                        message=(
                            f"{stmt.period}: implied effective tax rate is "
                            f"{effective_rate:.1%}, outside the typical range. "
                            "Not necessarily an error (deferred tax, one-offs) "
                            "but worth analyst review."
                        ),
                        period=stmt.period,
                        context={"effective_tax_rate": effective_rate},
                    )
                )
    return issues


def check_unit_consistency(statements: list[FinancialStatement]) -> list[ValidationIssue]:
    """Flag statements whose declared unit differs from the rest of the series."""
    issues: list[ValidationIssue] = []
    units = {stmt.unit for stmt in statements}
    if len(units) > 1:
        issues.append(
            ValidationIssue(
                rule="inconsistent_units",
                severity=ValidationSeverity.BLOCKING,
                message=(
                    f"Statements use inconsistent units across periods: "
                    f"{sorted(u.value for u in units)}. All periods must share one "
                    "canonical unit before calculations run."
                ),
                context={"units_found": sorted(u.value for u in units)},
            )
        )
    return issues


def check_negative_values_where_inappropriate(
    statements: list[FinancialStatement],
) -> list[ValidationIssue]:
    """Flag negative values in fields that should structurally never be negative."""
    issues: list[ValidationIssue] = []
    for stmt in statements:
        for field in _FIELDS_THAT_SHOULD_NOT_BE_NEGATIVE:
            value = getattr(stmt, field, None)
            if value is not None and value < 0:
                issues.append(
                    ValidationIssue(
                        rule="unexpected_negative_value",
                        severity=ValidationSeverity.ERROR,
                        message=f"{stmt.period}: {field} = {value}, expected non-negative.",
                        field=field,
                        period=stmt.period,
                    )
                )
    return issues


def check_date_ordering(statements: list[FinancialStatement]) -> list[ValidationIssue]:
    """Flag statements whose period_end_date does not increase monotonically
    when sorted by the period label itself (catches mislabeled periods)."""
    issues: list[ValidationIssue] = []
    dated = [s for s in statements if s.period_end_date is not None]
    dated_sorted_by_label = sorted(dated, key=lambda s: s.period)
    dates_in_label_order = [s.period_end_date for s in dated_sorted_by_label]
    if dates_in_label_order != sorted(dates_in_label_order):
        issues.append(
            ValidationIssue(
                rule="date_ordering_mismatch",
                severity=ValidationSeverity.ERROR,
                message=(
                    "Period labels and period_end_date do not agree on chronological "
                    "order. Check for a mislabeled fiscal year."
                ),
                context={
                    "periods_in_label_order": [s.period for s in dated_sorted_by_label]
                },
            )
        )
    return issues


def check_balance_sheet_tie_out(statements: list[FinancialStatement]) -> list[ValidationIssue]:
    """Flag periods where Total Assets != Total Liabilities beyond tolerance."""
    issues: list[ValidationIssue] = []
    for stmt in statements:
        if stmt.total_assets is None or stmt.total_liabilities is None:
            continue
        diff = abs(stmt.total_assets - stmt.total_liabilities)
        if diff > _BALANCE_SHEET_TOLERANCE_CR:
            issues.append(
                ValidationIssue(
                    rule="balance_sheet_mismatch",
                    severity=ValidationSeverity.BLOCKING,
                    message=(
                        f"{stmt.period}: Total Assets ({stmt.total_assets}) != "
                        f"Total Liabilities ({stmt.total_liabilities}); "
                        f"difference {diff:.2f} cr exceeds tolerance "
                        f"({_BALANCE_SHEET_TOLERANCE_CR} cr)."
                    ),
                    period=stmt.period,
                    context={"difference_cr": diff},
                )
            )
    return issues


def check_share_count_discontinuity(statements: list[FinancialStatement]) -> list[ValidationIssue]:
    """Flag large period-over-period jumps in share count.

    Not necessarily an error (IPOs, bonus issues, stock splits all cause
    this legitimately) but worth surfacing explicitly rather than letting
    it silently distort per-share metrics (EPS, book value per share)
    across the discontinuity.
    """
    issues: list[ValidationIssue] = []
    ordered = sorted(
        (s for s in statements if s.num_equity_shares and s.period_end_date),
        key=lambda s: s.period_end_date,
    )
    for prev, curr in zip(ordered, ordered[1:]):
        if prev.num_equity_shares in (None, 0):
            continue
        ratio = curr.num_equity_shares / prev.num_equity_shares
        if ratio > 1.5 or ratio < 0.67:
            issues.append(
                ValidationIssue(
                    rule="share_count_discontinuity",
                    severity=ValidationSeverity.WARNING,
                    message=(
                        f"Equity share count changed {ratio:.2f}x between {prev.period} "
                        f"({prev.num_equity_shares:,.0f}) and {curr.period} "
                        f"({curr.num_equity_shares:,.0f}). Likely IPO/bonus/split — "
                        "verify before trusting per-share trend metrics across this boundary."
                    ),
                    period=curr.period,
                    context={"ratio": ratio},
                )
            )
    return issues


def run_all_validations(statements: list[FinancialStatement]) -> list[ValidationIssue]:
    """Convenience entry point: run every validator and return the combined list."""
    issues: list[ValidationIssue] = []
    for check in (
        check_missing_values,
        check_duplicate_periods,
        check_impossible_values,
        check_unit_consistency,
        check_negative_values_where_inappropriate,
        check_date_ordering,
        check_balance_sheet_tie_out,
        check_share_count_discontinuity,
    ):
        issues.extend(check(statements))
    return issues
