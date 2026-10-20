"""IFRS 16 lessee accounting engine (Decimal arithmetic, dated schedule, journals, reassessment, modification, termination).

Conventions (stated assumptions – see docs/ASSUMPTIONS.md):
* Payment dates are the dates cash is due. "Arrears" payments fall on the period-end boundary (the first day of the next
  period, e.g. 1 Feb for January rent); "advance" payments fall on the first day of the period.
* Interest accrues by actual dates between schedule dates using the selected day-count and compounding convention.
* Payments dated on or before commencement are treated as paid at commencement (IFRS 16.26 / 16.24(b)): they are excluded
  from the liability and added to the ROU asset.
* Events take effect at the START of their effective date: payments dated on/after the effective date are "future payments".
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from decimal import Decimal

from .models import Event, LeaseTerms, Payment, dumps, to_jsonable
from .money import D, ZERO, FREQ_MONTHS, add_months, dec, growth_factor, parse_date

ACCOUNTS = {
    'ROU_COST': 'Right-of-use asset – cost',
    'ROU_ACCDEP': 'Accumulated depreciation – right-of-use asset',
    'LEASE_LIAB': 'Lease liability',
    'INTEREST_EXP': 'Interest expense on lease liabilities',
    'DEP_EXP': 'Depreciation expense – right-of-use assets',
    'CASH': 'Cash and bank',
    'PROVISION': 'Restoration provision',
    'PREPAID': 'Prepaid lease payments',
    'GAIN_LOSS': 'Gain / (loss) on lease modification or termination',
    'LEASE_EXP': 'Short-term / low-value lease expense',
    'ACCRUED_LEASE': 'Accrued lease payable',
}


class EngineError(ValueError):
    """Raised for invalid inputs or when a calculation cannot be completed. The message is written for the end user."""


# ------------------------------------------------------------------ result objects
@dataclass
class Row:
    row_no: int
    version: int
    kind: str                 # 'normal' | 'day0' (payment on the first day of a new segment)
    start: dt.date
    end: dt.date
    days: int
    open_liab: Decimal
    interest: Decimal
    payment: Decimal
    principal: Decimal
    close_liab: Decimal
    open_rou: Decimal
    depreciation: Decimal
    close_rou: Decimal
    rounding_adj: Decimal = ZERO
    trace: dict = field(default_factory=dict)
    adjustment: Decimal = ZERO        # liability change from a dated event (remeasurement / derecognition)
    rou_adjustment: Decimal = ZERO    # ROU net carrying-amount change from a dated event

    def to_dict(self):
        d = dict(self.__dict__)
        return to_jsonable(d)


@dataclass
class JLine:
    account: str
    debit: Decimal = ZERO
    credit: Decimal = ZERO
    memo: str = ''


@dataclass
class Journal:
    ref: str
    date: dt.date
    source: str
    narration: str
    lines: list
    trace: list
    version: int = 0
    row_no: int | None = None

    def total(self):
        return sum((l.debit for l in self.lines), ZERO), sum((l.credit for l in self.lines), ZERO)

    def balanced(self):
        d, c = self.total()
        return d == c

    def to_dict(self):
        return to_jsonable({'ref': self.ref, 'date': self.date, 'source': self.source, 'narration': self.narration, 'version': self.version,
                            'row_no': self.row_no, 'trace': self.trace, 'lines': [l.__dict__ for l in self.lines]})


@dataclass
class EventResult:
    index: int
    type: str
    effective_date: dt.date
    decision: str
    rate_used: Decimal | None
    rate_reason: str
    before: dict
    after: dict
    bridge: list              # [{'label','amount','trace'}]
    journals: list
    notes: list
    new_lease_template: dict | None = None

    def to_dict(self):
        return to_jsonable({'index': self.index, 'type': self.type, 'effective_date': self.effective_date, 'decision': self.decision,
                            'rate_used': self.rate_used, 'rate_reason': self.rate_reason, 'before': self.before, 'after': self.after,
                            'bridge': self.bridge, 'journals': [j.to_dict() for j in self.journals], 'notes': self.notes,
                            'new_lease_template': self.new_lease_template})


@dataclass
class Timeline:
    terms: LeaseTerms
    initial: dict
    pv_lines: list
    rows: list
    journals: list
    events: list
    warnings: list
    final: dict
    exempt: bool = False

    def journal_by_ref(self, ref):
        return next((j for j in self.journals if j.ref == ref), None)


# ------------------------------------------------------------------ payment schedule generation
def lease_end_boundary(end_date: dt.date) -> dt.date:
    return end_date + dt.timedelta(days=1)


def generate_payments(t: LeaseTerms, end_date=None, amount=None, start_from: dt.date | None = None) -> list[Payment]:
    """Regular lease payments (functional currency) from the lease pattern; plus option items at the end of the lease."""
    if not t.commencement or not (end_date or t.end_date):
        raise EngineError('Enter the commencement date and the lease end date.')
    end = end_date or t.end_date
    if end <= t.commencement:
        raise EngineError('The lease end date must be after the commencement date.')
    step = FREQ_MONTHS.get(t.frequency)
    if not step:
        raise EngineError(f"Unknown payment frequency '{t.frequency}'.")
    boundary = lease_end_boundary(end)
    amt = t.fx(amount if amount is not None else t.payment_amount)
    n = 0
    while add_months(t.commencement, n * step, t.commencement.day) < boundary:
        n += 1
    if n == 0:
        raise EngineError('The lease term is shorter than one payment period.')
    out = []
    for k in range(n):
        if t.timing == 'advance':
            d = add_months(t.commencement, k * step, t.commencement.day)
        else:
            d = min(add_months(t.commencement, (k + 1) * step, t.commencement.day), boundary)
        if start_from is None or d >= start_from:
            out.append(Payment(d, amt, 'lease'))
    out.extend(option_payments(t, boundary))
    return out


def option_payments(t: LeaseTerms, boundary: dt.date) -> list[Payment]:
    out = []
    if t.rvg_expected > 0:
        out.append(Payment(boundary, t.fx(t.rvg_expected), 'rvg', 'Residual value guarantee expected to be payable'))
    if t.purchase_option_certain and t.purchase_option_price > 0:
        out.append(Payment(boundary, t.fx(t.purchase_option_price), 'purchase_option', 'Purchase option – reasonably certain to be exercised'))
    if t.termination_penalty_included and t.termination_penalty > 0:
        out.append(Payment(boundary, t.fx(t.termination_penalty), 'termination_penalty', 'Termination penalty – lease term reflects exercise of termination option'))
    return out


def ensure_payments(t: LeaseTerms) -> list[Payment]:
    return t.payments if t.payments else generate_payments(t)


# ------------------------------------------------------------------ exemptions
def exemption_check(t: LeaseTerms) -> dict:
    """Eligibility indicators for the recognition exemptions (IFRS 16.5-8). The election itself is the user's policy choice."""
    res = {'short_term_eligible': False, 'low_value_eligible': False, 'messages': []}
    if t.commencement and t.end_date:
        months = (t.end_date.year - t.commencement.year) * 12 + (t.end_date.month - t.commencement.month) + (1 if t.end_date.day >= t.commencement.day - 1 else 0)
        term_ok = lease_end_boundary(t.end_date) <= add_months(t.commencement, 12, t.commencement.day)
        res['short_term_eligible'] = term_ok and not t.purchase_option_certain and t.purchase_option_price == 0
        res['messages'].append(('Short-term: term of 12 months or less at commencement and no purchase option – ' + ('eligible' if res['short_term_eligible'] else 'NOT eligible')))
    if t.asset_value_new > 0:
        res['low_value_eligible'] = t.asset_value_new <= t.low_value_threshold
        res['messages'].append(f"Low-value: asset value when new {t.asset_value_new:,} vs threshold {t.low_value_threshold:,} – " + ('eligible' if res['low_value_eligible'] else 'NOT eligible'))
    else:
        res['messages'].append('Low-value: enter the value of the asset when new to test eligibility.')
    return res


# ------------------------------------------------------------------ PV
def present_value(payments, at: dt.date, rate, day_count, compounding, rp):
    lines, total = [], ZERO
    for p in payments:
        gf = growth_factor(at, p.date, rate, day_count, compounding)
        pv = p.amount / gf
        lines.append({'date': p.date, 'kind': p.kind, 'amount': p.amount, 'days': (p.date - at).days, 'discount_factor': D(1) / gf, 'pv': rp.q(pv)})
        total += pv
    return rp.q(total), lines


# ------------------------------------------------------------------ journal helpers
class _Refs:
    def __init__(self, lease_ref):
        self.lease_ref = lease_ref
        self.count = {}

    def make(self, version, source, date):
        k = (version, source, date)
        self.count[k] = self.count.get(k, 0) + 1
        return f"{self.lease_ref}/V{version}/{source}/{date.isoformat()}/{self.count[k]}"


def _jl(account, amount, side, memo=''):
    return JLine(account, amount if side == 'D' else ZERO, amount if side == 'C' else ZERO, memo)


def _drop_zero(lines):
    return [l for l in lines if l.debit != 0 or l.credit != 0]


# ------------------------------------------------------------------ depreciation planning
def depreciation_end(t: LeaseTerms, lease_end_date: dt.date, option_certain: bool) -> dt.date:
    boundary = lease_end_boundary(lease_end_date)
    life_end = add_months(t.commencement, int(t.useful_life_years * 12), t.commencement.day) if t.useful_life_years > 0 else None
    if (t.ownership_transfers or option_certain) and life_end:
        return life_end
    if life_end and life_end < boundary:
        return life_end
    return boundary


class _State:
    pass


def _dep_amount(st, d0, d1, carrying, rp):
    plan = st.dep
    if carrying <= 0 or d0 >= plan['end']:
        return ZERO, 'no depreciation (fully depreciated or beyond depreciation end date)'
    d1c = min(d1, plan['end'])
    days = (d1c - d0).days
    total = max((plan['end'] - plan['start']).days, 1)
    rem = max((plan['end'] - d0).days, 1)
    if d1c >= plan['end']:
        return carrying, f"final period: remaining carrying amount {carrying:,} depreciated to nil by {plan['end']}"
    if plan['method'] == 'declining_balance':
        sl = carrying * D(days) / D(rem)
        db = carrying * plan['db_rate'] * D(days) / D(365)
        amt = rp.q(max(sl, db))
        return min(amt, carrying), f"max(declining {carrying:,} × {plan['db_rate']} × {days}/365, straight-line on remaining {carrying:,} × {days}/{rem}) = {amt:,}"
    amt = rp.q(plan['basis'] * D(days) / D(total))
    return min(amt, carrying), f"straight-line: {plan['basis']:,} × {days}/{total} days = {amt:,}"


def _new_plan(t, st, start, carrying):
    st.dep = {'start': start, 'basis': carrying, 'end': st.dep_end, 'method': t.depreciation_method,
              'db_rate': t.db_rate if t.db_rate > 0 else (D(2) / t.useful_life_years if t.useful_life_years > 0 else D('0.2'))}


# ------------------------------------------------------------------ main builder
def build_timeline(terms: LeaseTerms, events: list[Event] | None = None) -> Timeline:
    t = terms
    events = list(events or [])
    rp = t.rounding
    _validate_terms(t)
    if t.exemption != 'none' and t.exemption_elected:
        return _exempt_timeline(t)
    payments = [Payment(p.date, p.amount, p.kind, p.note, p.edited) for p in ensure_payments(t)]
    payments.sort(key=lambda p: p.date)
    refs = _Refs(t.ref)
    warnings, journals, rows, results = [], [], [], []
    st = _State()
    st.rate = t.discount_rate
    st.reg_amount = t.fx(t.payment_amount)
    st.end = t.end_date
    st.option_certain = bool(t.purchase_option_certain)

    # ---- initial recognition
    at_comm = [p for p in payments if p.date <= t.commencement]
    remaining = [p for p in payments if p.date > t.commencement]
    L0, pv_lines = present_value(remaining, t.commencement, st.rate, t.day_count, t.compounding, rp)
    adv = sum((p.amount for p in at_comm), ZERO)
    prepaid, idc, rest, inc = t.fx(t.prepaid_before_commencement), t.fx(t.initial_direct_costs), t.fx(t.restoration_obligation), t.fx(t.incentives_received)
    rou0 = L0 + adv + prepaid + idc + rest - inc
    if rou0 < 0:
        raise EngineError('Incentives received exceed the liability and other components, giving a negative right-of-use asset. Check the incentive amount.')
    initial = {'liability': L0, 'payments_at_commencement': adv, 'prepaid_before_commencement': prepaid, 'initial_direct_costs': idc,
               'restoration': rest, 'incentives': inc, 'rou_cost': rou0, 'rate': st.rate, 'commencement': t.commencement,
               'trace': [f"Lease liability = Σ PV of {len(remaining)} unpaid lease payments at {st.rate:.6%} ({t.day_count}, {t.compounding} compounding) = {L0:,}",
                         f"ROU asset = liability {L0:,} + payments at/before commencement {adv + prepaid:,} + initial direct costs {idc:,} + restoration {rest:,} − incentives {inc:,} = {rou0:,}"]}
    cash_out = adv + prepaid + idc - inc
    lines = [_jl('ROU_COST', rou0, 'D', 'Initial measurement of right-of-use asset'), _jl('LEASE_LIAB', L0, 'C', 'PV of unpaid lease payments')]
    if rest:
        lines.append(_jl('PROVISION', rest, 'C', 'Restoration obligation'))
    if cash_out > 0:
        lines.append(_jl('CASH', cash_out, 'C', 'Payments at/before commencement and direct costs, net of incentives'))
    elif cash_out < 0:
        lines.append(_jl('CASH', -cash_out, 'D', 'Incentives received net of payments'))
    journals.append(Journal(refs.make(0, 'INITIAL', t.commencement), t.commencement, 'INITIAL', f"{t.ref}: initial recognition of lease",
                            _drop_zero(lines), list(initial['trace']), 0))
    st.liab, st.cost, st.accum = L0, rou0, ZERO
    st.payments = remaining
    st.dep_end = depreciation_end(t, st.end, st.option_certain)
    _new_plan(t, st, t.commencement, rou0)
    st.cur = t.commencement
    st.version = 0
    st.terminated = False
    row_no = [0]

    def run_segment(seg_end, final, version):
        """Accrue interest, payments and depreciation from st.cur to seg_end (rows end at or before seg_end)."""
        nonlocal rows, journals
        cur = st.cur
        pays = st.payments
        include_end = final
        # day-0 payments (events): payments dated exactly at segment start
        day0 = [p for p in pays if p.date == cur and cur != t.commencement]
        if day0:
            amt = sum((p.amount for p in day0), ZERO)
            _add_row(cur, cur, 'day0', amt, version, rp)
        dates = {p.date for p in pays if cur < p.date < seg_end or (final and p.date == seg_end)}
        if t.posting_granularity == 'monthly':
            k = 1
            while True:
                m = add_months(t.commencement, k, t.commencement.day)
                if m >= seg_end:
                    break
                if m > cur:
                    dates.add(m)
                k += 1
        if cur < st.dep['end'] < seg_end and st.cost - st.accum > 0:
            dates.add(st.dep['end'])
        if seg_end > cur:
            dates.add(seg_end)
        prev = cur
        for d in sorted(x for x in dates if x > cur):
            amt = sum((p.amount for p in pays if p.date == d and (d < seg_end or include_end)), ZERO)
            _add_row(prev, d, 'normal', amt, version, rp)
            prev = d
        st.payments = [p for p in pays if p.date >= seg_end] if not final else []
        st.cur = seg_end

    def _add_row(d0, d1, kind, pay, version, rp):
        row_no[0] += 1
        open_l = st.liab
        gf = growth_factor(d0, d1, st.rate, t.day_count, t.compounding)
        interest = rp.q(open_l * (gf - 1)) if (open_l != 0 and d1 > d0) else ZERO
        tr = {}
        if interest:
            tr['interest'] = f"{open_l:,} × ((1 + {st.rate:.6%}{'' if t.compounding == 'annual' else '/' + t.compounding})^({(d1 - d0).days} days {t.day_count}) − 1) = {interest:,}"
        close_l = open_l + interest - pay
        open_r = st.cost - st.accum
        dep, why = (ZERO, '')
        if d1 > d0 and not st.terminated:
            dep, why = _dep_amount(st, d0, d1, open_r, rp)
        if dep:
            tr['depreciation'] = why
        if pay:
            tr['payment'] = f"Contractual payment(s) due {d1.isoformat()}: {pay:,}"
        st.accum += dep
        close_r = st.cost - st.accum
        row = Row(row_no[0], version, kind, d0, d1, (d1 - d0).days, open_l, interest, pay, pay - interest, close_l, open_r, dep, close_r, ZERO, tr)
        rows.append(row)
        st.liab = close_l
        # journals
        if interest:
            journals.append(Journal(refs.make(version, 'INTEREST', d1), d1, 'INTEREST', f"{t.ref}: interest on lease liability {d0} to {d1}",
                                    [_jl('INTEREST_EXP', interest, 'D'), _jl('LEASE_LIAB', interest, 'C')], [tr['interest']], version, row.row_no))
        if pay:
            journals.append(Journal(refs.make(version, 'PAYMENT', d1), d1, 'PAYMENT', f"{t.ref}: lease payment {d1}",
                                    [_jl('LEASE_LIAB', pay, 'D'), _jl('CASH', pay, 'C')], [tr['payment']], version, row.row_no))
        if dep:
            journals.append(Journal(refs.make(version, 'DEPRECIATION', d1), d1, 'DEPRECIATION', f"{t.ref}: depreciation of right-of-use asset {d0} to {d1}",
                                    [_jl('DEP_EXP', dep, 'D'), _jl('ROU_ACCDEP', dep, 'C')], [tr['depreciation']], version, row.row_no))

    # ---- replay events
    boundary_end = lambda: max([lease_end_boundary(st.end)] + [p.date for p in st.payments] + [st.dep['end']])
    evs = sorted(enumerate(events), key=lambda x: (x[1].effective_date, x[0]))
    for idx, ev in evs:
        if st.terminated:
            raise EngineError('No further events can be applied after a full termination.')
        E = ev.effective_date
        if E <= st.cur and E != st.cur:
            raise EngineError(f'Event effective date {E} is before the previous event date {st.cur}.')
        if E <= t.commencement:
            raise EngineError(f'Event effective date {E} must be after the commencement date {t.commencement}.')
        if E > boundary_end():
            raise EngineError(f'Event effective date {E} is after the end of the lease schedule ({boundary_end()}).')
        if E > st.cur:
            run_segment(E, False, st.version)
        st.version += 1
        res = _apply_event(t, st, ev, idx + 1, refs, rp, journals)
        results.append(res)
        b_l, a_l = res.before['liability'], res.after['liability']
        b_r, a_r = res.before['rou_carrying'], res.after['rou_carrying']
        if b_l != a_l or b_r != a_r:
            row_no[0] += 1
            rows.append(Row(row_no[0], st.version, 'event', E, E, 0, b_l, ZERO, ZERO, ZERO, a_l, b_r, ZERO, a_r, ZERO,
                            {'event': f"{res.type} ({res.decision}) effective {E}: liability {b_l:,} → {a_l:,}; ROU {b_r:,} → {a_r:,}"}, a_l - b_l, a_r - b_r))
    # ---- final segment
    if not st.terminated:
        end_b = boundary_end()
        if end_b > st.cur:
            run_segment(end_b, True, st.version)
        # reconcile rounding on the final row
        if rows and abs(st.liab) > 0:
            tol = max(D('0.05'), D('0.005') * len(rows)) if rp.decimals >= 1 else D(len(rows))
            if abs(st.liab) > tol:
                raise EngineError(f"The liability does not run down to nil (residual {st.liab:,}). Check edited payments, dates or the discount rate.")
            last = rows[-1]
            adj = -st.liab
            last.rounding_adj = adj
            last.interest += adj
            last.principal = last.payment - last.interest
            last.close_liab = ZERO
            last.trace['rounding'] = f"Rounding reconciliation of {adj:,} added to final-period interest so the liability closes at nil"
            st.liab = ZERO
            # amend the last interest journal (or create one)
            j = next((x for x in reversed(journals) if x.source == 'INTEREST' and x.row_no == last.row_no), None)
            if j:
                newint = last.interest
                j.lines = [_jl('INTEREST_EXP', newint, 'D'), _jl('LEASE_LIAB', newint, 'C')]
                j.trace.append(last.trace['rounding'])
            elif last.interest != 0:
                journals.append(Journal(refs.make(st.version, 'INTEREST', last.end), last.end, 'INTEREST', f"{t.ref}: interest on lease liability {last.start} to {last.end}",
                                        [_jl('INTEREST_EXP', last.interest, 'D'), _jl('LEASE_LIAB', last.interest, 'C')], [last.trace['rounding']], st.version, last.row_no))
    journals.sort(key=lambda j: (j.date, _ORDER.get(j.source, 5), j.ref))
    for j in journals:
        if not j.balanced():
            raise EngineError(f'Internal check failed: journal {j.ref} does not balance.')
    final = {'liability': st.liab, 'rou_carrying': st.cost - st.accum, 'rate': st.rate, 'terminated': st.terminated}
    return Timeline(t, initial, pv_lines, rows, journals, results, warnings, final)


_ORDER = {'INITIAL': 0, 'REASSESS': 1, 'MODIFICATION': 1, 'TERMINATION': 1, 'INTEREST': 2, 'PAYMENT': 3, 'DEPRECIATION': 4}


def _validate_terms(t: LeaseTerms):
    if not t.ref.strip():
        raise EngineError('Enter a lease reference.')
    if not t.commencement or not t.end_date:
        raise EngineError('Enter the commencement date and the end date.')
    if t.end_date <= t.commencement:
        raise EngineError('The end date must be after the commencement date.')
    if t.signing_date and t.signing_date > t.commencement:
        raise EngineError('The contract signing date is after the commencement date. Please check the dates.')
    if t.payment_amount < 0:
        raise EngineError('The payment amount cannot be negative.')
    if t.discount_rate < 0 or t.discount_rate >= 1:
        raise EngineError('Enter the discount rate as a percentage between 0 and 100 (for example 5.25).')
    if t.currency != t.functional_currency and t.fx_rate <= 0:
        raise EngineError('Enter the exchange rate from the lease currency to the functional currency.')
    if (t.ownership_transfers or t.purchase_option_certain) and t.useful_life_years <= 0:
        raise EngineError('Enter the useful life: the asset will be depreciated over its useful life because ownership transfers or a purchase option is reasonably certain (IFRS 16.32).')
    if t.depreciation_method not in ('straight_line', 'declining_balance'):
        raise EngineError('Unknown depreciation method.')


# ------------------------------------------------------------------ events
def _carrying(st):
    return st.cost - st.accum


def _snapshot(st):
    pays = st.payments
    reg = next((p.amount for p in pays if p.kind == 'lease'), ZERO)
    return {'date': st.cur, 'liability': st.liab, 'rou_cost': st.cost, 'accumulated_depreciation': st.accum, 'rou_carrying': _carrying(st),
            'remaining_payments': sum((p.amount for p in pays), ZERO), 'number_of_payments': len(pays), 'next_regular_payment': reg,
            'rate': st.rate, 'lease_end': st.end, 'depreciation_end': st.dep_end}


def _remeasure(t, st, E, new_payments, rate, rp, bridge, why):
    """Remeasure the liability at E (IFRS 16.39): adjust ROU; any excess reduction beyond a nil ROU goes to profit or loss."""
    new_l, lines = present_value(new_payments, E, rate, t.day_count, t.compounding, rp)
    delta = new_l - st.liab
    carrying = _carrying(st)
    pl = ZERO
    if delta >= 0:
        st.cost += delta
        rou_adj = delta
    else:
        red = -delta
        applied = min(red, carrying)
        st.cost -= applied
        pl = red - applied
        rou_adj = -applied
    bridge.append({'label': 'Liability before remeasurement', 'amount': st.liab, 'trace': 'Carrying amount at the effective date after interest to date'})
    bridge.append({'label': f'Liability after remeasurement (PV of revised payments at {rate:.6%})', 'amount': new_l, 'trace': why})
    bridge.append({'label': 'Remeasurement of liability', 'amount': delta, 'trace': 'After − before'})
    bridge.append({'label': 'Adjustment to ROU asset (IFRS 16.39)', 'amount': rou_adj, 'trace': 'Equal to the liability remeasurement, limited to the ROU carrying amount'})
    if pl:
        bridge.append({'label': 'Excess reduction recognised in profit or loss (ROU asset is nil)', 'amount': pl, 'trace': 'IFRS 16.39: remaining remeasurement amount goes to profit or loss'})
    old_l = st.liab
    st.liab = new_l
    st.rate = rate
    st.payments = list(new_payments)
    return delta, rou_adj, pl, old_l, new_l


def _remeasure_lines(delta, rou_adj, pl):
    lines = []
    if delta > 0:
        lines += [_jl('ROU_COST', rou_adj, 'D', 'Increase in ROU asset'), _jl('LEASE_LIAB', delta, 'C', 'Increase in lease liability')]
    elif delta < 0:
        lines += [_jl('LEASE_LIAB', -delta, 'D', 'Decrease in lease liability')]
        if rou_adj:
            lines.append(_jl('ROU_COST', -rou_adj, 'C', 'Decrease in ROU asset'))
        if pl:
            lines.append(_jl('GAIN_LOSS', pl, 'C', 'Excess reduction in liability – ROU asset reduced to nil'))
    return _drop_zero(lines)


def _rate_for(ev_type, p, st, floating=False):
    """IFRS 16 discount-rate rule per event type (paras 40-43, 45)."""
    if ev_type in ('term_reassessment',):
        r = p.get('revised_rate')
        if r in (None, ''):
            raise EngineError('A revised discount rate is required for a change in lease term or purchase-option assessment (IFRS 16.40-41): enter the rate implicit in the lease for the remainder of the term if readily determinable, otherwise the incremental borrowing rate at the reassessment date.')
        return dec(r) / 100, 'Revised discount rate (IFRS 16.41): change in lease term / purchase option assessment'
    if ev_type == 'index_change':
        if floating:
            r = p.get('revised_rate')
            if r in (None, ''):
                raise EngineError('The change in payments results from a change in a floating interest rate, so a revised discount rate that reflects the rate change is required (IFRS 16.43).')
            return dec(r) / 100, 'Revised discount rate (IFRS 16.43): payments depend on a floating interest rate'
        return st.rate, 'Unchanged (original) discount rate (IFRS 16.42(b)): index-linked change in payments'
    if ev_type == 'rvg_change':
        return st.rate, 'Unchanged (original) discount rate (IFRS 16.42(a)): change in amounts expected under residual value guarantee'
    raise EngineError('Unknown rate rule')


def _pattern_payments(t, st, end_date, amount, from_date):
    base = generate_payments(t, end_date=end_date, amount=amount, start_from=from_date)
    return [p for p in base if p.kind == 'lease']


def _apply_event(t, st, ev, n, refs, rp, journals):
    E, p = ev.effective_date, ev.params
    before = _snapshot(st)
    bridge, notes, out_j = [], [], []
    version = st.version
    decision, rate_used, rate_reason, new_lease = ev.type, None, '', None
    src = {'term_reassessment': 'REASSESS', 'index_change': 'REASSESS', 'rvg_change': 'REASSESS', 'modification': 'MODIFICATION', 'termination': 'TERMINATION'}[ev.type]

    def post(lines, narr, trace):
        lines = _drop_zero(lines)
        if lines:
            j = Journal(refs.make(version, src, E), E, src, f"{t.ref}: {narr}", lines, trace, version)
            out_j.append(j)
            journals.append(j)

    def re_plan(option_certain=None):
        if option_certain is not None:
            st.option_certain = option_certain
        st.dep_end = depreciation_end(t, st.end, st.option_certain)
        _new_plan(t, st, E, _carrying(st))

    def option_items(boundary, old):
        """Carry non-regular items (RVG / purchase option / penalty) forward to the new end, with parameter overrides."""
        items = {q.kind: q for q in old if q.kind != 'lease'}
        if p.get('new_rvg') not in (None, ''):
            items.pop('rvg', None)
            if dec(p['new_rvg']) > 0:
                items['rvg'] = Payment(boundary, t.fx(p['new_rvg']), 'rvg', 'Residual value guarantee expected to be payable')
        if p.get('purchase_option_certain') is True:
            price = dec(p.get('purchase_option_price') or t.purchase_option_price)
            if price > 0:
                items['purchase_option'] = Payment(boundary, t.fx(price), 'purchase_option', 'Purchase option – reasonably certain to be exercised')
        elif p.get('purchase_option_certain') is False:
            items.pop('purchase_option', None)
        if p.get('termination_penalty_included') is True:
            pen = dec(p.get('termination_penalty') or t.termination_penalty)
            if pen > 0:
                items['termination_penalty'] = Payment(boundary, t.fx(pen), 'termination_penalty', 'Termination penalty included in lease payments')
        elif p.get('termination_penalty_included') is False:
            items.pop('termination_penalty', None)
        return [Payment(boundary, q.amount, q.kind, q.note) for q in items.values()]

    if ev.type == 'term_reassessment':
        rate_used, rate_reason = _rate_for(ev.type, p, st)
        new_end = parse_date(p['new_end_date']) if p.get('new_end_date') else st.end
        if new_end < E:
            raise EngineError('The revised lease end date is before the effective date.')
        amount = dec(p['new_payment_amount']) if p.get('new_payment_amount') not in (None, '') else None
        old_lease = [q for q in st.payments if q.kind == 'lease']
        if p.get('payments_override'):
            lease_part = [Payment(parse_date(x['date']), t.fx(x['amount']), 'lease', x.get('note', ''), True) for x in p['payments_override']]
        elif new_end != st.end or amount is not None:
            lease_part = _pattern_payments(t, st, new_end, amount if amount is not None else st.reg_amount / t.fx_rate, E)
        else:
            lease_part = old_lease
        boundary = lease_end_boundary(new_end)
        new_pay = sorted(lease_part + option_items(boundary, [q for q in st.payments if q.kind != 'lease']), key=lambda q: q.date)
        if not new_pay:
            raise EngineError('The revised schedule has no future payments. Use the Termination workspace to end the lease.')
        new_cert = p.get('purchase_option_certain')
        delta, rou_adj, pl, ol, nl = _remeasure(t, st, E, new_pay, rate_used, rp, bridge, f"Σ PV of {len(new_pay)} revised payments from {E}")
        st.end = new_end
        if amount is not None:
            st.reg_amount = t.fx(amount)
        post(_remeasure_lines(delta, rou_adj, pl), f"remeasurement – {ev.label or 'change in lease term / purchase option'}", [r['trace'] for r in bridge])
        re_plan(new_cert if new_cert is not None else None)
        decision = 'reassessment_revised_rate'

    elif ev.type == 'index_change':
        floating = bool(p.get('floating_rate_linked', t.floating_rate_linked))
        rate_used, rate_reason = _rate_for(ev.type, p, st, floating)
        if p.get('new_payment_amount') not in (None, ''):
            newamt = t.fx(p['new_payment_amount'])
        elif p.get('index_change_pct') not in (None, ''):
            base = st.reg_amount
            newamt = rp.q(base * (D(1) + dec(p['index_change_pct']) / 100))
        else:
            raise EngineError('Enter the new payment amount or the percentage change in the index / rate.')
        new_pay = [Payment(q.date, newamt if q.kind == 'lease' else q.amount, q.kind, q.note) for q in st.payments]
        if not any(q.kind == 'lease' for q in st.payments):
            raise EngineError('There are no future lease payments to change.')
        delta, rou_adj, pl, ol, nl = _remeasure(t, st, E, new_pay, rate_used, rp, bridge, f"Future regular payments restated to {newamt:,}")
        st.reg_amount = newamt
        post(_remeasure_lines(delta, rou_adj, pl), f"remeasurement – {ev.label or 'change in index / rate-linked payments'}", [r['trace'] for r in bridge])
        re_plan()
        decision = 'reassessment_unchanged_rate' if not floating else 'reassessment_revised_rate'

    elif ev.type == 'rvg_change':
        rate_used, rate_reason = _rate_for(ev.type, p, st)
        if p.get('new_rvg') in (None, ''):
            raise EngineError('Enter the revised amount expected to be payable under the residual value guarantee.')
        boundary = lease_end_boundary(st.end)
        keep = [q for q in st.payments if q.kind != 'rvg']
        if dec(p['new_rvg']) > 0:
            keep.append(Payment(max(boundary, max((q.date for q in st.payments), default=boundary)), t.fx(p['new_rvg']), 'rvg', 'Residual value guarantee expected to be payable'))
        delta, rou_adj, pl, ol, nl = _remeasure(t, st, E, sorted(keep, key=lambda q: q.date), rate_used, rp, bridge, 'Revised residual value guarantee amount')
        post(_remeasure_lines(delta, rou_adj, pl), f"remeasurement – {ev.label or 'change in residual value guarantee'}", [r['trace'] for r in bridge])
        re_plan()
        decision = 'reassessment_unchanged_rate'

    elif ev.type == 'termination':
        decision, rate_used, rate_reason = _termination(t, st, ev, p, E, rp, bridge, notes, post, re_plan, _pattern_payments, option_items)

    elif ev.type == 'modification':
        decision, rate_used, rate_reason, new_lease = _modification(t, st, ev, p, E, rp, bridge, notes, post, re_plan, _pattern_payments, option_items)
    else:
        raise EngineError(f'Unknown event type {ev.type}')
    st.cur = E
    after = _snapshot(st)
    after['date'] = E
    return EventResult(n, ev.type, E, decision, rate_used, rate_reason, before, after, bridge, out_j, notes, new_lease)


def _termination(t, st, ev, p, E, rp, bridge, notes, post, re_plan, pattern, option_items, from_modification=False, pct_override=None):
    pct = dec(pct_override if pct_override is not None else p.get('scope_pct', 100))
    if not (0 < pct <= 100):
        raise EngineError('The reduction in scope must be between 0 and 100 per cent.')
    cash = rp.q(t.fx(p.get('termination_payment', 0)))
    frac = pct / 100
    L0, C, A = st.liab, st.cost, st.accum
    dL, dC, dA = rp.q(L0 * frac), rp.q(C * frac), rp.q(A * frac)
    if pct == 100:
        dL, dC, dA = L0, C, A
    dROU = dC - dA
    gain = dL - dROU - cash
    full = pct == 100
    bridge.append({'label': f'Reduction in scope', 'amount': pct, 'trace': f"{pct}% of the lease terminated effective {E} (full termination)" if full else f"{pct}% of the lease terminated effective {E}"})
    bridge.append({'label': 'Lease liability derecognised', 'amount': dL, 'trace': f"{L0:,} × {pct}% = {dL:,}"})
    bridge.append({'label': 'ROU asset derecognised (net carrying amount)', 'amount': dROU, 'trace': f"({C:,} − {A:,}) × {pct}% = {dROU:,}"})
    if cash:
        bridge.append({'label': 'Termination payment made to lessor', 'amount': cash, 'trace': 'Cash paid'})
    bridge.append({'label': 'Gain / (loss) on termination (IFRS 16.46(a))', 'amount': gain, 'trace': f"Liability derecognised {dL:,} − ROU derecognised {dROU:,} − cash paid {cash:,} = {gain:,}"})
    lines = [_jl('LEASE_LIAB', dL, 'D', 'Derecognise lease liability'), _jl('ROU_ACCDEP', dA, 'D', 'Derecognise accumulated depreciation'),
             _jl('ROU_COST', dC, 'C', 'Derecognise ROU asset cost')]
    if cash:
        lines.append(_jl('CASH', cash, 'C', 'Termination payment'))
    if gain > 0:
        lines.append(_jl('GAIN_LOSS', gain, 'C', 'Gain on termination'))
    elif gain < 0:
        lines.append(_jl('GAIN_LOSS', -gain, 'D', 'Loss on termination'))
    post(lines, f"{'full' if full else 'partial'} termination – {ev.label or ''}".strip(' –'), [r['trace'] for r in bridge])
    st.liab, st.cost, st.accum = L0 - dL, C - dC, A - dA
    rate_reason = 'Original discount rate used to derecognise the proportion terminated (IFRS 16.46(a))'
    rate_used = st.rate
    if full:
        st.payments, st.terminated = [], True
        st.dep_end = E
        st.dep = {'start': E, 'basis': ZERO, 'end': E, 'method': t.depreciation_method, 'db_rate': ZERO}
        notes.append('Full termination: scheduled interest, payments and depreciation stop from the effective date.')
        return 'full_termination', rate_used, rate_reason
    scaled = [Payment(q.date, rp.q(q.amount * (1 - frac)), q.kind, q.note) for q in st.payments]
    changed = any(p.get(k) not in (None, '', False) for k in ('new_payment_amount', 'new_end_date', 'revised_rate', 'payments_override'))
    if changed:
        r = p.get('revised_rate')
        if r in (None, ''):
            raise EngineError('You changed the remaining payments or term, so enter the revised discount rate for remeasuring the remaining liability (IFRS 16.45(c)).')
        rate_used = dec(r) / 100
        rate_reason += '; revised discount rate used to remeasure the remaining liability (IFRS 16.45(c))'
        if p.get('payments_override'):
            new_pay = sorted([Payment(parse_date(x['date']), t.fx(x['amount']), 'lease', '', True) for x in p['payments_override']], key=lambda q: q.date)
        else:
            new_end = parse_date(p['new_end_date']) if p.get('new_end_date') else st.end
            amount = dec(p['new_payment_amount']) if p.get('new_payment_amount') not in (None, '') else None
            if new_end != st.end or amount is not None:
                amt = amount if amount is not None else (st.reg_amount * (1 - frac)) / t.fx_rate
                new_pay = sorted(pattern(t, st, new_end, amt, E) + option_items(lease_end_boundary(new_end), scaled), key=lambda q: q.date)
            else:
                new_pay = scaled
            st.end = new_end
        delta, rou_adj, pl, ol, nl = _remeasure(t, st, E, new_pay, rate_used, rp, bridge, 'Remaining liability remeasured after partial termination')
        post(_remeasure_lines(delta, rou_adj, pl), 'remeasurement of remaining lease after partial termination', [r_['trace'] for r_ in bridge[-5:]])
    else:
        chk, _ = present_value(scaled, E, st.rate, t.day_count, t.compounding, rp)
        diff = st.liab - chk
        bridge.append({'label': 'Check: remaining liability vs PV of remaining (scaled) payments', 'amount': diff, 'trace': f"Carried {st.liab:,} vs PV {chk:,}; difference reflects rounding only"})
        if abs(diff) > max(D('1'), st.liab * D('0.0005')):
            notes.append(f'The remaining liability differs from the PV of the remaining payments by {diff:,}. Review payments or consider remeasuring with a revised rate.')
        st.payments = scaled
        st.reg_amount = rp.q(st.reg_amount * (1 - frac))
    re_plan()
    return 'partial_termination', rate_used, rate_reason


def classify_modification(p: dict, rp) -> dict:
    """IFRS 16.44: is the modification a separate lease? Both conditions are required."""
    adds = bool(p.get('adds_right_of_use'))
    cons = dec(p.get('added_consideration', 0))
    standalone = dec(p.get('standalone_price', 0))
    tol = dec(p.get('price_tolerance_pct', 0)) / 100
    reasons = []
    commensurate = False
    if adds:
        if standalone > 0:
            commensurate = abs(cons - standalone) <= standalone * tol
            reasons.append(f"Consideration increase {cons:,} vs stand-alone price {standalone:,} (tolerance {tol:.2%}) → {'commensurate' if commensurate else 'NOT commensurate'}")
        else:
            reasons.append('Stand-alone price of the additional right of use not provided → cannot demonstrate commensurate pricing')
    else:
        reasons.append('The modification does not add the right to use one or more underlying assets → not a separate lease')
    separate = adds and commensurate
    pct = dec(p.get('scope_decrease_pct', 0))
    kind = 'separate_lease' if separate else ('scope_decrease' if pct > 0 else 'other_modification')
    return {'kind': kind, 'separate': separate, 'reasons': reasons}


def _modification(t, st, ev, p, E, rp, bridge, notes, post, re_plan, pattern, option_items):
    cls = classify_modification(p, rp)
    for r in cls['reasons']:
        notes.append(r)
    if cls['separate']:
        notes.append('Separate lease (IFRS 16.44): the existing lease is NOT adjusted. Create a new lease for the additional right of use and account for it from its commencement date.')
        template = {'ref': f"{t.ref}-ADD", 'lessor': t.lessor, 'asset': 'Additional right of use – ' + (p.get('added_asset') or t.asset), 'commencement': E.isoformat(),
                    'end_date': st.end.isoformat(), 'payment_amount': str(dec(p.get('added_consideration', 0))), 'frequency': t.frequency, 'timing': t.timing}
        bridge.append({'label': 'Additional consideration (separate lease)', 'amount': dec(p.get('added_consideration', 0)), 'trace': 'Accounted for as a new lease'})
        return 'separate_lease', st.rate, 'Not applicable – a new lease is created with its own rate at its commencement date (IFRS 16.44)', template
    notes.append('Not a separate lease (IFRS 16.45): the existing lease is adjusted at the modification effective date.')
    pct = dec(p.get('scope_decrease_pct', 0))
    if pct > 0:
        d, r, why = _termination(t, st, ev, dict(p, scope_pct=pct), E, rp, bridge, notes, post, re_plan, pattern, option_items, True, pct_override=pct)
        decision = 'modification_scope_decrease' if pct < 100 else 'full_termination'
        return decision, r, why, None
    # other modification: remeasure with revised discount rate (IFRS 16.45(c), 46(b))
    r = p.get('revised_rate')
    if r in (None, ''):
        raise EngineError('A revised discount rate is required to remeasure the liability for this modification (IFRS 16.45(c)): the rate implicit in the lease for the remainder of the term if readily determinable, otherwise the incremental borrowing rate at the modification effective date.')
    rate_used = dec(r) / 100
    new_end = parse_date(p['new_end_date']) if p.get('new_end_date') else st.end
    amount = dec(p['new_payment_amount']) if p.get('new_payment_amount') not in (None, '') else None
    if p.get('payments_override'):
        new_pay = sorted([Payment(parse_date(x['date']), t.fx(x['amount']), 'lease', '', True) for x in p['payments_override']], key=lambda q: q.date)
    elif new_end != st.end or amount is not None:
        new_pay = sorted(pattern(t, st, new_end, amount if amount is not None else st.reg_amount / t.fx_rate, E) + option_items(lease_end_boundary(new_end), st.payments), key=lambda q: q.date)
    else:
        new_pay = list(st.payments)
    if cls['kind'] == 'other_modification' and p.get('adds_right_of_use'):
        notes.append('Increase in scope that is not priced at the stand-alone amount: the liability is remeasured and the ROU asset increased (IFRS 16.46(b)).')
    delta, rou_adj, pl, ol, nl = _remeasure(t, st, E, new_pay, rate_used, rp, bridge, 'Revised payments after the modification')
    st.end = new_end
    if amount is not None:
        st.reg_amount = t.fx(amount)
    post(_remeasure_lines(delta, rou_adj, pl), f"lease modification – {ev.label or 'remeasurement'}", [r_['trace'] for r_ in bridge])
    re_plan()
    return 'modification_remeasured', rate_used, 'Revised discount rate (IFRS 16.45(c)): modification not accounted for as a separate lease', None


# ------------------------------------------------------------------ exempt leases
def _exempt_timeline(t: LeaseTerms) -> Timeline:
    rp = t.rounding
    payments = [p for p in ensure_payments(t)]
    total = sum((p.amount for p in payments), ZERO)
    start, end = t.commencement, lease_end_boundary(t.end_date)
    days = (end - start).days
    refs = _Refs(t.ref)
    rows, journals = [], []
    months = []
    k = 0
    while add_months(start, k, start.day) < end:
        months.append((add_months(start, k, start.day), min(add_months(start, k + 1, start.day), end)))
        k += 1
    accrued = ZERO
    paid = ZERO
    # straight-line expense by days; payments per schedule
    events = sorted({m[1] for m in months} | {p.date for p in payments})
    prev = start
    cum_exp = ZERO
    for i, d in enumerate(events, 1):
        exp_cum = total if d >= end else rp.q(total * D((d - start).days) / D(days))
        exp = exp_cum - cum_exp
        pay = sum((p.amount for p in payments if p.date == d), ZERO)
        if exp:
            journals.append(Journal(refs.make(0, 'LEASE_EXPENSE', d), d, 'LEASE_EXPENSE', f"{t.ref}: {t.exemption.replace('_', '-')} lease expense (straight-line)",
                                    [_jl('LEASE_EXP', exp, 'D'), _jl('ACCRUED_LEASE', exp, 'C')], [f"Straight-line: total payments {total:,} × {(d - start).days}/{days} days, less expense already recognised {cum_exp:,}"], 0, i))
        if pay:
            journals.append(Journal(refs.make(0, 'PAYMENT', d), d, 'PAYMENT', f"{t.ref}: lease payment", [_jl('ACCRUED_LEASE', pay, 'D'), _jl('CASH', pay, 'C')], [f"Contractual payment {pay:,}"], 0, i))
        accrued += exp - pay
        cum_exp = exp_cum
        rows.append(Row(i, 0, 'normal', prev, d, (d - prev).days, ZERO, ZERO, pay, ZERO, ZERO, ZERO, ZERO, ZERO, ZERO, {'expense': f"{exp:,}"}))
        prev = d
    initial = {'liability': ZERO, 'rou_cost': ZERO, 'rate': ZERO, 'commencement': start, 'trace': [f"{t.exemption.replace('_', '-')} lease exemption elected (IFRS 16.5-8): no right-of-use asset or lease liability; payments of {total:,} expensed straight-line"]}
    return Timeline(t, initial, [], rows, journals, [], ['Exempt lease: expense recognised straight-line; no ROU asset or liability.'], {'liability': ZERO, 'rou_carrying': ZERO, 'rate': ZERO, 'terminated': False}, True)


# ------------------------------------------------------------------ preview of an uncommitted event
def preview_event(terms: LeaseTerms, committed: list[Event], new_event: Event):
    """Return (timeline_after, event_result) without persisting anything."""
    tl = build_timeline(terms, committed + [new_event])
    res = next(r for r in tl.events if r.index == len(committed) + 1)
    return tl, res
