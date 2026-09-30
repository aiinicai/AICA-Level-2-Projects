"""The 25 accounting test cases required by the specification (section 35).

Each case documents: Inputs -> Expected calculation -> Expected journal entry ->
Expected closing balances. Expected figures are computed independently (closed-form
annuities, float XNPV) or taken from IFRS 16 Illustrative Examples, never from the
engine itself.
"""
from datetime import date
from decimal import Decimal as Dd

import pytest

from app.engine.calendar_utils import add_months, prev_day
from app.engine.decimal_utils import q
from app.engine.exemptions import ExemptionInput, exempt_expense_schedule, validate_exemption
from app.engine.lessee import EngineInputError, calculate_lessee
from app.engine.models import (CostItem, DepositInput, EventType, FxInput, ImpairmentInput, LeaseEvent, LeaseOption,
                               LeaseTermInput, LesseeLeaseInput, ModificationInput, OptionKind, OptionHolder,
                               PaymentCategory, PaymentLine, Policy, ReassessmentInput, ReassessmentKind, RestorationInput,
                               Timing, TerminationInput)
from app.engine.payments import EscalationRule, PaymentTerms, RentFree, generate_payments
from app.engine.rates import DayCount, RateConvention
from app.engine.sale_leaseback import SaleLeasebackInput, calculate_sale_leaseback
from app.engine.sublease import SubleaseInput, calculate_sublease

from .helpers import annuity_pv, assert_close, balanced, je, rows_reconcile, xnpv

C = date(2025, 4, 1)                       # commencement used in most cases
PERIODIC = Policy(daycount=DayCount.MONTHLY, rate_convention=RateConvention.NOMINAL_MONTHLY)
ANNUAL_IE = Policy(daycount=DayCount.MONTHLY, rate_convention=RateConvention.EFFECTIVE_ANNUAL, depreciation_method="MONTHLY_EQUAL")


def monthly_lines(amount, n, start=C, advance=True):
    out = []
    for k in range(n):
        ps = add_months(start, k)
        pe = prev_day(add_months(start, k + 1))
        out.append(PaymentLine(date=ps if advance else add_months(start, k + 1), lease_amount=Dd(amount),
                               period_start=ps, period_end=pe, line_no=k + 1))
    return out


def annual_arrears(amount, k_from, k_to, c=date(2020, 1, 1)):
    return [PaymentLine(date=add_months(c, 12 * k), lease_amount=Dd(amount), period_start=add_months(c, 12 * (k - 1)),
                        period_end=prev_day(add_months(c, 12 * k)), line_no=k) for k in range(k_from, k_to + 1)]


def basic(lines, rate="10", policy=None, months=60, **kw):
    return LesseeLeaseInput("T", C, LeaseTermInput(C, prev_day(add_months(C, months))), lines, Dd(rate),
                            policy=policy or Policy(), **kw)


def common_checks(res):
    assert balanced(res.postings), "every journal must balance"
    assert rows_reconcile(res) == []
    assert not [i for i in res.issues if i.severity.value == "ERROR"]


# 1 -------------------------------------------------------------------------
def test_01_simple_fixed_monthly_lease():
    """Inputs: 60 monthly payments of 1,00,000 in arrears; 12% nominal p.a. compounded monthly (1% per month).
    Expected: liability = 1,00,000 x a(60, 1%) = 44,95,504.00; ROU = liability; closes to nil.
    JE: Dr ROU 44,95,504.00 / Cr Lease liability 44,95,504.00."""
    res = calculate_lessee(basic(monthly_lines("100000", 60, advance=False), rate="12", policy=PERIODIC))
    expected = annuity_pv(100000, 0.01, 60)
    assert_close(res.initial.liability, expected)
    assert res.initial.rou == res.initial.liability
    com = je(res.postings, "COMMENCEMENT")[0]
    assert com.lines == [("ROU_ASSET", res.initial.liability, Dd(0)), ("LEASE_LIABILITY", Dd(0), res.initial.liability)]
    assert res.periods[-1].liab_close == 0 and res.periods[-1].rou_close == 0
    assert_close(res.totals["total_interest"], 6_000_000 - expected)
    # first month's interest = 1% of opening
    assert_close(res.periods[0].interest, expected * 0.01)
    common_checks(res)


# 2 -------------------------------------------------------------------------
def test_02_payments_in_advance():
    """Inputs: 60 monthly payments of 1,00,000 in advance, first on commencement; 1% per month.
    Expected: liability = PV of 59 payments (annuity immediate) ; ROU = liability + 1,00,000 paid at commencement (24(b)).
    JE: Dr ROU / Cr Lease liability; Dr ROU 1,00,000 / Cr Lessor payable."""
    res = calculate_lessee(basic(monthly_lines("100000", 60), rate="12", policy=PERIODIC))
    expected_l = annuity_pv(100000, 0.01, 59)
    assert_close(res.initial.liability, expected_l)
    assert_close(res.initial.rou, expected_l + 100000)
    pre = [p for p in res.postings if p.event == "PREPAYMENT"][0]
    assert pre.lines[0] == ("ROU_ASSET", Dd("100000.00"), Dd(0))
    assert res.periods[0].cash_outflow == Dd("100000.00")  # payment on commencement is a cash outflow of the period
    assert res.periods[-1].liab_close == 0
    common_checks(res)


# 3 -------------------------------------------------------------------------
def test_03_payments_in_arrears_exact_dates():
    """Inputs: quarterly rent 3,00,000 paid at quarter-end, 5 years; IBR 9.5% effective; ACT/365 exact dates.
    Expected: liability = XNPV(9.5%) of the 20 payments (independent float XNPV)."""
    t = PaymentTerms(amount=Dd("300000"), start_date=C, end_date=prev_day(add_months(C, 60)), frequency_months=3,
                     timing=Timing.ARREARS)
    lines = generate_payments(t)
    assert len(lines) == 20 and lines[0].date == date(2025, 6, 30)
    res = calculate_lessee(basic(lines, rate="9.5"))
    exp = xnpv(9.5, [(l.date, 300000.0) for l in lines], C)
    assert_close(res.initial.liability, exp)
    assert res.periods[-1].liab_close == 0
    common_checks(res)


# 4 -------------------------------------------------------------------------
def test_04_rent_free_period():
    """Inputs: 5-year lease, rent 2,00,000 p.m. in advance, first 3 months rent-free (fit-out).
    Expected: 3 nil lines; liability = XNPV of the 57 paying months; ROU depreciated from commencement
    (asset available) — not from rent start; depreciation over 60 months."""
    t = PaymentTerms(amount=Dd("200000"), start_date=C, end_date=prev_day(add_months(C, 60)),
                     rent_free=[RentFree(C, prev_day(add_months(C, 3)))])
    lines = generate_payments(t)
    assert [l.lease_amount for l in lines[:4]] == [Dd("0.00")] * 3 + [Dd("200000.00")]
    res = calculate_lessee(basic(lines, rate="10"))
    exp = xnpv(10, [(l.date, float(l.lease_amount)) for l in lines if l.date > C], C)
    assert_close(res.initial.liability, exp)
    assert res.periods[0].depreciation > 0, "depreciation starts at commencement"
    assert res.initial.depreciation_end == prev_day(add_months(C, 60))
    common_checks(res)


# 5 -------------------------------------------------------------------------
def test_05_annual_escalation_compounding():
    """Inputs: 1,00,000 p.m. in advance escalating 5% every 12 months (compounding), 5 years, 10% IBR.
    Expected: year-5 rent 1,21,550.63; liability = XNPV (independent)."""
    t = PaymentTerms(amount=Dd("100000"), start_date=C, end_date=prev_day(add_months(C, 60)),
                     escalations=[EscalationRule(value=Dd("5"), every_months=12)])
    lines = generate_payments(t)
    assert lines[48].lease_amount == Dd("121550.63")
    res = calculate_lessee(basic(lines, rate="10"))
    exp = xnpv(10, [(l.date, float(l.lease_amount)) for l in lines if l.date > C], C)
    assert_close(res.initial.liability, exp)
    assert_close(res.initial.liability, Dd("5145423.29"))
    common_checks(res)


# 6 -------------------------------------------------------------------------
def test_06_cpi_linked_rentals_reassessment():
    """Inputs: annual rent 12,00,000 in advance, CPI-linked, 5 years, 8% IBR. After 1 year CPI rises 6% —
    payments from year 2 become 12,72,000.
    Expected: at commencement payments measured at the commencement index (27(b)); on the CPI change the liability is
    remeasured at the UNCHANGED 8% (42(b)); adjustment = PV at 8% of the 72,000 increase on the 4 remaining payments;
    ROU increased by the same amount (39)."""
    c = C
    lines = [PaymentLine(date=add_months(c, 12 * k), lease_amount=Dd("1200000"), category=PaymentCategory.INDEX_LINKED,
                         period_start=add_months(c, 12 * k), line_no=k + 1) for k in range(5)]
    e = add_months(c, 12)
    new = [PaymentLine(date=add_months(c, 12 * k), lease_amount=Dd("1272000"), category=PaymentCategory.INDEX_LINKED,
                       period_start=add_months(c, 12 * k)) for k in range(1, 5)]
    ev = LeaseEvent(EventType.REASSESSMENT, e, reassessment=ReassessmentInput(e, ReassessmentKind.INDEX_RATE, new_payments=new,
                                                                              revised_rate_pct=Dd("9")))
    res = calculate_lessee(basic(lines, rate="8", events=[ev]))
    er = res.events[0]
    exp_adj = xnpv(8, [(l.date, 72000.0) for l in new], e)
    assert er.rate_after_pct == Dd("8"), "unchanged discount rate for index changes (42(b))"
    assert_close(er.liability_after - er.liability_before, exp_adj)
    assert_close(er.rou_after - er.rou_before, exp_adj)
    assert any(i.code == "REASSESS_RATE_IGNORED" for i in res.issues)
    rea = je(res.postings, "REASSESSMENT")[0]
    assert rea.lines[0][0] == "ROU_ASSET" and rea.lines[1][0] == "LEASE_LIABILITY"
    common_checks(res)


# 7 -------------------------------------------------------------------------
def test_07_purchase_option_reasonably_certain():
    """Inputs: 3-year equipment lease, 50,000 p.m. in arrears, purchase option 2,00,000 at end (reasonably certain);
    asset useful life 8 years; 11% IBR.
    Expected: price included in liability (27(d)); ROU depreciated over useful life (32), so ROU is not nil at lease end."""
    c = C
    end = prev_day(add_months(c, 36))
    lines = monthly_lines("50000", 36, advance=False)
    lines.append(PaymentLine(date=add_months(c, 36), lease_amount=Dd("200000"), category=PaymentCategory.PURCHASE_OPTION,
                             description="Purchase option exercise price"))
    term = LeaseTermInput(c, end, options=[LeaseOption(OptionKind.PURCHASE, exercise_date=end, price=Dd("200000"),
                                                       reasonably_certain=True, rationale="Bargain price vs expected FV")])
    inp = LesseeLeaseInput("PO", c, term, lines, Dd("11"), useful_life_end=prev_day(add_months(c, 96)))
    res = calculate_lessee(inp)
    exp = xnpv(11, [(l.date, float(l.lease_amount)) for l in lines], c)
    assert_close(res.initial.liability, exp)
    row_end_term = [r for r in res.periods if r.period_end == end][0]
    assert row_end_term.rou_close > 0
    assert res.initial.depreciation_end == prev_day(add_months(c, 96))
    assert res.periods[-1].rou_close == 0
    common_checks(res)


# 8 -------------------------------------------------------------------------
def test_08_renewal_option():
    """Inputs: 3-year office lease + 3-year lessee renewal option at 10% higher rent; 10% IBR.
    Expected: not reasonably certain -> term 36 months, renewal payments excluded;
    reasonably certain -> term 72 months, renewal payments included."""
    c = C
    base = generate_payments(PaymentTerms(amount=Dd("100000"), start_date=c, end_date=prev_day(add_months(c, 36))))
    ren = generate_payments(PaymentTerms(amount=Dd("110000"), start_date=add_months(c, 36), end_date=prev_day(add_months(c, 72))),
                            start_line_no=37)
    for rc in (False, True):
        opt = LeaseOption(OptionKind.EXTENSION, OptionHolder.LESSEE, exercise_date=add_months(c, 36),
                          extension_end_date=prev_day(add_months(c, 72)), reasonably_certain=rc, rationale="test")
        inp = LesseeLeaseInput("RN", c, LeaseTermInput(c, prev_day(add_months(c, 36)), [opt]), base + ren, Dd("10"))
        res = calculate_lessee(inp)
        included = [l for l in res.payments if l.included]
        if rc:
            assert res.term.term_end == prev_day(add_months(c, 72)) and len(included) == 72
            exp = xnpv(10, [(l.date, float(l.lease_amount)) for l in base + ren if l.date > c], c)
        else:
            assert res.term.term_end == prev_day(add_months(c, 36)) and len(included) == 36
            exp = xnpv(10, [(l.date, float(l.lease_amount)) for l in base if l.date > c], c)
        assert_close(res.initial.liability, exp)
        common_checks(res)


# 9 -------------------------------------------------------------------------
def test_09_termination_option():
    """Inputs: 9-year lease (3+3+3) with lessee break after year 3 (penalty 3 months' rent = 3,00,000);
    lessee NOT reasonably certain to continue.
    Expected: lease term ends at the break date; termination penalty included (27(e)); liability = XNPV of 36 rents + penalty."""
    c = C
    brk = prev_day(add_months(c, 36))
    lines = generate_payments(PaymentTerms(amount=Dd("100000"), start_date=c, end_date=prev_day(add_months(c, 108))))
    lines.append(PaymentLine(date=brk, lease_amount=Dd("300000"), category=PaymentCategory.TERMINATION_PENALTY))
    opt = LeaseOption(OptionKind.TERMINATION, OptionHolder.LESSEE, exercise_date=brk, price=Dd("300000"), reasonably_certain=False)
    inp = LesseeLeaseInput("TO", c, LeaseTermInput(c, prev_day(add_months(c, 108)), [opt]), lines, Dd("10"))
    res = calculate_lessee(inp)
    assert res.term.term_end == brk and res.term.termination_reflected
    inc = [l for l in res.payments if l.included]
    assert len(inc) == 37
    exp = xnpv(10, [(l.date, float(l.lease_amount)) for l in inc if l.date > c], c)
    assert_close(res.initial.liability, exp)
    assert any(f.code == "TERM_TERMINATION_OPTION" for f in res.flags)
    common_checks(res)


# 10 ------------------------------------------------------------------------
def test_10_initial_direct_costs():
    """Inputs: brokerage 1,50,000 and stamp duty/registration 60,000 (incremental).
    Expected: ROU = liability + 2,10,000 (24(c)); JE Dr ROU / Cr IDC clearing 2,10,000."""
    res = calculate_lessee(basic(monthly_lines("100000", 60, advance=False), rate="12", policy=PERIODIC,
                                 idc=[CostItem(C, Dd("150000"), "Brokerage"), CostItem(C, Dd("60000"), "Stamp duty")]))
    assert res.initial.rou == res.initial.liability + Dd("210000.00")
    idc = je(res.postings, "IDC")[0]
    assert idc.lines == [("ROU_ASSET", Dd("210000.00"), Dd(0)), ("IDC_CLEARING", Dd(0), Dd("210000.00"))]
    common_checks(res)


# 11 ------------------------------------------------------------------------
def test_11_lease_incentive():
    """Inputs: (a) fit-out reimbursement 5,00,000 received at commencement; (b) further incentive 2,00,000 receivable in month 6.
    Expected: (a) reduces ROU (24(b)); (b) is a negative lease payment reducing the liability (27(a))."""
    lines = monthly_lines("300000", 60)
    lines.append(PaymentLine(date=add_months(C, 6), lease_amount=Dd("-200000"), category=PaymentCategory.INCENTIVE,
                             description="Incentive receivable"))
    res = calculate_lessee(basic(lines, rate="10", incentives_received=[CostItem(C, Dd("500000"), "Fit-out reimbursement")]))
    exp = xnpv(10, [(l.date, float(l.lease_amount)) for l in lines if l.date > C], C)
    assert_close(res.initial.liability, exp)
    assert res.initial.rou == res.initial.liability + Dd("300000.00") - Dd("500000.00")
    inc = je(res.postings, "INCENTIVE")[0]
    assert inc.lines[1] == ("ROU_ASSET", Dd(0), Dd("500000.00"))
    common_checks(res)


# 12 ------------------------------------------------------------------------
def test_12_restoration_obligation():
    """Inputs: reinstatement cost 10,00,000 payable at lease end (5 years); pre-tax rate 8%.
    Expected: provision = 10,00,000 / 1.08^(days/365) added to ROU (24(d)); unwinding in finance cost;
    provision accretes to 10,00,000 at settlement then settled."""
    settle = add_months(C, 60)
    res = calculate_lessee(basic(monthly_lines("100000", 60), rate="10",
                                 restoration=RestorationInput(Dd("1000000"), settle, Dd("8"))))
    exp_pv = 1_000_000 / 1.08 ** ((settle - C).days / 365)
    assert_close(res.restoration["initial_pv"], exp_pv)
    comp = dict((c[0], c[1]) for c in res.initial.rou_components)
    assert_close(comp["Estimated restoration / dismantling costs (present value)"], exp_pv)
    total_unwind = sum(r.prov_unwinding for r in res.periods)
    assert_close(total_unwind, 1_000_000 - float(res.restoration["initial_pv"]), 0.02)
    assert res.periods[-1].prov_close == 0
    assert je(res.postings, "RESTORATION_SETTLED")[0].lines[0][1] == Dd("1000000.00")
    common_checks(res)


# 13 ------------------------------------------------------------------------
def test_13_security_deposit():
    """Inputs: interest-free refundable deposit 6,00,000 paid at commencement, refundable after 5 years; market rate 9%.
    Expected: fair value = 6,00,000 / 1.09^(days/365); difference -> ROU as prepaid rent (policy); deposit accretes
    to 6,00,000 by refund date via interest income; closing deposit nil after refund."""
    refund = add_months(C, 60)
    res = calculate_lessee(basic(monthly_lines("100000", 60), rate="10",
                                 deposit=DepositInput(Dd("600000"), C, refund, market_rate_pct=Dd("9"))))
    fv = 600000 / 1.09 ** ((refund - C).days / 365)
    assert_close(res.deposit["initial_fair_value"], fv)
    assert_close(res.deposit["difference_prepaid_rent"], 600000 - fv, 0.02)
    comp = dict((c[0], c[1]) for c in res.initial.rou_components)
    assert "Security deposit — excess of amount paid over fair value (prepaid rent)" in comp
    total_int = sum(r.dep_interest for r in res.periods)
    assert_close(total_int, 600000 - float(res.deposit["initial_fair_value"]), 0.02)
    assert res.periods[-1].dep_close == 0
    assert any(f.code == "DEPOSIT" for f in res.flags)
    common_checks(res)


# 14 ------------------------------------------------------------------------
def test_14_mid_term_modification_consideration_change():
    """IFRS 16 IE18: 10-year lease, 1,00,000 p.a. in arrears, 6%; year 6 rent reduced to 95,000; revised rate 7%.
    Expected: liability before 4,21,236; after 3,89,519; ROU reduced by 31,717 (46(b))."""
    c = date(2020, 1, 1)
    e = add_months(c, 60)
    new = annual_arrears("95000", 6, 10)
    ev = LeaseEvent(EventType.MODIFICATION, e, apply_after_payments=True,
                    modification=ModificationInput(e, new_payments=new, revised_rate_pct=Dd("7")))
    res = calculate_lessee(LesseeLeaseInput("IE18", c, LeaseTermInput(c, prev_day(add_months(c, 120))),
                                            annual_arrears("100000", 1, 10), Dd("6"), policy=ANNUAL_IE, events=[ev]))
    er = res.events[0]
    assert_close(er.liability_before, 421236, 0.5)
    assert_close(er.liability_after, 389519, 0.5)
    assert_close(er.rou_before - er.rou_after, 31717, 1.0)  # IE figures are rounded to whole units
    common_checks(res)


# 15 ------------------------------------------------------------------------
def test_15_increase_in_scope():
    """(a) IFRS 16 IE16 — term extended by 4 years (not a separate lease): liability 3,46,511 -> 5,97,130; ROU +2,50,619.
    (b) IE15-style — additional floor at commensurate stand-alone price: separate lease; original lease unchanged (44)."""
    c = date(2020, 1, 1)
    e = add_months(c, 72)
    new = [PaymentLine(date=add_months(c, 12 * k), lease_amount=Dd("100000"), period_start=add_months(c, 12 * (k - 1)))
           for k in range(7, 15)]
    ev = LeaseEvent(EventType.MODIFICATION, e, apply_after_payments=True,
                    modification=ModificationInput(e, new_payments=new, revised_rate_pct=Dd("7"),
                                                   new_term_end=prev_day(add_months(c, 168))))
    res = calculate_lessee(LesseeLeaseInput("IE16", c, LeaseTermInput(c, prev_day(add_months(c, 120))),
                                            annual_arrears("100000", 1, 10), Dd("6"), policy=ANNUAL_IE, events=[ev]))
    er = res.events[0]
    assert_close(er.liability_before, 346511, 0.5)
    assert_close(er.liability_after, 597130, 0.5)
    assert_close(er.rou_after - er.rou_before, 250619, 0.5)
    assert res.periods[-1].period_end == date(2034, 1, 31) and res.periods[-1].liab_close == 0
    common_checks(res)
    ev2 = LeaseEvent(EventType.MODIFICATION, e, modification=ModificationInput(e, additional_rou=True,
                                                                                 commensurate_standalone_price=True))
    res2 = calculate_lessee(LesseeLeaseInput("IE15", c, LeaseTermInput(c, prev_day(add_months(c, 120))),
                                             annual_arrears("100000", 1, 10), Dd("6"), policy=ANNUAL_IE, events=[ev2]))
    assert res2.events[0].separate_lease is True
    assert res2.events[0].liability_before == res2.events[0].liability_after


# 16 ------------------------------------------------------------------------
def test_16_decrease_in_scope():
    """IFRS 16 IE17: space reduced by 50% at the beginning of year 6; rent 30,000; revised rate 5%.
    Expected: ROU reduced 92,001; liability reduced 1,05,309; gain 13,308; remeasurement +24,575 to ROU.
    JE: Dr Lease liability 1,05,309 / Cr ROU (net) 92,001 / Cr Gain 13,308."""
    c = date(2020, 1, 1)
    e = add_months(c, 60)
    ev = LeaseEvent(EventType.MODIFICATION, e, apply_after_payments=True,
                    modification=ModificationInput(e, new_payments=annual_arrears("30000", 6, 10), revised_rate_pct=Dd("5"),
                                                   scope_decrease_fraction=Dd("0.5")))
    res = calculate_lessee(LesseeLeaseInput("IE17", c, LeaseTermInput(c, prev_day(add_months(c, 120))),
                                            annual_arrears("50000", 1, 10), Dd("6"), policy=ANNUAL_IE, events=[ev]))
    steps = {s[0]: s[1] for s in res.events[0].steps}
    assert_close(steps["Reduction in ROU carrying amount"], 92001, 0.5)
    assert_close(steps["Reduction in lease liability"], 105309, 0.5)
    assert_close(steps["Gain / (loss) on partial termination"], 13308, 0.5)
    assert_close(steps["Adjustment to lease liability"], 24575, 0.5)
    pt = je(res.postings, "PARTIAL_TERMINATION")[0]
    gain_line = [l for l in pt.lines if l[0] == "GAIN_LOSS_MODIFICATION"][0]
    assert_close(gain_line[2], 13308, 0.5)
    common_checks(res)


# 17 ------------------------------------------------------------------------
def test_17_partial_termination_term_reduction():
    """IFRS 16 IE19: add 1,500 sqm and reduce term 10 -> 8 years; rent 1,50,000; revised 7%.
    Expected: ROU reduced 1,47,202 (3 of 5 remaining years retained); liability reduced 1,53,935 (retained scope at 6%);
    gain 6,733; remeasurement +1,26,346."""
    c = date(2020, 1, 1)
    e = add_months(c, 60)
    new = [PaymentLine(date=add_months(c, 12 * k), lease_amount=Dd("150000"), period_start=add_months(c, 12 * (k - 1)))
           for k in range(6, 9)]
    ev = LeaseEvent(EventType.MODIFICATION, e, apply_after_payments=True,
                    modification=ModificationInput(e, new_payments=new, revised_rate_pct=Dd("7"),
                                                   new_term_end=prev_day(add_months(c, 96)), additional_rou=True))
    res = calculate_lessee(LesseeLeaseInput("IE19", c, LeaseTermInput(c, prev_day(add_months(c, 120))),
                                            annual_arrears("100000", 1, 10), Dd("6"), policy=ANNUAL_IE, events=[ev]))
    steps = {s[0]: s[1] for s in res.events[0].steps}
    assert_close(steps["Reduction in ROU carrying amount"], 147202, 0.5)
    assert_close(steps["Reduction in lease liability"], 153935, 0.5)
    assert_close(steps["Gain / (loss) on partial termination"], 6733, 0.5)
    assert_close(steps["Adjustment to lease liability"], 126346, 0.5)
    assert res.periods[-1].period_end == date(2028, 1, 31)
    common_checks(res)


# 18 ------------------------------------------------------------------------
def test_18_full_termination():
    """Inputs: 5-year lease terminated after 24 months with penalty 2,50,000.
    Expected: gain/(loss) = liability − ROU carrying amount − penalty; all balances nil after termination;
    JE: Dr Lease liability, Dr Acc. dep., Cr ROU (gross), Cr Lessor payable (penalty), balancing gain/loss."""
    e = add_months(C, 24)
    ev = LeaseEvent(EventType.TERMINATION, e, termination=TerminationInput(e, Dd("250000")))
    res = calculate_lessee(basic(monthly_lines("100000", 60), rate="10", events=[ev]))
    er = res.events[0]
    assert er.gain_loss == er.liability_before - er.rou_before - Dd("250000.00")
    after = [r for r in res.periods if r.period_start >= e]
    assert all(r.liab_close == 0 and r.rou_close == 0 for r in after)
    t = je(res.postings, "TERMINATION")[0]
    roles = [l[0] for l in t.lines]
    assert roles[:4] == ["LEASE_LIABILITY", "ROU_ACC_DEP", "ROU_ASSET", "LESSOR_PAYABLE"]
    assert "GAIN_LOSS_TERMINATION" in roles
    common_checks(res)


# 19 ------------------------------------------------------------------------
def test_19_lease_term_reassessment():
    """IFRS 16 IE13: 10 years, 50,000 p.a. in advance, 5%; IDC 20,000; incentive 5,000; extension to year 15 at 55,000
    becomes reasonably certain at end of year 6; revised IBR 6%.
    Expected: liability 3,55,391; ROU 4,20,391; before reassessment 1,86,162; remeasured 3,78,174; ROU 1,68,156 -> 3,60,168."""
    c = date(2020, 1, 1)
    pays = [PaymentLine(date=add_months(c, 12 * k), lease_amount=Dd("50000"), period_start=add_months(c, 12 * k)) for k in range(10)]
    ext = [PaymentLine(date=add_months(c, 12 * k), lease_amount=Dd("55000"), period_start=add_months(c, 12 * k)) for k in range(10, 15)]
    term = LeaseTermInput(c, prev_day(add_months(c, 120)), [LeaseOption(OptionKind.EXTENSION, extension_end_date=prev_day(add_months(c, 180)))])
    e = add_months(c, 72)
    ev = LeaseEvent(EventType.REASSESSMENT, e, reassessment=ReassessmentInput(
        e, ReassessmentKind.LEASE_TERM, new_payments=[p for p in pays if p.date >= e] + ext, revised_rate_pct=Dd("6"),
        new_term_end=prev_day(add_months(c, 180))))
    res = calculate_lessee(LesseeLeaseInput("IE13", c, term, pays + ext, Dd("5"), policy=ANNUAL_IE,
                                            idc=[CostItem(c, Dd("20000"))], incentives_received=[CostItem(c, Dd("5000"))],
                                            events=[ev]))
    assert_close(res.initial.liability, 355391, 0.5)
    assert_close(res.initial.rou, 420391, 0.5)
    er = res.events[0]
    assert_close(er.liability_before, 186162, 0.5)
    assert_close(er.liability_after, 378174, 0.5)
    assert_close(er.rou_before, 168156, 0.5)
    assert_close(er.rou_after, 360168, 0.5)
    dep_2027 = sum(r.depreciation for r in res.periods if r.period_end.year == 2027)
    assert_close(dep_2027, 40019, 0.5)
    common_checks(res)


# 20 ------------------------------------------------------------------------
def test_20_foreign_currency_lease():
    """Inputs: USD lease, 10,000 USD p.m. in arrears for 24 months, 6% IBR; INR functional currency;
    rate 83.00 at commencement rising 0.10 each month.
    Expected: ROU fixed at historical rate (83.00); liability retranslated at closing rate; FX difference to P&L;
    INR journals balance; INR liability at each month-end = USD liability x closing rate."""
    lines = monthly_lines("10000", 24, advance=False)
    rates = {}
    for k in range(0, 26):
        d = add_months(C, k)
        rates[d] = Dd("83.00") + Dd("0.10") * k
        rates[prev_day(d)] = Dd("83.00") + Dd("0.10") * k if k else Dd("83.00")
    inp = basic(lines, rate="6", months=24, currency="USD", fx=FxInput("INR", rates))
    res = calculate_lessee(inp)
    fx = res.fx_periods
    assert fx and fx[0]["rou_additions"] == q(res.initial.rou * Dd("83.00"))
    for fr, r in zip(fx, res.periods):
        assert fr["liab_close"] == q(r.liab_close * fr["closing_rate"])
    assert any(p.event == "FX" for p in res.postings)
    assert balanced(res.postings)
    assert fx[-1]["rou_close"] == 0


# 21 ------------------------------------------------------------------------
def test_21_impairment_and_capped_reversal():
    """Inputs: impairment loss 5,00,000 after 12 months; reversal of 10,00,000 claimed after 36 months.
    Expected: depreciation revised prospectively; reversal capped at carrying amount had no impairment been recognised
    (Ind AS 36.117); ROU nil at end."""
    e1, e2 = add_months(C, 12), add_months(C, 36)
    evs = [LeaseEvent(EventType.IMPAIRMENT, e1, impairment=ImpairmentInput(e1, Dd("500000"), cgu="Store 12")),
           LeaseEvent(EventType.IMPAIRMENT, e2, impairment=ImpairmentInput(e2, Dd("-1000000")))]
    res = calculate_lessee(basic(monthly_lines("100000", 60), rate="10", events=evs))
    base = calculate_lessee(basic(monthly_lines("100000", 60), rate="10"))
    row_e2 = [r for r in res.periods if r.period_end == prev_day(add_months(C, 37))][0]
    base_e2 = [r for r in base.periods if r.period_end == prev_day(add_months(C, 37))][0]
    assert_close(row_e2.rou_close, base_e2.rou_close, 0.05), "after capped reversal the ROU returns to the no-impairment path"
    assert res.events[0].rou_before - res.events[0].rou_after == Dd("500000.00")
    assert res.periods[-1].rou_close == 0
    assert je(res.postings, "IMPAIRMENT")[0].lines[0] == ("IMPAIRMENT_LOSS_ROU", Dd("500000.00"), Dd(0))
    common_checks(res)


# 22 ------------------------------------------------------------------------
def test_22_short_term_lease():
    """Inputs: 11-month leave-and-licence, 50,000 p.m.; class election made for 'Buildings'.
    Expected: valid short-term exemption; straight-line expense 5,50,000 over the term; no ROU/liability.
    A lease with a purchase option cannot be short-term."""
    c = C
    lines = monthly_lines("50000", 11)
    inp = ExemptionInput("ST", "SHORT_TERM", LeaseTermInput(c, prev_day(add_months(c, 11))), lines, "Buildings",
                         class_election_short_term=True)
    res = exempt_expense_schedule(inp)
    assert res.valid
    assert sum(r["expense"] for r in res.rows) == Dd("550000.00")
    assert res.rows[-1]["accrued_liability"] == 0
    bad = ExemptionInput("ST2", "SHORT_TERM", LeaseTermInput(c, prev_day(add_months(c, 11)),
                                                               [LeaseOption(OptionKind.PURCHASE, reasonably_certain=False)]),
                         lines, "Buildings", class_election_short_term=True)
    assert not validate_exemption(bad).valid
    no_election = ExemptionInput("ST3", "SHORT_TERM", LeaseTermInput(c, prev_day(add_months(c, 11))), lines, "Buildings")
    assert not validate_exemption(no_election).valid


# 23 ------------------------------------------------------------------------
def test_23_low_value_lease():
    """Inputs: laptops, value when new 80,000 each; policy threshold 3,50,000 (entity policy).
    Expected: valid only when a threshold is set and value when new is within it; B5/B7 conditions enforced."""
    lines = monthly_lines("4000", 36)
    ok = ExemptionInput("LV", "LOW_VALUE", LeaseTermInput(C, prev_day(add_months(C, 36))), lines, "IT equipment",
                        asset_value_when_new=Dd("80000"), low_value_threshold=Dd("350000"))
    assert validate_exemption(ok).valid
    no_policy = ExemptionInput("LV2", "LOW_VALUE", LeaseTermInput(C, prev_day(add_months(C, 36))), lines, "IT equipment",
                               asset_value_when_new=Dd("80000"))
    r = validate_exemption(no_policy)
    assert not r.valid and any(i.code == "NO_THRESHOLD" for i in r.issues)
    head = ExemptionInput("LV3", "LOW_VALUE", LeaseTermInput(C, prev_day(add_months(C, 36))), lines, "IT equipment",
                          asset_value_when_new=Dd("80000"), low_value_threshold=Dd("350000"), head_lease_of_sublease=True)
    assert not validate_exemption(head).valid
    sched = exempt_expense_schedule(ok)
    assert sum(x["expense"] for x in sched.rows) == Dd("144000.00")


# 24 ------------------------------------------------------------------------
def test_24_sublease():
    """Inputs: head-lease ROU 30,00,000 (portion subleased 100%) with 36 months remaining; sublease for 34 months at
    95,000 p.m. in arrears; head-lease rate 10% (sublease implicit rate not determinable — para 68).
    Expected: finance sublease (term covers ~94% of remaining ROU life, B58); net investment = PV at 10%;
    ROU derecognised; gain/loss = NI − ROU; head-lease liability retained."""
    c = C
    lines = monthly_lines("95000", 34, advance=False)
    res = calculate_sublease(SubleaseInput("SL1", "HL1", c, prev_day(add_months(c, 34)), lines, Dd("3000000"),
                                           prev_day(add_months(c, 36)), Dd("10")))
    assert res.classification == "FINANCE"
    exp = xnpv(10, [(l.date, 95000.0) for l in lines], c)
    assert_close(res.net_investment, exp)
    assert res.gain_loss == res.net_investment - Dd("3000000.00")
    assert balanced(res.postings)
    assert res.rows[-1]["ni_close"] == 0
    # the net investment is carried on its own GL role and runs down to nil through income and receipts
    ni_bal = sum((l[1] - l[2] for p in res.postings for l in p.lines if l[0] == "NET_INVESTMENT_SUBLEASE"), Dd(0))
    assert ni_bal == 0 and not any(l[0] == "NET_INVESTMENT_LEASE" for p in res.postings for l in p.lines)


# 25 ------------------------------------------------------------------------
def test_25_sale_and_leaseback():
    """IFRS 16 IE24: sale price 20,00,000; carrying amount 10,00,000; fair value 18,00,000; 18 annual payments of 1,20,000
    in arrears; implicit rate 4.5%.
    Expected: PV 14,59,200; additional financing 2,00,000; ROU 6,99,555; gain on rights transferred 2,40,355.
    JE: Dr Cash 20,00,000; Dr ROU 6,99,555; Cr Building 10,00,000; Cr Financial liability 14,59,200; Cr Gain 2,40,355."""
    d = date(2020, 1, 1)
    lines = [PaymentLine(date=add_months(d, 12 * k), lease_amount=Dd("120000")) for k in range(1, 19)]
    res = calculate_sale_leaseback(SaleLeasebackInput("SLB1", d, "Building", Dd("1000000"), Dd("2000000"), Dd("1800000"),
                                                      lines, Dd("4.5"), is_sale_ind_as_115=True,
                                                      policy=Policy(daycount=DayCount.MONTHLY)))
    assert_close(res.financial_liability_total, 1459200, 1.0)
    assert res.additional_financing == Dd("200000.00")
    assert_close(res.rou_asset, 699555, 1.0)
    assert_close(res.gain_rights_transferred, 240355, 1.0)
    assert balanced(res.postings)
    lines_je = {l[0]: (l[1], l[2]) for l in res.postings[0].lines}
    assert lines_je["BANK"][0] == Dd("2000000.00") and lines_je["ASSET_SOLD"][1] == Dd("1000000.00")
    failed = calculate_sale_leaseback(SaleLeasebackInput("SLB2", d, "Building", Dd("1000000"), Dd("2000000"), Dd("1800000"),
                                                         lines, Dd("4.5"), is_sale_ind_as_115=False))
    assert failed.is_sale is False and failed.financial_liability_total == Dd("2000000.00")
    with pytest.raises(ValueError):
        calculate_sale_leaseback(SaleLeasebackInput("SLB3", d, "Building", Dd("1"), Dd("1"), Dd("1"), lines, Dd("4.5")))
