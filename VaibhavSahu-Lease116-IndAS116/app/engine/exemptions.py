"""Recognition exemptions — short-term leases and leases of low-value assets
(Ind AS 116.5–8, B3–B8, Appendix A).

An exemption is *never* applied merely because a user selects it: the lease must
pass validation against the definition and the entity's policy elections.
Exempt leases are expensed on a straight-line basis over the lease term (para 6).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Optional

from .calendar_utils import month_ends_between, next_day, prev_day
from .decimal_utils import D, ZERO, engine_context, q
from .lease_term import determine_lease_term, is_short_term
from .models import Issue, LeaseTermInput, OptionKind, PaymentCategory, PaymentLine, Severity
from .references import ref

LOW_VALUE_EXCLUDED_CATEGORIES = {"vehicle", "car", "motor vehicle", "building", "land", "office premises", "warehouse", "plant"}


@dataclass
class ExemptionInput:
    lease_id: str
    exemption: str                             # SHORT_TERM | LOW_VALUE
    term: LeaseTermInput
    payments: list[PaymentLine]
    asset_class: str = ""
    class_election_short_term: bool = False    # para 8: short-term election is by class of underlying asset
    asset_value_when_new: Optional[Decimal] = None
    low_value_threshold: Optional[Decimal] = None   # entity policy — must be set (no default is assumed)
    benefits_on_own: bool = True               # B5(a)
    not_highly_dependent: bool = True          # B5(b)
    head_lease_of_sublease: bool = False       # B7
    evidence: str = ""
    policy_reference: str = ""


@dataclass
class ExemptionResult:
    valid: bool
    exemption: str
    reasons: list[str]
    issues: list[Issue]
    term_months: Decimal
    reference: str
    rows: list[dict] = field(default_factory=list)
    total_expense: Decimal = ZERO


def validate_exemption(inp: ExemptionInput) -> ExemptionResult:
    term = determine_lease_term(inp.term)
    reasons: list[str] = []
    issues: list[Issue] = []
    valid = True
    has_po = any(o.kind == OptionKind.PURCHASE for o in inp.term.options) or \
        any(PaymentCategory(p.category) == PaymentCategory.PURCHASE_OPTION for p in inp.payments)
    if inp.exemption == "SHORT_TERM":
        ok, why = is_short_term(term, has_po)
        reasons.append(why)
        if not ok:
            valid = False
            issues.append(Issue("NOT_SHORT_TERM", why, Severity.ERROR, reference=ref("SHORT_TERM_DEF")))
        if not inp.class_election_short_term:
            valid = False
            issues.append(Issue("NO_CLASS_ELECTION", f"Short-term exemption is not elected for asset class '{inp.asset_class}' "
                                                     "(Ind AS 116.8 — election by class).", Severity.ERROR))
        else:
            reasons.append(f"Entity has elected the short-term exemption for class '{inp.asset_class}' (para 8).")
    elif inp.exemption == "LOW_VALUE":
        if inp.low_value_threshold is None:
            valid = False
            issues.append(Issue("NO_THRESHOLD", "Low-value threshold is not set in entity policy — the exemption cannot be validated.",
                                Severity.ERROR))
        if inp.asset_value_when_new is None:
            valid = False
            issues.append(Issue("NO_VALUE_NEW", "Value of the underlying asset when new is required (B3–B4).", Severity.ERROR))
        if inp.low_value_threshold is not None and inp.asset_value_when_new is not None:
            if D(inp.asset_value_when_new) > D(inp.low_value_threshold):
                valid = False
                issues.append(Issue("ABOVE_THRESHOLD", f"Value when new {q(inp.asset_value_when_new)} exceeds policy threshold "
                                                       f"{q(inp.low_value_threshold)}.", Severity.ERROR))
            else:
                reasons.append(f"Value when new {q(inp.asset_value_when_new)} ≤ policy threshold {q(inp.low_value_threshold)} "
                               "(assessed on an absolute basis — B4).")
        if not inp.benefits_on_own:
            valid = False
            issues.append(Issue("B5A", "Lessee cannot benefit from the asset on its own or with readily available resources (B5(a)).",
                                Severity.ERROR))
        if not inp.not_highly_dependent:
            valid = False
            issues.append(Issue("B5B", "Asset is highly dependent on / interrelated with other assets (B5(b)).", Severity.ERROR))
        if inp.head_lease_of_sublease:
            valid = False
            issues.append(Issue("B7", "A head lease of a sublease does not qualify as a low-value lease (B7).", Severity.ERROR))
        if inp.asset_class and inp.asset_class.strip().lower() in LOW_VALUE_EXCLUDED_CATEGORIES:
            issues.append(Issue("B6", f"Assets such as '{inp.asset_class}' are typically not of low value when new (B6) — "
                                      "confirm the assessment.", Severity.WARNING))
    else:
        valid = False
        issues.append(Issue("EXEMPTION_TYPE", f"Unknown exemption {inp.exemption}.", Severity.ERROR))
    return ExemptionResult(valid, inp.exemption, reasons, issues, term.term_months,
                           ref("EXEMPT") if inp.exemption == "LOW_VALUE" else ref("SHORT_TERM_DEF"))


@engine_context
def exempt_expense_schedule(inp: ExemptionInput, decimals: int = 2) -> ExemptionResult:
    """Straight-line expense (para 6) with accrual / prepayment balance."""
    res = validate_exemption(inp)
    term = determine_lease_term(inp.term)
    c, end = term.commencement, term.term_end
    total_days = Decimal((next_day(end) - c).days)
    pays = [p for p in inp.payments if PaymentCategory(p.category) not in (PaymentCategory.VARIABLE, PaymentCategory.NON_LEASE)
            and (p.period_start or p.date) <= end]
    total = sum((D(p.lease_amount) for p in pays), ZERO)
    variable = [p for p in inp.payments if PaymentCategory(p.category) == PaymentCategory.VARIABLE]
    rows = []
    cum_exp_r = ZERO
    cum_cash = ZERO
    prev_cum_exact = ZERO
    ends = month_ends_between(c, max(end, max((p.date for p in pays), default=end)))
    start = c
    for pe in ends:
        days_to = Decimal((min(next_day(pe), next_day(end)) - c).days)
        days_to = max(days_to, Decimal(0))
        cum_exact = total * days_to / total_days if total_days else ZERO
        exp_r = q(cum_exact, decimals) - q(prev_cum_exact, decimals)
        prev_cum_exact = cum_exact
        cash = sum((D(p.lease_amount) for p in pays if start <= p.date <= pe), ZERO)
        var = sum((D(p.lease_amount) for p in variable if start <= p.date <= pe), ZERO)
        cum_exp_r += exp_r
        cum_cash += cash
        rows.append({"period_start": start, "period_end": pe, "expense": exp_r, "variable_expense": q(var, decimals),
                     "cash_paid": q(cash + var, decimals), "accrued_liability": q(cum_exp_r - cum_cash, decimals)})
        start = next_day(pe)
    res.rows = rows
    res.total_expense = q(total, decimals)
    return res
