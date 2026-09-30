"""Invariant, policy-variant and module tests for the accounting engine."""
from datetime import date
from decimal import Decimal as Dd

import pytest

from app.engine.calendar_utils import add_months, month_end, next_day, prev_day
from app.engine.decimal_utils import fmt_money, q
from app.engine.disclosures import LeaseForDisclosure, build_disclosures
from app.engine.lessee import EngineInputError, calculate_lessee
from app.engine.lessor import LessorLeaseInput, calculate_lessor
from app.engine.models import (CostItem, DepositInput, EventType, LeaseEvent, LeaseTermInput, LesseeLeaseInput,
                               ModificationInput, OpeningBalance, PaymentCategory, PaymentLine, Policy, RestorationInput,
                               RestorationRevisionInput, Timing)
from app.engine.payments import EscalationRule, PaymentTerms, RentFree, generate_payments
from app.engine.rates import DayCount, Discounter, RateConvention, TimeBasis, effective_annual_rate
from app.engine.tax import TaxSettings, deferred_tax_rows, income_tax_computation_adjustments

from .helpers import assert_close, balanced, rows_reconcile, xnpv

C = date(2024, 7, 15)   # mid-month commencement on purpose


def lease(policy=None, **kw):
    t = PaymentTerms(amount=Dd("250000"), start_date=C, end_date=prev_day(add_months(C, 84)), alignment="CALENDAR",
                     due_day=7, escalations=[EscalationRule(value=Dd("15"), every_months=36)], non_lease_amount=Dd("40000"))
    lines = generate_payments(t)
    return LesseeLeaseInput("INV", C, LeaseTermInput(C, prev_day(add_months(C, 84))), lines, Dd("9.25"),
                            policy=policy or Policy(), **kw)


@pytest.mark.parametrize("policy", [
    Policy(),
    Policy(daycount=DayCount.MONTHLY, rate_convention=RateConvention.NOMINAL_MONTHLY),
    Policy(depreciation_method="MONTHLY_EQUAL"),
    Policy(current_split_method="PV_12M"),
    Policy(rounding_method="INTEREST_TRUEUP"),
    Policy(commencement_payment_paid=False),
])
def test_invariants_all_policies(policy):
    res = calculate_lessee(lease(policy))
    assert rows_reconcile(res) == []
    assert balanced(res.postings)
    assert res.periods[-1].liab_close == 0
    assert res.periods[-1].rou_close == 0
    total_int = sum(r.interest for r in res.periods)
    total_pay = sum(r.payments for r in res.periods)
    assert res.initial.liability + total_int - total_pay == 0
    assert sum(r.depreciation for r in res.periods) == res.initial.rou


def test_liability_equals_pv_of_remaining_payments_each_month():
    inp = lease()
    res = calculate_lessee(inp)
    R = effective_annual_rate(Dd("9.25"), RateConvention.EFFECTIVE_ANNUAL)
    disc = Discounter(R, TimeBasis(C, DayCount.ACT_365F))
    for r in res.periods[::7]:
        t = next_day(r.period_end)
        pv = sum(Dd(l.lease_amount) * disc.df(l.date, t) for l in res.payments if l.included and l.date >= t)
        assert abs(pv - r.liab_close) <= Dd("0.01")


def test_calendar_alignment_partial_first_period_and_due_day():
    t = PaymentTerms(amount=Dd("310000"), start_date=C, end_date=prev_day(add_months(C, 12)), alignment="CALENDAR", due_day=7)
    lines = generate_payments(t)
    # first partial period 15-Jul to 31-Jul = 17 of 31 days
    assert lines[0].period_start == C and lines[0].period_end == date(2024, 7, 31)
    assert lines[0].lease_amount == q(Dd("310000") * 17 / 31)
    assert lines[0].date == C            # due day 7 precedes period start -> paid on period start
    assert lines[1].date == date(2024, 8, 7)
    assert lines[-1].period_end == prev_day(add_months(C, 12))


def test_current_noncurrent_principal_method():
    res = calculate_lessee(lease())
    r = [x for x in res.periods if x.period_end == date(2025, 3, 31)][0]
    # non-current = balance projected 12 months ahead
    r12 = [x for x in res.periods if x.period_end == date(2026, 3, 31)][0]
    assert_close(r.liab_noncurrent, r12.liab_close, 0.02)


def test_non_lease_components_separated_and_expedient():
    res = calculate_lessee(lease())
    assert sum(r.non_lease_expense for r in res.periods) > 0
    res2 = calculate_lessee(lease(non_lease_expedient=True))
    assert sum(r.non_lease_expense for r in res2.periods) == 0
    assert res2.initial.liability > res.initial.liability


def test_variable_payments_excluded_and_tracked():
    inp = lease()
    inp.payments.append(PaymentLine(date=date(2025, 4, 30), lease_amount=Dd("75000"), category=PaymentCategory.VARIABLE,
                                    description="Revenue share"))
    res = calculate_lessee(inp)
    assert sum(r.variable_expense for r in res.periods) == Dd("75000.00")
    assert any(e.category == "VARIABLE" for e in res.initial.excluded)
    assert any(f.code == "VARIABLE_PAYMENTS" for f in res.flags)


def test_validation_errors():
    inp = lease()
    inp.term = LeaseTermInput(C, date(2020, 1, 1))
    with pytest.raises(EngineInputError) as ei:
        calculate_lessee(inp)
    assert any(i.code == "DATE_ORDER" for i in ei.value.issues)
    inp = lease()
    inp.discount_rate_pct = None
    with pytest.raises(EngineInputError):
        calculate_lessee(inp)
    inp = lease()
    inp.payments[0].include_override = False
    with pytest.raises(EngineInputError):
        calculate_lessee(inp)


def test_cutover_opening_balance_implied_rate():
    full = calculate_lessee(lease())
    row = [r for r in full.periods if r.period_end == date(2026, 3, 31)][0]
    ob = OpeningBalance(date(2026, 4, 1), row.liab_close, row.rou_cost_close, row.rou_accdep_close)
    res = calculate_lessee(lease(opening=ob))
    assert_close(res.initial.rate_pct, 9.25, 0.0005)
    assert res.periods[0].liab_open == row.liab_close
    assert res.periods[-1].liab_close == 0 and res.periods[-1].rou_close == 0
    assert rows_reconcile(res) == []


def test_restoration_revision_adjusts_rou():
    settle = add_months(C, 84)
    e = add_months(C, 30)
    ev = LeaseEvent(EventType.RESTORATION_REVISION, e,
                    restoration_revision=RestorationRevisionInput(e, new_estimated_cost=Dd("1800000")))
    res = calculate_lessee(lease(restoration=RestorationInput(Dd("1200000"), settle, Dd("8")), events=[ev]))
    er = res.events[0]
    assert er.rou_after > er.rou_before
    assert res.periods[-1].prov_close == 0
    assert [p for p in res.postings if p.event == "RESTORATION_SETTLED"][0].lines[0][1] == Dd("1800000.00")
    assert rows_reconcile(res) == [] and balanced(res.postings)


def test_termination_brings_deposit_refund_forward():
    e = add_months(C, 24)
    ev = LeaseEvent(EventType.TERMINATION, e)
    from app.engine.models import TerminationInput
    ev.termination = TerminationInput(e, Dd("0"))
    res = calculate_lessee(lease(deposit=DepositInput(Dd("1500000"), C, add_months(C, 84), market_rate_pct=Dd("9")), events=[ev]))
    assert any(p.event == "DEPOSIT_CATCHUP" for p in res.postings)
    assert res.periods[-1].dep_close == 0
    assert balanced(res.postings)


def test_lessor_finance_lease_benchmark():
    """FV 10,00,000 recovered by 5 annual payments in arrears at 10% implicit rate = 2,63,797.48 each.
    Textbook amortisation: finance income 1,00,000.00 / 83,620.25 / 65,602.53 / 45,783.03 / 23,981.59."""
    c = date(2025, 4, 1)
    pays = [PaymentLine(date=add_months(c, 12 * k), lease_amount=Dd("263797.48")) for k in range(1, 6)]
    inp = LessorLeaseInput("LR1", c, prev_day(add_months(c, 60)), pays, fair_value=Dd("1000000"), carrying_amount=Dd("1000000"),
                           economic_life_months=72, policy=Policy(daycount=DayCount.MONTHLY))
    res = calculate_lessor(inp)
    assert res.classification == "FINANCE"
    assert_close(res.implicit_rate_pct, 10, 0.0001)
    assert_close(res.net_investment, 1000000, 0.02)
    by_year = [sum(r["finance_income"] for r in res.rows[12 * y:12 * (y + 1)]) for y in range(5)]
    for got, exp in zip(by_year, (100000, 83620.25, 65602.53, 45783.03, 23981.59)):
        assert_close(got, exp, 0.05)
    assert res.rows[-1]["ni_close"] == 0
    assert balanced(res.postings)


def test_lessor_operating_lease_straight_line():
    c = date(2025, 4, 1)
    pays = [PaymentLine(date=add_months(c, k), lease_amount=Dd("0") if k < 3 else Dd("100000")) for k in range(36)]
    inp = LessorLeaseInput("LR2", c, prev_day(add_months(c, 36)), pays, fair_value=Dd("50000000"), economic_life_months=480)
    res = calculate_lessor(inp)          # no implicit rate needed: undiscounted payments are 6.6% of fair value (63(d) not met)
    assert res.classification == "OPERATING" and res.rate_source == "not determinable"
    incomes = [r["lease_income"] for r in res.rows]
    assert sum(incomes) == Dd("3300000.00")
    assert max(incomes) - min(incomes) <= Dd("0.01")          # equal monthly income across the rent-free period (para 81)
    assert res.rows[-1]["accrued_close"] == 0
    assert balanced(res.postings)


def test_disclosures_aggregate_and_reconcile():
    r1 = calculate_lessee(lease())
    r2 = calculate_lessee(LesseeLeaseInput("V2", date(2025, 1, 1), LeaseTermInput(date(2025, 1, 1), date(2027, 12, 31)),
                                           generate_payments(PaymentTerms(amount=Dd("40000"), start_date=date(2025, 1, 1),
                                                                          end_date=date(2027, 12, 31))), Dd("10"),
                                           asset_class="Vehicles"))
    items = [LeaseForDisclosure("INV", "Entity A", "Buildings", r1), LeaseForDisclosure("V2", "Entity A", "Vehicles", r2)]
    d = build_disclosures(items, date(2025, 4, 1), date(2026, 3, 31))
    assert all(row["reconciliation_difference"] == 0 for row in d["rou_movement"])
    assert d["liability_movement"]["reconciliation_difference"] == 0
    m = d["maturity"]
    assert m["total_undiscounted"] - m["future_finance_charges"] == m["carrying_amount"]
    assert d["presentation"]["total"] == d["liability_movement"]["closing"]
    assert d["para53"][1]["amount"] == d["liability_movement"]["interest"]


def test_tax_bridge():
    res = calculate_lessee(lease())
    rows = deferred_tax_rows(res.periods, TaxSettings())
    assert rows[0]["dtl"] > 0 and rows[0]["dta"] > 0
    adj = income_tax_computation_adjustments(res.periods, date(2025, 4, 1), date(2026, 3, 31))
    assert adj["net_adjustment"] == (adj["add_back_rou_depreciation"] + adj["add_back_interest_on_lease_liability"]
                                     + adj["add_back_provision_unwinding"] - adj["less_gain_on_modification_or_termination"]
                                     - adj["less_lease_rent_paid_or_payable"])


def test_indian_number_format():
    assert fmt_money(Dd("12345678.9")) == "1,23,45,678.90"
    assert fmt_money(Dd("-1500")) == "(1,500.00)"
    assert fmt_money(Dd("12345678.9"), indian=False) == "12,345,678.90"


def test_modification_without_rate_is_rejected():
    e = add_months(C, 12)
    ev = LeaseEvent(EventType.MODIFICATION, e, modification=ModificationInput(e))
    with pytest.raises(EngineInputError):
        calculate_lessee(lease(events=[ev]))
