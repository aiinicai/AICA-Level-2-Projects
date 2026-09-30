"""Lessor accounting (Ind AS 116.61–97, B58) — logically separate from the lessee engine.

Scope
-----
* Classification (paras 61–66): indicators 63(a)–(e) and 64(a)–(c), with the PV test and the term test shown as
  evidence. The "substantially all" / "major part" benchmarks are entity policy (the standard sets no bright
  lines) and the conclusion is always a judgment that can be overridden with a documented rationale. Where the
  interest rate implicit in the lease cannot be determined (no unguaranteed residual value entered), the PV test is
  concluded on the undiscounted lease payments when these fall below the benchmark — their present value at any
  positive rate is lower still. Anything that cannot be concluded blocks the calculation; nothing is assumed.
* Lease payments (para 70): fixed / in-substance fixed payments less incentives payable, index- or rate-linked
  payments, residual value guarantees, purchase-option price if reasonably certain and termination penalties where
  the lease term reflects termination. Variable payments not linked to an index or rate are income when earned and
  are disclosed separately (paras 81, 90). A lessor always separates non-lease components (para 17) — they are
  revenue under Ind AS 115.
* Finance leases (paras 67–80): net investment = PV of lease payments not yet received + PV of the unguaranteed
  residual value at the rate implicit in the lease (initial direct costs enter through the rate, para 69); finance
  income at a constant periodic rate (paras 75–76); manufacturer / dealer revenue, cost of sale and selling profit
  (paras 71–74); reduction of the unguaranteed residual value (para 77); loss allowance under Ind AS 109 (para 77);
  modifications (paras 79–80).
* Operating leases (paras 81–88): straight-line income over the lease term (equal-monthly or daily basis — entity
  policy); initial direct costs added to the carrying amount of the asset and expensed on the same basis (para 83);
  modifications accounted for as a new lease from the effective date, carrying forward accrued / deferred lease
  income (para 87).
* Refundable security deposits received: financial liability initially at fair value (Ind AS 109.5.1.1); the excess
  received over fair value is a lease payment received in advance; unwinding is a finance cost (effective interest).
* Maturity analyses (paras 94, 97) and the reconciliation of undiscounted lease payments to the net investment
  (para 94) are produced at any reporting date from the stored result — see ``position_at``.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Optional

from .calendar_utils import (add_months, month_end, month_ends_between, month_start, month_weight, months_between_frac,
                             next_day, parse_date, prev_day)
from .decimal_utils import D, ZERO, engine_context, fmt_money, q
from .models import Issue, JudgmentFlag, PaymentCategory, PaymentLine, Policy, Posting, Severity, TermResult
from .rates import DayCount, Discounter, RateConvention, TimeBasis, effective_annual_rate, nominal_from_effective, present_value, solve_rate
from .references import ref

LESSOR_ENGINE_VERSION = "2.0.0"
TINY = Decimal("0.005")
MOD_NATURES = ("OPERATING_MODIFICATION", "SEPARATE_LEASE", "FINANCE_TO_OPERATING", "FINANCE_REMEASURE")


class LessorInputError(Exception):
    """Inputs are incomplete or contradictory — the calculation is blocked (never guessed)."""

    def __init__(self, issues: list[Issue]):
        super().__init__("; ".join(i.message for i in issues))
        self.issues = issues


# --------------------------------------------------------------------------- inputs
@dataclass
class LessorDepositInput:
    """Refundable security deposit RECEIVED from the lessee (a financial liability of the lessor)."""

    amount: Decimal
    receipt_date: date
    refund_date: date
    interest_bearing: bool = False
    contractual_rate_pct: Decimal = ZERO        # simple annual interest payable at refund, if interest-bearing
    market_rate_pct: Optional[Decimal] = None   # rate for fair value (Ind AS 109) — required when interest-free
    treat_difference_as_lease_payment: bool = True
    description: str = "Refundable security deposit received"


@dataclass
class LessorEvent:
    kind: str                                   # MODIFICATION | TERMINATION | UGR_REVISION | ECL
    effective_date: date
    ref: str = ""
    description: str = ""
    nature: str = ""                            # MODIFICATION: one of MOD_NATURES
    new_payments: Optional[list[PaymentLine]] = None   # replaces lease payments on / after the effective date
    new_term_end: Optional[date] = None
    new_unguaranteed_residual: Optional[Decimal] = None
    penalty: Decimal = ZERO                     # TERMINATION: amount receivable from the lessee
    asset_value_returned: Optional[Decimal] = None     # TERMINATION of a finance lease: asset recognised at this amount
    loss_allowance: Optional[Decimal] = None    # ECL: cumulative loss allowance at the effective date


@dataclass
class LessorLeaseInput:
    lease_id: str
    commencement: date
    term_end: date
    payments: list[PaymentLine]                  # lease payments receivable (incl. variable / non-lease lines)
    fair_value: Decimal = ZERO                   # fair value of the underlying asset at inception
    carrying_amount: Decimal = ZERO              # lessor's carrying amount of the asset (derecognised on a finance lease)
    economic_life_months: Optional[int] = None
    unguaranteed_residual: Decimal = ZERO
    residual_date: Optional[date] = None
    lessor_idc: Decimal = ZERO
    implicit_rate_pct: Optional[Decimal] = None  # if known; otherwise solved
    transfers_ownership: bool = False            # 63(a)
    bargain_purchase_option: bool = False        # 63(b)
    specialised_asset: bool = False              # 63(e)
    lessee_bears_cancellation_losses: bool = False  # 64(a)
    residual_fv_gains_to_lessee: bool = False    # 64(b)
    bargain_renewal: bool = False                # 64(c)
    manufacturer_dealer: bool = False
    substantially_all_pct: Decimal = Decimal("90")   # entity policy benchmark (not in the standard)
    major_part_pct: Decimal = Decimal("75")          # entity policy benchmark (not in the standard)
    classification_override: Optional[str] = None     # FINANCE | OPERATING (with rationale)
    override_rationale: str = ""
    asset_depreciation_per_month: Decimal = ZERO      # kept for compatibility (depreciation stays in the asset register)
    policy: Policy = field(default_factory=Policy)
    market_rate_pct: Optional[Decimal] = None         # manufacturer / dealer with artificially low rates (para 73)
    deposit: Optional[LessorDepositInput] = None
    events: list[LessorEvent] = field(default_factory=list)
    term: Optional[TermResult] = None                 # lease-term determination (options); default = contract term
    ni_role: str = "NET_INVESTMENT_LEASE"             # GL role of the net investment (subleases use their own role)
    currency: str = "INR"
    description: str = ""


# --------------------------------------------------------------------------- result
@dataclass
class LessorResult:
    lease_id: str
    classification: str                          # at commencement
    indicators: list[dict]
    implicit_rate_pct: Optional[Decimal]
    pv_ratio_pct: Optional[Decimal]
    term_ratio_pct: Optional[Decimal]
    net_investment: Decimal = ZERO
    gross_investment: Decimal = ZERO
    unearned_finance_income: Decimal = ZERO
    selling_profit: Decimal = ZERO               # manufacturer / dealer: revenue less cost of sale (paras 71-74)
    derecognition_gain: Decimal = ZERO           # other lessors: fair value (+ IDC) less carrying amount (Ind AS 16.68, 71)
    rows: list[dict] = field(default_factory=list)
    postings: list[Posting] = field(default_factory=list)
    maturity: list[dict] = field(default_factory=list)      # at commencement (compatibility; use position_at for any date)
    flags: list[JudgmentFlag] = field(default_factory=list)
    explanation: list[str] = field(default_factory=list)
    rate_source: str = ""
    suggested_classification: str = ""
    undiscounted_ratio_pct: Optional[Decimal] = None
    revenue: Decimal = ZERO
    cost_of_sale: Decimal = ZERO
    pv_unguaranteed_residual: Decimal = ZERO
    receivable_at_commencement: Decimal = ZERO
    payments: list[PaymentLine] = field(default_factory=list)
    pv_lines: list[dict] = field(default_factory=list)
    events: list[dict] = field(default_factory=list)
    segments: list[dict] = field(default_factory=list)
    deposit: Optional[dict] = None
    idc: dict = field(default_factory=dict)
    issues: list[Issue] = field(default_factory=list)
    totals: dict = field(default_factory=dict)
    term: Optional[TermResult] = None
    rate_basis: dict = field(default_factory=dict)
    classification_final: str = ""
    income_method: str = ""
    engine_version: str = LESSOR_ENGINE_VERSION


# --------------------------------------------------------------------------- helpers
def _fmt(d: date) -> str:
    return d.strftime("%d-%b-%Y")


def _weight(method: str, a: date, b: date) -> Decimal:
    """Time weight of [a, b): days (DAILY) or calendar months pro-rated by days (MONTHLY_EQUAL)."""
    if b <= a:
        return ZERO
    if method == "DAILY":
        return Decimal((b - a).days)
    return month_weight(a, b)


def _dc(dr_role: str, cr_role: str, amount: Decimal) -> list[tuple[str, Decimal, Decimal]]:
    """Two-line entry; a negative amount swaps the sides so every line stays positive."""
    if amount >= 0:
        return [(dr_role, amount, ZERO), (cr_role, ZERO, amount)]
    return [(cr_role, -amount, ZERO), (dr_role, ZERO, -amount)]


def _default_term(c: date, term_end: date) -> TermResult:
    return TermResult(commencement=c, contract_end=term_end, noncancellable_end=term_end, term_end=term_end,
                      max_possible_end=term_end, term_days=(next_day(term_end) - c).days,
                      term_months=months_between_frac(c, next_day(term_end)), purchase_option_rc=False,
                      explanation=[f"Lease term {_fmt(c)} to {_fmt(term_end)} (contractual term)."])


def classify_lessor_payments(lines: list[PaymentLine], term: TermResult) -> list[PaymentLine]:
    """Set ``included`` / ``inclusion_reason`` for a lessor (para 70) and return the lines sorted by date."""
    term_end = term.term_end
    for ln in lines:
        cat = PaymentCategory(ln.category)
        if ln.include_override is not None:
            ln.included = bool(ln.include_override)
            ln.inclusion_reason = f"User override: {ln.override_reason or 'reason not stated'}"
            continue
        # a line belongs to the term by the period it pays for; an undated arrears payment due on the day after the
        # term end (e.g. annual rent in arrears) still relates to the last period of the term
        within = (ln.period_start or ln.date) <= term_end or (ln.period_start is None and ln.date <= next_day(term_end))
        if cat == PaymentCategory.VARIABLE:
            ln.included = False
            ln.inclusion_reason = ("Variable lease payment not depending on an index or rate — recognised as income when earned "
                                   "and disclosed separately (Ind AS 116.70, 81, 90).")
        elif cat == PaymentCategory.NON_LEASE:
            ln.included = False
            ln.inclusion_reason = ("Non-lease component (services / CAM) — a lessor always separates non-lease components "
                                   "(Ind AS 116.17); revenue under Ind AS 115.")
        elif cat == PaymentCategory.PURCHASE_OPTION:
            ln.included = term.purchase_option_rc
            ln.inclusion_reason = ("Purchase option reasonably certain to be exercised by the lessee (70(d))." if ln.included
                                   else "Purchase option not reasonably certain — excluded (70(d)).")
        elif cat == PaymentCategory.TERMINATION_PENALTY:
            ln.included = term.termination_reflected and ln.date <= next_day(term_end)
            ln.inclusion_reason = ("Lease term reflects the lessee's termination option — penalty included (70(e))." if ln.included
                                   else "Lease term does not reflect termination — penalty excluded (70(e)).")
        elif cat == PaymentCategory.RVG:
            ln.included = True
            ln.inclusion_reason = ("Residual value guarantee provided by the lessee, a party related to the lessee or a "
                                   "financially capable third party (70(c)).")
        elif cat in (PaymentCategory.INDEX_LINKED, PaymentCategory.RATE_LINKED):
            ln.included = within
            ln.inclusion_reason = ("Index / rate-linked payment measured using the index or rate at commencement (70(b))."
                                   if within else "Falls outside the lease term — excluded.")
        elif cat == PaymentCategory.INCENTIVE:
            ln.included = within
            ln.inclusion_reason = "Lease incentive payable to the lessee — reduces the lease payments (70(a))."
        else:
            ln.included = within
            if within:
                ln.inclusion_reason = ("In-substance fixed payment (B42)." if cat == PaymentCategory.IN_SUBSTANCE_FIXED
                                       else "Fixed payment within the lease term (70(a)).")
            else:
                ln.inclusion_reason = "Relates to an optional period not included in the lease term — excluded."
    return sorted(lines, key=lambda x: (x.date, x.line_no))


def _split(lines: list[PaymentLine]) -> tuple[list, list, list]:
    """(included lease payments, variable income lines, non-lease lines) as (date, amount, line) tuples."""
    incl, var, nl = [], [], []
    for ln in lines:
        cat = PaymentCategory(ln.category)
        if ln.included:
            incl.append((ln.date, D(ln.lease_amount), ln))
        elif cat == PaymentCategory.VARIABLE:
            if D(ln.lease_amount):
                var.append((ln.period_end or ln.date, D(ln.lease_amount), ln))
        if cat == PaymentCategory.NON_LEASE and not ln.included:
            amt = D(ln.lease_amount) + D(ln.non_lease_amount)
            if amt:
                nl.append((ln.date, amt, ln))
        elif D(ln.non_lease_amount) and cat != PaymentCategory.VARIABLE:
            nl.append((ln.date, D(ln.non_lease_amount), ln))
    return incl, var, nl


def _maturity(lines: list[tuple[date, Decimal]], as_of: date, dp: int = 2) -> list[dict]:
    """Undiscounted lease payments to be received — each of the first five years and a total thereafter (94 / 97)."""
    buckets = []
    for y in range(1, 6):
        lo, hi = add_months(as_of, 12 * (y - 1)), add_months(as_of, 12 * y)
        buckets.append({"bucket": f"Year {y}", "amount": q(sum((a for d, a in lines if lo < d <= hi), ZERO), dp)})
    later = add_months(as_of, 60)
    buckets.append({"bucket": "Later than five years", "amount": q(sum((a for d, a in lines if d > later), ZERO), dp)})
    return buckets


# --------------------------------------------------------------------------- classification
@engine_context
def classify_lessor(inp: LessorLeaseInput, lines: list[PaymentLine] | None = None, term: TermResult | None = None) -> dict:
    """Classification evidence and conclusion (paras 61–66). Returns a dict; raises nothing (issues are returned)."""
    c = inp.commencement
    term = term or inp.term or _default_term(c, inp.term_end)
    if lines is None:
        lines = classify_lessor_payments([PaymentLine(**{k: getattr(p, k) for k in p.__dataclass_fields__}) for p in inp.payments], term)
    incl, _, _ = _split(lines)
    issues: list[Issue] = []
    expl: list[str] = []
    fv = D(inp.fair_value)
    idc = D(inp.lessor_idc)
    ugr = D(inp.unguaranteed_residual)
    rdate = inp.residual_date or next_day(term.term_end)
    basis = TimeBasis(c, inp.policy.daycount)
    conv = inp.policy.rate_convention
    cfs = [(max(d, c), a) for d, a, _ in incl]
    total_lp = sum((a for _, a in cfs), ZERO)

    def solve_implicit() -> Optional[Decimal]:
        if fv <= 0:
            return None
        target = fv + (ZERO if inp.manufacturer_dealer else idc)
        allcf = cfs + ([(rdate, ugr)] if ugr else [])
        if sum((a for _, a in allcf), ZERO) <= target:
            return None
        try:
            return nominal_from_effective(solve_rate(allcf, target, c, basis), conv)
        except ValueError:
            return None

    rate_pct: Optional[Decimal] = None
    source = ""
    if inp.implicit_rate_pct not in (None, ""):
        rate_pct, source = D(inp.implicit_rate_pct), "given"
    elif inp.manufacturer_dealer and inp.market_rate_pct not in (None, ""):
        rate_pct, source = D(inp.market_rate_pct), "market rate (manufacturer / dealer, para 73)"
        implicit = solve_implicit()
        if implicit is not None and rate_pct < implicit:
            issues.append(Issue("LESSOR_MARKET_RATE", f"The market rate ({q(rate_pct, 4)}%) is below the rate implicit in the lease "
                                f"({q(implicit, 4)}%). Para 73 applies only where the quoted rate is artificially low.",
                                Severity.ERROR, "market_rate_pct", ref("LESSOR_FINANCE")))
    else:
        rate_pct = solve_implicit()
        source = "solved" if rate_pct is not None else "not determinable"

    pv_lp = None
    pv_ratio = None
    if rate_pct is not None:
        disc = Discounter(effective_annual_rate(rate_pct, conv), basis)
        pv_lp = present_value(cfs, disc, c)
        pv_ratio = (pv_lp / fv * 100) if fv > 0 else None
    und_ratio = (total_lp / fv * 100) if fv > 0 else None
    sa = D(inp.substantially_all_pct)
    mp = D(inp.major_part_pct)

    # 63(d) — PV test
    d_note = ""
    if pv_ratio is not None:
        d_met, d_val = pv_ratio >= sa, q(pv_ratio, 2)
        d_note = f"PV of lease payments {fmt_money(pv_lp)} = {q(pv_ratio, 2)}% of fair value {fmt_money(fv)}."
    elif und_ratio is not None and und_ratio < sa:
        d_met, d_val = False, q(und_ratio, 2)
        d_note = (f"Rate implicit in the lease not determinable; even undiscounted, lease payments {fmt_money(total_lp)} are only "
                  f"{q(und_ratio, 2)}% of fair value {fmt_money(fv)} — the PV test cannot be met.")
    elif fv <= 0:
        d_met, d_val = None, None
        d_note = "Fair value of the underlying asset not entered — PV test not performed."
    else:
        d_met, d_val = None, None if und_ratio is None else q(und_ratio, 2)
        d_note = ("Rate implicit in the lease not determinable and undiscounted lease payments reach the benchmark — enter the "
                  "unguaranteed residual value or the implicit rate to conclude the PV test.")
    # 63(c) — term test
    term_months = term.term_months
    if inp.economic_life_months:
        term_ratio = term_months / Decimal(inp.economic_life_months) * 100
        c_met, c_val = term_ratio >= mp, q(term_ratio, 2)
        c_note = f"Lease term {q(term_months, 2)} months vs economic life {inp.economic_life_months} months ({q(term_ratio, 2)}%)."
    else:
        term_ratio = None
        c_met, c_val = None, None
        c_note = "Economic life of the asset not entered — term test not performed."
    ind = [
        {"code": "63(a)", "indicator": "Ownership transfers to the lessee by the end of the lease term", "met": bool(inp.transfers_ownership)},
        {"code": "63(b)", "indicator": "Purchase option at a price expected to be sufficiently below fair value", "met": bool(inp.bargain_purchase_option)},
        {"code": "63(c)", "indicator": f"Lease term is for the major part of the economic life (policy benchmark ≥ {q(mp, 0)}%)",
         "met": c_met, "value": c_val, "note": c_note},
        {"code": "63(d)", "indicator": f"PV of lease payments amounts to at least substantially all of the fair value (policy benchmark ≥ {q(sa, 0)}%)",
         "met": d_met, "value": d_val, "note": d_note},
        {"code": "63(e)", "indicator": "Asset is of a specialised nature (only the lessee can use it without major modification)", "met": bool(inp.specialised_asset)},
        {"code": "64(a)", "indicator": "Lessee bears the lessor's losses associated with cancellation", "met": bool(inp.lessee_bears_cancellation_losses)},
        {"code": "64(b)", "indicator": "Gains / losses from the fluctuation in the fair value of the residual accrue to the lessee", "met": bool(inp.residual_fv_gains_to_lessee)},
        {"code": "64(c)", "indicator": "Lessee can continue the lease for a secondary period at a rent substantially below market", "met": bool(inp.bargain_renewal)},
    ]
    primary = ind[:5]
    if any(i["met"] is True for i in primary):
        suggested = "FINANCE"
    elif all(i["met"] is False for i in primary):
        suggested = "OPERATING"
    else:
        suggested = "UNDETERMINED"
    override = (inp.classification_override or "").upper() or None
    final = override or suggested
    if rate_pct is not None:
        expl.append(f"Interest rate implicit in the lease: {q(rate_pct, 4)}% p.a. ({source}).")
    else:
        expl.append("Interest rate implicit in the lease: not determinable from the inputs (no unguaranteed residual value / rate entered).")
    expl.append(d_note)
    expl.append(c_note)
    met_64 = [i["code"] for i in ind[5:] if i["met"]]
    expl.append(f"Indicator-based suggestion: {suggested.title()}."
                + (f" Final classification: {final.title()} (override — {inp.override_rationale or 'rationale not documented'})."
                   if override else f" Final classification: {final.title()}."))
    if override and not (inp.override_rationale or "").strip():
        issues.append(Issue("LESSOR_OVERRIDE_RATIONALE", "Document the rationale for the classification override (Ind AS 116.62–65 judgment).",
                            Severity.ERROR, "override_rationale", ref("LESSOR_CLASS")))
    if final == "UNDETERMINED":
        missing = [i["code"] for i in primary if i["met"] is None]
        issues.append(Issue("LESSOR_CLASSIFICATION_OPEN",
                            "Lease classification cannot be concluded — " + "; ".join(i["note"] for i in primary if i["met"] is None)
                            + f" ({', '.join(missing)}). Enter the missing inputs, or record the classification with a rationale.",
                            Severity.ERROR, "lessor_details", ref("LESSOR_CLASS")))
    if final == "FINANCE" and rate_pct is None:
        issues.append(Issue("LESSOR_RATE", "Finance lease: the interest rate implicit in the lease cannot be determined — enter the fair "
                            "value and unguaranteed residual value (or the implicit rate) to measure the net investment (Ind AS 116.68–70).",
                            Severity.ERROR, "implicit_rate_pct", ref("LESSOR_FINANCE")))
    flags = [JudgmentFlag("LESSOR_CLASSIFICATION", "Lessor lease classification",
                          "Classification depends on the substance of the transaction (para 63); the benchmarks are entity policy, not "
                          "bright lines.", ref("LESSOR_CLASS"),
                          assumptions=[f"'Substantially all' benchmark {q(sa, 0)}%", f"'Major part' benchmark {q(mp, 0)}%"]
                          + ([f"Override: {inp.override_rationale}"] if override else []))]
    if met_64 and final == "OPERATING":
        flags.append(JudgmentFlag("LESSOR_64", "Para 64 indicators present",
                                  f"Indicators {', '.join(met_64)} are met but the lease is classified as operating — document why "
                                  "substantially all risks and rewards are not transferred (para 65).", ref("LESSOR_CLASS")))
    if override and override != suggested:
        flags.append(JudgmentFlag("LESSOR_OVERRIDE", "Classification differs from the indicators",
                                  f"Indicators suggest {suggested.title()}; recorded as {override.title()}.", ref("LESSOR_CLASS"),
                                  assumptions=[inp.override_rationale or "Rationale not documented"]))
    return {"classification": final, "suggested": suggested, "indicators": ind, "rate_pct": rate_pct, "rate_source": source,
            "pv_ratio": None if pv_ratio is None else q(pv_ratio, 4), "undiscounted_ratio": None if und_ratio is None else q(und_ratio, 4),
            "term_ratio": None if term_ratio is None else q(term_ratio, 4), "explanation": expl, "issues": issues, "flags": flags,
            "pv_lp": pv_lp, "total_lp": total_lp}


# --------------------------------------------------------------------------- the calculation
class _Calc:
    def __init__(self, inp: LessorLeaseInput):
        self.inp = inp
        self.pol = inp.policy
        self.dp = inp.policy.currency_decimals
        self.c = inp.commencement
        self.method = (inp.policy.lessor_income_method or "MONTHLY_EQUAL").upper()
        self.basis = TimeBasis(self.c, inp.policy.daycount)
        self.conv = inp.policy.rate_convention
        self.ni_role = inp.ni_role
        self.issues: list[Issue] = []
        self.flags: list[JudgmentFlag] = []
        self.postings: list[Posting] = []
        self.rows: list[dict] = []
        self.events_out: list[dict] = []
        self.segments: list[dict] = []
        self.expl: list[str] = []

    def r(self, v) -> Decimal:
        return q(v, self.dp)

    def post(self, d: date, event: str, narration: str, lines, pe: date | None = None, ref_: str = ""):
        lines = [(role, self.r(dr), self.r(cr)) for role, dr, cr in lines if self.r(dr) or self.r(cr)]
        if lines:
            self.postings.append(Posting(d, event, narration, lines, pe or month_end(d), ref_))

    # ------------------------------------------------------------------ validation
    def validate(self):
        inp = self.inp
        iss = self.issues
        if inp.commencement is None or inp.term_end is None:
            iss.append(Issue("LESSOR_DATES", "Commencement date and lease end date are required.", Severity.ERROR, "commencement"))
            return
        if inp.term_end < inp.commencement:
            iss.append(Issue("LESSOR_DATES", "The lease end date precedes the commencement date.", Severity.ERROR, "contract_end"))
        for p in inp.payments:
            if p.include_override is not None and not (p.override_reason or "").strip():
                iss.append(Issue("OVERRIDE_REASON", f"Payment line {p.line_no}: an inclusion override requires a reason.", Severity.ERROR, "payments"))
        dp = inp.deposit
        if dp is not None:
            if dp.refund_date is None or dp.receipt_date is None or dp.refund_date <= dp.receipt_date:
                iss.append(Issue("DEPOSIT_DATES", "Security deposit: the refund date must follow the receipt date.", Severity.ERROR, "deposit"))
            if not dp.interest_bearing and dp.market_rate_pct in (None, "") and dp.treat_difference_as_lease_payment:
                iss.append(Issue("DEPOSIT_RATE", "Security deposit received: a market interest rate is required to measure the interest-free "
                                 "deposit at fair value (Ind AS 109.5.1.1, B5.1.1).", Severity.ERROR, "deposit", ref("DEPOSIT")))
        for ev in inp.events:
            if ev.effective_date < inp.commencement:
                iss.append(Issue("EVENT_DATE", f"{ev.kind.title()} effective {_fmt(ev.effective_date)} precedes commencement.", Severity.ERROR, "events"))
            if ev.kind == "MODIFICATION" and ev.nature not in MOD_NATURES:
                iss.append(Issue("EVENT_NATURE", "Select the nature of the lessor modification (paras 79–80 or 87).", Severity.ERROR, "events"))
            if ev.kind == "ECL" and ev.loss_allowance in (None, ""):
                iss.append(Issue("EVENT_ECL", "Enter the loss allowance (Ind AS 109) at the effective date.", Severity.ERROR, "events"))
            if ev.kind == "UGR_REVISION" and ev.new_unguaranteed_residual in (None, ""):
                iss.append(Issue("EVENT_UGR", "Enter the revised unguaranteed residual value.", Severity.ERROR, "events"))

    # ------------------------------------------------------------------ run
    @engine_context
    def run(self) -> LessorResult:
        inp = self.inp
        self.validate()
        if any(i.severity == Severity.ERROR for i in self.issues):
            raise LessorInputError(self.issues)
        c = self.c
        self.term = inp.term or _default_term(c, inp.term_end)
        self.term_end = self.term.term_end
        lines = [PaymentLine(**{k: getattr(p, k) for k in p.__dataclass_fields__}) for p in inp.payments]
        # security deposit: fair value and the lease-payment element (Ind AS 109)
        self._setup_deposit(lines)
        self.lines = classify_lessor_payments(lines, self.term)
        cl = classify_lessor(inp, self.lines, self.term)
        self.issues += cl["issues"]
        self.flags += cl["flags"]
        if any(i.severity == Severity.ERROR for i in self.issues):
            raise LessorInputError(self.issues)
        self.cl = cl
        self.mode = cl["classification"]
        self.rate_pct = cl["rate_pct"]
        self.disc = Discounter(effective_annual_rate(self.rate_pct, self.conv), self.basis) if self.rate_pct is not None else None
        incl, var, nl = _split(self.lines)
        self.var_lines = sorted([(max(d, c), a) for d, a, _ in var])
        self.nl_lines = sorted([(max(d, c), a) for d, a, _ in nl])
        self.ugr = D(inp.unguaranteed_residual)
        self.rdate = inp.residual_date or next_day(self.term_end)
        self.ugr_done = False
        self.allowance = ZERO
        # period accumulators and balances
        self.ni = ZERO
        self.ni_last = c
        self.accr = ZERO
        self.cum_inc = ZERO             # cumulative exact operating-lease income
        self.cum_inc_r = ZERO           # cumulative rounded (posted) operating-lease income
        self.seg = None
        self.ol_mark = c
        self.idc_rem = ZERO
        self.idc_seg = None
        self.fl_lines: list[tuple[date, Decimal]] = []
        self.ol_lines: list[tuple[date, Decimal]] = []
        self._reset_period()
        self.bal = {"ni": ZERO, "accr": ZERO, "idc": ZERO, "dep": ZERO, "allow": ZERO}
        self._initial(incl)
        self._simulate()
        return self._result()

    def _reset_period(self):
        self.per = {"add": ZERO, "recv": ZERO, "resid": ZERO, "remeas": ZERO, "derec": ZERO, "ol_due": ZERO, "accr_adj": ZERO,
                    "var": ZERO, "nl": ZERO, "gain": ZERO, "ecl": ZERO, "allow_rel": ZERO, "dep_add": ZERO, "dep_refund": ZERO,
                    "idc_add": ZERO, "idc_wo": ZERO, "billed": ZERO, "catchup": False}

    # ------------------------------------------------------------------ deposit
    def _setup_deposit(self, lines: list[PaymentLine]):
        dp = self.inp.deposit
        self.dep = None
        self.dep_active = False
        if dp is None:
            return
        c = self.c
        recog = max(dp.receipt_date, c)
        amount = D(dp.amount)
        refund = amount
        if dp.interest_bearing and D(dp.contractual_rate_pct):
            yrs = Decimal((dp.refund_date - dp.receipt_date).days) / Decimal(365)
            refund = amount + amount * D(dp.contractual_rate_pct) / 100 * yrs
        if dp.market_rate_pct not in (None, ""):
            R = effective_annual_rate(dp.market_rate_pct, self.conv)
            fv = refund * Discounter(R, self.basis).df(dp.refund_date, recog)
            rate_used = D(dp.market_rate_pct)
        else:
            fv = amount                       # at market terms
            R = solve_rate([(dp.refund_date, refund)], amount, recog, self.basis) if refund != amount else ZERO
            rate_used = nominal_from_effective(R, self.conv)
        if not dp.treat_difference_as_lease_payment:
            fv = amount
            R = solve_rate([(dp.refund_date, refund)], amount, recog, self.basis) if refund != amount else ZERO
        benefit = self.r(amount) - self.r(fv)
        self.dep = {"amount": amount, "recog": recog, "refund_date": dp.refund_date, "refund": refund, "fv": fv, "R": R,
                    "benefit": benefit, "rate_used": rate_used, "disc": Discounter(R, self.basis)}
        if benefit:
            lines.append(PaymentLine(date=recog, lease_amount=benefit, category=PaymentCategory.FIXED, line_no=10 ** 6,
                                     description="Security deposit — excess of amount received over fair value "
                                                 "(lease payment received in advance, Ind AS 109)", source="DEPOSIT"))
        self.dep_amort = ZERO
        self.dep_last = recog

    # ------------------------------------------------------------------ commencement
    def _initial(self, incl):
        inp, c = self.inp, self.c
        cl = self.cl
        self.ni0 = ZERO
        self.gross = ZERO
        self.unearned = ZERO
        self.selling = ZERO
        self.derec_gain = ZERO
        self.revenue = ZERO
        self.cost = ZERO
        self.pv_ugr = ZERO
        self.day1 = ZERO
        self.pv_lines: list[dict] = []
        idc = D(inp.lessor_idc)
        if self.mode == "FINANCE":
            disc = self.disc
            day1 = [(d, a) for d, a, _ in incl if d <= c]
            fut = [(d, a) for d, a, _ in incl if d > c]
            self.day1 = sum((a for _, a in day1), ZERO)
            pv_f = present_value(fut, disc, c)
            self.pv_ugr = self.ugr * disc.df(self.rdate, c) if self.ugr else ZERO
            self.ni0 = pv_f + self.pv_ugr
            self.gross = sum((a for _, a in fut), ZERO) + self.ugr
            self.unearned = self.gross - self.ni0
            for d, a in fut:
                self.pv_lines.append({"date": d, "amount": a, "years": disc.years(d, c), "discount_factor": disc.df(d, c),
                                      "present_value": a * disc.df(d, c), "kind": "Lease payment"})
            if self.ugr:
                self.pv_lines.append({"date": self.rdate, "amount": self.ugr, "years": disc.years(self.rdate, c),
                                      "discount_factor": disc.df(self.rdate, c), "present_value": self.pv_ugr,
                                      "kind": "Unguaranteed residual value"})
            self.fl_lines = sorted(fut)
            ni0_r = self.r(self.ni0)
            ca = self.r(inp.carrying_amount)
            if inp.manufacturer_dealer:
                pv_all = pv_f + self.day1
                self.revenue = min(D(inp.fair_value), pv_all) if D(inp.fair_value) > 0 else pv_all
                self.cost = D(inp.carrying_amount) - self.pv_ugr
                self.selling = self.r(self.revenue) - self.r(self.cost)
                lines = [(self.ni_role, ni0_r, ZERO), ("LESSEE_RECEIVABLE", self.r(self.day1), ZERO),
                         ("LESSOR_COST_OF_SALES", self.r(self.cost), ZERO), ("LESSOR_SALES_REVENUE", ZERO, self.r(self.revenue)),
                         ("LEASED_ASSET_DERECOGNISED", ZERO, ca)]
                diff = sum((x[1] for x in lines), ZERO) - sum((x[2] for x in lines), ZERO)
                if diff:
                    lines.append(("SELLING_PROFIT_LESSOR", ZERO, diff) if diff > 0 else ("SELLING_PROFIT_LESSOR", -diff, ZERO))
                self.post(c, "LESSOR_COMMENCEMENT", "Finance lease (manufacturer / dealer): revenue, cost of sale and net investment "
                                                   "(Ind AS 116.71)", lines)
                if idc:
                    self.post(c, "LESSOR_IDC", "Costs of obtaining the finance lease expensed at commencement — manufacturer / dealer "
                                               "(Ind AS 116.74)", [("LESSOR_IDC_EXPENSE", idc, ZERO), ("BANK", ZERO, idc)])
            else:
                lines = [(self.ni_role, ni0_r, ZERO), ("LESSEE_RECEIVABLE", self.r(self.day1), ZERO),
                         ("LEASED_ASSET_DERECOGNISED", ZERO, ca), ("BANK", ZERO, self.r(idc))]
                diff = sum((x[1] for x in lines), ZERO) - sum((x[2] for x in lines), ZERO)
                # not a manufacturer / dealer: the difference between the fair value and the carrying amount of the asset is a
                # gain / (loss) on derecognition (Ind AS 16.68, 71) — other income, not revenue or selling profit (para 71)
                self.derec_gain = diff
                if diff:
                    lines.append(("GAIN_DERECOGNITION_LESSOR", ZERO, diff) if diff > 0 else ("GAIN_DERECOGNITION_LESSOR", -diff, ZERO))
                self.post(c, "LESSOR_COMMENCEMENT", "Finance lease: derecognise the underlying asset, recognise the net investment "
                                                   "(Ind AS 116.67–69); difference to carrying amount is a gain / (loss) on "
                                                   "derecognition (Ind AS 16.68)", lines)
                if diff:
                    self.expl.append(f"Gain / (loss) on derecognition of the underlying asset {fmt_money(diff)} = net investment and "
                                     f"amounts received at commencement less the carrying amount {fmt_money(ca)} and initial direct costs — "
                                     "the lessor is not a manufacturer / dealer, so this is a gain on disposal (Ind AS 16.68, 71) "
                                     "presented in other income, not revenue or selling profit (Ind AS 116.71).")
                if not D(inp.carrying_amount):
                    self.issues.append(Issue("LESSOR_CARRYING", "Carrying amount of the underlying asset not entered — the asset derecognised "
                                             "at commencement is nil; confirm (Ind AS 116.67).", Severity.WARNING, "carrying_amount"))
            self.ni = self.ni0
            self.ni_last = c
            self.per["add"] = ni0_r
            self.per["billed"] += self.day1
            self.expl.append(f"Net investment at commencement {fmt_money(self.ni0)} = PV of lease payments not yet received "
                             f"{fmt_money(self.ni0 - self.pv_ugr)} + PV of unguaranteed residual {fmt_money(self.pv_ugr)}; "
                             f"gross investment {fmt_money(self.gross)}; unearned finance income {fmt_money(self.unearned)}.")
            if self.day1:
                self.expl.append(f"Lease payments received at or before commencement {fmt_money(self.day1)} are not part of the net investment (para 70).")
        else:
            self._start_ol_segment(c, [(max(d, c), a) for d, a, _ in incl], ZERO)
            if idc:
                self.idc_rem = idc
                self.idc_seg = {"start": c, "end": self.seg["end"], "amount": idc, "W": self.seg["W"]}
                self.per["idc_add"] = self.r(idc)
                self.post(c, "LESSOR_IDC", "Initial direct costs added to the carrying amount of the underlying asset (Ind AS 116.83)",
                          [("LESSOR_IDC_ASSET", idc, ZERO), ("BANK", ZERO, idc)])
            total = sum((a for _, a in self.ol_lines), ZERO)
            self.expl.append(f"Operating lease: lease payments {fmt_money(total)} recognised as income on a straight-line basis over the lease "
                             f"term ({'equal monthly amounts, part months pro-rata by days' if self.method != 'DAILY' else 'daily'}) — para 81.")
        self._segment_snapshot(c, "Commencement")

    def _start_ol_segment(self, start: date, lines: list[tuple[date, Decimal]], accr_before: Decimal):
        end = next_day(self.term_end)
        self.ol_lines = sorted(lines)
        remaining = sum((a for d, a in self.ol_lines if d >= start), ZERO)
        W = _weight(self.method, start, end)
        self.seg = {"start": start, "end": end, "I": remaining - accr_before, "W": W}
        self.ol_mark = start

    def _segment_snapshot(self, start: date, label: str):
        if self.mode == "FINANCE":
            lines = [{"date": d, "amount": a} for d, a in self.fl_lines]
            ugr, rdate = (self.ugr, self.rdate) if not self.ugr_done else (ZERO, None)
        elif self.mode == "OPERATING":
            lines = [{"date": d, "amount": a} for d, a in self.ol_lines]
            ugr, rdate = ZERO, None
        else:
            lines, ugr, rdate = [], ZERO, None
        self.segments.append({"start": start, "label": label, "classification": self.mode, "term_end": self.term_end,
                              "rate_pct": self.rate_pct, "R": self.disc.R if self.disc else None, "lines": lines,
                              "ugr": ugr, "ugr_date": rdate})

    # ------------------------------------------------------------------ time accrual
    def _accrue_to(self, x: date):
        if self.mode == "FINANCE" and x > self.ni_last:
            if self.ni:
                self.ni = self.ni * self.disc.growth(self.ni_last, x)
            self.ni_last = x
        if self.mode == "OPERATING" and self.seg is not None:
            a = max(self.ol_mark, self.seg["start"])
            b = min(x, self.seg["end"])
            if b > a and self.seg["W"] > 0:
                w = _weight(self.method, a, b)
                inc = self.seg["I"] * w / self.seg["W"]
                self.cum_inc += inc
                self.accr += inc
                if self.idc_seg is not None and self.idc_seg["W"] > 0:
                    am = self.idc_seg["amount"] * _weight(self.method, max(a, self.idc_seg["start"]), min(b, self.idc_seg["end"])) / self.idc_seg["W"]
                    self.idc_rem -= am
            self.ol_mark = max(self.ol_mark, x)
        if self.dep_active and x > self.dep_last:
            self.dep_amort = self.dep_amort * self.dep["disc"].growth(self.dep_last, x)
            self.dep_last = x

    # ------------------------------------------------------------------ simulation
    def _simulate(self):
        c = self.c
        inp = self.inp
        horizon = max([self.term_end] + ([self.rdate] if (self.mode == "FINANCE" and self.ugr) else [])
                      + [d for d, _ in self.fl_lines + self.ol_lines + self.var_lines + self.nl_lines]
                      + [e.effective_date for e in inp.events]
                      + ([self.dep["refund_date"], self.dep["recog"]] if self.dep else []))
        ends = month_ends_between(c, month_end(horizon))
        events = sorted(inp.events, key=lambda e: (e.effective_date, e.ref))

        def next_point(ps: date, t: date, after: Optional[date]) -> Optional[date]:
            # recomputed after every step: an event can add payment dates later in the same month
            cands = [d for d, _ in self.fl_lines + self.ol_lines + self.var_lines + self.nl_lines]
            cands += [e.effective_date for e in events]
            if self.dep:
                cands += [self.dep["recog"], self.dep["refund_date"]]
            if self.ugr and not self.ugr_done:
                cands.append(self.rdate)
            cands = [d for d in cands if ps <= d < t and (after is None or d > after)]
            return min(cands) if cands else None

        for pe in ends:
            ps = max(c, month_start(pe))
            t = next_day(pe)
            x = next_point(ps, t, None)
            while x is not None:
                self._accrue_to(x)
                for e in [e for e in events if e.effective_date == x]:
                    self._event(e, x)
                self._due_at(x)
                x = next_point(ps, t, x)
            self._accrue_to(t)
            self._close_row(ps, pe)

    def _due_at(self, x: date):
        if self.mode == "FINANCE":
            for d, a in [l for l in self.fl_lines if l[0] == x]:
                self.ni -= a
                self.per["recv"] += a
                self.per["billed"] += a
            if self.ugr and not self.ugr_done and self.rdate == x:
                self.ni -= self.ugr
                self.per["resid"] += self.ugr
                self.ugr_done = True
        elif self.mode == "OPERATING":
            for d, a in [l for l in self.ol_lines if l[0] == x]:
                self.accr -= a
                self.per["ol_due"] += a
                self.per["billed"] += a
        if self.mode != "ENDED":
            for d, a in [l for l in self.var_lines if l[0] == x]:
                self.per["var"] += a
            for d, a in [l for l in self.nl_lines if l[0] == x]:
                self.per["nl"] += a
        dep = self.dep
        if dep:
            if x == dep["recog"] and not self.dep_active and not dep.get("refunded"):
                self.dep_amort = dep["fv"]
                self.dep_last = x
                self.dep_active = True
                fv_r = self.r(dep["fv"])
                self.per["dep_add"] += fv_r
                self.post(x, "DEPOSIT_RECEIVED", "Security deposit received — financial liability at fair value; excess over fair value is a "
                                                 "lease payment received in advance (Ind AS 109.5.1.1, B5.1.1)",
                          _net([("BANK", self.r(dep["amount"]), ZERO), ("SECURITY_DEPOSIT_RECEIVED", ZERO, fv_r),
                                ("LESSEE_RECEIVABLE", ZERO, dep["benefit"])]))
            if self.dep_active and x == dep["refund_date"]:
                self._refund_deposit(x)

    def _refund_deposit(self, x: date, early: bool = False):
        dep = self.dep
        if early:
            # refund brought forward: amortised cost adjusted to the amount now payable (Ind AS 109.B5.4.6)
            self.per["catchup"] = abs(dep["refund"] - self.dep_amort) >= TINY
        self.dep_amort = ZERO
        self.dep_active = False
        dep["refunded"] = True
        refund_r = self.r(dep["refund"])
        self.per["dep_refund"] += refund_r
        self.post(x, "DEPOSIT_REFUND", "Security deposit refunded to the lessee" + (" on early termination" if early else ""),
                  [("SECURITY_DEPOSIT_RECEIVED", refund_r, ZERO), ("BANK", ZERO, refund_r)])

    # ------------------------------------------------------------------ events
    def _new_lines(self, ev: LessorEvent, x: date, new_end: date):
        """Classify the replacement payment lines of a modification against the revised lease term."""
        src = ev.new_payments
        if src is None:
            src = [PaymentLine(**{k: getattr(p, k) for k in p.__dataclass_fields__}) for p in self.inp.payments if p.date >= x]
        tr = TermResult(commencement=self.c, contract_end=new_end, noncancellable_end=new_end, term_end=new_end, max_possible_end=new_end,
                        term_days=(next_day(new_end) - self.c).days, term_months=months_between_frac(self.c, next_day(new_end)),
                        purchase_option_rc=self.term.purchase_option_rc, termination_reflected=self.term.termination_reflected)
        new = classify_lessor_payments([PaymentLine(**{k: getattr(p, k) for k in p.__dataclass_fields__}) for p in src if p.date >= x], tr)
        incl, var, nl = _split(new)
        self.var_lines = [l for l in self.var_lines if l[0] < x] + sorted((max(d, x), a) for d, a, _ in var)
        self.nl_lines = [l for l in self.nl_lines if l[0] < x] + sorted((max(d, x), a) for d, a, _ in nl)
        for ln in new:
            ln.source = ln.source or "EVENT"
        self.lines = [l for l in self.lines if l.date < x] + new
        return sorted((max(d, x), a) for d, a, _ in incl)

    def _ol_ledger_accr(self) -> Decimal:
        """Accrued / (deferred) lease income as booked so far (rounded ledger view) — used for write-offs."""
        return self.bal["accr"] + (self.r(self.cum_inc) - self.cum_inc_r) - self.r(self.per["ol_due"]) + self.per["accr_adj"]

    def _event(self, ev: LessorEvent, x: date):
        kind = ev.kind.upper()
        before_mode = self.mode
        res = {"type": kind, "nature": ev.nature, "effective_date": x, "ref": ev.ref, "description": ev.description,
               "classification_before": before_mode.title(), "classification_after": before_mode.title(), "gain_loss": ZERO,
               "steps": [], "flags": [], "reference": "", "separate_lease": False}
        if self.mode == "ENDED":
            raise LessorInputError([Issue("EVENT_AFTER_END", f"{kind.title()} effective {_fmt(x)} is after the lease was terminated.",
                                          Severity.ERROR, "events")])
        steps = res["steps"]
        if kind == "MODIFICATION":
            nature = ev.nature
            new_end = ev.new_term_end or self.term_end
            if nature == "SEPARATE_LEASE":
                res["separate_lease"] = True
                res["reference"] = "Ind AS 116.79" if self.mode == "FINANCE" else "Ind AS 116.79 / 87"
                steps.append(("Accounted for as a separate lease", ZERO, "The modification adds the right to use one or more underlying assets "
                              "at a price commensurate with the stand-alone price — create a separate lease record; this lease is unchanged."))
                self._balances_to_result(res, res)
            elif nature == "OPERATING_MODIFICATION":
                if self.mode != "OPERATING":
                    raise LessorInputError([Issue("EVENT_NATURE", "A para 87 modification applies to operating leases. For a finance lease "
                                                  "choose para 79 / 80(a) / 80(b).", Severity.ERROR, "events")])
                accr_before = self.accr
                self.term_end = new_end
                new_incl = self._new_lines(ev, x, new_end)
                self._start_ol_segment(x, new_incl, accr_before)
                if self.idc_seg is not None:
                    self.idc_seg = {"start": x, "end": self.seg["end"], "amount": self.idc_rem, "W": self.seg["W"]}
                remaining = sum((a for _, a in new_incl), ZERO)
                res["reference"] = "Ind AS 116.87"
                res["balance_label"] = "Accrued / (deferred) lease income"
                res["balance_before"] = self.r(accr_before)
                res["balance_after"] = self.r(accr_before)
                steps += [("Accrued / (deferred) lease income at the effective date", self.r(accr_before),
                           "Treated as part of the lease payments of the modified lease (para 87)."),
                          ("Remaining lease payments under the modified lease", self.r(remaining), f"From {_fmt(x)} to the revised lease end "
                           f"{_fmt(new_end)}."),
                          ("Income to recognise over the remaining term", self.r(self.seg["I"]),
                           "Remaining payments less accrued (plus deferred) lease income — straight-line from the effective date.")]
                self._segment_snapshot(x, f"Modification (para 87) — {ev.description or ''}".strip(" —"))
            elif nature == "FINANCE_REMEASURE":
                if self.mode != "FINANCE":
                    raise LessorInputError([Issue("EVENT_NATURE", "Para 80(b) applies to finance leases.", Severity.ERROR, "events")])
                ni_before = self.ni
                self.term_end = new_end
                new_incl = self._new_lines(ev, x, new_end)
                if ev.new_unguaranteed_residual not in (None, ""):
                    self.ugr = D(ev.new_unguaranteed_residual)
                if ev.new_term_end:
                    self.rdate = next_day(new_end)
                self.fl_lines = new_incl
                ni_after = present_value(new_incl, self.disc, x) + (self.ugr * self.disc.df(self.rdate, x) if (self.ugr and not self.ugr_done) else ZERO)
                self.ni = ni_after
                adj = self.r(ni_after) - self.r(ni_before)
                self.per["remeas"] += adj
                self.per["gain"] += adj
                res["gain_loss"] = adj
                res["reference"] = "Ind AS 116.80(b); Ind AS 109.5.4.3"
                steps += [("Net investment immediately before the modification", self.r(ni_before), "Gross carrying amount (Ind AS 109)."),
                          ("Net investment recalculated", self.r(ni_after), f"PV of the modified lease payments and unguaranteed residual at the "
                           f"original rate implicit in the lease ({q(self.rate_pct, 4)}%)."),
                          ("Modification gain / (loss) in profit or loss", adj, "Ind AS 109.5.4.3.")]
                res["flags"].append(JudgmentFlag("LESSOR_MOD_109", "Finance lease modification — Ind AS 109",
                                                 "Assess whether the modification is substantial (derecognition of the receivable under Ind AS 109); "
                                                 "this calculation applies para 5.4.3 (no derecognition).", "Ind AS 116.80(b)"))
                self.post(x, "LESSOR_MODIFICATION", "Finance lease modification — net investment recalculated at the original rate "
                                                    "(Ind AS 116.80(b); Ind AS 109.5.4.3)", _dc(self.ni_role, "GAIN_LOSS_MODIFICATION_LESSOR", adj),
                          ref_=ev.ref)
                res["balance_label"] = "Net investment"
                res["balance_before"], res["balance_after"] = self.r(ni_before), self.r(ni_after)
                self._segment_snapshot(x, f"Modification (para 80(b)) — {ev.description or ''}".strip(" —"))
            elif nature == "FINANCE_TO_OPERATING":
                if self.mode != "FINANCE":
                    raise LessorInputError([Issue("EVENT_NATURE", "Para 80(a) applies to finance leases.", Severity.ERROR, "events")])
                ni_before_r = self.r(self.ni)
                allow = self.allowance
                asset = ni_before_r - allow
                self.post(x, "FL_TO_OL_RECLASS", "Modified finance lease that would have been an operating lease — underlying asset "
                                                 "recognised at the net investment (Ind AS 116.80(a))",
                          [("UNDERLYING_ASSET_RECOGNISED", asset, ZERO), ("LOSS_ALLOWANCE_LEASE_RECEIVABLES", allow, ZERO),
                           (self.ni_role, ZERO, ni_before_r)], ref_=ev.ref)
                self.per["derec"] += ni_before_r
                self.per["allow_rel"] += allow
                self.allowance = ZERO
                self.ni = ZERO
                self.fl_lines = []
                self.ugr_done = True
                self.mode = "OPERATING"
                self.term_end = new_end
                new_incl = self._new_lines(ev, x, new_end)
                self.accr = ZERO
                self._start_ol_segment(x, new_incl, ZERO)
                res["classification_after"] = "Operating"
                res["reference"] = "Ind AS 116.80(a)"
                res["balance_label"] = "Net investment → underlying asset"
                res["balance_before"], res["balance_after"] = ni_before_r, ZERO
                steps += [("Net investment immediately before the effective date", ni_before_r, "Derecognised."),
                          ("Underlying asset recognised", asset, "Carrying amount = net investment (net of any loss allowance) (para 80(a))."),
                          ("Lease payments of the new operating lease", self.r(sum((a for _, a in new_incl), ZERO)),
                           "Straight-line income from the effective date (para 81).")]
                if allow:
                    res["flags"].append(JudgmentFlag("LESSOR_80A_ALLOWANCE", "Loss allowance on reclassification",
                                                     "Policy: the underlying asset is recognised at the net investment net of the loss "
                                                     "allowance (update the expected credit losses first). Para 80(a) does not address "
                                                     "the allowance explicitly — document the policy.", "Ind AS 116.80(a); Ind AS 109.5.5"))
                res["flags"].append(JudgmentFlag("LESSOR_80A_ASSET", "Underlying asset back on the balance sheet",
                                                 "Depreciate the underlying asset under Ind AS 16 / 40 from the effective date and test for "
                                                 "impairment (Ind AS 36) — outside Lease116.", "Ind AS 116.80(a), 84–85"))
                self._segment_snapshot(x, f"Reclassified to operating (para 80(a)) — {ev.description or ''}".strip(" —"))
        elif kind == "TERMINATION":
            penalty = self.r(ev.penalty or 0)
            if self.mode == "FINANCE":
                ni_r = self.r(self.ni)
                allow = self.allowance
                asset = self.r(ev.asset_value_returned) if ev.asset_value_returned not in (None, "") else ni_r - allow - penalty
                gain = asset + penalty + allow - ni_r
                lines = [("UNDERLYING_ASSET_RECOGNISED", asset, ZERO), ("LESSEE_RECEIVABLE", penalty, ZERO),
                         ("LOSS_ALLOWANCE_LEASE_RECEIVABLES", allow, ZERO), (self.ni_role, ZERO, ni_r)]
                lines += _dc_single("GAIN_LOSS_TERMINATION_LESSOR", gain)
                self.post(x, "LESSOR_TERMINATION", "Early termination of a finance lease — net investment derecognised, asset returned",
                          lines, ref_=ev.ref)
                self.per["derec"] += ni_r
                self.per["allow_rel"] += allow
                self.allowance = ZERO
                res["balance_label"] = "Net investment"
                res["balance_before"], res["balance_after"] = ni_r, ZERO
                steps += [("Net investment derecognised", ni_r, ""), ("Underlying asset recognised", asset,
                           "At the amount entered" if ev.asset_value_returned not in (None, "") else "Default: net investment less penalty "
                                                                                                   "and loss allowance — enter the asset value if different"),
                          ("Termination payment receivable", penalty, ""), ("Gain / (loss) on termination", gain, "")]
            else:
                accr_r = self._ol_ledger_accr()
                gain = penalty - accr_r
                lines = [("LESSEE_RECEIVABLE", penalty, ZERO), ("GAIN_LOSS_TERMINATION_LESSOR", ZERO, penalty)]
                lines += _dc("GAIN_LOSS_TERMINATION_LESSOR", "ACCRUED_LEASE_INCOME", accr_r)
                self.post(x, "LESSOR_TERMINATION", "Early termination of an operating lease — accrued / deferred lease income released",
                          _net(lines), ref_=ev.ref)
                self.per["accr_adj"] -= accr_r
                self.accr = ZERO
                if self.idc_rem:
                    wo = self.r(self.idc_rem)
                    self.per["idc_wo"] += wo
                    self.post(x, "LESSOR_IDC", "Unamortised initial direct costs written off on termination",
                              [("LESSOR_IDC_EXPENSE", wo, ZERO), ("LESSOR_IDC_ASSET", ZERO, wo)], ref_=ev.ref)
                    steps.append(("Unamortised initial direct costs written off", wo, "Para 83."))
                    self.idc_rem = ZERO
                    self.idc_seg = None
                res["balance_label"] = "Accrued / (deferred) lease income"
                res["balance_before"], res["balance_after"] = accr_r, ZERO
                steps += [("Accrued / (deferred) lease income released", accr_r, "Straight-line balance at the termination date."),
                          ("Termination payment receivable", penalty, ""), ("Gain / (loss) on termination", gain, "")]
            self.per["gain"] += gain
            res["gain_loss"] = gain
            res["flags"].append(JudgmentFlag("LESSOR_TERMINATION_TIMING", "Termination agreed in advance?",
                                             "Record an early termination only where the lease ends on the date the termination is agreed. "
                                             "Where the parties agree now to end the lease on a later date, record a modification that "
                                             "shortens the lease term instead (paras 79–80 / 87) — the penalty and the straight-line "
                                             "balance are then spread to the exit date.", "Ind AS 116 Appendix A; 79–80, 87"))
            res["reference"] = "Ind AS 116.79–80 / 87; Ind AS 109.3.2.3"
            res["classification_after"] = "Terminated"
            if self.dep_active:
                catch = self.dep["refund"] - self.dep_amort
                steps.append(("Security deposit refunded", self.r(self.dep["refund"]), "Refund brought forward to the termination date — "
                              f"catch-up of {self.r(catch)} in finance cost (Ind AS 109.B5.4.6)."))
                self._refund_deposit(x, early=True)
            self.mode = "ENDED"
            self.ni = ZERO
            self.fl_lines, self.ol_lines = [], []
            self.var_lines = [l for l in self.var_lines if l[0] < x]
            self.nl_lines = [l for l in self.nl_lines if l[0] < x]
            self.seg = None
            self.term_end = prev_day(x)
            self._segment_snapshot(x, f"Terminated — {ev.description or ''}".strip(" —"))
        elif kind == "UGR_REVISION":
            if self.mode != "FINANCE" or self.ugr_done:
                raise LessorInputError([Issue("EVENT_UGR", "A revision of the unguaranteed residual value applies to a finance lease before the "
                                              "residual date.", Severity.ERROR, "events")])
            new = D(ev.new_unguaranteed_residual)
            old = self.ugr
            if new > old:
                raise LessorInputError([Issue("EVENT_UGR", "Only a reduction in the estimated unguaranteed residual value is recognised "
                                              "(Ind AS 116.77).", Severity.ERROR, "events")])
            ni_before = self.ni
            self.ni -= (old - new) * self.disc.df(self.rdate, x)
            adj = self.r(self.ni) - self.r(ni_before)
            self.ugr = new
            self.per["remeas"] += adj
            self.per["gain"] += adj
            res["gain_loss"] = adj
            res["reference"] = "Ind AS 116.77"
            res["balance_label"] = "Net investment"
            res["balance_before"], res["balance_after"] = self.r(ni_before), self.r(self.ni)
            steps += [("Unguaranteed residual value — previous estimate", self.r(old), f"Residual date {_fmt(self.rdate)}."),
                      ("Unguaranteed residual value — revised estimate", self.r(new), ""),
                      ("Loss recognised immediately (PV of the reduction at the original rate)", adj,
                       "Income allocation revised for the remaining term (para 77).")]
            self.post(x, "UGR_REVISION", "Reduction in estimated unguaranteed residual value (Ind AS 116.77)",
                      _dc(self.ni_role, "UGR_REDUCTION_LOSS", adj), ref_=ev.ref)
            self._segment_snapshot(x, "Unguaranteed residual revised")
        elif kind == "ECL":
            new = self.r(ev.loss_allowance)
            charge = new - self.allowance
            self.allowance = new
            self.per["ecl"] += charge
            res["reference"] = "Ind AS 116.77; Ind AS 109.5.5.15(b)"
            res["balance_label"] = "Loss allowance"
            res["balance_before"], res["balance_after"] = new - charge, new
            res["gain_loss"] = -charge
            steps.append(("Impairment loss / (reversal) — expected credit losses", charge, "Loss allowance on lease receivables "
                          "(simplified approach permitted for lease receivables)."))
            self.post(x, "ECL", "Expected credit loss allowance on lease receivables (Ind AS 109.5.5.15(b))",
                      _dc("ECL_LEASE_RECEIVABLES", "LOSS_ALLOWANCE_LEASE_RECEIVABLES", charge), ref_=ev.ref)
        res["classification_after"] = res["classification_after"] if kind in ("TERMINATION",) else self.mode.title() if self.mode != "ENDED" else "Terminated"
        self.events_out.append(res)

    def _balances_to_result(self, res, _):
        if self.mode == "FINANCE":
            res["balance_label"] = "Net investment"
            res["balance_before"] = res["balance_after"] = self.r(self.ni)
        else:
            res["balance_label"] = "Accrued / (deferred) lease income"
            res["balance_before"] = res["balance_after"] = self.r(self.accr)

    # ------------------------------------------------------------------ period close
    def _close_row(self, ps: date, pe: date):
        p = self.per
        b = self.bal
        # finance lease — balance-driven finance income
        ni_close = self.r(self.ni) if (self.mode == "FINANCE" and abs(self.ni) >= TINY) else ZERO
        recv, resid = self.r(p["recv"]), self.r(p["resid"])
        fin_inc = ni_close - b["ni"] - p["add"] - p["remeas"] + p["derec"] + recv + resid
        # operating lease — cumulative (balance-driven) straight-line income
        cum_r = self.r(self.cum_inc)
        inc = cum_r - self.cum_inc_r
        self.cum_inc_r = cum_r
        due = self.r(p["ol_due"])
        accr_close = b["accr"] + inc - due + p["accr_adj"]
        # IDC, deposit, loss allowance
        idc_close = self.r(self.idc_rem) if abs(self.idc_rem) >= TINY else ZERO
        idc_am = b["idc"] + p["idc_add"] - p["idc_wo"] - idc_close
        dep_close = self.r(self.dep_amort) if self.dep_active else ZERO
        dep_unw = dep_close - b["dep"] - p["dep_add"] + p["dep_refund"]
        allow_close = self.allowance
        var, nl = self.r(p["var"]), self.r(p["nl"])
        row = {"period_start": ps, "period_end": pe, "classification": self.mode,
               "ni_open": b["ni"], "ni_additions": p["add"], "finance_income": fin_inc, "ni_receipts": recv,
               "ni_residual_returned": resid, "ni_remeasurement": p["remeas"], "ni_derecognised": p["derec"], "ni_close": ni_close,
               "ni_current": ZERO, "ni_noncurrent": ZERO,
               "accrued_open": b["accr"], "lease_income": inc, "lease_payments_due": due, "accrued_adjustment": p["accr_adj"],
               "accrued_close": accr_close,
               "variable_income": var, "non_lease_income": nl, "receipts": self.r(p["billed"]), "gain_loss": p["gain"],
               "ecl_charge": p["ecl"], "loss_allowance_released": p["allow_rel"], "loss_allowance_close": allow_close,
               "idc_open": b["idc"], "idc_additions": p["idc_add"], "idc_amortisation": idc_am, "idc_written_off": p["idc_wo"], "idc_close": idc_close,
               "dep_open": b["dep"], "dep_additions": p["dep_add"], "dep_unwinding": dep_unw, "dep_refund": p["dep_refund"], "dep_close": dep_close}
        self.rows.append(row)
        # periodic postings (dated at the period end)
        if fin_inc:
            self.post(pe, "FINANCE_INCOME", "Finance income on the net investment — constant periodic rate (Ind AS 116.75)",
                      _dc(self.ni_role, "FINANCE_INCOME_LESSOR", fin_inc), pe)
        if recv:
            self.post(pe, "LESSOR_RECEIPT", "Lease payments due from the lessee — applied against the net investment (Ind AS 116.76)",
                      [("LESSEE_RECEIVABLE", recv, ZERO), (self.ni_role, ZERO, recv)], pe)
        if resid:
            self.post(pe, "RESIDUAL_RETURNED", "Underlying asset returned at the end of the lease — unguaranteed residual value",
                      [("UNDERLYING_ASSET_RECOGNISED", resid, ZERO), (self.ni_role, ZERO, resid)], pe)
        if inc:
            self.post(pe, "OPERATING_LEASE_INCOME", "Operating lease income — straight-line over the lease term (Ind AS 116.81)",
                      _dc("ACCRUED_LEASE_INCOME", "OPERATING_LEASE_INCOME", inc), pe)
        if due:
            self.post(pe, "LESSOR_RECEIPT", "Lease payments due from the lessee — operating lease",
                      [("LESSEE_RECEIVABLE", due, ZERO), ("ACCRUED_LEASE_INCOME", ZERO, due)], pe)
        if var:
            self.post(pe, "VARIABLE_LEASE_INCOME", "Variable lease income not depending on an index or rate — recognised when earned "
                                                   "(Ind AS 116.81, 90)", _dc("LESSEE_RECEIVABLE", "VARIABLE_LEASE_INCOME", var), pe)
        if nl:
            self.post(pe, "NON_LEASE_REVENUE", "Non-lease component (services / CAM) — revenue under Ind AS 115 (Ind AS 116.17)",
                      _dc("LESSEE_RECEIVABLE", "NON_LEASE_REVENUE", nl), pe)
        if idc_am:
            self.post(pe, "LESSOR_IDC_AMORTISATION", "Initial direct costs expensed over the lease term on the same basis as lease income "
                                                     "(Ind AS 116.83)", _dc("LESSOR_IDC_EXPENSE", "LESSOR_IDC_ASSET", idc_am), pe)
        if dep_unw:
            self.post(pe, "DEPOSIT_UNWINDING", "Unwinding of discount on security deposit received — effective interest (Ind AS 109)"
                      + (" incl. catch-up on early refund (Ind AS 109.B5.4.6)" if p["catchup"] else ""),
                      _dc("FINANCE_COST_DEPOSIT_RECEIVED", "SECURITY_DEPOSIT_RECEIVED", dep_unw), pe)
        self.bal = {"ni": ni_close, "accr": accr_close, "idc": idc_close, "dep": dep_close, "allow": allow_close}
        self._reset_period()

    # ------------------------------------------------------------------ outputs
    def _result(self) -> LessorResult:
        inp, c, cl = self.inp, self.c, self.cl
        rows = self.rows
        # a lease terminated or shortened by an event: drop the trailing months after its (revised) end in which nothing
        # happens — the schedule stops where the lease stops
        limit = month_end(self.term_end)
        while len(rows) > 1 and rows[-1]["period_end"] > limit and all(v == 0 for v in rows[-1].values() if isinstance(v, Decimal)):
            rows.pop()
        # current / non-current split of the net investment: principal recovered within the next 12 months
        for i, r in enumerate(rows):
            if not r["ni_close"]:
                continue
            nxt = rows[i + 1:i + 13]
            rec = sum((x["ni_receipts"] + x["ni_residual_returned"] for x in nxt), ZERO) - sum((x["finance_income"] for x in nxt), ZERO)
            cur = min(max(rec, ZERO), r["ni_close"])
            r["ni_current"], r["ni_noncurrent"] = cur, r["ni_close"] - cur
        self.postings.sort(key=lambda p: (p.date, 0 if p.event in ("LESSOR_COMMENCEMENT", "LESSOR_IDC", "DEPOSIT_RECEIVED") else 1))
        tot = lambda k: sum((r[k] for r in rows), ZERO)  # noqa: E731
        totals = {"total_finance_income": tot("finance_income"), "total_lease_income": tot("lease_income"),
                  "total_variable_income": tot("variable_income"), "total_non_lease_income": tot("non_lease_income"),
                  "total_receipts": tot("receipts"), "total_gain_loss": tot("gain_loss"), "total_ecl": tot("ecl_charge"),
                  "total_idc_amortisation": tot("idc_amortisation") + tot("idc_written_off"), "total_deposit_unwinding": tot("dep_unwinding")}
        incl_lines = [(max(ln.date, c), D(ln.lease_amount)) for ln in self.lines if ln.included]
        dep_out = None
        if self.dep:
            d = self.dep
            dep_out = {"amount_received": self.r(d["amount"]), "receipt_date": d["recog"], "refund_date": d["refund_date"],
                       "refund_amount": self.r(d["refund"]), "market_rate_pct": d["rate_used"], "initial_fair_value": self.r(d["fv"]),
                       "lease_payment_element": d["benefit"],
                       "treatment": "Excess of the amount received over fair value treated as a lease payment received in advance "
                                    "(recognised through lease income / the net investment)."}
            self.flags.append(JudgmentFlag("DEPOSIT_RECEIVED", "Interest-free security deposit received",
                                           "Measured at fair value using a market rate for a similar liability (Ind AS 109); confirm the rate "
                                           "and the expected refund date.", ref("DEPOSIT"),
                                           assumptions=[f"Market rate {d['rate_used']}% p.a.", f"Refund on {_fmt(d['refund_date'])}"]))
        if self.var_lines or any(PaymentCategory(l.category) == PaymentCategory.VARIABLE for l in self.lines):
            self.flags.append(JudgmentFlag("LESSOR_VARIABLE", "Variable lease payments", "Variable payments not linked to an index or rate are "
                                           "income when earned (disclosed under para 90); confirm none are in-substance fixed (B42).",
                                           "Ind AS 116.70, 90, B42"))
        if self.nl_lines:
            self.flags.append(JudgmentFlag("LESSOR_NON_LEASE", "Non-lease components", "Consideration allocated between lease and non-lease "
                                           "components under Ind AS 115.73–90 (Ind AS 116.17) — confirm the allocation basis.", "Ind AS 116.17"))
        if self.mode == "OPERATING" or cl["classification"] == "OPERATING":
            self.flags.append(JudgmentFlag("LESSOR_OL_ASSET", "Underlying asset remains with the lessor",
                                           "Depreciate the underlying asset under Ind AS 16 / 40 and test it for impairment (Ind AS 36) — "
                                           "maintained in the fixed-asset register, not in Lease116.", "Ind AS 116.84–85, 88"))
        idc = D(inp.lessor_idc)
        idc_out = {"amount": self.r(idc), "treatment": ("Expensed at commencement (manufacturer / dealer, para 74)" if (cl["classification"] == "FINANCE" and inp.manufacturer_dealer)
                                                        else "Included in the net investment through the implicit rate (para 69)" if cl["classification"] == "FINANCE"
                                                        else "Added to the carrying amount of the asset and expensed over the lease term (para 83)")} if idc else {}
        term = self.term
        res = LessorResult(
            lease_id=inp.lease_id, classification=cl["classification"], indicators=cl["indicators"], implicit_rate_pct=cl["rate_pct"],
            pv_ratio_pct=cl["pv_ratio"], term_ratio_pct=cl["term_ratio"], net_investment=self.r(self.ni0), gross_investment=self.r(self.gross),
            unearned_finance_income=self.r(self.unearned), selling_profit=self.r(self.selling),
            derecognition_gain=self.r(self.derec_gain), rows=rows, postings=self.postings,
            maturity=_maturity(incl_lines, c, self.dp),
            flags=self.flags, explanation=cl["explanation"] + self.expl, rate_source=cl["rate_source"], suggested_classification=cl["suggested"],
            undiscounted_ratio_pct=cl["undiscounted_ratio"], revenue=self.r(self.revenue), cost_of_sale=self.r(self.cost),
            pv_unguaranteed_residual=self.r(self.pv_ugr), receivable_at_commencement=self.r(self.day1), payments=self.lines,
            pv_lines=self.pv_lines, events=self.events_out, segments=self.segments, deposit=dep_out, idc=idc_out, issues=self.issues,
            totals=totals, term=term,
            rate_basis={"origin": c, "daycount": self.pol.daycount.value if hasattr(self.pol.daycount, "value") else str(self.pol.daycount),
                        "convention": self.conv.value if hasattr(self.conv, "value") else str(self.conv),
                        "effective_annual_rate": self.disc.R if self.disc else None},
            classification_final=self.mode, income_method=self.method)
        return res


def _dc_single(role: str, amount: Decimal, credit: bool = False) -> list[tuple[str, Decimal, Decimal]]:
    """One line for ``role``: a positive amount is a credit (gain) unless ``credit`` forces the side."""
    if not amount:
        return []
    if credit:
        return [(role, ZERO, amount)] if amount > 0 else [(role, -amount, ZERO)]
    return [(role, ZERO, amount)] if amount > 0 else [(role, -amount, ZERO)]


def _net(lines: list[tuple[str, Decimal, Decimal]]) -> list[tuple[str, Decimal, Decimal]]:
    """Net debit and credit lines per role (keeps journals tidy)."""
    agg: dict[str, Decimal] = {}
    order: list[str] = []
    for role, dr, cr in lines:
        if role not in agg:
            agg[role] = ZERO
            order.append(role)
        agg[role] += dr - cr
    out = []
    for role in order:
        v = agg[role]
        if v > 0:
            out.append((role, v, ZERO))
        elif v < 0:
            out.append((role, ZERO, -v))
    return out


@engine_context
def calculate_lessor(inp: LessorLeaseInput) -> LessorResult:
    return _Calc(inp).run()


def compute_implicit_rate(inp: LessorLeaseInput) -> Decimal:
    """Rate at which PV(lease payments + unguaranteed residual) = fair value + lessor IDC (App. A)."""
    cl = classify_lessor(inp)
    if cl["rate_pct"] is None:
        raise ValueError("The interest rate implicit in the lease cannot be determined: undiscounted lease payments plus "
                         "unguaranteed residual do not exceed fair value. Provide the unguaranteed residual value or the implicit rate.")
    return cl["rate_pct"]


# --------------------------------------------------------------------------- reporting-date position (from a stored result)
def position_at(summary: dict, as_of: date) -> dict:
    """Lessor position at a reporting date, computed from a stored (JSON) result:
    classification, balances, maturity analysis (paras 94 / 97) and — for finance leases — the reconciliation of
    undiscounted lease payments to the net investment (para 94)."""
    segs = summary.get("segments") or []
    rows = summary.get("rows") or []
    rb = summary.get("rate_basis") or {}
    active = None
    for s in segs:
        if parse_date(s["start"]) <= as_of:
            active = s
    row = None
    for r in rows:
        if parse_date(r["period_end"]) <= as_of:
            row = r
    out = {"as_of": as_of, "classification": active["classification"] if active else "NOT_COMMENCED", "maturity": [],
           "total_undiscounted": ZERO, "reconciliation": None, "row_period_end": row["period_end"] if row else None}
    g = (lambda k: D((row or {}).get(k) or 0))
    out.update({"ni_close": g("ni_close"), "ni_current": g("ni_current"), "ni_noncurrent": g("ni_noncurrent"),
                "accrued_lease_income": g("accrued_close"), "deposit_carrying": g("dep_close"), "loss_allowance": g("loss_allowance_close"),
                "idc_carrying": g("idc_close")})
    if not active or active["classification"] not in ("FINANCE", "OPERATING"):
        return out
    lines = [(parse_date(x["date"]), D(x["amount"])) for x in active.get("lines") or []]
    remaining = [(d, a) for d, a in lines if d > as_of]
    out["maturity"] = _maturity(remaining, as_of)
    out["total_undiscounted"] = q(sum((a for _, a in remaining), ZERO))
    if active["classification"] == "FINANCE" and active.get("R") not in (None, ""):
        with_ctx = engine_context(lambda: _recon(active, rb, remaining, as_of))
        out["reconciliation"] = with_ctx()
        out["reconciliation"]["ni_per_schedule"] = g("ni_close") if row and parse_date(row["period_end"]) == as_of else None
        if out["reconciliation"]["ni_per_schedule"] is not None:
            out["reconciliation"]["difference"] = out["reconciliation"]["ni_per_schedule"] - out["reconciliation"]["net_investment"]
    return out


def _recon(seg: dict, rb: dict, remaining: list[tuple[date, Decimal]], as_of: date) -> dict:
    origin = parse_date(rb.get("origin"))
    basis = TimeBasis(origin, DayCount(rb.get("daycount") or "ACT/365F"))
    disc = Discounter(D(seg["R"]), basis)
    t0 = next_day(as_of)
    undiscounted = sum((a for _, a in remaining), ZERO)
    pv = sum((a * disc.df(d, t0) for d, a in remaining), ZERO)
    ugr = D(seg.get("ugr") or 0)
    ud = parse_date(seg.get("ugr_date")) if seg.get("ugr_date") else None
    pv_ugr = ugr * disc.df(ud, t0) if (ugr and ud and ud > as_of) else ZERO
    return {"undiscounted_lease_payments": q(undiscounted), "unearned_finance_income": q(undiscounted) - q(pv),
            "pv_lease_payments": q(pv), "discounted_unguaranteed_residual": q(pv_ugr), "net_investment": q(pv) + q(pv_ugr),
            "rate_pct": D(seg.get("rate_pct") or 0)}


def lessor_maturity(inp: LessorLeaseInput, as_of: date) -> list[dict]:
    """Compatibility helper: undiscounted included lease payments after ``as_of`` (paras 94 / 97)."""
    term = inp.term or _default_term(inp.commencement, inp.term_end)
    lines = classify_lessor_payments([PaymentLine(**{k: getattr(p, k) for k in p.__dataclass_fields__}) for p in inp.payments], term)
    return _maturity([(max(l.date, inp.commencement), D(l.lease_amount)) for l in lines if l.included and l.date > as_of], as_of)


# --------------------------------------------------------------------------- portfolio disclosures (paras 89–97)
@engine_context
def aggregate_lessor_disclosures(entries: list[dict], start: date, end: date) -> dict:
    """Aggregate stored lessor results (dicts: lease_code, asset_class, kind, summary) for a reporting period.

    Para 90 amounts (tabular, para 91), the movement in the net investment (para 93), the finance-lease maturity
    analysis with the reconciliation to the net investment (para 94) and the operating-lease maturity analysis
    (para 97). Qualitative items (paras 92, 95–96) are prompts for management — never invented."""
    Z = ZERO
    inc = {"selling_profit": Z, "finance_income": Z, "variable_finance": Z, "operating_income": Z, "variable_operating": Z,
           "non_lease_revenue": Z, "derecognition_gain": Z}
    mv = {k: Z for k in ("opening", "additions", "finance_income", "receipts", "residual_returned", "remeasurement", "derecognised", "closing")}
    allow = {"opening": Z, "charge": Z, "released": Z, "closing": Z}
    mat_f: dict[str, Decimal] = {}
    mat_o: dict[str, Decimal] = {}
    rec = {k: Z for k in ("undiscounted_lease_payments", "unearned_finance_income", "pv_lease_payments",
                          "discounted_unguaranteed_residual", "net_investment")}
    pres = {"ni_current": Z, "ni_noncurrent": Z, "accrued_income_asset": Z, "deferred_income_liability": Z, "deposits_received": Z,
            "idc_carrying": Z}
    by_lease = []
    op_assets = []
    for e in entries:
        s = e["summary"] or {}
        rows = s.get("rows") or []
        prd = [r for r in rows if start <= parse_date(r["period_end"]) <= end]
        before = [r for r in rows if parse_date(r["period_end"]) < start]
        at_end = [r for r in rows if parse_date(r["period_end"]) <= end]
        g = lambda rs, k: sum((D(r.get(k) or 0) for r in rs), ZERO)  # noqa: E731
        fin_inc = g(prd, "finance_income")
        op_inc = g(prd, "lease_income")
        var_f = sum((D(r.get("variable_income") or 0) for r in prd if r.get("classification") == "FINANCE"), ZERO)
        var_o = sum((D(r.get("variable_income") or 0) for r in prd if r.get("classification") != "FINANCE"), ZERO)
        inc["finance_income"] += fin_inc
        inc["operating_income"] += op_inc
        inc["variable_finance"] += var_f
        inc["variable_operating"] += var_o
        inc["non_lease_revenue"] += g(prd, "non_lease_income")
        comm = parse_date(((s.get("term") or {}).get("commencement")) or (rows[0]["period_start"] if rows else None))
        if e.get("kind") != "SUBLEASE" and s.get("classification") == "FINANCE" and comm and start <= comm <= end:
            inc["selling_profit"] += D(s.get("selling_profit") or 0)
            inc["derecognition_gain"] += D(s.get("derecognition_gain") or 0)
        open_ni = D(before[-1]["ni_close"]) if before else ZERO
        close_row = at_end[-1] if at_end else None
        mv["opening"] += open_ni
        mv["additions"] += g(prd, "ni_additions")
        mv["finance_income"] += fin_inc
        mv["receipts"] += g(prd, "ni_receipts")
        mv["residual_returned"] += g(prd, "ni_residual_returned")
        mv["remeasurement"] += g(prd, "ni_remeasurement")
        mv["derecognised"] += g(prd, "ni_derecognised")
        mv["closing"] += D(close_row["ni_close"]) if close_row else ZERO
        allow["opening"] += D(before[-1]["loss_allowance_close"]) if before else ZERO
        allow["charge"] += g(prd, "ecl_charge")
        allow["released"] += g(prd, "loss_allowance_released")
        allow["closing"] += D(close_row["loss_allowance_close"]) if close_row else ZERO
        pos = position_at(s, end)
        target = mat_f if pos["classification"] == "FINANCE" else mat_o if pos["classification"] == "OPERATING" else None
        if target is not None:
            for m in pos["maturity"]:
                target[m["bucket"]] = target.get(m["bucket"], ZERO) + D(m["amount"])
        if pos.get("reconciliation"):
            for k in rec:
                rec[k] += D(pos["reconciliation"][k])
        if close_row:
            pres["ni_current"] += D(close_row.get("ni_current") or 0)
            pres["ni_noncurrent"] += D(close_row.get("ni_noncurrent") or 0)
            acc = D(close_row.get("accrued_close") or 0)
            if acc >= 0:
                pres["accrued_income_asset"] += acc
            else:
                pres["deferred_income_liability"] -= acc
            pres["deposits_received"] += D(close_row.get("dep_close") or 0)
            pres["idc_carrying"] += D(close_row.get("idc_close") or 0)
        if pos["classification"] == "OPERATING":
            op_assets.append({"lease_code": e["lease_code"], "asset_class": e.get("asset_class") or "", "kind": e.get("kind")})
        by_lease.append({"lease_code": e["lease_code"], "kind": e.get("kind"), "classification": pos["classification"],
                         "finance_income": q(fin_inc), "operating_income": q(op_inc), "variable_income": q(var_f + var_o),
                         "net_investment": q(D(close_row["ni_close"]) if close_row else ZERO),
                         "accrued_income": q(D(close_row["accrued_close"]) if close_row else ZERO),
                         "undiscounted_receipts": q(pos["total_undiscounted"])})
    calc_close = (mv["opening"] + mv["additions"] + mv["finance_income"] - mv["receipts"] - mv["residual_returned"]
                  + mv["remeasurement"] - mv["derecognised"])
    mv["reconciliation_difference"] = q(calc_close - mv["closing"])
    order = [f"Year {i}" for i in range(1, 6)] + ["Later than five years"]
    rec_total = rec["net_investment"]
    return {
        "reference": ref("LESSOR_DISCLOSURE"),
        "income": {k: q(v) for k, v in inc.items()},
        "income_table": [
            {"ref": "90(a)(i)", "item": "Finance leases — selling profit / (loss)", "amount": q(inc["selling_profit"])},
            {"ref": "90(a)(ii)", "item": "Finance leases — finance income on the net investment", "amount": q(inc["finance_income"])},
            {"ref": "90(a)(iii)", "item": "Finance leases — income from variable lease payments not included in the net investment",
             "amount": q(inc["variable_finance"])},
            {"ref": "90(b)", "item": "Operating leases — lease income (excluding variable payments)", "amount": q(inc["operating_income"])},
            {"ref": "90(b)", "item": "Operating leases — income from variable lease payments not depending on an index or rate",
             "amount": q(inc["variable_operating"])},
        ],
        "net_investment_movement": {k: q(v) for k, v in mv.items()},
        "loss_allowance": {k: q(v) for k, v in allow.items()},
        "maturity_finance": [{"bucket": b, "amount": q(mat_f.get(b, ZERO))} for b in order] if mat_f else [],
        "maturity_operating": [{"bucket": b, "amount": q(mat_o.get(b, ZERO))} for b in order] if mat_o else [],
        "reconciliation": ({**{k: q(v) for k, v in rec.items()}, "loss_allowance": q(allow["closing"]),
                            "net_investment_net_of_allowance": q(rec_total - allow["closing"])} if mat_f else None),
        "other_items": ([{"ref": "Ind AS 16.68, 71", "item": "Gain / (loss) on derecognition of assets let out under finance leases by a "
                                                          "lessor that is not a manufacturer / dealer — presented in other income; not "
                                                          "part of the para 90(a)(i) selling profit",
                          "amount": q(inc["derecognition_gain"])}] if inc["derecognition_gain"] else []),
        "presentation": {k: q(v) for k, v in pres.items()},
        "current_method": "Current portion of the net investment = principal expected to be recovered within 12 months after the "
                          "reporting date (net investment now less the net investment 12 months later).",
        "by_lease": by_lease,
        "operating_lease_assets": op_assets,
        "qualitative_prompts": [
            {"ref": "92(a)", "prompt": "Describe the nature of the entity's leasing activities (assets let out, typical terms, escalation "
                                       "and renewal clauses)."},
            {"ref": "92(b)", "prompt": "Explain how the risk associated with rights retained in underlying assets is managed — e.g. buy-back "
                                       "agreements, residual value guarantees, variable payments for use beyond specified limits."},
            {"ref": "93", "prompt": "Explain significant changes in the carrying amount of the net investment in finance leases "
                                    "(see the movement table)."},
            {"ref": "95–96", "prompt": "Disaggregate property, plant and equipment / investment property into assets subject to operating "
                                       "leases and other assets (Ind AS 16 / 40 disclosures) — from the fixed-asset register."},
        ],
        "count": len(entries),
    }
