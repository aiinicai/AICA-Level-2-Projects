"""Lessee accounting engine — initial measurement, subsequent measurement and events.

The engine is a deterministic, day-accurate *timeline simulator*. Starting at the
commencement date it walks through every payment, month-end and event:

* liability interest between two dates   = L x ((1+R)^(tau2 - tau1) - 1)          (Ind AS 116.36–37)
* ROU depreciation between two dates     = NBV_segment x weight(a,b) / weight(segment)  (31–32)
* restoration provision unwinding and security-deposit interest use the same maths
* events (modification 44–46, reassessment 39–43, termination, impairment,
  restoration revision) are applied at the START of their effective date

Balances are carried exactly (40 significant digits). Reported figures are rounded
with the *balance-driven* method: each closing balance is rounded and the period
movement (interest/depreciation) is the difference, so every row reconciles
exactly and no rounding accumulates. The alternative *interest-driven* method
rounds interest each period and shows an explicit final true-up.
"""
from __future__ import annotations

import copy
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from .calendar_utils import add_months, month_end, month_ends_between, month_weight, next_day, prev_day
from .decimal_utils import D, ONE, ZERO, dpow, engine_context, pct, q
from .lease_term import determine_lease_term
from .models import (EventResult, EventType, ExcludedLine, InitialMeasurement, Issue, JudgmentFlag,
                     LeaseEvent, LesseeLeaseInput, LesseeResult, PaymentCategory, PaymentLine, PaymentRow,
                     PeriodRow, Posting, PVLine, ReassessmentKind, Severity, TermResult)
from .payments import classify_payments, measure_amount
from .rates import (CONVENTION_LABEL, DAYCOUNT_LABEL, Discounter, TimeBasis, effective_annual_rate,
                    present_value, solve_rate)
from .references import ref

ENGINE_VERSION = "1.0.0"


class EngineInputError(Exception):
    def __init__(self, issues: list[Issue]):
        self.issues = issues
        super().__init__("; ".join(i.message for i in issues if i.severity == Severity.ERROR))


def _fmt(d: date) -> str:
    return d.strftime("%d-%b-%Y")


# ---------------------------------------------------------------------------
# validation (spec section 33) — engine-level checks
# ---------------------------------------------------------------------------
def validate_lessee_input(inp: LesseeLeaseInput) -> list[Issue]:
    iss: list[Issue] = []
    c = inp.commencement
    if inp.term.contract_end < c:
        iss.append(Issue("DATE_ORDER", "Commencement date cannot follow the contract expiry date.", Severity.ERROR, "contract_end"))
    if inp.discount_rate_pct is None:
        iss.append(Issue("RATE_MISSING", "Discount rate is required for a capitalised lease (Ind AS 116.26).", Severity.ERROR, "discount_rate"))
    else:
        r = D(inp.discount_rate_pct)
        if r < 0 or r > 50:
            iss.append(Issue("RATE_RANGE", f"Discount rate {r}% is outside a plausible range (0–50%).", Severity.ERROR, "discount_rate"))
        elif r == 0:
            iss.append(Issue("RATE_ZERO", "Discount rate is 0% — confirm this is intended.", Severity.WARNING, "discount_rate"))
    if not inp.payments:
        iss.append(Issue("NO_PAYMENTS", "No lease payments entered.", Severity.ERROR, "payments"))
    for ln in inp.payments:
        if ln.date is None:
            iss.append(Issue("PAY_DATE", f"Payment line {ln.line_no} has no date.", Severity.ERROR, "payments"))
        if ln.include_override is not None and not ln.override_reason:
            iss.append(Issue("OVERRIDE_REASON", f"Payment line {ln.line_no}: inclusion override requires a reason.", Severity.ERROR, "payments"))
        if ln.date and ln.date > add_months(inp.term.contract_end, 12 * 50):
            iss.append(Issue("PAY_DATE_RANGE", f"Payment line {ln.line_no} date {ln.date} is implausible.", Severity.ERROR, "payments"))
    if (inp.ownership_transfers) and inp.useful_life_end is None:
        iss.append(Issue("USEFUL_LIFE", "Useful life end date is required when ownership transfers (Ind AS 116.32).", Severity.ERROR, "useful_life_end"))
    for ev in inp.events:
        if ev.effective_date < c:
            iss.append(Issue("EVENT_DATE", f"{ev.type.value.title()} dated {ev.effective_date} precedes commencement.", Severity.ERROR, "events"))
    if inp.deposit is not None:
        dp = inp.deposit
        if dp.refund_date <= dp.payment_date:
            iss.append(Issue("DEPOSIT_DATES", "Security deposit refund date must follow the payment date.", Severity.ERROR, "deposit"))
        if dp.market_rate_pct is None and not dp.interest_bearing:
            iss.append(Issue("DEPOSIT_RATE", "Market interest rate is required to fair-value an interest-free deposit (Ind AS 109).",
                             Severity.ERROR, "deposit"))
    if inp.restoration is not None and inp.restoration.settlement_date < c:
        iss.append(Issue("RESTORATION_DATE", "Restoration settlement date precedes commencement.", Severity.ERROR, "restoration"))
    if inp.fx is not None and not inp.fx.rates:
        iss.append(Issue("FX_RATES", "Exchange rates are required for a foreign-currency lease.", Severity.ERROR, "fx"))
    return iss


# ---------------------------------------------------------------------------
# simulator
# ---------------------------------------------------------------------------
@dataclass
class _PeriodAcc:
    interest_exact: Decimal = ZERO
    payments: Decimal = ZERO
    liab_add: Decimal = ZERO
    liab_remeasure: Decimal = ZERO
    liab_modif: Decimal = ZERO
    liab_derecog: Decimal = ZERO
    rou_add: Decimal = ZERO
    rou_remeasure: Decimal = ZERO
    rou_modif: Decimal = ZERO
    rou_derecog: Decimal = ZERO
    ev_accdep: Decimal = ZERO     # rounded changes to acc dep from events (derecognition)
    ev_accimp: Decimal = ZERO     # rounded changes to acc imp from events (derecognition)
    impairment: Decimal = ZERO    # rounded impairment loss (+) / reversal (−)
    gain_loss: Decimal = ZERO
    remeasure_pl: Decimal = ZERO
    variable: Decimal = ZERO
    nonlease: Decimal = ZERO
    cash: Decimal = ZERO
    prov_add: Decimal = ZERO
    prov_rev: Decimal = ZERO
    prov_settle: Decimal = ZERO
    dep_add: Decimal = ZERO
    dep_refund: Decimal = ZERO
    dep_catchup: Decimal = ZERO
    pay_dates: list = field(default_factory=list)
    int_parts: list = field(default_factory=list)
    dep_parts: list = field(default_factory=list)
    # FX (functional currency)
    fx_interest: Decimal = ZERO
    fx_payments: Decimal = ZERO
    fx_liab_adj: Decimal = ZERO
    fx_liab_add: Decimal = ZERO
    fx_liab_derecog: Decimal = ZERO


class LesseeSimulator:
    def __init__(self, inp: LesseeLeaseInput):
        self.inp = inp
        self.policy = inp.policy
        self.dp = inp.policy.currency_decimals
        self.c = inp.commencement
        self.flags: list[JudgmentFlag] = []
        self.issues: list[Issue] = []
        self.postings: list[Posting] = []
        self.event_results: list[EventResult] = []
        self.rows: list[PeriodRow] = []
        self.payment_rows: list[PaymentRow] = []
        self.expedient = inp.non_lease_expedient

    # ------------------------------------------------------------------ utils
    def r(self, x) -> Decimal:
        return q(x, self.dp)

    def weight(self, a: date, b: date) -> Decimal:
        if b <= a:
            return ZERO
        if self.policy.depreciation_method == "MONTHLY_EQUAL":
            return month_weight(a, b)
        return Decimal((b - a).days)

    def fx_rate(self, d: date) -> Decimal:
        rates = self.inp.fx.rates
        best = None
        for k in sorted(rates):
            if k <= d:
                best = rates[k]
            else:
                break
        if best is None:
            best = rates[min(rates)]
            self.issues.append(Issue("FX_RATE_FALLBACK", f"No exchange rate on/before {d}; earliest available rate used.",
                                     Severity.WARNING, "fx"))
        return D(best)

    def fx_avg(self, ps: date, pe: date) -> Decimal:
        avg = self.inp.fx.average_rates.get(pe)
        if avg is not None:
            return D(avg)
        return (self.fx_rate(ps) + self.fx_rate(pe)) / 2

    # ------------------------------------------------------------------ run
    @engine_context
    def run(self) -> LesseeResult:
        inp = self.inp
        errs = validate_lessee_input(inp)
        if any(i.severity == Severity.ERROR for i in errs):
            raise EngineInputError(errs)
        self.issues.extend(errs)

        self.term: TermResult = determine_lease_term(inp.term)
        self.flags.extend(self.term.flags)
        lines = classify_payments([copy.copy(l) for l in inp.payments], self.term, self.expedient)
        for i, l in enumerate(lines, start=1):
            if not l.line_no:
                l.line_no = i
        self.all_lines = lines
        self.basis = TimeBasis(self.c, self.policy.daycount)
        self.rate_pct = D(inp.discount_rate_pct)
        self.disc = Discounter(effective_annual_rate(self.rate_pct, self.policy.rate_convention), self.basis)
        self.fx_on = inp.fx is not None

        self._judgment_flags_from_input(lines)
        if inp.opening is not None:
            initial = self._initial_cutover(lines)
        else:
            initial = self._initial_measurement(lines)
        self._simulate()
        self.postings.sort(key=lambda p: (p.date, 0 if p.event in ("DEPOSIT_PAID", "COMMENCEMENT") else 1))
        self._final_checks()
        totals = self._totals()
        return LesseeResult(lease_id=inp.lease_id, currency=inp.currency, term=self.term, initial=initial,
                            periods=self.rows, payment_rows=self.payment_rows, events=self.event_results,
                            postings=self.postings, payments=self.all_lines, flags=self.flags, issues=self.issues,
                            deposit=self.deposit_summary, restoration=self.restoration_summary,
                            fx_periods=self.fx_rows if self.fx_on else None, totals=totals,
                            engine_version=ENGINE_VERSION)

    # ------------------------------------------------------------------ flags
    def _judgment_flags_from_input(self, lines: list[PaymentLine]):
        inp = self.inp
        cats = {PaymentCategory(l.category) for l in lines}
        if PaymentCategory.VARIABLE in cats:
            self.flags.append(JudgmentFlag("VARIABLE_PAYMENTS", "Variable lease payments",
                                           "Variable payments not depending on an index or rate are excluded from the liability. "
                                           "Confirm none are in-substance fixed (B42).", ref("VARIABLE_EXCL")))
        if cats & {PaymentCategory.INDEX_LINKED, PaymentCategory.RATE_LINKED}:
            self.flags.append(JudgmentFlag("INDEX_PAYMENTS", "Index / rate-linked payments",
                                           "Measured at the index/rate at commencement; remeasure when cash flows change (42(b)).",
                                           ref("PAYMENTS")))
        if any(D(l.non_lease_amount) != 0 for l in lines):
            self.flags.append(JudgmentFlag("NON_LEASE_COMPONENTS", "Non-lease components",
                                           ("Practical expedient elected — non-lease charges combined with lease payments."
                                            if self.expedient else
                                            "Non-lease charges (e.g. maintenance/CAM) separated and expensed."),
                                           ref("COMPONENTS")))
        if inp.deposit is not None and not inp.deposit.interest_bearing:
            self.flags.append(JudgmentFlag("DEPOSIT", "Interest-free security deposit",
                                           "Measured at fair value under Ind AS 109; the difference from cash paid is treated as "
                                           "prepaid rent (entity policy). Confirm market rate used.", ref("DEPOSIT"),
                                           assumptions=[f"Market rate {inp.deposit.market_rate_pct}% p.a."]))
        if inp.restoration is not None:
            self.flags.append(JudgmentFlag("RESTORATION", "Restoration obligation estimate",
                                           "Estimate, timing and pre-tax discount rate are management estimates (Ind AS 37).",
                                           ref("RESTORATION_ROU")))
        if self.fx_on:
            self.flags.append(JudgmentFlag("FX_LEASE", "Foreign-currency lease",
                                           "Liability retranslated at closing rates (monetary); ROU at historical rate (non-monetary).",
                                           ref("FX_MONETARY")))
        if inp.rate_basis == "IBR":
            self.flags.append(JudgmentFlag("IBR", "Incremental borrowing rate",
                                           "IBR must reflect the lease term, currency, security and economic environment; "
                                           "document source, methodology and approval.", ref("LIAB_INITIAL"),
                                           assumptions=[f"IBR {self.rate_pct}% ({CONVENTION_LABEL[self.policy.rate_convention]})"]))

    # ------------------------------------------------------------------ initial
    def _split_lines(self, lines: list[PaymentLine], at: date, paid_at_date: bool):
        liab, prepaid, excluded = [], [], []
        for ln in lines:
            if not ln.included:
                excluded.append(ln)
            elif ln.date < at or (ln.date == at and paid_at_date):
                prepaid.append(ln)
            else:
                liab.append(ln)
        return liab, prepaid, excluded

    def _initial_measurement(self, lines: list[PaymentLine]) -> InitialMeasurement:
        inp, c = self.inp, self.c
        liab, prepaid, excluded = self._split_lines(lines, c, self.policy.commencement_payment_paid)
        pv_lines = []
        L0 = ZERO
        undiscounted = ZERO
        for ln in liab:
            amt = measure_amount(ln, self.expedient)
            df = self.disc.df(ln.date, c)
            pv = amt * df
            L0 += pv
            undiscounted += amt
            pv_lines.append(PVLine(ln.date, amt, self.disc.years(ln.date, c), df, pv, PaymentCategory(ln.category).value,
                                   ln.description))
        excl = [ExcludedLine(ln.date, D(ln.lease_amount) + D(ln.non_lease_amount), PaymentCategory(ln.category).value,
                             ln.inclusion_reason, ln.description) for ln in excluded]
        for ln in prepaid:
            excl.append(ExcludedLine(ln.date, measure_amount(ln, self.expedient), PaymentCategory(ln.category).value,
                                     "Paid at or before commencement — not part of the liability; included in ROU cost (24(b)).",
                                     ln.description))
        self.liab_lines = liab
        self.excluded_lines = excluded
        self.L = L0
        self.L0_r = self.r(L0)

        comps: list[tuple[str, Decimal, str]] = [("Initial measurement of lease liability", self.r(L0), "Ind AS 116.24(a), 26")]
        before_total = sum((measure_amount(l, self.expedient) for l in prepaid if l.date < c), ZERO) + \
            sum((D(x.amount) for x in inp.prepaid_before_commencement), ZERO)
        at_total = sum((measure_amount(l, self.expedient) for l in prepaid if l.date == c), ZERO)
        if before_total:
            comps.append(("Lease payments made before commencement (advance to lessor)", self.r(before_total), "Ind AS 116.24(b)"))
        if at_total:
            comps.append(("Lease payment made at commencement", self.r(at_total), "Ind AS 116.24(b)"))
        inc = sum((D(x.amount) for x in inp.incentives_received), ZERO)
        if inc:
            comps.append(("Less: lease incentives received", -self.r(inc), "Ind AS 116.24(b)"))
        idc = sum((D(x.amount) for x in inp.idc), ZERO)
        if idc:
            comps.append(("Initial direct costs", self.r(idc), "Ind AS 116.24(c)"))
        # restoration
        self._setup_restoration()
        if self.prov_P0 is not None and self.prov_recog <= c:
            comps.append(("Estimated restoration / dismantling costs (present value)", self.r(self.prov_P0), "Ind AS 116.24(d); Ind AS 37"))
        # deposit
        self._setup_deposit()
        if self.dep_diff_r and self.dep_recog <= c:
            comps.append(("Security deposit — excess of amount paid over fair value (prepaid rent)", self.dep_diff_r,
                          "Ind AS 109 B5.1.1; Ind AS 116.24(b)"))
        for x in inp.other_rou_adjustments:
            comps.append((x.description or "Other adjustment", self.r(D(x.amount)), "Manual adjustment (reason documented)"))
        rou0 = sum((cp[1] for cp in comps), ZERO)
        self.rou_components = comps
        self.rou0 = rou0

        # depreciation end (para 32)
        if inp.ownership_transfers or self.term.purchase_option_rc:
            if inp.useful_life_end is None:
                raise EngineInputError([Issue("USEFUL_LIFE", "Useful life end date is required when a purchase option is reasonably "
                                                             "certain or ownership transfers (Ind AS 116.32).", Severity.ERROR)])
            dep_last = inp.useful_life_end
        else:
            dep_last = self.term.term_end if inp.useful_life_end is None else min(self.term.term_end, inp.useful_life_end)
        self.dep_end = next_day(dep_last)
        return InitialMeasurement(measurement_date=c, rate_pct=self.rate_pct, effective_annual_rate=self.disc.R,
                                  daycount=DAYCOUNT_LABEL[self.policy.daycount],
                                  convention=CONVENTION_LABEL[self.policy.rate_convention],
                                  liability_exact=L0, liability=self.r(L0), pv_lines=pv_lines, excluded=excl,
                                  undiscounted_total=undiscounted, rou_components=comps, rou=rou0,
                                  depreciation_end=dep_last)

    def _initial_cutover(self, lines: list[PaymentLine]) -> InitialMeasurement:
        """Opening-balance migration: continue from given balances at the cut-over date."""
        inp = self.inp
        ob = inp.opening
        T0 = ob.cutover_date
        liab, prepaid, excluded = self._split_lines(lines, T0, False)
        self.liab_lines = liab
        self.excluded_lines = excluded
        cfs = [(l.date, measure_amount(l, self.expedient)) for l in liab]
        if ob.use_implied_rate and cfs:
            R = solve_rate(cfs, D(ob.liability), T0, self.basis)
            self.disc = Discounter(R, self.basis)
            from .rates import nominal_from_effective
            self.rate_pct = nominal_from_effective(R, self.policy.rate_convention)
            self.flags.append(JudgmentFlag("CUTOVER_RATE", "Implied rate on opening balances",
                                           f"Opening liability {self.r(ob.liability)} amortised at the implied rate "
                                           f"{self.rate_pct.quantize(Decimal('0.0001'))}% so that it reconciles to remaining payments. "
                                           f"Compare with the documented IBR {inp.discount_rate_pct}%.", ref("LIAB_SUBSEQ")))
        pv_lines = []
        und = ZERO
        for d, a in cfs:
            df = self.disc.df(d, T0)
            pv_lines.append(PVLine(d, a, self.disc.years(d, T0), df, a * df, "FIXED"))
            und += a
        pv_total = sum((p.present_value for p in pv_lines), ZERO)
        if abs(pv_total - D(ob.liability)) > Decimal("0.5"):
            self.issues.append(Issue("CUTOVER_DIFF", f"Opening liability {self.r(ob.liability)} differs from PV of remaining payments "
                                                     f"{self.r(pv_total)} at {self.rate_pct}% — difference will not amortise to nil.",
                                     Severity.WARNING))
        self.L = D(ob.liability)
        self.L0_r = self.r(self.L)
        self.rou_components = [("Opening ROU cost", self.r(ob.rou_cost), "Opening balance"),
                               ("Less: opening accumulated depreciation", -self.r(ob.rou_acc_dep), "Opening balance"),
                               ("Less: opening accumulated impairment", -self.r(ob.rou_acc_imp), "Opening balance")]
        self.rou0 = self.r(ob.rou_cost) - self.r(ob.rou_acc_dep) - self.r(ob.rou_acc_imp)
        self._setup_restoration()
        self._setup_deposit()
        if inp.ownership_transfers or self.term.purchase_option_rc:
            dep_last = inp.useful_life_end or self.term.term_end
        else:
            dep_last = self.term.term_end if inp.useful_life_end is None else min(self.term.term_end, inp.useful_life_end)
        self.dep_end = next_day(dep_last)
        excl = [ExcludedLine(l.date, D(l.lease_amount), PaymentCategory(l.category).value,
                             "Before cut-over date" if l.date < T0 else l.inclusion_reason, l.description)
                for l in prepaid + excluded]
        return InitialMeasurement(measurement_date=T0, rate_pct=self.rate_pct, effective_annual_rate=self.disc.R,
                                  daycount=DAYCOUNT_LABEL[self.policy.daycount],
                                  convention=CONVENTION_LABEL[self.policy.rate_convention],
                                  liability_exact=self.L, liability=self.r(self.L), pv_lines=pv_lines, excluded=excl,
                                  undiscounted_total=und, rou_components=self.rou_components, rou=self.rou0,
                                  depreciation_end=dep_last)

    # ------------------------------------------------------------------ restoration & deposit set-up
    def _setup_restoration(self):
        rs = self.inp.restoration
        self.prov_P0 = None
        self.prov = ZERO
        self.prov_disc = None
        self.prov_recog = None
        self.prov_settle = None
        self.prov_cost = ZERO
        self.restoration_rows = []
        if rs is None:
            return
        recog = rs.recognition_date or self.c
        self.prov_recog = recog
        self.prov_settle = rs.settlement_date
        self.prov_rate_pct = D(rs.discount_rate_pct)
        self.prov_disc = Discounter(effective_annual_rate(rs.discount_rate_pct, self.policy.rate_convention), self.basis)
        cost = D(rs.estimated_cost)
        if rs.cost_is_current_price and D(rs.inflation_pct) != 0:
            yrs = self.prov_disc.years(rs.settlement_date, recog)
            cost = cost * dpow(ONE + pct(rs.inflation_pct), yrs)
        self.prov_cost = cost
        self.prov_P0 = cost * self.prov_disc.df(rs.settlement_date, recog)

    def _setup_deposit(self):
        dp = self.inp.deposit
        self.dep_amort = ZERO
        self.dep_diff_r = ZERO
        self.dep_recog = None
        self.dep_refund_date = None
        self.dep_refund_amount = ZERO
        self.dep_disc = None
        self.dep_FV = None
        if dp is None:
            return
        recog = max(dp.payment_date, self.c)
        self.dep_recog = recog
        self.dep_refund_date = dp.refund_date
        amount = D(dp.amount)
        refund = amount
        if dp.interest_bearing and D(dp.contractual_rate_pct):
            yrs = Decimal((dp.refund_date - dp.payment_date).days) / Decimal(365)
            refund = amount + amount * pct(dp.contractual_rate_pct) * yrs
        self.dep_refund_amount = refund
        mrate = dp.market_rate_pct if dp.market_rate_pct is not None else dp.contractual_rate_pct
        self.dep_disc = Discounter(effective_annual_rate(mrate, self.policy.rate_convention), self.basis)
        FV = refund * self.dep_disc.df(dp.refund_date, recog)
        if dp.interest_bearing and dp.market_rate_pct is None:
            FV = amount  # at market terms
        self.dep_FV = FV
        diff = self.r(amount) - self.r(FV)
        if not dp.treat_difference_as_prepaid_rent:
            diff = ZERO
            FV = amount
            self.dep_FV = FV
        self.dep_diff_r = diff
        self.dep_cash = self.r(amount)

    # ------------------------------------------------------------------ simulation
    def _simulate(self):
        inp = self.inp
        start = inp.opening.cutover_date if inp.opening else self.c
        self.start = start
        # ROU state
        if inp.opening:
            ob = inp.opening
            self.cost, self.accdep, self.accimp = self.r(ob.rou_cost), self.r(ob.rou_acc_dep), self.r(ob.rou_acc_imp)
        else:
            self.cost, self.accdep, self.accimp = self.rou0, ZERO, ZERO
        self.seg_start = start
        self.seg_nbv = self.nbv
        self.seg_W = self.weight(start, self.dep_end)
        # shadow (no-impairment) path for reversal cap
        self.sh_nbv = self.cost - self.accdep
        self.sh_seg_nbv = self.sh_nbv
        self.term_end = self.term.term_end
        self.active = True
        # FX state
        if self.fx_on:
            r0 = self.fx_rate(start)
            self.fx_cost = self.cost * r0
            self.fx_accdep = self.accdep * r0
            self.fx_accimp = self.accimp * r0
            self.fx_seg_nbv = self.fx_cost - self.fx_accdep - self.fx_accimp
            self.fx_liab_booked = ZERO
            self.fx_rows = []
        else:
            self.fx_rows = []

        # restoration / deposit balances at start
        if self.prov_P0 is not None:
            if self.prov_recog <= start:
                self.prov = self.prov_P0 * self.prov_disc.growth(self.prov_recog, start)
            self.prov_active = self.prov_recog <= start
        if self.dep_FV is not None:
            if self.dep_recog <= start:
                self.dep_amort = self.dep_FV * self.dep_disc.growth(self.dep_recog, start)
            self.dep_active = self.dep_recog <= start

        # events & ticks
        events = sorted([e for e in inp.events if e.effective_date >= start], key=lambda e: e.effective_date)
        for e in inp.events:
            if e.effective_date < start:
                self.issues.append(Issue("EVENT_BEFORE_CUTOVER", f"Event {e.type.value} on {e.effective_date} precedes the cut-over "
                                                                 "date and is ignored.", Severity.WARNING))
        self.events_at = defaultdict(list)
        for e in events:
            self.events_at[e.effective_date].append(e)

        last_candidates = [self.term.term_end, prev_day(self.dep_end)]
        last_candidates += [l.date for l in self.all_lines if l.included or PaymentCategory(l.category) in
                            (PaymentCategory.VARIABLE, PaymentCategory.NON_LEASE)]
        if self.prov_settle:
            last_candidates.append(self.prov_settle)
        if self.dep_refund_date:
            last_candidates.append(self.dep_refund_date)
        last_candidates += [e.effective_date for e in events]
        for e in events:
            if e.modification and e.modification.new_payments:
                last_candidates += [l.date for l in e.modification.new_payments]
            if e.modification and e.modification.new_term_end:
                last_candidates.append(e.modification.new_term_end)
            if e.modification and e.modification.new_useful_life_end:
                last_candidates.append(e.modification.new_useful_life_end)
            if e.reassessment and e.reassessment.new_payments:
                last_candidates += [l.date for l in e.reassessment.new_payments]
            if e.reassessment and e.reassessment.new_term_end:
                last_candidates.append(e.reassessment.new_term_end)
            if e.reassessment and e.reassessment.new_useful_life_end:
                last_candidates.append(e.reassessment.new_useful_life_end)
            if e.restoration_revision and e.restoration_revision.new_settlement_date:
                last_candidates.append(e.restoration_revision.new_settlement_date)
        if inp.schedule_end:
            last_candidates.append(inp.schedule_end)
        horizon = month_end(max(d for d in last_candidates if d is not None))
        self.horizon = horizon
        self.close_points = [next_day(pe) for pe in month_ends_between(start, horizon)]

        # period accumulator
        self.acc = _PeriodAcc()
        self.row_start = start
        self._open_snapshot()

        # initial recognition postings
        if not inp.opening:
            self._post_commencement()
        else:
            self.acc.liab_add = ZERO

        self.pay_open_r = self.r(self.L)
        self.pay_adj_r = ZERO
        self.pay_no = 0
        self.last_t = start
        self.processed_close = set()

        ticks = set(self.close_points) | {start} | set(self.events_at.keys())
        self._lines_by_date = defaultdict(list)
        for l in self.all_lines:
            if l.date >= start:
                self._lines_by_date[l.date].append(l)
        ticks |= set(self._lines_by_date.keys())
        ticks.add(self.dep_end)
        if self.prov_settle and self.prov_settle >= start:
            ticks.add(self.prov_settle)
        if self.prov_recog and self.prov_recog > start:
            ticks.add(self.prov_recog)
        if self.dep_refund_date and self.dep_refund_date >= start:
            ticks.add(self.dep_refund_date)
        if self.dep_recog and self.dep_recog > start:
            ticks.add(self.dep_recog)
        self._dynamic_ticks = ticks
        self.current_t = start
        self._after_pay = False
        while self._dynamic_ticks:
            t = min(self._dynamic_ticks)
            self._dynamic_ticks.discard(t)
            if t > next_day(self.horizon):
                break
            self.current_t = t
            self._accrue(self.last_t, t)
            self.last_t = t
            if t in self.close_points and t not in self.processed_close:
                self._close_period(t)
                self.processed_close.add(t)
            for ev in self.events_at.get(t, []):
                if not ev.apply_after_payments:
                    self._apply_event(ev)
            if self.prov_recog and t == self.prov_recog and t > start and not self.prov_active:
                self._recognise_restoration_later(t)
            if self.dep_recog and t == self.dep_recog and t > start and not self.dep_active:
                self._recognise_deposit_later(t)
            for ln in sorted(self._lines_by_date.get(t, []), key=lambda x: x.line_no):
                self._pay(ln, t)
            for ev in self.events_at.get(t, []):
                if ev.apply_after_payments:
                    self._apply_event(ev)
            if self.dep_refund_date and t == self.dep_refund_date and self.dep_active:
                self._refund_deposit(t)
            if self.prov_settle and t == self.prov_settle and self.prov_active:
                self._settle_restoration(t)
        # close any remaining period (safety)
        for cp in self.close_points:
            if cp not in self.processed_close:
                self._accrue(self.last_t, cp)
                self.last_t = cp
                self._close_period(cp)
                self.processed_close.add(cp)
        # trim trailing rows with no balances and no movements (e.g. after an early end)
        while len(self.rows) > 1 and self._row_is_empty(self.rows[-1]):
            self.rows.pop()
            if self.fx_on and self.fx_rows:
                self.fx_rows.pop()

    @staticmethod
    def _row_is_empty(r: PeriodRow) -> bool:
        vals = (r.liab_open, r.liab_additions, r.interest, r.payments, r.liab_remeasurement, r.liab_modification,
                r.liab_derecognised, r.liab_close, r.rou_open, r.rou_additions, r.depreciation, r.impairment,
                r.rou_remeasurement, r.rou_modification, r.rou_derecognised, r.rou_close, r.gain_loss, r.remeasurement_pl,
                r.variable_expense, r.non_lease_expense, r.cash_outflow, r.prov_open, r.prov_additions, r.prov_unwinding,
                r.prov_revision, r.prov_settled, r.prov_close, r.dep_open, r.dep_additions, r.dep_interest, r.dep_refund,
                r.dep_close)
        return all(v == 0 for v in vals)

    @property
    def nbv(self) -> Decimal:
        return self.cost - self.accdep - self.accimp

    def _open_snapshot(self):
        self.open_liab_r = self.r(self.L) if self.inp.opening else ZERO
        if self.inp.opening is None and self.start == self.c:
            self.open_liab_r = ZERO  # liability is an addition in the first period
        self.open_cost_r = self.r(self.cost) if self.inp.opening else ZERO
        self.open_accdep_r = self.r(self.accdep) if self.inp.opening else ZERO
        self.open_accimp_r = self.r(self.accimp) if self.inp.opening else ZERO
        self.open_prov_r = self.r(self.prov) if (self.prov_P0 is not None and self.prov_recog <= self.start and self.inp.opening) else ZERO
        self.open_dep_r = self.r(self.dep_amort) if (self.dep_FV is not None and self.dep_recog <= self.start and self.inp.opening) else ZERO
        self.open_fx_liab = ZERO
        self.open_fx_cost = ZERO
        self.open_fx_accdep = ZERO
        self.open_fx_accimp = ZERO
        if self.fx_on and self.inp.opening:
            r0 = self.fx_rate(self.start)
            self.open_fx_liab = self.r(self.L * r0)
            self.fx_liab_booked = self.open_fx_liab
            self.open_fx_cost, self.open_fx_accdep, self.open_fx_accimp = (self.r(self.fx_cost), self.r(self.fx_accdep),
                                                                            self.r(self.fx_accimp))

    # ------------------------------------------------------------------ accrual
    def _accrue(self, a: date, b: date):
        if b <= a:
            return
        if self.active and self.L != 0:
            g = self.disc.growth(a, b)
            i = self.L * (g - ONE)
            self.acc.int_parts.append((a, b, self.L, g, i, self.rate_pct))
            self.L += i
            self.acc.interest_exact += i
        # depreciation
        if self.active:
            self._depreciate(a, b)
        if self.prov_P0 is not None and self.prov_active and self.prov != 0:
            self.prov += self.prov * (self.prov_disc.growth(a, b) - ONE)
        if self.dep_FV is not None and self.dep_active and self.dep_amort != 0:
            self.dep_amort += self.dep_amort * (self.dep_disc.growth(a, b) - ONE)

    def _depreciate(self, a: date, b: date):
        de = self.dep_end
        if a >= de or self.seg_W <= 0:
            return
        lo = max(a, self.seg_start)
        hi = min(b, de)
        if hi <= lo:
            return
        if hi == de:
            dep = self.nbv
            sh = self.sh_nbv
            fxd = (self.fx_cost - self.fx_accdep - self.fx_accimp) if self.fx_on else ZERO
        else:
            frac = self.weight(lo, hi) / self.seg_W
            dep = self.seg_nbv * frac
            sh = self.sh_seg_nbv * frac
            fxd = self.fx_seg_nbv * frac if self.fx_on else ZERO
        self.accdep += dep
        self.acc.dep_parts.append((lo, hi, self.seg_nbv, self.weight(lo, hi), self.seg_W, dep, self.seg_start, de))
        self.sh_nbv -= sh
        if self.fx_on:
            self.fx_accdep += fxd

    def _new_segment(self, at: date):
        self.seg_start = at
        self.seg_nbv = self.nbv
        self.sh_seg_nbv = self.sh_nbv
        self.seg_W = self.weight(at, self.dep_end)
        if self.fx_on:
            self.fx_seg_nbv = self.fx_cost - self.fx_accdep - self.fx_accimp

    # ------------------------------------------------------------------ payments
    def _is_liability_payment(self, ln: PaymentLine) -> bool:
        if not ln.included:
            return False
        if ln.date < self.start:
            return False
        if (self.inp.opening is None and ln.date == self.c and self.policy.commencement_payment_paid):
            return False  # paid at commencement — part of ROU cost (24(b))
        return True

    def _pay(self, ln: PaymentLine, t: date):
        if not self.active:
            return
        if self._is_liability_payment(ln):
            amt = measure_amount(ln, self.expedient)
            self.L -= amt
            self.acc.payments += amt
            self.acc.cash += amt
            self.acc.pay_dates.append((t, amt))
            if not self.expedient and D(ln.non_lease_amount):
                self.acc.nonlease += D(ln.non_lease_amount)
                self.acc.cash += D(ln.non_lease_amount)
            if self.fx_on:
                self._fx_pending_pay += self.r(amt * self.fx_rate(t))
            self.pay_no += 1
            closing_r = self.r(self.L)
            opening_r = self.pay_open_r
            interest_r = closing_r - opening_r + self.r(amt) - self.pay_adj_r
            self.payment_rows.append(PaymentRow(self.pay_no, t, opening_r, interest_r, self.r(amt), self.pay_adj_r,
                                                self.r(amt) - interest_r, closing_r, ln.description))
            self.pay_open_r = closing_r
            self.pay_adj_r = ZERO
            return
        if ln.included and ln.date >= self.start:
            # paid at commencement — already in ROU cost; record the cash outflow only
            self.acc.cash += measure_amount(ln, self.expedient)
            if not self.expedient and D(ln.non_lease_amount):
                self.acc.nonlease += D(ln.non_lease_amount)
                self.acc.cash += D(ln.non_lease_amount)
            return
        cat = PaymentCategory(ln.category)
        if cat == PaymentCategory.VARIABLE:
            amt = D(ln.lease_amount) + D(ln.non_lease_amount)
            self.acc.variable += amt
            self.acc.cash += amt
        elif cat == PaymentCategory.NON_LEASE and not ln.included:
            amt = D(ln.lease_amount) + D(ln.non_lease_amount)
            self.acc.nonlease += amt
            self.acc.cash += amt

    def _post(self, p: Posting, fc_lines=None):
        """Record a posting; for foreign-currency leases translate to functional currency."""
        if self.fx_on:
            if fc_lines is None:
                rate = self.fx_rate(p.date)
                fc_lines = [(role, self.r(dr * rate), self.r(cr * rate)) for role, dr, cr in p.lines]
            fc_lines = _balanced(fc_lines, "FX_LOSS_GAIN")
            p = Posting(p.date, p.event, p.narration + " [functional currency]", fc_lines, p.period_end, p.ref)
        self.postings.append(p)

    def _add_tick(self, d: date):
        if d is not None and d > self.current_t:
            self._dynamic_ticks.add(d)

    # ------------------------------------------------------------------ deposits & restoration lifecycle
    def _recognise_restoration_later(self, t: date):
        self.prov_active = True
        self.prov = self.prov_P0
        add_r = self.r(self.prov_P0)
        self.acc.prov_add += add_r
        before_cost_r = self.r(self.cost)
        self.cost += add_r
        self.sh_nbv += add_r
        if self.fx_on:
            self.fx_cost += add_r * self.fx_rate(t)
        self.acc.rou_remeasure += self.r(self.cost) - before_cost_r
        self._new_segment(t)
        self._post(Posting(t, "RESTORATION", "Restoration obligation recognised (Ind AS 116.25)",
                                     [("ROU_ASSET", add_r, ZERO), ("RESTORATION_PROVISION", ZERO, add_r)]))

    def _recognise_deposit_later(self, t: date):
        self.dep_active = True
        self.dep_amort = self.dep_FV
        self.acc.dep_add += self.r(self.dep_FV)
        self.acc.cash += ZERO
        lines = [("SECURITY_DEPOSIT", self.dep_cash, ZERO), ("LESSOR_PAYABLE", ZERO, self.dep_cash)]
        self._post(Posting(t, "DEPOSIT_PAID", "Security deposit paid", lines))
        if self.dep_diff_r:
            before_cost_r = self.r(self.cost)
            self.cost += self.dep_diff_r
            self.sh_nbv += self.dep_diff_r
            if self.fx_on:
                self.fx_cost += self.dep_diff_r * self.fx_rate(t)
            self.acc.rou_remeasure += self.r(self.cost) - before_cost_r
            self._new_segment(t)
            self._post(Posting(t, "DEPOSIT_FV", "Security deposit fair-value adjustment treated as prepaid rent",
                                         [("ROU_ASSET", self.dep_diff_r, ZERO), ("SECURITY_DEPOSIT", ZERO, self.dep_diff_r)]))

    def _refund_deposit(self, t: date):
        refund = self.dep_refund_amount
        residual = self.dep_amort - refund
        self.acc.dep_refund += self.r(refund)
        if abs(residual) > Decimal("0.005"):
            self.acc.dep_catchup += -residual
        self.dep_amort = ZERO
        self.dep_active = False
        self._post(Posting(t, "DEPOSIT_REFUND", "Security deposit refunded by lessor",
                                     [("BANK", self.r(refund), ZERO), ("SECURITY_DEPOSIT", ZERO, self.r(refund))]))

    def _settle_restoration(self, t: date):
        amt = self.prov
        self.acc.prov_settle += self.r(amt)
        self.prov = ZERO
        self.prov_active = False
        self._post(Posting(t, "RESTORATION_SETTLED", "Restoration obligation settled (estimate; true-up actual cost to P&L)",
                                     [("RESTORATION_PROVISION", self.r(amt), ZERO), ("BANK", ZERO, self.r(amt))]))

    # ------------------------------------------------------------------ commencement postings
    def _post_commencement(self):
        c = self.c
        L0r = self.r(self.L)
        self.acc.liab_add = L0r
        self.acc.rou_add = self.rou0
        lines = [("ROU_ASSET", L0r, ZERO), ("LEASE_LIABILITY", ZERO, L0r)]
        self._post(Posting(c, "COMMENCEMENT", "Initial recognition of ROU asset and lease liability (Ind AS 116.22–26)", lines))
        for label, amt, refr in self.rou_components[1:]:
            if amt == 0:
                continue
            if label.startswith("Lease payments made before"):
                lines = [("ROU_ASSET", amt, ZERO), ("PREPAID_LEASE_PAYMENTS", ZERO, amt)]
                narr = "Advance lease payments made before commencement transferred to ROU (24(b))"
                ev = "PREPAYMENT"
            elif label.startswith("Lease payment made at commencement"):
                lines = [("ROU_ASSET", amt, ZERO), ("LESSOR_PAYABLE", ZERO, amt)]
                narr = "Lease payment made at commencement included in ROU cost (24(b))"
                ev = "PREPAYMENT"
            elif label.startswith("Less: lease incentives"):
                lines = [("LEASE_INCENTIVE_RECEIVED", -amt, ZERO), ("ROU_ASSET", ZERO, -amt)]
                narr = "Lease incentives received deducted from ROU (24(b))"
                ev = "INCENTIVE"
            elif label.startswith("Initial direct costs"):
                lines = [("ROU_ASSET", amt, ZERO), ("IDC_CLEARING", ZERO, amt)]
                narr = "Initial direct costs capitalised (24(c))"
                ev = "IDC"
            elif label.startswith("Estimated restoration"):
                lines = [("ROU_ASSET", amt, ZERO), ("RESTORATION_PROVISION", ZERO, amt)]
                narr = "Restoration obligation recognised (24(d), Ind AS 37)"
                ev = "RESTORATION"
                self.acc.prov_add += amt
            elif label.startswith("Security deposit"):
                lines = [("ROU_ASSET", amt, ZERO), ("SECURITY_DEPOSIT", ZERO, amt)]
                narr = "Security deposit remeasured to fair value; difference treated as prepaid rent (Ind AS 109)"
                ev = "DEPOSIT_FV"
            else:
                if amt > 0:
                    lines = [("ROU_ASSET", amt, ZERO), ("OTHER_ROU_ADJUSTMENT", ZERO, amt)]
                else:
                    lines = [("OTHER_ROU_ADJUSTMENT", -amt, ZERO), ("ROU_ASSET", ZERO, -amt)]
                narr = label
                ev = "ROU_ADJUSTMENT"
            self._post(Posting(c, ev, narr, lines))
        if self.dep_FV is not None and self.dep_recog <= c:
            self.acc.dep_add += self.dep_cash - self.dep_diff_r
            self._post(Posting(self.inp.deposit.payment_date, "DEPOSIT_PAID", "Security deposit paid to lessor",
                                            [("SECURITY_DEPOSIT", self.dep_cash, ZERO), ("BANK", ZERO, self.dep_cash)]))
            self.dep_active = True
            self.dep_amort = self.dep_FV
        if self.prov_P0 is not None and self.prov_recog <= c:
            self.prov_active = True
            self.prov = self.prov_P0
        if self.fx_on:
            r0 = self.fx_rate(c)
            self._fx_pending_add = self.r(L0r * r0)
            self._fx_pending_rou_add = self.r(self.rou0 * r0)

    # ------------------------------------------------------------------ period close
    def _close_period(self, t: date):
        pe = prev_day(t)
        acc = self.acc
        row = PeriodRow(period_start=self.row_start, period_end=pe)
        row.rate_pct = self.rate_pct
        # --- liability
        row.liab_open = self.open_liab_r
        row.liab_additions = acc.liab_add
        row.payments = self.r(acc.payments)
        row.liab_remeasurement = acc.liab_remeasure
        row.liab_modification = acc.liab_modif
        row.liab_derecognised = acc.liab_derecog
        if self.policy.rounding_method == "INTEREST_TRUEUP":
            interest_r = self.r(acc.interest_exact)
            close_r = row.liab_open + row.liab_additions + interest_r - row.payments + row.liab_remeasurement + \
                row.liab_modification - row.liab_derecognised
            no_future = not any(self._is_liability_payment(l) and l.date >= t for l in self.liab_lines)
            if ((not self.active) or (self.r(self.L) == 0 and no_future)) and close_r != 0:
                row.rounding_trueup = -close_r
                interest_r += row.rounding_trueup
                close_r = ZERO
                if abs(row.rounding_trueup) > self.policy.truep_tolerance:
                    self.issues.append(Issue("TRUEUP", f"Rounding true-up {row.rounding_trueup} exceeds tolerance.", Severity.WARNING))
            row.interest = interest_r
            row.liab_close = close_r
        else:
            row.liab_close = self.r(self.L) if self.active else ZERO
            row.interest = (row.liab_close - row.liab_open - row.liab_additions + row.payments - row.liab_remeasurement
                            - row.liab_modification + row.liab_derecognised)
        # current / non-current split (state as at t)
        cur, noncur = self._current_split(t, row.liab_close)
        row.liab_current, row.liab_noncurrent = cur, noncur
        row.maturity = self._maturity(t, pe)
        # --- ROU (component rounding)
        cost_r, accdep_r, accimp_r = self.r(self.cost), self.r(self.accdep), self.r(self.accimp)
        row.rou_open = self.open_cost_r - self.open_accdep_r - self.open_accimp_r
        row.rou_additions = acc.rou_add
        row.rou_remeasurement = acc.rou_remeasure
        row.rou_modification = acc.rou_modif
        row.rou_derecognised = acc.rou_derecog
        row.impairment = acc.impairment
        row.depreciation = (accdep_r - self.open_accdep_r) - acc.ev_accdep
        row.rou_cost_close, row.rou_accdep_close, row.rou_accimp_close = cost_r, accdep_r, accimp_r
        row.rou_close = cost_r - accdep_r - accimp_r
        # consistency: open + add - dep - imp + rem + mod - derecog == close
        chk = (row.rou_open + row.rou_additions - row.depreciation - row.impairment + row.rou_remeasurement
               + row.rou_modification - row.rou_derecognised - row.rou_close)
        if chk != 0:
            self.issues.append(Issue("ROU_RECON", f"ROU roll-forward difference {chk} in period ending {pe} — shown as exception.",
                                     Severity.WARNING))
        # --- P&L / cash
        row.gain_loss = acc.gain_loss
        row.remeasurement_pl = acc.remeasure_pl
        row.variable_expense = self.r(acc.variable)
        row.non_lease_expense = self.r(acc.nonlease)
        row.cash_outflow = self.r(acc.cash)
        # --- restoration
        if self.prov_P0 is not None:
            row.prov_open = self.open_prov_r
            row.prov_additions = acc.prov_add
            row.prov_revision = acc.prov_rev
            row.prov_settled = acc.prov_settle
            row.prov_close = self.r(self.prov) if self.prov_active else ZERO
            row.prov_unwinding = row.prov_close - row.prov_open - row.prov_additions - row.prov_revision + row.prov_settled
        # --- deposit
        if self.dep_FV is not None:
            row.dep_open = self.open_dep_r
            row.dep_additions = acc.dep_add
            row.dep_refund = acc.dep_refund
            row.dep_close = self.r(self.dep_amort) if self.dep_active else ZERO
            row.dep_interest = row.dep_close - row.dep_open - row.dep_additions + row.dep_refund
        row.status = "ACTIVE" if self.active else "TERMINATED"
        row.detail = {
            "interest": [{"from": a, "to": b, "balance": q(bal, 6), "factor": q(g, 12), "interest": q(i, 6), "rate_pct": rp}
                         for a, b, bal, g, i, rp in acc.int_parts],
            "depreciation": [{"from": lo, "to": hi, "segment_nbv": q(nbv, 6), "weight": w, "segment_weight": W,
                              "depreciation": q(dep, 6), "segment_start": ss, "depreciation_end": prev_day(de)}
                             for lo, hi, nbv, w, W, dep, ss, de in acc.dep_parts],
            "method": self.policy.depreciation_method,
        }
        self.rows.append(row)
        # --- periodic postings
        self._post_period(row, pe)
        # --- FX row
        if self.fx_on:
            self._fx_close(row, t, pe)
        # --- next period
        self.open_liab_r = row.liab_close
        self.open_cost_r, self.open_accdep_r, self.open_accimp_r = cost_r, accdep_r, accimp_r
        self.open_prov_r = row.prov_close
        self.open_dep_r = row.dep_close
        self.acc = _PeriodAcc()
        self.row_start = t

    def _t12(self, t: date) -> date:
        pe = prev_day(t)
        return next_day(month_end(add_months(pe, 12))) if pe == month_end(pe) else next_day(add_months(pe, 12))

    def _current_split(self, t: date, liab_close_r: Decimal) -> tuple[Decimal, Decimal]:
        if not self.active or liab_close_r == 0:
            return ZERO, ZERO
        t12 = self._t12(t)
        fut = [(l.date, measure_amount(l, self.expedient)) for l in self.liab_lines
               if self._is_liability_payment(l) and t <= l.date]
        if self.policy.current_split_method == "PV_12M":
            cur = sum((a * self.disc.df(d, t) for d, a in fut if d < t12), ZERO)
            cur_r = min(max(self.r(cur), ZERO), liab_close_r)
            return cur_r, liab_close_r - cur_r
        E12 = self.L * self.disc.growth(t, t12)
        for d, a in fut:
            if d < t12:
                E12 -= a * self.disc.growth(d, t12)
        non_r = self.r(E12) if E12 > 0 else ZERO
        non_r = min(non_r, liab_close_r)
        return liab_close_r - non_r, non_r

    def _maturity(self, t: date, pe: date) -> dict:
        buckets = self.policy.maturity_buckets
        keys = [f"{a}-{b}" for a, b in zip((0,) + tuple(buckets[:-1]), buckets)] + [f">{buckets[-1]}"]
        out = {k: ZERO for k in keys}
        if not self.active:
            return out
        limits = [next_day(month_end(add_months(pe, 12 * b))) for b in buckets]
        for l in self.liab_lines:
            if not self._is_liability_payment(l) or l.date < t:
                continue
            amt = measure_amount(l, self.expedient)
            for k, lim in zip(keys, limits):
                if l.date < lim:
                    out[k] += amt
                    break
            else:
                out[keys[-1]] += amt
        return {k: self.r(v) for k, v in out.items()}

    def _post_period(self, row: PeriodRow, pe: date):
        cur = self.inp.currency
        if self.fx_on:
            return  # functional-currency postings generated in _fx_close
        if row.interest:
            self.postings.append(Posting(pe, "INTEREST", f"Interest on lease liability for the period ended {_fmt(pe)} (36(a))",
                                         _dc("FINANCE_COST_LEASE", "LEASE_LIABILITY", row.interest), pe))
        if row.payments:
            dates = ", ".join(_fmt(d) for d, _ in self.acc.pay_dates[:6])
            self.postings.append(Posting(pe, "PAYMENT", f"Lease payments ({dates}) adjusted against lease liability (36(b))",
                                         _dc("LEASE_LIABILITY", "LESSOR_PAYABLE", row.payments), pe))
        if row.depreciation:
            self.postings.append(Posting(pe, "DEPRECIATION", f"Depreciation on ROU asset for the period ended {_fmt(pe)} (31)",
                                         _dc("DEPRECIATION_ROU", "ROU_ACC_DEP", row.depreciation), pe))
        if row.variable_expense:
            self.postings.append(Posting(pe, "VARIABLE", "Variable lease payments not included in the liability (38(b))",
                                         _dc("VARIABLE_LEASE_EXPENSE", "LESSOR_PAYABLE", row.variable_expense), pe))
        if row.non_lease_expense:
            self.postings.append(Posting(pe, "NON_LEASE", "Non-lease component (maintenance/services) expensed",
                                         _dc("NON_LEASE_EXPENSE", "LESSOR_PAYABLE", row.non_lease_expense), pe))
        if row.prov_unwinding:
            self.postings.append(Posting(pe, "UNWINDING", "Unwinding of discount on restoration provision (Ind AS 37.60)",
                                         _dc("FINANCE_COST_PROVISION", "RESTORATION_PROVISION", row.prov_unwinding), pe))
        if row.dep_interest:
            self.postings.append(Posting(pe, "DEPOSIT_INTEREST", "Interest income on security deposit — effective interest method (Ind AS 109)",
                                         _dc("SECURITY_DEPOSIT", "INTEREST_INCOME_DEPOSIT", row.dep_interest), pe))

    # ------------------------------------------------------------------ FX layer
    def _fx_close(self, row: PeriodRow, t: date, pe: date):
        acc_ps = row.period_start
        avg = self.fx_avg(acc_ps, pe)
        clos = self.fx_rate(pe)
        open_fc = self.open_fx_liab
        add_fc = self._fx_pending_add
        interest_fc = self.r(row.interest * avg)
        pay_fc = self._fx_pending_pay
        adj_fc = self._fx_pending_adj
        derecog_fc = self._fx_pending_derecog
        close_fc = self.r(row.liab_close * clos)
        fx_diff = close_fc - (open_fc + add_fc + interest_fc - pay_fc + adj_fc - derecog_fc)
        cost_fc_r, accdep_fc_r, accimp_fc_r = self.r(self.fx_cost), self.r(self.fx_accdep), self.r(self.fx_accimp)
        dep_fc = (accdep_fc_r - self.open_fx_accdep) - self._fx_pending_ev_accdep
        rou_close_fc = cost_fc_r - accdep_fc_r - accimp_fc_r
        fxrow = {"period_start": acc_ps, "period_end": pe, "avg_rate": avg, "closing_rate": clos,
                 "liab_open": open_fc, "liab_additions": add_fc, "interest": interest_fc, "payments": pay_fc,
                 "adjustments": adj_fc, "derecognised": derecog_fc, "fx_difference": fx_diff, "liab_close": close_fc,
                 "rou_open": self.open_fx_cost - self.open_fx_accdep - self.open_fx_accimp,
                 "rou_additions": self._fx_pending_rou_add, "rou_adjustments": self._fx_pending_rou_adj,
                 "depreciation": dep_fc, "rou_close": rou_close_fc, "gain_loss": self._fx_pending_gain,
                 "rou_cost_close": cost_fc_r, "rou_accdep_close": accdep_fc_r}
        self.fx_rows.append(fxrow)
        # postings in functional currency
        if interest_fc:
            self.postings.append(Posting(pe, "INTEREST", f"Interest on lease liability (at average rate {avg:.4f})",
                                         _dc("FINANCE_COST_LEASE", "LEASE_LIABILITY", interest_fc), pe))
        if pay_fc:
            self.postings.append(Posting(pe, "PAYMENT", "Lease payments (at spot rates on payment dates)",
                                         _dc("LEASE_LIABILITY", "LESSOR_PAYABLE", pay_fc), pe))
        if dep_fc:
            self.postings.append(Posting(pe, "DEPRECIATION", "Depreciation on ROU asset (historical rate — non-monetary item)",
                                         _dc("DEPRECIATION_ROU", "ROU_ACC_DEP", dep_fc), pe))
        if fx_diff:
            if fx_diff > 0:
                self.postings.append(Posting(pe, "FX", f"Exchange loss on retranslation of lease liability at closing rate {clos:.4f} (Ind AS 21.28)",
                                             _dc("FX_LOSS_GAIN", "LEASE_LIABILITY", fx_diff), pe))
            else:
                self.postings.append(Posting(pe, "FX", f"Exchange gain on retranslation of lease liability at closing rate {clos:.4f} (Ind AS 21.28)",
                                             _dc("LEASE_LIABILITY", "FX_LOSS_GAIN", -fx_diff), pe))
        for kind, role_dr, role_cr, amt in (("VARIABLE", "VARIABLE_LEASE_EXPENSE", "LESSOR_PAYABLE", row.variable_expense),
                                            ("NON_LEASE", "NON_LEASE_EXPENSE", "LESSOR_PAYABLE", row.non_lease_expense),
                                            ("UNWINDING", "FINANCE_COST_PROVISION", "RESTORATION_PROVISION", row.prov_unwinding),
                                            ("DEPOSIT_INTEREST", "SECURITY_DEPOSIT", "INTEREST_INCOME_DEPOSIT", row.dep_interest)):
            if amt:
                self.postings.append(Posting(pe, kind, f"{kind.replace('_', ' ').title()} (at average rate)",
                                             _dc(role_dr, role_cr, self.r(amt * avg)), pe))
        self.open_fx_liab = close_fc
        self.open_fx_cost, self.open_fx_accdep, self.open_fx_accimp = cost_fc_r, accdep_fc_r, accimp_fc_r
        self._fx_reset_pending()

    def _fx_reset_pending(self):
        self._fx_pending_add = ZERO
        self._fx_pending_pay = ZERO
        self._fx_pending_adj = ZERO
        self._fx_pending_derecog = ZERO
        self._fx_pending_ev_accdep = ZERO
        self._fx_pending_rou_add = ZERO
        self._fx_pending_rou_adj = ZERO
        self._fx_pending_gain = ZERO

    # ------------------------------------------------------------------ events
    def _is_future(self, l: PaymentLine, e: date) -> bool:
        """Payment still outstanding at the event (payments dated e are outstanding unless the event is processed after them)."""
        return l.date > e if self._after_pay else l.date >= e

    def _apply_event(self, ev: LeaseEvent):
        self._after_pay = bool(ev.apply_after_payments)
        if not self.active and ev.type != EventType.RESTORATION_REVISION:
            self.issues.append(Issue("EVENT_AFTER_END", f"{ev.type.value} on {ev.effective_date} ignored — lease already terminated.",
                                     Severity.WARNING))
            return
        if ev.type == EventType.MODIFICATION:
            self._modification(ev)
        elif ev.type == EventType.REASSESSMENT:
            self._reassessment(ev)
        elif ev.type == EventType.TERMINATION:
            self._termination(ev)
        elif ev.type == EventType.IMPAIRMENT:
            self._impairment(ev)
        elif ev.type == EventType.RESTORATION_REVISION:
            self._restoration_revision(ev)
        elif ev.type == EventType.ROU_DERECOGNITION:
            self._rou_derecognition(ev)

    def _replace_future_lines(self, e: date, new_lines: list[PaymentLine], term_end: date, purchase_rc: bool | None):
        """Replace payment lines dated on/after e by new lines (classified against the revised term)."""
        synthetic = copy.copy(self.term)
        synthetic.term_end = term_end
        if purchase_rc is not None:
            synthetic.purchase_option_rc = purchase_rc
        synthetic.termination_reflected = any(PaymentCategory(l.category) == PaymentCategory.TERMINATION_PENALTY for l in new_lines)
        base_no = max([l.line_no for l in self.all_lines] + [0])
        new = []
        for i, l in enumerate(new_lines, start=1):
            nl = copy.copy(l)
            nl.line_no = base_no + i
            nl.source = nl.source or "EVENT"
            new.append(nl)
        new = classify_payments(new, synthetic, self.expedient)
        kept = [l for l in self.all_lines if not self._is_future(l, e)]
        new = [l for l in new if self._is_future(l, e)]
        self.all_lines = kept + new
        self.liab_lines = [l for l in self.liab_lines if not self._is_future(l, e)] + [l for l in new if l.included]
        self.excluded_lines = [l for l in self.all_lines if not l.included]
        # refresh tick map for outstanding dates
        for d in list(self._lines_by_date.keys()):
            if d > e or (d == e and not self._after_pay):
                del self._lines_by_date[d]
        for l in new:
            self._lines_by_date[l.date].append(l)
            self._add_tick(l.date)
        return new

    def _pv_future(self, disc: Discounter, e: date, lines: list[PaymentLine]) -> Decimal:
        return sum((measure_amount(l, self.expedient) * disc.df(l.date, e) for l in lines
                    if l.included and self._is_future(l, e)), ZERO)

    def _set_dep_end(self, term_end: date, purchase_rc: bool, useful_life_end: date | None):
        ul = useful_life_end or self.inp.useful_life_end
        if self.inp.ownership_transfers or purchase_rc:
            last = ul or term_end
        else:
            last = term_end if ul is None else min(term_end, ul)
        self.dep_end = next_day(last)
        self._add_tick(self.dep_end)
        if month_end(last) > self.horizon:
            self._extend_horizon(month_end(last))

    def _extend_horizon(self, new_h: date):
        extra = [next_day(pe) for pe in month_ends_between(next_day(self.horizon), new_h)]
        self.close_points.extend(extra)
        for x in extra:
            self._add_tick(x)
        self.horizon = new_h

    def _rou_adjust(self, amount_r: Decimal, e: date, kind: str) -> tuple[Decimal, Decimal]:
        """Apply a remeasurement adjustment to ROU cost; excess reduction beyond NBV to P&L (para 39).
        Returns (applied_to_rou, to_pl)."""
        nbv_r = self.r(self.nbv)
        to_pl = ZERO
        applied = amount_r
        if amount_r < 0 and -amount_r > nbv_r:
            applied = -nbv_r
            to_pl = -(amount_r - applied)  # positive = gain
        before_cost_r = self.r(self.cost)
        self.cost += applied
        self.sh_nbv += applied
        if self.fx_on:
            fxa = self.r(applied * self.fx_rate(e))
            self.fx_cost += fxa
            self._fx_pending_rou_adj += fxa
        delta_cost_r = self.r(self.cost) - before_cost_r
        if kind == "MOD":
            self.acc.rou_modif += delta_cost_r
        else:
            self.acc.rou_remeasure += delta_cost_r
        return applied, to_pl

    def _liab_adjust(self, new_L: Decimal, kind: str, e: date) -> Decimal:
        before_r = self.r(self.L)
        self.L = new_L
        delta_r = self.r(self.L) - before_r
        if kind == "MOD":
            self.acc.liab_modif += delta_r
        else:
            self.acc.liab_remeasure += delta_r
        self.pay_adj_r += delta_r
        if self.fx_on:
            self._fx_pending_adj += self.r(delta_r * self.fx_rate(e))
        return delta_r

    def _modification(self, ev: LeaseEvent):
        m = ev.modification
        e = ev.effective_date
        steps: list[tuple[str, Decimal, str]] = []
        flags: list[JudgmentFlag] = [JudgmentFlag("MODIFICATION", "Lease modification — reviewer attention",
                                                  "Modification accounting involves judgment on scope, consideration and revised rate.",
                                                  ref("MOD_ACCOUNTING"))]
        L_pre = self.L
        rou_pre_r = self.r(self.nbv)
        rate_before = self.rate_pct
        term_before = self.term_end
        if m.additional_rou and m.commensurate_standalone_price and not m.scope_decrease_fraction and not m.new_term_end:
            res = EventResult("MODIFICATION", e, ev.ref, m.description or "Separate lease (para 44)",
                              [("Separate lease — original lease unchanged", ZERO,
                                "Adds right to use additional asset(s) at a price commensurate with stand-alone price (44). "
                                "Recognise the new component as a new lease from its commencement date.")],
                              self.r(L_pre), self.r(L_pre), rou_pre_r, rou_pre_r, ZERO, rate_before, rate_before,
                              term_before, term_before, separate_lease=True, flags=flags, reference=ref("MOD_SEPARATE"))
            self.event_results.append(res)
            return
        if m.revised_rate_pct is None:
            raise EngineInputError([Issue("MOD_RATE", "Revised discount rate is required at the modification effective date (45(c)).",
                                          Severity.ERROR)])
        new_term_end = m.new_term_end or self.term_end
        new_disc = Discounter(effective_annual_rate(m.revised_rate_pct, self.policy.rate_convention), self.basis)
        gain = ZERO
        # ---- decrease in scope (partial termination) — para 46(a)
        f = D(m.scope_decrease_fraction)
        term_reduced = new_term_end < self.term_end
        if f > 0 or term_reduced:
            old_dep_end = self.dep_end
            if term_reduced:
                new_dep_end_candidate = next_day(new_term_end) if not (self.inp.ownership_transfers or self.term.purchase_option_rc) \
                    else old_dep_end
                w_old = self.weight(e, old_dep_end)
                w_new = self.weight(e, min(new_dep_end_candidate, old_dep_end))
                term_ratio = (w_new / w_old) if w_old else ONE
            else:
                term_ratio = ONE
            retained = (ONE - f) * term_ratio
            # liability retained measured at the ORIGINAL rate on the ORIGINAL payments within the revised term
            orig_future = [l for l in self.liab_lines if l.included and self._is_future(l, e)]
            if term_reduced:
                orig_future_kept = [l for l in orig_future if (l.period_start or l.date) <= new_term_end]
            else:
                orig_future_kept = orig_future
            L_ret = (ONE - f) * self._pv_future(self.disc, e, orig_future_kept)
            # ROU proportionate reduction
            cost_b, accdep_b, accimp_b = self.cost, self.accdep, self.accimp
            red = ONE - retained
            cost_b_r, accdep_b_r, accimp_b_r = self.r(cost_b), self.r(accdep_b), self.r(accimp_b)
            self.cost = cost_b * retained
            self.accdep = accdep_b * retained
            self.accimp = accimp_b * retained
            self.sh_nbv = self.sh_nbv * retained
            d_cost_r = self.r(self.cost) - cost_b_r
            d_accdep_r = self.r(self.accdep) - accdep_b_r
            d_accimp_r = self.r(self.accimp) - accimp_b_r
            nbv_reduction_r = -(d_cost_r - d_accdep_r - d_accimp_r)
            self.acc.rou_derecog += nbv_reduction_r
            self.acc.ev_accdep += d_accdep_r
            self.acc.ev_accimp += d_accimp_r
            if self.fx_on:
                fx_red_cost = self.fx_cost * red
                fx_red_accdep = self.fx_accdep * red
                fx_red_accimp = self.fx_accimp * red
                self.fx_cost -= fx_red_cost
                self.fx_accdep -= fx_red_accdep
                self.fx_accimp -= fx_red_accimp
                self._fx_pending_ev_accdep += -self.r(fx_red_accdep)
            # liability reduction
            before_r = self.r(self.L)
            self.L = L_ret
            liab_red_r = before_r - self.r(self.L)
            self.acc.liab_modif -= liab_red_r
            self.pay_adj_r -= liab_red_r
            gain = liab_red_r - nbv_reduction_r
            self.acc.gain_loss += gain
            if self.fx_on:
                rate_e = self.fx_rate(e)
                self._fx_pending_adj -= self.r(liab_red_r * rate_e)
                fx_nbv_red = self.r(fx_red_cost - fx_red_accdep - fx_red_accimp)
                self._fx_pending_gain += self.r(liab_red_r * rate_e) - fx_nbv_red
            steps += [
                ("Decrease in scope — area/units reduction", f * 100, "% of the underlying asset returned"),
                ("Decrease in scope — remaining-term retained ratio", term_ratio, "remaining ROU life retained ÷ remaining ROU life before"),
                ("Proportion of ROU retained", retained, "(1 − area reduction) × term ratio"),
                ("Lease liability immediately before modification", self.r(L_pre), "carrying amount incl. accrued interest"),
                ("Liability for retained scope at ORIGINAL rate", self.r(L_ret), f"PV of original payments for retained scope at {rate_before}%"),
                ("Reduction in lease liability", liab_red_r, "Dr Lease liability"),
                ("Reduction in ROU carrying amount", nbv_reduction_r, "Cr ROU (net of accumulated depreciation)"),
                ("Gain / (loss) on partial termination", gain, "recognised in profit or loss — Ind AS 116.46(a)"),
            ]
            fc_lines = None
            if self.fx_on:
                fc_lines = _balanced([("LEASE_LIABILITY", self.r(liab_red_r * rate_e), ZERO),
                                      ("ROU_ACC_DEP", self.r(fx_red_accdep), ZERO), ("ROU_ACC_IMP", self.r(fx_red_accimp), ZERO),
                                      ("ROU_ASSET", ZERO, self.r(fx_red_cost))], "GAIN_LOSS_MODIFICATION")
            self._post(Posting(e, "PARTIAL_TERMINATION", "Partial termination of lease — decrease in scope (Ind AS 116.46(a))",
                               _balanced([("LEASE_LIABILITY", liab_red_r, ZERO), ("ROU_ACC_DEP", -d_accdep_r, ZERO),
                                          ("ROU_ACC_IMP", -d_accimp_r, ZERO), ("ROU_ASSET", ZERO, -d_cost_r)],
                                         "GAIN_LOSS_MODIFICATION"), ref=ev.ref), fc_lines)
        # ---- remeasurement of remaining liability at revised rate — para 45(c), 46(b)
        new_lines = m.new_payments
        if not new_lines:
            new_lines = [copy.copy(l) for l in self.all_lines if self._is_future(l, e) and
                         (l.period_start or l.date) <= new_term_end]
            if f > 0:
                for l in new_lines:
                    l.lease_amount = q(D(l.lease_amount) * (ONE - f), self.dp)
                    l.non_lease_amount = q(D(l.non_lease_amount) * (ONE - f), self.dp)
        purchase_rc = m.purchase_option_rc if m.purchase_option_rc is not None else self.term.purchase_option_rc
        new = self._replace_future_lines(e, new_lines, new_term_end, purchase_rc)
        L_before_remeasure = self.L
        L_post = self._pv_future(new_disc, e, new)
        self.disc = new_disc
        self.rate_pct = D(m.revised_rate_pct)
        delta_r = self._liab_adjust(L_post, "MOD", e)
        applied, to_pl = self._rou_adjust(delta_r, e, "MOD")
        if to_pl:
            self.acc.remeasure_pl += to_pl
        steps += [
            ("Liability before remeasurement", self.r(L_before_remeasure), ""),
            ("Revised discount rate", D(m.revised_rate_pct), "% p.a. at the effective date — Ind AS 116.45(c)"),
            ("Remeasured liability — PV of revised payments", self.r(L_post), "revised payments over the revised term"),
            ("Adjustment to lease liability", delta_r, "Dr/(Cr) ROU — Ind AS 116.46(b)"),
            ("Adjustment to ROU asset", applied, ""),
        ]
        if to_pl:
            steps.append(("Excess reduction recognised in profit or loss", to_pl, "ROU reduced to nil — Ind AS 116.39"))
        if delta_r:
            lines = [("ROU_ASSET", applied, ZERO), ("LEASE_LIABILITY", ZERO, delta_r)] if delta_r > 0 else \
                    [("LEASE_LIABILITY", -delta_r, ZERO), ("ROU_ASSET", ZERO, -applied)]
            if to_pl:
                lines.append(("GAIN_LOSS_MODIFICATION", ZERO, to_pl))
            self._post(Posting(e, "MODIFICATION", "Remeasurement of lease liability on modification (Ind AS 116.45–46(b))",
                                         lines, ref=ev.ref))
        # term / depreciation
        self.term_end = new_term_end
        self._set_dep_end(new_term_end, purchase_rc, m.new_useful_life_end)
        self._new_segment(e)
        self.event_results.append(EventResult("MODIFICATION", e, ev.ref, m.description or "Lease modification", steps,
                                              self.r(L_pre), self.r(self.L), rou_pre_r, self.r(self.nbv), gain + to_pl,
                                              rate_before, self.rate_pct, term_before, self.term_end, False, flags,
                                              ref("MOD_REMEASURE")))

    def _reassessment(self, ev: LeaseEvent):
        ra = ev.reassessment
        e = ev.effective_date
        kind = ReassessmentKind(ra.kind)
        L_pre = self.L
        rou_pre_r = self.r(self.nbv)
        rate_before = self.rate_pct
        term_before = self.term_end
        revised = kind in (ReassessmentKind.LEASE_TERM, ReassessmentKind.PURCHASE_OPTION, ReassessmentKind.FLOATING_RATE)
        if revised:
            if ra.revised_rate_pct is None:
                raise EngineInputError([Issue("REASSESS_RATE", f"{kind.value}: a revised discount rate is required (Ind AS 116.40–41, 43).",
                                              Severity.ERROR)])
            disc = Discounter(effective_annual_rate(ra.revised_rate_pct, self.policy.rate_convention), self.basis)
            new_rate = D(ra.revised_rate_pct)
            basis_txt = "Revised discount rate (Ind AS 116.40–41)" if kind != ReassessmentKind.FLOATING_RATE else \
                "Revised rate reflecting change in floating interest rate (Ind AS 116.43)"
        else:
            if ra.revised_rate_pct is not None and D(ra.revised_rate_pct) != self.rate_pct:
                self.issues.append(Issue("REASSESS_RATE_IGNORED", f"{kind.value}: unchanged discount rate required (Ind AS 116.42–43); "
                                                                  "revised rate supplied was ignored.", Severity.WARNING))
            disc = self.disc
            new_rate = self.rate_pct
            basis_txt = "Unchanged discount rate (Ind AS 116.42–43)"
        new_term_end = ra.new_term_end or self.term_end
        purchase_rc = ra.purchase_option_rc if ra.purchase_option_rc is not None else self.term.purchase_option_rc
        new_lines = ra.new_payments or [copy.copy(l) for l in self.all_lines if self._is_future(l, e)]
        new = self._replace_future_lines(e, new_lines, new_term_end, purchase_rc)
        L_post = self._pv_future(disc, e, new)
        self.disc = disc
        self.rate_pct = new_rate
        delta_r = self._liab_adjust(L_post, "REM", e)
        applied, to_pl = self._rou_adjust(delta_r, e, "REM")
        if to_pl:
            self.acc.remeasure_pl += to_pl
        steps = [
            ("Lease liability immediately before reassessment", self.r(L_pre), "carrying amount incl. accrued interest"),
            ("Discount rate applied", new_rate, basis_txt),
            ("Remeasured liability — PV of revised lease payments", self.r(L_post), ""),
            ("Adjustment to lease liability", delta_r, "Ind AS 116.39"),
            ("Adjustment to ROU asset", applied, ""),
        ]
        if to_pl:
            steps.append(("Excess reduction recognised in profit or loss", to_pl, "ROU reduced to nil — Ind AS 116.39"))
        if delta_r:
            lines = [("ROU_ASSET", applied, ZERO), ("LEASE_LIABILITY", ZERO, delta_r)] if delta_r > 0 else \
                    [("LEASE_LIABILITY", -delta_r, ZERO), ("ROU_ASSET", ZERO, -applied)]
            if to_pl:
                lines.append(("GAIN_REMEASUREMENT", ZERO, to_pl))
            self._post(Posting(e, "REASSESSMENT", f"Remeasurement of lease liability — {kind.value.replace('_', ' ').lower()} "
                                                            "reassessment (Ind AS 116.39–43)", lines, ref=ev.ref))
        self.term_end = new_term_end
        if kind == ReassessmentKind.PURCHASE_OPTION:
            self.term.purchase_option_rc = bool(purchase_rc)
        self._set_dep_end(new_term_end, purchase_rc, ra.new_useful_life_end)
        self._new_segment(e)
        flags = [JudgmentFlag("REASSESSMENT", f"Reassessment — {kind.value.replace('_', ' ').title()}",
                              "Confirm the triggering event and the discount-rate basis.", ref("REMEASURE_ROU"))]
        self.event_results.append(EventResult("REASSESSMENT", e, ev.ref, ra.description or f"Reassessment: {kind.value}", steps,
                                              self.r(L_pre), self.r(self.L), rou_pre_r, self.r(self.nbv), to_pl,
                                              rate_before, self.rate_pct, term_before, self.term_end, False, flags,
                                              ref("REVISED_RATE") if revised else ref("UNCHANGED_RATE")))

    def _termination(self, ev: LeaseEvent):
        tm = ev.termination
        e = ev.effective_date
        L_pre_r = self.r(self.L)
        cost_r, accdep_r, accimp_r = self.r(self.cost), self.r(self.accdep), self.r(self.accimp)
        nbv_r = cost_r - accdep_r - accimp_r
        penalty = self.r(D(tm.penalty))
        gain = L_pre_r - nbv_r - penalty
        lines = [("LEASE_LIABILITY", L_pre_r, ZERO), ("ROU_ACC_DEP", accdep_r, ZERO), ("ROU_ACC_IMP", accimp_r, ZERO),
                 ("ROU_ASSET", ZERO, cost_r)]
        if penalty:
            lines.append(("LESSOR_PAYABLE", ZERO, penalty))
        fc_lines = None
        if self.fx_on:
            rate_t = self.fx_rate(e)
            fc_lines = [("LEASE_LIABILITY", self.r(L_pre_r * rate_t), ZERO), ("ROU_ACC_DEP", self.r(self.fx_accdep), ZERO),
                        ("ROU_ACC_IMP", self.r(self.fx_accimp), ZERO), ("ROU_ASSET", ZERO, self.r(self.fx_cost))]
            if penalty:
                fc_lines.append(("LESSOR_PAYABLE", ZERO, self.r(penalty * rate_t)))
            fc_lines = _balanced(fc_lines, "GAIN_LOSS_TERMINATION")
        self._post(Posting(e, "TERMINATION", "Full termination of lease — derecognition of ROU asset and lease liability",
                           _balanced(lines, "GAIN_LOSS_TERMINATION"), ref=ev.ref), fc_lines)
        self.acc.liab_derecog += L_pre_r
        self.acc.rou_derecog += nbv_r
        self.acc.ev_accdep += -accdep_r
        self.acc.ev_accimp += -accimp_r
        self.acc.gain_loss += gain
        self.acc.cash += penalty
        self.pay_adj_r -= L_pre_r
        if self.fx_on:
            rate_e = self.fx_rate(e)
            fx_nbv = self.r(self.fx_cost - self.fx_accdep - self.fx_accimp)
            self._fx_pending_derecog += self.r(L_pre_r * rate_e)
            self._fx_pending_ev_accdep += -self.r(self.fx_accdep)
            self._fx_pending_gain += self.r(L_pre_r * rate_e) - fx_nbv - self.r(penalty * rate_e)
            self.fx_cost = self.fx_accdep = self.fx_accimp = ZERO
        self.L = ZERO
        self.cost = self.accdep = self.accimp = ZERO
        self.sh_nbv = ZERO
        self.active = False
        # cancel outstanding payments
        for d in list(self._lines_by_date.keys()):
            if d > e or (d == e and not self._after_pay):
                del self._lines_by_date[d]
        self.liab_lines = [l for l in self.liab_lines if not self._is_future(l, e)]
        self.all_lines = [l for l in self.all_lines if not self._is_future(l, e)]
        # deposit refund brought forward (Ind AS 109 B5.4.6 catch-up)
        if self.dep_FV is not None and self.dep_active and self.dep_refund_date and self.dep_refund_date > e:
            catch = self.dep_refund_amount - self.dep_amort
            self.acc.dep_catchup += catch
            self.dep_amort = self.dep_refund_amount
            self.dep_refund_date = e
            self._post(Posting(e, "DEPOSIT_CATCHUP", "Security deposit refund brought forward — catch-up adjustment (Ind AS 109 B5.4.6)",
                                         _dc("SECURITY_DEPOSIT", "INTEREST_INCOME_DEPOSIT", self.r(catch)), ref=ev.ref))
            # refund handled when tick e processed (same tick) — process immediately
            self._refund_deposit(e)
        steps = [("Lease liability derecognised", L_pre_r, ""), ("ROU cost derecognised", cost_r, ""),
                 ("Accumulated depreciation derecognised", accdep_r, ""), ("Accumulated impairment derecognised", accimp_r, ""),
                 ("ROU carrying amount derecognised", nbv_r, ""), ("Termination penalty payable", penalty, ""),
                 ("Gain / (loss) on termination", gain, "Liability − ROU carrying amount − penalty")]
        self.event_results.append(EventResult("TERMINATION", e, ev.ref, tm.description or "Full termination", steps,
                                              L_pre_r, ZERO, nbv_r, ZERO, gain, self.rate_pct, self.rate_pct, self.term_end, e,
                                              False, [JudgmentFlag("TERMINATION", "Lease termination",
                                                                   "Confirm termination date, penalty and restoration settlement.",
                                                                   ref("MOD_ACCOUNTING"))], ref("MOD_ACCOUNTING")))
        self.term_end = prev_day(e) if e > self.c else e

    def _impairment(self, ev: LeaseEvent):
        im = ev.impairment
        e = ev.effective_date
        nbv_r = self.r(self.nbv)
        if im.impairment_amount is not None:
            loss = self.r(D(im.impairment_amount))
        elif im.recoverable_amount is not None:
            loss = nbv_r - self.r(D(im.recoverable_amount))
            if loss < 0:
                loss = ZERO  # recoverable above carrying amount: no loss (reversal must be entered explicitly)
        else:
            loss = ZERO
        steps = [("Carrying amount before test", nbv_r, "")]
        if im.recoverable_amount is not None:
            steps.append(("Recoverable amount", self.r(D(im.recoverable_amount)), "higher of FVLCD and value in use — Ind AS 36"))
        if loss < 0:
            cap = self.r(self.sh_nbv) - nbv_r
            if -loss > cap:
                steps.append(("Reversal capped at carrying amount had no impairment been recognised", cap, "Ind AS 36.117"))
                loss = -cap
        if loss > nbv_r:
            loss = nbv_r
        before_r = self.r(self.accimp)
        self.accimp += loss
        d_r = self.r(self.accimp) - before_r
        self.acc.impairment += d_r
        if self.fx_on:
            self.fx_accimp += self.r(loss * self.fx_rate(e))
        if loss > 0:
            self._post(Posting(e, "IMPAIRMENT", "Impairment loss on ROU asset (Ind AS 116.33; Ind AS 36)",
                                         _dc("IMPAIRMENT_LOSS_ROU", "ROU_ACC_IMP", d_r), ref=ev.ref))
        elif loss < 0:
            self._post(Posting(e, "IMPAIRMENT_REVERSAL", "Reversal of impairment loss on ROU asset (Ind AS 36.117)",
                                         _dc("ROU_ACC_IMP", "IMPAIRMENT_REVERSAL_ROU", -d_r), ref=ev.ref))
        steps += [("Impairment loss / (reversal)", d_r, ""), ("Carrying amount after", self.r(self.nbv), ""),
                  ("Depreciation revised prospectively over remaining life", ZERO, f"to {_fmt(prev_day(self.dep_end))}")]
        self._new_segment(e)
        self.event_results.append(EventResult("IMPAIRMENT", e, ev.ref, im.rationale or "Impairment", steps,
                                              self.r(self.L), self.r(self.L), nbv_r, self.r(self.nbv), -d_r, self.rate_pct,
                                              self.rate_pct, self.term_end, self.term_end, False,
                                              [JudgmentFlag("IMPAIRMENT", "Impairment assessment",
                                                            f"CGU {im.cgu or 'n/a'}; recoverable amount and indicators require review.",
                                                            ref("IMPAIRMENT"))], ref("IMPAIRMENT")))

    def _restoration_revision(self, ev: LeaseEvent):
        rv = ev.restoration_revision
        e = ev.effective_date
        if self.prov_P0 is None:
            raise EngineInputError([Issue("NO_RESTORATION", "No restoration obligation exists for this lease.", Severity.ERROR)])
        prev_r = self.r(self.prov)
        if rv.new_discount_rate_pct is not None:
            self.prov_disc = Discounter(effective_annual_rate(rv.new_discount_rate_pct, self.policy.rate_convention), self.basis)
            self.prov_rate_pct = D(rv.new_discount_rate_pct)
        if rv.new_settlement_date is not None:
            self.prov_settle = rv.new_settlement_date
            self._add_tick(self.prov_settle)
            if month_end(self.prov_settle) > self.horizon:
                self._extend_horizon(month_end(self.prov_settle))
        if rv.new_estimated_cost is not None:
            self.prov_cost = D(rv.new_estimated_cost)
        new_P = self.prov_cost * self.prov_disc.df(self.prov_settle, e)
        self.prov = new_P
        delta_r = self.r(new_P) - prev_r
        self.acc.prov_rev += delta_r
        applied, to_pl = (ZERO, ZERO)
        if self.active:
            applied, to_pl = self._rou_adjust(delta_r, e, "REM")
            self._new_segment(e)
        else:
            to_pl = -delta_r
        if to_pl:
            self.acc.remeasure_pl += to_pl
        lines = []
        if delta_r > 0:
            lines = [("ROU_ASSET", applied, ZERO)] + ([("RESTORATION_REVISION_PL", -to_pl, ZERO)] if to_pl else []) + \
                    [("RESTORATION_PROVISION", ZERO, delta_r)]
        elif delta_r < 0:
            lines = [("RESTORATION_PROVISION", -delta_r, ZERO), ("ROU_ASSET", ZERO, -applied)] + \
                    ([("RESTORATION_REVISION_PL", ZERO, to_pl)] if to_pl else [])
        if lines:
            self._post(Posting(e, "RESTORATION_REVISION", "Revision of restoration obligation (Ind AS 16 App. A; Ind AS 37)",
                                         _balanced(lines, "RESTORATION_REVISION_PL"), ref=ev.ref))
        steps = [("Provision before revision", prev_r, ""), ("Revised provision (PV)", self.r(new_P), ""),
                 ("Change adjusted to ROU asset", applied, ""), ("Recognised in profit or loss", to_pl, "")]
        self.event_results.append(EventResult("RESTORATION_REVISION", e, ev.ref, rv.description or "Restoration estimate revised",
                                              steps, self.r(self.L), self.r(self.L), self.r(self.nbv) - applied, self.r(self.nbv),
                                              to_pl, self.rate_pct, self.rate_pct, self.term_end, self.term_end, False,
                                              [JudgmentFlag("RESTORATION_REVISION", "Restoration estimate revision",
                                                            "Management estimate — obtain support for cost, timing and rate.",
                                                            ref("DECOM_CHANGES"))], ref("DECOM_CHANGES")))

    def _rou_derecognition(self, ev: LeaseEvent):
        rd = ev.rou_derecognition
        e = ev.effective_date
        f = D(rd.fraction)
        nbv_before = self.r(self.nbv)
        cost_b_r, accdep_b_r, accimp_b_r = self.r(self.cost), self.r(self.accdep), self.r(self.accimp)
        keep = ONE - f
        if self.fx_on:
            fx_red = (self.fx_cost * f, self.fx_accdep * f, self.fx_accimp * f)
            self.fx_cost -= fx_red[0]
            self.fx_accdep -= fx_red[1]
            self.fx_accimp -= fx_red[2]
            self._fx_pending_ev_accdep += -self.r(fx_red[1])
        self.cost *= keep
        self.accdep *= keep
        self.accimp *= keep
        self.sh_nbv *= keep
        d_cost_r = self.r(self.cost) - cost_b_r
        d_accdep_r = self.r(self.accdep) - accdep_b_r
        d_accimp_r = self.r(self.accimp) - accimp_b_r
        red_r = -(d_cost_r - d_accdep_r - d_accimp_r)
        self.acc.rou_derecog += red_r
        self.acc.ev_accdep += d_accdep_r
        self.acc.ev_accimp += d_accimp_r
        self._post(Posting(e, "ROU_DERECOGNITION", rd.description or "Derecognition of ROU asset (portion subleased — finance sublease, B58)",
                           _balanced([("ROU_ACC_DEP", -d_accdep_r, ZERO), ("ROU_ACC_IMP", -d_accimp_r, ZERO),
                                      (rd.clearing_role, red_r, ZERO), ("ROU_ASSET", ZERO, -d_cost_r)], rd.clearing_role), ref=ev.ref))
        self._new_segment(e)
        self.event_results.append(EventResult("ROU_DERECOGNITION", e, ev.ref, rd.description or "ROU derecognition",
                                              [("Portion derecognised", f, ""), ("ROU carrying amount derecognised", red_r,
                                                                                 "transferred to sublease accounting")],
                                              self.r(self.L), self.r(self.L), nbv_before, self.r(self.nbv), ZERO, self.rate_pct,
                                              self.rate_pct, self.term_end, self.term_end, False, [], ref("SUBLEASE")))

    # ------------------------------------------------------------------ checks & totals
    def _final_checks(self):
        for row in self.rows:
            lhs = (row.liab_open + row.liab_additions + row.interest - row.payments + row.liab_remeasurement
                   + row.liab_modification - row.liab_derecognised)
            if lhs != row.liab_close:
                self.issues.append(Issue("LIAB_RECON", f"Liability roll-forward difference {lhs - row.liab_close} for "
                                                       f"{row.period_end}.", Severity.WARNING))
        if self.rows:
            last = self.rows[-1]
            if self.active and last.liab_close != 0:
                self.issues.append(Issue("LIAB_NOT_NIL", f"Lease liability does not close to nil ({last.liab_close}) at the end of "
                                                         "the schedule — check payments beyond the horizon.", Severity.WARNING))
        for p in self.postings:
            dr = sum((l[1] for l in p.lines), ZERO)
            cr = sum((l[2] for l in p.lines), ZERO)
            if dr != cr:
                self.issues.append(Issue("JE_UNBALANCED", f"Journal {p.event} {p.date}: debits {dr} ≠ credits {cr}.", Severity.ERROR))
        self.deposit_summary = None
        if self.dep_FV is not None:
            dp = self.inp.deposit
            self.deposit_summary = {"amount_paid": self.r(dp.amount), "payment_date": dp.payment_date,
                                    "refund_date": dp.refund_date, "refund_amount": self.r(self.dep_refund_amount),
                                    "market_rate_pct": dp.market_rate_pct, "initial_fair_value": self.r(self.dep_FV),
                                    "difference_prepaid_rent": self.dep_diff_r,
                                    "treatment": ("Difference treated as additional lease payment (prepaid rent) and added to ROU"
                                                  if dp.treat_difference_as_prepaid_rent else "Carried at amount paid"),
                                    "reference": ref("DEPOSIT")}
        self.restoration_summary = None
        if self.prov_P0 is not None:
            rs = self.inp.restoration
            self.restoration_summary = {"estimated_cost_at_settlement": self.r(self.prov_cost), "settlement_date": self.prov_settle,
                                        "discount_rate_pct": self.prov_rate_pct, "initial_pv": self.r(self.prov_P0),
                                        "recognition_date": self.prov_recog, "reference": ref("RESTORATION_ROU")}

    def _totals(self) -> dict:
        rows = self.rows
        return {
            "total_interest": sum((r.interest for r in rows), ZERO),
            "total_payments": sum((r.payments for r in rows), ZERO),
            "total_depreciation": sum((r.depreciation for r in rows), ZERO),
            "total_impairment": sum((r.impairment for r in rows), ZERO),
            "total_gain_loss": sum((r.gain_loss + r.remeasurement_pl for r in rows), ZERO),
            "final_liability": rows[-1].liab_close if rows else ZERO,
            "final_rou": rows[-1].rou_close if rows else ZERO,
            "initial_liability": self.L0_r,
            "initial_rou": self.rou0,
        }


def _dc(dr_role: str, cr_role: str, amount: Decimal) -> list[tuple[str, Decimal, Decimal]]:
    if amount >= 0:
        return [(dr_role, amount, ZERO), (cr_role, ZERO, amount)]
    return [(cr_role, -amount, ZERO), (dr_role, ZERO, -amount)]


def _balanced(lines: list[tuple[str, Decimal, Decimal]], balancing_role: str) -> list[tuple[str, Decimal, Decimal]]:
    """Normalise negative amounts, drop zeros and add a balancing gain/loss line."""
    out = []
    for role, dr, cr in lines:
        if dr < 0:
            cr, dr = cr - dr, ZERO
        if cr < 0:
            dr, cr = dr - cr, ZERO
        if dr == 0 and cr == 0:
            continue
        out.append((role, dr, cr))
    diff = sum((l[1] for l in out), ZERO) - sum((l[2] for l in out), ZERO)
    if diff > 0:
        out.append((balancing_role, ZERO, diff))      # gain
    elif diff < 0:
        out.append((balancing_role, -diff, ZERO))     # loss
    return out


def calculate_lessee(inp: LesseeLeaseInput) -> LesseeResult:
    sim = LesseeSimulator(inp)
    if inp.fx is not None:
        sim._fx_reset_pending()
    return sim.run()
