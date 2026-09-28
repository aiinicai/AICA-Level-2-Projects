"""Lease payment engine (Ind AS 116.26–28, 38, B42).

Two responsibilities:

1. ``generate_payments`` turns contractual payment terms (base rent, frequency,
   advance/arrears, due day, escalations, step table, rent-free periods, CAM /
   non-lease charges) into dated payment lines. Lines remain editable so that
   irregular schedules can be keyed or imported.
2. ``classify_payments`` decides, line by line, whether a payment is included in
   the lease liability and records the reason. Nothing is included merely
   because it is contractual.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Optional

from .calendar_utils import add_months, days_in_month, month_end, next_day, prev_day
from .decimal_utils import D, ONE, ZERO, dpow, engine_context, pct, q
from .models import PaymentCategory, PaymentLine, Policy, TermResult, Timing
from .references import ref


@dataclass
class EscalationRule:
    value: Decimal                       # % or amount
    every_months: int = 12
    kind: str = "PERCENT"                # PERCENT | AMOUNT
    first_date: Optional[date] = None    # first escalation effective date; default anchor + every_months
    compounding: bool = True             # on last rent (True) or on base rent (False)
    applies_to: str = "LEASE"            # LEASE | NON_LEASE | BOTH
    max_count: Optional[int] = None


@dataclass
class RentStep:
    start: date
    amount: Decimal                      # per-period lease component from this date
    non_lease_amount: Optional[Decimal] = None


@dataclass
class RentFree:
    start: date
    end: date                            # inclusive
    applies_to: str = "LEASE"            # LEASE | BOTH


@dataclass
class PaymentTerms:
    amount: Decimal                      # base lease-component amount per period
    start_date: date                     # first period start (normally commencement)
    end_date: date                       # last day covered (inclusive)
    frequency_months: int = 1            # 1, 3, 6, 12
    timing: Timing = Timing.ADVANCE
    alignment: str = "ANNIVERSARY"       # ANNIVERSARY | CALENDAR
    due_day: Optional[int] = None        # e.g. 7 => 7th of the month
    due_offset_days: int = 0
    escalations: list[EscalationRule] = field(default_factory=list)
    escalation_anchor: Optional[date] = None
    steps: list[RentStep] = field(default_factory=list)
    rent_free: list[RentFree] = field(default_factory=list)
    non_lease_amount: Decimal = ZERO
    prorate_partial: bool = True
    category: PaymentCategory = PaymentCategory.FIXED
    description: str = "Rent"
    fy_start_month: int = 4
    split_at: list[date] = field(default_factory=list)   # force period boundaries (e.g. term end + 1)


# ---------------------------------------------------------------------------
# generation
# ---------------------------------------------------------------------------
def _calendar_block_start(d: date, f: int, fy_start_month: int) -> date:
    if f == 1:
        return date(d.year, d.month, 1)
    offset = (d.month - fy_start_month) % 12
    block_offset = offset - (offset % f)
    months_back = offset - block_offset
    return add_months(date(d.year, d.month, 1), -months_back)


def _build_periods(t: PaymentTerms) -> list[tuple[date, date, date, date]]:
    """Return (period_start, period_end, nominal_start, nominal_end) tuples."""
    f = t.frequency_months
    periods = []
    if t.alignment == "CALENDAR":
        cur = t.start_date
        while cur <= t.end_date:
            nominal_start = _calendar_block_start(cur, f, t.fy_start_month)
            nominal_end = prev_day(add_months(nominal_start, f))
            pe = min(nominal_end, t.end_date)
            periods.append((cur, pe, nominal_start, nominal_end))
            cur = next_day(pe)
    else:
        k = 0
        while True:
            ps = add_months(t.start_date, k * f)
            if ps > t.end_date:
                break
            nominal_end = prev_day(add_months(t.start_date, (k + 1) * f))
            pe = min(nominal_end, t.end_date)
            periods.append((ps, pe, ps, nominal_end))
            k += 1
    # forced splits (e.g. at lease-term end) so that no line straddles a boundary
    if t.split_at:
        out = []
        for ps, pe, ns, ne in periods:
            cuts = sorted(s for s in t.split_at if ps < s <= pe)
            start = ps
            for s in cuts:
                out.append((start, prev_day(s), ns, ne))
                start = s
            out.append((start, pe, ns, ne))
        periods = out
    return periods


def _escalation_dates(rule: EscalationRule, anchor: date, until: date) -> list[date]:
    first = rule.first_date or add_months(anchor, rule.every_months)
    out = []
    k = 0
    while True:
        d = add_months(first, k * rule.every_months)
        if d > until:
            break
        out.append(d)
        k += 1
        if rule.max_count and k >= rule.max_count:
            break
    return out


def _rate_on(day: date, base: Decimal, rules: list[EscalationRule], anchor: date, until: date,
             steps: list[tuple[date, Decimal]]) -> Decimal:
    """Per-period amount applicable on a given day."""
    if steps:
        amt = base
        for s_date, s_amt in steps:
            if s_date <= day:
                amt = s_amt
        return amt
    amt = base
    for rule in rules:
        n = sum(1 for d in _escalation_dates(rule, anchor, until) if d <= day)
        if n == 0:
            continue
        if rule.kind == "AMOUNT":
            amt = amt + D(rule.value) * n
        elif rule.compounding:
            amt = amt * dpow(ONE + pct(rule.value), Decimal(n))
        else:
            amt = amt + base * pct(rule.value) * n
    return amt


def _change_points(ps: date, pe: date, rules, anchor, until, steps, rent_free) -> list[date]:
    pts = {ps, next_day(pe)}
    for rule in rules:
        for d in _escalation_dates(rule, anchor, until):
            if ps < d <= pe:
                pts.add(d)
    for s_date, _ in steps:
        if ps < s_date <= pe:
            pts.add(s_date)
    for rf in rent_free:
        if ps < rf.start <= pe:
            pts.add(rf.start)
        if ps < next_day(rf.end) <= pe:
            pts.add(next_day(rf.end))
    return sorted(pts)


def _in_rent_free(day: date, rent_free: list[RentFree], component: str) -> bool:
    for rf in rent_free:
        if rf.start <= day <= rf.end and (rf.applies_to == "BOTH" or component == "LEASE"):
            return True
    return False


@engine_context
def generate_payments(t: PaymentTerms, start_line_no: int = 1) -> list[PaymentLine]:
    anchor = t.escalation_anchor or t.start_date
    lease_rules = [r for r in t.escalations if r.applies_to in ("LEASE", "BOTH")]
    nl_rules = [r for r in t.escalations if r.applies_to in ("NON_LEASE", "BOTH")]
    lease_steps = sorted((s.start, D(s.amount)) for s in t.steps)
    nl_steps = sorted((s.start, D(s.non_lease_amount)) for s in t.steps if s.non_lease_amount is not None)
    lines: list[PaymentLine] = []
    no = start_line_no
    for ps, pe, ns, ne in _build_periods(t):
        full_days = Decimal((next_day(ne) - ns).days)
        actual_days = Decimal((next_day(pe) - ps).days)
        pts = _change_points(ps, pe, lease_rules + nl_rules, anchor, t.end_date, lease_steps + nl_steps, t.rent_free)
        lease_amt = ZERO
        nl_amt = ZERO
        rent_free_days = 0
        for a, b in zip(pts[:-1], pts[1:]):
            seg_days = Decimal((b - a).days)
            # pro-rata by days of the nominal period; without pro-rating a partial period bears the full amount
            frac = seg_days / (full_days if t.prorate_partial else actual_days)
            lr = _rate_on(a, D(t.amount), lease_rules, anchor, t.end_date, lease_steps)
            nr = _rate_on(a, D(t.non_lease_amount), nl_rules, anchor, t.end_date, nl_steps)
            if _in_rent_free(a, t.rent_free, "LEASE"):
                rent_free_days += (b - a).days
            else:
                lease_amt += lr * frac
            if not _in_rent_free(a, t.rent_free, "NON_LEASE"):
                nl_amt += nr * frac
        # payment date
        if t.timing == Timing.ADVANCE:
            if t.due_day:
                pay = date(ps.year, ps.month, min(t.due_day, days_in_month(ps.year, ps.month)))
                if pay < ps:
                    pay = ps
            else:
                pay = ps
            pay = date.fromordinal(pay.toordinal() + t.due_offset_days)
        else:
            if t.due_day:
                nxt = next_day(pe)
                pay = date(nxt.year, nxt.month, min(t.due_day, days_in_month(nxt.year, nxt.month)))
            else:
                pay = pe
            pay = date.fromordinal(pay.toordinal() + t.due_offset_days)
        desc = t.description
        if rent_free_days and lease_amt == 0:
            desc += " (rent-free)"
        elif rent_free_days:
            desc += f" (incl. {rent_free_days} rent-free days)"
        lines.append(PaymentLine(date=pay, lease_amount=q(lease_amt), non_lease_amount=q(nl_amt),
                                 category=t.category, period_start=ps, period_end=pe,
                                 description=desc, line_no=no, source="GENERATED"))
        no += 1
    return lines


# ---------------------------------------------------------------------------
# classification (inclusion in the lease liability)
# ---------------------------------------------------------------------------
def measure_amount(line: PaymentLine, non_lease_expedient: bool) -> Decimal:
    """Amount of the line that is a lease payment for measurement purposes."""
    amt = D(line.lease_amount)
    if non_lease_expedient:
        amt += D(line.non_lease_amount)
    return amt


def classify_payments(lines: list[PaymentLine], term: TermResult, non_lease_expedient: bool = False) -> list[PaymentLine]:
    """Set ``included`` and ``inclusion_reason`` on every line (in place) and return lines sorted by date."""
    term_end = term.term_end
    for ln in lines:
        cat = PaymentCategory(ln.category)
        if ln.include_override is not None:
            ln.included = bool(ln.include_override)
            ln.inclusion_reason = f"User override: {ln.override_reason or 'reason not stated'}"
            continue
        anchor_day = ln.period_start or ln.date
        within_term = anchor_day <= term_end
        if cat == PaymentCategory.VARIABLE:
            ln.included = False
            ln.inclusion_reason = f"Variable payment not depending on an index or rate — expensed when incurred ({ref('VARIABLE_EXCL')})."
        elif cat == PaymentCategory.NON_LEASE:
            ln.included = non_lease_expedient and within_term
            ln.inclusion_reason = ("Non-lease component combined under the practical expedient (Ind AS 116.15)." if ln.included
                                   else "Non-lease component (service/CAM) — accounted for separately (Ind AS 116.12).")
        elif cat == PaymentCategory.PURCHASE_OPTION:
            ln.included = term.purchase_option_rc
            ln.inclusion_reason = ("Purchase option reasonably certain to be exercised (27(d))." if ln.included
                                   else "Purchase option not reasonably certain — excluded (27(d)).")
        elif cat == PaymentCategory.TERMINATION_PENALTY:
            ln.included = term.termination_reflected and ln.date <= next_day(term_end)
            ln.inclusion_reason = ("Lease term reflects exercise of the termination option — penalty included (27(e))." if ln.included
                                   else "Lease term does not reflect termination — penalty excluded (27(e)).")
        elif cat == PaymentCategory.RVG:
            ln.included = True
            ln.inclusion_reason = "Amount expected to be payable under a residual value guarantee (27(c))."
        elif cat in (PaymentCategory.INDEX_LINKED, PaymentCategory.RATE_LINKED):
            ln.included = within_term
            ln.inclusion_reason = ("Index/rate-linked payment measured using the index/rate at commencement (27(b), 28)."
                                   if within_term else "Falls outside the accounting lease term.")
        elif cat == PaymentCategory.INCENTIVE:
            ln.included = within_term
            ln.inclusion_reason = "Lease incentive receivable — reduces fixed lease payments (27(a))."
        else:  # FIXED / IN_SUBSTANCE_FIXED
            ln.included = within_term
            if within_term:
                ln.inclusion_reason = ("In-substance fixed payment (B42)." if cat == PaymentCategory.IN_SUBSTANCE_FIXED
                                       else "Fixed payment within the accounting lease term (27(a)).")
            else:
                ln.inclusion_reason = "Payment relates to an optional period not included in the lease term (18) — excluded."
        if ln.included and measure_amount(ln, non_lease_expedient) == 0 and cat != PaymentCategory.NON_LEASE:
            ln.inclusion_reason += " Nil amount (rent-free period)."
    return sorted(lines, key=lambda x: (x.date, x.line_no))


def payments_from_table(rows: list[dict]) -> list[PaymentLine]:
    """Build lines from a simple table: [{date, amount, non_lease, category, description}]."""
    from .calendar_utils import parse_date

    out = []
    for i, r in enumerate(rows, start=1):
        out.append(PaymentLine(date=parse_date(r["date"]), lease_amount=q(D(r.get("amount") or r.get("lease_amount"))),
                               non_lease_amount=q(D(r.get("non_lease") or r.get("non_lease_amount") or 0)),
                               category=PaymentCategory(r.get("category") or "FIXED"),
                               period_start=parse_date(r.get("period_start")), period_end=parse_date(r.get("period_end")),
                               description=r.get("description", ""), line_no=i, source=r.get("source", "MANUAL")))
    return out
