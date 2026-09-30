"""Lessor accounting (Ind AS 116.61–97, B58) — engine tests against independent worked examples.

Every expected figure below is computed in this file with plain floating-point maths (discounting on an ACT/365
basis, straight-lining by calendar months, Ind AS 109 fair value of deposits) — the engine's own rate, discounting
and calendar functions are NOT used to build expectations. Tolerances are a few paise to absorb the engine's
balance-driven rounding to 2 decimals.
"""
from __future__ import annotations

import calendar
from datetime import date, timedelta
from decimal import Decimal as Dd

import pytest

from app.engine.lessor import (LessorDepositInput, LessorEvent, LessorInputError, LessorLeaseInput, aggregate_lessor_disclosures,
                               calculate_lessor, position_at)
from app.engine.models import PaymentCategory, PaymentLine, Policy, Timing
from app.engine.payments import EscalationRule, PaymentTerms, RentFree, generate_payments
from app.engine.rates import DayCount
from app.engine.sublease import SubleaseInput, calculate_sublease
from app.services.lease_service import serialize_lessor

from .helpers import assert_close, balanced


# --------------------------------------------------------------------------- independent helpers (float maths)
def yrs(d: date, t0: date) -> float:
    return (d - t0).days / 365.0


def pv_at(cfs, r: float, t0: date) -> float:
    """PV at the start of ``t0`` of cash flows dated on / after ``t0`` (ACT/365, effective annual rate)."""
    return sum(float(a) / (1.0 + r) ** yrs(d, t0) for d, a in cfs if d >= t0)


def solve_rate(cfs, target: float, t0: date) -> float:
    lo, hi = -0.9, 5.0
    for _ in range(300):
        mid = (lo + hi) / 2
        if pv_at(cfs, mid, t0) > target:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def nd(d: date) -> date:
    return d + timedelta(days=1)


def row_at(res, pe: date) -> dict:
    return next(r for r in res.rows if r["period_end"] == pe)


def fy_sum(res, key: str, start: date, end: date) -> Dd:
    return sum((r[key] for r in res.rows if start <= r["period_end"] <= end), Dd(0))


def ledger(postings) -> dict:
    """Net debit balance per GL role across all postings."""
    bal: dict[str, Dd] = {}
    for p in postings:
        for role, dr, cr in p.lines:
            bal[role] = bal.get(role, Dd(0)) + dr - cr
    return bal


def month_ends(start: date, end: date):
    y, m = start.year, start.month
    while True:
        d = date(y, m, calendar.monthrange(y, m)[1])
        if d > end:
            return
        yield d
        m += 1
        if m == 13:
            y, m = y + 1, 1


def deposit_fair_value(amount: float, receipt: date, refund: date, rate_pct: float) -> float:
    return amount / (1 + rate_pct / 100) ** yrs(refund, receipt)


# --------------------------------------------------------------------------- worked example A — finance lease
C_A = date(2025, 4, 1)
END_A = date(2030, 3, 31)


def pays_a(amount="150000"):
    return generate_payments(PaymentTerms(amount=Dd(amount), start_date=C_A, end_date=END_A, frequency_months=3, timing=Timing.ARREARS))


def fl_input(**kw):
    base = dict(fair_value=Dd("2500000"), carrying_amount=Dd("2100000"), economic_life_months=72, unguaranteed_residual=Dd("200000"),
                lessor_idc=Dd("25000"))
    base.update(kw)
    return LessorLeaseInput("FL-A", C_A, END_A, pays_a(), **base)


def a_cashflows():
    return [(l.date, float(l.lease_amount)) for l in pays_a()]


A_UGR_DATE = date(2030, 4, 1)          # default residual date: the day after the lease term ends


def a_rate() -> float:
    """Rate implicit in the lease: PV(lease payments) + PV(unguaranteed residual) = fair value + lessor IDC (Appendix A)."""
    return solve_rate(a_cashflows() + [(A_UGR_DATE, 200000.0)], 2525000.0, C_A)


def a_ni(pe: date, r: float) -> float:
    """Independent net investment at the end of ``pe``: PV of payments not yet received + PV of the residual."""
    t0 = nd(pe)
    return pv_at(a_cashflows(), r, t0) + (200000.0 / (1 + r) ** yrs(A_UGR_DATE, t0) if A_UGR_DATE >= t0 else 0.0)


def test_finance_lease_initial_measurement_and_classification():
    res = calculate_lessor(fl_input())
    r = a_rate()
    assert res.classification == "FINANCE" and res.classification_final == "FINANCE" and res.rate_source == "solved"
    assert_close(res.implicit_rate_pct, r * 100, 0.0001)
    # net investment at commencement = fair value + IDC (para 68-69, App. A); gross investment and unearned income (para 94)
    assert_close(res.net_investment, 2525000, 0.01)
    assert res.gross_investment == Dd("3200000.00")                       # 20 x 1,50,000 + UGR 2,00,000
    assert_close(res.unearned_finance_income, 3200000 - 2525000, 0.01)
    # PV of the residual and the PV test 63(d)
    pv_ugr = 200000 / (1 + r) ** yrs(A_UGR_DATE, C_A)
    assert_close(res.pv_unguaranteed_residual, pv_ugr, 0.01)
    assert_close(res.pv_ratio_pct, (2525000 - pv_ugr) / 2500000 * 100, 0.001)
    # term test 63(c): 60 of 72 months = 83.33% >= 75% policy benchmark
    ind = {i["code"]: i for i in res.indicators}
    assert ind["63(c)"]["met"] is True and and_close(ind["63(c)"]["value"], 83.33)
    # derecognition of the asset: gain = fair value - carrying amount (IDC is capitalised through the rate). The lessor is not a
    # manufacturer / dealer, so this is a gain on disposal (Ind AS 16.68) — not selling profit under para 71 / 90(a)(i)
    assert res.derecognition_gain == Dd("400000.00") and res.selling_profit == 0
    comm = next(p for p in res.postings if p.event == "LESSOR_COMMENCEMENT")
    lines = {l[0]: (l[1], l[2]) for l in comm.lines}
    assert lines["NET_INVESTMENT_LEASE"][0] == Dd("2525000.00")
    assert lines["LEASED_ASSET_DERECOGNISED"][1] == Dd("2100000.00")
    assert lines["BANK"][1] == Dd("25000.00")
    assert lines["GAIN_DERECOGNITION_LESSOR"][1] == Dd("400000.00") and "SELLING_PROFIT_LESSOR" not in lines


def and_close(a, b, tol=0.01):
    return abs(float(a) - float(b)) <= tol


def test_finance_lease_income_follows_constant_periodic_rate():
    res = calculate_lessor(fl_input())
    r = a_rate()
    # closing net investment at each financial year end agrees with an independent PV computation
    for fy_end in (date(2026, 3, 31), date(2027, 3, 31), date(2028, 3, 31), date(2029, 3, 31)):
        assert_close(row_at(res, fy_end)["ni_close"], a_ni(fy_end, r), 0.02, f"NI at {fy_end}")
    # finance income by year = movement in the NI + receipts (para 75-76)
    ni_prev = 2525000.0
    for y in range(2025, 2030):
        s, e = date(y, 4, 1), date(y + 1, 3, 31)
        ni_end = a_ni(e, r) if y < 2029 else 0.0
        receipts = 600000.0 + (200000.0 if y == 2029 else 0.0)       # 4 quarterly payments (+ residual in the last year)
        assert_close(fy_sum(res, "finance_income", s, e), ni_end - ni_prev + receipts, 0.03, f"FY {y}-{y + 1}")
        ni_prev = ni_end
    # totals: income = gross investment - net investment; the NI is fully recovered
    assert res.totals["total_finance_income"] == Dd("675000.00")
    assert res.rows[-1]["ni_close"] == 0
    assert res.rows[-1]["period_end"] == date(2030, 4, 30)                # residual returned on 01-Apr-2030
    assert fy_sum(res, "ni_residual_returned", date(2030, 4, 1), date(2030, 4, 30)) == Dd("200000.00")
    # ledger: all entries balance; NI nets to nil; the returned asset is recognised at the residual value
    assert balanced(res.postings)
    bal = ledger(res.postings)
    assert bal["NET_INVESTMENT_LEASE"] == 0
    assert bal["FINANCE_INCOME_LESSOR"] == Dd("-675000.00")
    assert bal["UNDERLYING_ASSET_RECOGNISED"] == Dd("200000.00")
    assert bal["LESSEE_RECEIVABLE"] == Dd("3000000.00")                 # receivable raised as each payment falls due


def test_finance_lease_current_split_and_reconciliation_at_reporting_date():
    res = calculate_lessor(fl_input())
    r = a_rate()
    summ = serialize_lessor(res)
    pos = position_at(summ, date(2026, 3, 31))
    rec = pos["reconciliation"]
    # para 94: undiscounted payments to be received, reconciled to the net investment
    assert Dd(rec["undiscounted_lease_payments"]) == Dd("2400000.00")                    # 16 quarterly payments left
    assert sum(Dd(m["amount"]) for m in pos["maturity"]) == Dd("2400000.00")
    assert [Dd(m["amount"]) for m in pos["maturity"]] == [Dd("600000.00")] * 4 + [Dd("0.00")] * 2
    assert_close(rec["discounted_unguaranteed_residual"], 200000 / (1 + r) ** yrs(A_UGR_DATE, date(2026, 4, 1)), 0.01)
    assert Dd(rec["difference"]) == 0 and rec["ni_per_schedule"] == row_at(res, date(2026, 3, 31))["ni_close"]
    # current portion = principal recovered in the next 12 months = NI now - NI a year later
    row = row_at(res, date(2026, 3, 31))
    assert_close(row["ni_current"], a_ni(date(2026, 3, 31), r) - a_ni(date(2027, 3, 31), r), 0.03)
    assert row["ni_current"] + row["ni_noncurrent"] == row["ni_close"]
    # a non-month-end date: PV at that date, no schedule comparison
    mid = position_at(summ, date(2026, 5, 15))
    assert mid["reconciliation"]["ni_per_schedule"] is None and mid["row_period_end"] == "2026-04-30"
    assert_close(mid["reconciliation"]["net_investment"], a_ni(date(2026, 5, 15), r), 0.02)


# --------------------------------------------------------------------------- worked example B — operating lease
C_B = date(2025, 1, 1)
END_B = date(2029, 12, 31)


def pays_b(variable=False, cam=False):
    lines = generate_payments(PaymentTerms(amount=Dd("200000"), start_date=C_B, end_date=END_B,
                                           escalations=[EscalationRule(value=Dd("5"), every_months=12)],
                                           rent_free=[RentFree(date(2025, 1, 1), date(2025, 2, 28))],
                                           non_lease_amount=Dd("40000") if cam else Dd("0")))
    if variable:
        lines.append(PaymentLine(date=date(2025, 4, 10), lease_amount=Dd("55000"), category=PaymentCategory.VARIABLE,
                                 period_start=date(2025, 3, 1), period_end=date(2025, 3, 31), description="Revenue share — Mar-25",
                                 line_no=500))
    return lines


def ol_input(deposit=True, idc=True, events=None, policy=None, variable=False, cam=False):
    dep = LessorDepositInput(Dd("1200000"), C_B, date(2030, 1, 1), market_rate_pct=Dd("9")) if deposit else None
    return LessorLeaseInput("OL-B", C_B, END_B, pays_b(variable, cam), fair_value=Dd("200000000"), carrying_amount=Dd("150000000"),
                            economic_life_months=600, lessor_idc=Dd("200000") if idc else Dd("0"), deposit=dep, events=events or [],
                            policy=policy or Policy())


RENTS_B = 12861515.0


def b_deposit_fv() -> float:
    return deposit_fair_value(1200000, C_B, date(2030, 1, 1), 9)


def test_operating_lease_straight_line_with_rent_free_escalation_deposit_and_idc():
    res = calculate_lessor(ol_input())
    assert res.classification == "OPERATING" and res.rate_source == "not determinable"
    fv = b_deposit_fv()
    benefit = 1200000 - fv
    # deposit: fair value under Ind AS 109 and the excess treated as a lease payment received in advance
    assert_close(res.deposit["initial_fair_value"], fv, 0.01)
    assert_close(res.deposit["lease_payment_element"], benefit, 0.01)
    total = RENTS_B + benefit
    assert_close(res.totals["total_lease_income"], total, 0.01)
    # equal monthly income over 60 months (para 81) — rent-free months and escalations are spread
    monthly = total / 60
    for r in res.rows[:60]:
        assert_close(r["lease_income"], monthly, 0.011, str(r["period_end"]))
    # accrued / (deferred) income at 31-Dec-2025 = income - rent billed - deposit element received in advance
    assert_close(row_at(res, date(2025, 12, 31))["accrued_close"], 12 * monthly - 10 * 200000 - benefit, 0.02)
    assert res.rows[-1]["accrued_close"] == 0
    # IDC (para 83): added to the asset, expensed on the same basis as the income
    for r in res.rows[:60]:
        assert_close(r["idc_amortisation"], 200000 / 60, 0.011)
    assert res.totals["total_idc_amortisation"] == Dd("200000.00")
    # deposit unwinding (finance cost) and amortised cost after one year (365 days)
    assert_close(row_at(res, date(2025, 12, 31))["dep_close"], fv * 1.09, 0.02)
    assert_close(res.totals["total_deposit_unwinding"], benefit, 0.01)
    refund_row = row_at(res, date(2030, 1, 31))
    assert refund_row["dep_refund"] == Dd("1200000.00") and refund_row["dep_close"] == 0
    # ledger
    assert balanced(res.postings)
    bal = ledger(res.postings)
    for role in ("ACCRUED_LEASE_INCOME", "SECURITY_DEPOSIT_RECEIVED", "LESSOR_IDC_ASSET"):
        assert bal.get(role, 0) == 0, role
    assert_close(-bal["OPERATING_LEASE_INCOME"], total, 0.01)
    assert_close(bal["FINANCE_COST_DEPOSIT_RECEIVED"], benefit, 0.01)
    assert bal["LESSOR_IDC_EXPENSE"] == Dd("200000.00")
    # the rent receivable raised equals the rent billed; the deposit element nets off against the deposit receipt
    assert bal["LESSEE_RECEIVABLE"] == Dd(str(RENTS_B)).quantize(Dd("0.01"))


def test_operating_lease_variable_and_non_lease_components_are_kept_out_of_straight_lining():
    base = calculate_lessor(ol_input())
    res = calculate_lessor(ol_input(variable=True, cam=True))
    assert [r["lease_income"] for r in res.rows] == [r["lease_income"] for r in base.rows]
    # variable payment not linked to an index / rate: income when earned (period end of the sales month) — paras 81, 90
    assert row_at(res, date(2025, 3, 31))["variable_income"] == Dd("55000.00")
    assert res.totals["total_variable_income"] == Dd("55000.00")
    # CAM is a non-lease component: Ind AS 115 revenue as billed (para 17)
    assert all(r["non_lease_income"] == Dd("40000.00") for r in res.rows[:60])
    assert res.totals["total_non_lease_income"] == Dd("2400000.00")
    reasons = {p.category.value if hasattr(p.category, "value") else p.category: p.inclusion_reason for p in res.payments}
    assert "70, 81, 90" in reasons["VARIABLE"]
    bal = ledger(res.postings)
    assert bal["VARIABLE_LEASE_INCOME"] == Dd("-55000.00") and bal["NON_LEASE_REVENUE"] == Dd("-2400000.00")
    assert balanced(res.postings)


def test_income_basis_daily_vs_equal_monthly():
    c, e = date(2025, 4, 1), date(2026, 3, 31)
    pays = generate_payments(PaymentTerms(amount=Dd("100000"), start_date=c, end_date=e))
    mk = lambda method: calculate_lessor(LessorLeaseInput("OL-D", c, e, pays, fair_value=Dd("50000000"), economic_life_months=480,
                                                          policy=Policy(lessor_income_method=method)))  # noqa: E731
    eq, daily = mk("MONTHLY_EQUAL"), mk("DAILY")
    assert all(r["lease_income"] == Dd("100000.00") for r in eq.rows)
    assert_close(row_at(daily, date(2025, 4, 30))["lease_income"], 1200000 * 30 / 365, 0.01)
    assert_close(row_at(daily, date(2026, 2, 28))["lease_income"], 1200000 * 28 / 365, 0.01)
    assert eq.totals["total_lease_income"] == daily.totals["total_lease_income"] == Dd("1200000.00")
    assert eq.income_method == "MONTHLY_EQUAL" and daily.income_method == "DAILY"


def test_operating_lease_modification_para_87():
    x = date(2026, 7, 1)
    new = generate_payments(PaymentTerms(amount=Dd("230000"), start_date=x, end_date=END_B,
                                         escalations=[EscalationRule(value=Dd("5"), every_months=12)]))
    ev = LessorEvent("MODIFICATION", x, ref="ADD-1", description="Rent revised", nature="OPERATING_MODIFICATION", new_payments=new)
    res = calculate_lessor(ol_input(events=[ev]))
    fv = b_deposit_fv()
    benefit = 1200000 - fv
    old_monthly = (RENTS_B + benefit) / 60
    billed_before = 10 * 200000 + 6 * 210000                          # Mar-25 .. Jun-26 (Jan-Feb 25 rent-free)
    accrued_before = 18 * old_monthly - billed_before - benefit       # straight-lining balance carried forward (para 87)
    new_total = sum(float(l.lease_amount) for l in new)
    new_monthly = (new_total - accrued_before) / 42                   # Jul-26 .. Dec-29
    for r in res.rows[:18]:
        assert_close(r["lease_income"], old_monthly, 0.011)
    for r in res.rows[18:60]:
        assert_close(r["lease_income"], new_monthly, 0.011, str(r["period_end"]))
    ev_out = res.events[0]
    assert ev_out["reference"] == "Ind AS 116.87"
    assert_close(ev_out["balance_before"], accrued_before, 0.02)
    # over the life, income = everything billed (old payments to the effective date + new payments + deposit element)
    assert_close(res.totals["total_lease_income"], billed_before + new_total + benefit, 0.01)
    assert res.rows[-1]["accrued_close"] == 0
    assert len(res.segments) == 2 and res.segments[1]["label"].startswith("Modification (para 87)")
    assert balanced(res.postings)


def test_operating_lease_termination_with_early_deposit_refund():
    x = date(2027, 1, 1)
    ev = LessorEvent("TERMINATION", x, ref="TERM-1", description="Tenant exits", penalty=Dd("500000"))
    res = calculate_lessor(ol_input(events=[ev]))
    fv = b_deposit_fv()
    benefit = 1200000 - fv
    monthly = (RENTS_B + benefit) / 60
    accrued = 24 * monthly - (10 * 200000 + 12 * 210000) - benefit
    e = res.events[0]
    assert_close(e["balance_before"], accrued, 0.02)
    assert_close(e["gain_loss"], 500000 - accrued, 0.02)
    # unamortised IDC written off: 36 of 60 months remain
    assert_close(row_at(res, date(2027, 1, 31))["idc_written_off"], 200000 * 36 / 60, 0.02)
    # deposit refunded at termination: amortised cost caught up to the refund amount (Ind AS 109.B5.4.6)
    jan = row_at(res, date(2027, 1, 31))
    assert jan["dep_refund"] == Dd("1200000.00") and jan["dep_close"] == 0
    assert_close(res.totals["total_deposit_unwinding"], benefit, 0.01)
    unw_dec26 = row_at(res, date(2026, 12, 31))["dep_close"]
    assert_close(jan["dep_unwinding"], 1200000 - float(unw_dec26), 0.01)
    assert all(r["classification"] == "ENDED" and r["lease_income"] == 0 for r in res.rows if r["period_end"] > x)
    assert res.rows[-1]["period_end"] == date(2027, 1, 31)                 # the schedule stops where the lease stops
    bal = ledger(res.postings)
    assert bal.get("ACCRUED_LEASE_INCOME", 0) == 0 and bal.get("SECURITY_DEPOSIT_RECEIVED", 0) == 0 and bal.get("LESSOR_IDC_ASSET", 0) == 0
    assert balanced(res.postings)


# --------------------------------------------------------------------------- finance lease events (paras 77, 79-80)
def test_finance_lease_loss_allowance_does_not_change_gross_net_investment():
    plain = calculate_lessor(fl_input())
    res = calculate_lessor(fl_input(events=[LessorEvent("ECL", date(2026, 3, 31), loss_allowance=Dd("25000")),
                                            LessorEvent("ECL", date(2027, 3, 31), loss_allowance=Dd("15000"))]))
    assert [r["ni_close"] for r in res.rows] == [r["ni_close"] for r in plain.rows]
    assert row_at(res, date(2026, 3, 31))["ecl_charge"] == Dd("25000.00")
    assert row_at(res, date(2027, 3, 31))["ecl_charge"] == Dd("-10000.00")        # reversal
    assert row_at(res, date(2027, 3, 31))["loss_allowance_close"] == Dd("15000.00")
    bal = ledger(res.postings)
    assert bal["ECL_LEASE_RECEIVABLES"] == Dd("15000.00") and bal["LOSS_ALLOWANCE_LEASE_RECEIVABLES"] == Dd("-15000.00")


def test_finance_lease_reduction_in_unguaranteed_residual_para_77():
    x = date(2027, 4, 1)
    res = calculate_lessor(fl_input(events=[LessorEvent("UGR_REVISION", x, new_unguaranteed_residual=Dd("100000"))]))
    r = a_rate()
    loss = 100000 / (1 + r) ** yrs(A_UGR_DATE, x)
    assert_close(res.events[0]["gain_loss"], -loss, 0.02)
    # after the revision the NI equals the PV of the remaining payments and the revised residual at the original rate
    t0 = date(2028, 4, 1)
    exp = pv_at(a_cashflows(), r, t0) + 100000 / (1 + r) ** yrs(A_UGR_DATE, t0)
    assert_close(row_at(res, date(2028, 3, 31))["ni_close"], exp, 0.03)
    assert res.rows[-1]["ni_close"] == 0
    assert fy_sum(res, "ni_residual_returned", date(2030, 4, 1), date(2030, 4, 30)) == Dd("100000.00")
    # total income = receipts + revised residual + loss recognised - NI at commencement
    assert_close(res.totals["total_finance_income"], 3000000 + 100000 + loss - 2525000, 0.02)
    with pytest.raises(LessorInputError):          # an increase is not recognised (para 77)
        calculate_lessor(fl_input(events=[LessorEvent("UGR_REVISION", x, new_unguaranteed_residual=Dd("300000"))]))


def test_finance_lease_modification_para_80b_remeasured_at_original_rate():
    x = date(2027, 4, 1)
    new = generate_payments(PaymentTerms(amount=Dd("120000"), start_date=x, end_date=END_A, frequency_months=3, timing=Timing.ARREARS))
    ev = LessorEvent("MODIFICATION", x, nature="FINANCE_REMEASURE", new_payments=new, description="Rent reduced")
    res = calculate_lessor(fl_input(events=[ev]))
    r = a_rate()
    old_ni = a_ni(date(2027, 3, 31), r)
    new_ni = pv_at([(l.date, float(l.lease_amount)) for l in new], r, x) + 200000 / (1 + r) ** yrs(A_UGR_DATE, x)
    e = res.events[0]
    assert e["reference"].startswith("Ind AS 116.80(b)")
    assert_close(e["balance_before"], old_ni, 0.02)
    assert_close(e["balance_after"], new_ni, 0.02)
    assert_close(e["gain_loss"], new_ni - old_ni, 0.03)
    assert res.rows[-1]["ni_close"] == 0 and balanced(res.postings)
    assert ledger(res.postings)["NET_INVESTMENT_LEASE"] == 0


def test_finance_lease_modification_para_80a_reclassified_to_operating():
    x = date(2027, 4, 1)
    new = generate_payments(PaymentTerms(amount=Dd("40000"), start_date=x, end_date=date(2028, 3, 31)))
    ev = LessorEvent("MODIFICATION", x, nature="FINANCE_TO_OPERATING", new_payments=new, new_term_end=date(2028, 3, 31),
                     description="Term shortened — would have been an operating lease")
    res = calculate_lessor(fl_input(events=[ev]))
    r = a_rate()
    ni_x = a_ni(date(2027, 3, 31), r)
    rec = next(p for p in res.postings if p.event == "FL_TO_OL_RECLASS")
    asset = next(l for l in rec.lines if l[0] == "UNDERLYING_ASSET_RECOGNISED")[1]
    assert_close(asset, ni_x, 0.02)                                         # asset recognised at the net investment
    assert res.classification == "FINANCE" and res.classification_final == "OPERATING"
    assert all(r_["lease_income"] == Dd("40000.00") for r_ in res.rows if x <= r_["period_end"] <= date(2028, 3, 31))
    assert res.rows[-1]["period_end"] == date(2028, 3, 31) and res.rows[-1]["accrued_close"] == 0
    assert ledger(res.postings).get("NET_INVESTMENT_LEASE", 0) == 0 and balanced(res.postings)
    # with a loss allowance in place the netting policy is flagged for documentation
    res2 = calculate_lessor(fl_input(events=[LessorEvent("ECL", date(2027, 3, 31), loss_allowance=Dd("20000")), ev]))
    assert any(f.code == "LESSOR_80A_ALLOWANCE" for f in res2.events[-1]["flags"])
    rec2 = next(p for p in res2.postings if p.event == "FL_TO_OL_RECLASS")
    assert_close(next(l for l in rec2.lines if l[0] == "UNDERLYING_ASSET_RECOGNISED")[1], ni_x - 20000, 0.02)


def test_finance_lease_early_termination():
    x = date(2028, 4, 1)
    evs = [LessorEvent("ECL", date(2027, 3, 31), loss_allowance=Dd("20000")),
           LessorEvent("TERMINATION", x, penalty=Dd("50000"), asset_value_returned=Dd("800000"))]
    res = calculate_lessor(fl_input(events=evs))
    ni_x = a_ni(date(2028, 3, 31), a_rate())
    e = res.events[-1]
    # gain = asset returned + penalty receivable + loss allowance released - net investment derecognised
    assert_close(e["gain_loss"], 800000 + 50000 + 20000 - ni_x, 0.02)
    assert all(r["ni_close"] == 0 and r["finance_income"] == 0 for r in res.rows if r["period_end"] > x)
    assert res.rows[-1]["period_end"] == date(2028, 4, 30)
    bal = ledger(res.postings)
    assert bal.get("NET_INVESTMENT_LEASE", 0) == 0 and bal.get("LOSS_ALLOWANCE_LEASE_RECEIVABLES", 0) == 0
    assert bal["UNDERLYING_ASSET_RECOGNISED"] == Dd("800000.00") and balanced(res.postings)
    assert any(f.code == "LESSOR_TERMINATION_TIMING" for f in e["flags"])       # agreed in advance -> record a modification


# --------------------------------------------------------------------------- manufacturer / dealer (paras 71-74)
def test_manufacturer_dealer_uses_market_rate_and_expenses_costs():
    c, e = date(2025, 4, 1), date(2030, 3, 31)
    pays = [PaymentLine(date=date(2025 + k, 4, 1), lease_amount=Dd("250000"), line_no=k) for k in range(1, 6)]
    inp = LessorLeaseInput("MD", c, e, pays, fair_value=Dd("1000000"), carrying_amount=Dd("700000"), economic_life_months=72,
                           manufacturer_dealer=True, market_rate_pct=Dd("12"), lessor_idc=Dd("20000"))
    res = calculate_lessor(inp)
    cfs = [(p.date, 250000.0) for p in pays]
    pv_mkt = pv_at(cfs, 0.12, c)
    assert res.rate_source.startswith("market rate") and res.implicit_rate_pct == Dd("12")
    assert_close(res.revenue, pv_mkt, 0.01)                         # lower of fair value and PV at a market rate (71(a), 73)
    assert res.cost_of_sale == Dd("700000.00")                       # carrying amount less PV of UGR (nil) — 71(b)
    assert_close(res.selling_profit, pv_mkt - 700000, 0.01)
    assert_close(res.net_investment, pv_mkt, 0.01)
    idc = next(p for p in res.postings if p.event == "LESSOR_IDC")
    assert ("LESSOR_IDC_EXPENSE", Dd("20000.00"), Dd("0.00")) in idc.lines          # para 74: expensed at commencement
    assert res.rows[-1]["ni_close"] == 0 and balanced(res.postings)
    # a "market rate" below the rate implicit in the lease is not an artificially low rate — rejected
    with pytest.raises(LessorInputError) as exc:
        calculate_lessor(LessorLeaseInput("MD2", c, e, pays, fair_value=Dd("1000000"), carrying_amount=Dd("700000"),
                                          economic_life_months=72, manufacturer_dealer=True, market_rate_pct=Dd("5")))
    assert any(i.code == "LESSOR_MARKET_RATE" for i in exc.value.issues)


# --------------------------------------------------------------------------- classification judgments (paras 61-66)
def _pv_case(**kw):
    """Five annual payments in arrears of 2,32,142 at a given 10% rate — PV = 88.0% of a fair value of 10,00,000."""
    c = date(2025, 4, 1)
    pays = [PaymentLine(date=date(2025 + k, 4, 1), lease_amount=Dd("232142"), line_no=k) for k in range(1, 6)]
    base = dict(fair_value=Dd("1000000"), carrying_amount=Dd("1000000"), economic_life_months=120, implicit_rate_pct=Dd("10"),
                policy=Policy(daycount=DayCount.MONTHLY))
    base.update(kw)
    return LessorLeaseInput("PV", c, date(2030, 3, 31), pays, **base)


def test_classification_benchmarks_are_entity_policy():
    ann = sum(1 / 1.1 ** k for k in range(1, 6))
    res90 = calculate_lessor(_pv_case())
    assert_close(res90.pv_ratio_pct, 232142 * ann / 1000000 * 100, 0.001)
    assert res90.classification == "OPERATING"                      # 88% < 90% "substantially all" benchmark
    res85 = calculate_lessor(_pv_case(substantially_all_pct=Dd("85")))
    assert res85.classification == "FINANCE"
    term = {i["code"]: i for i in res90.indicators}["63(c)"]
    assert term["met"] is False and and_close(term["value"], 50)


def test_classification_that_cannot_be_concluded_blocks_the_calculation():
    with pytest.raises(LessorInputError) as exc:
        calculate_lessor(_pv_case(fair_value=Dd("0"), economic_life_months=None, implicit_rate_pct=None))
    assert any(i.code == "LESSOR_CLASSIFICATION_OPEN" for i in exc.value.issues)
    with pytest.raises(LessorInputError) as exc:
        calculate_lessor(_pv_case(classification_override="FINANCE"))          # no rationale
    assert any(i.code == "LESSOR_OVERRIDE_RATIONALE" for i in exc.value.issues)
    res = calculate_lessor(_pv_case(classification_override="FINANCE", override_rationale="Lessee bears obsolescence risk under side letter"))
    assert res.classification == "FINANCE" and res.suggested_classification == "OPERATING"
    assert any(f.code == "LESSOR_OVERRIDE" for f in res.flags)


def test_para_64_indicator_on_an_operating_lease_is_flagged():
    res = calculate_lessor(_pv_case(lessee_bears_cancellation_losses=True))
    assert res.classification == "OPERATING"
    assert any(f.code == "LESSOR_64" for f in res.flags)


def test_finance_lease_without_determinable_rate_is_blocked():
    c = date(2025, 4, 1)
    pays = [PaymentLine(date=date(2025 + k, 4, 1), lease_amount=Dd("300000"), line_no=k) for k in range(1, 6)]
    with pytest.raises(LessorInputError) as exc:
        calculate_lessor(LessorLeaseInput("NR", c, date(2030, 3, 31), pays, fair_value=Dd("1500000"), economic_life_months=60,
                                          transfers_ownership=True))
    # payments (15,00,000 undiscounted) do not exceed fair value — the implicit rate cannot be solved
    assert any(i.code == "LESSOR_RATE" for i in exc.value.issues)


def test_deposit_without_market_rate_is_blocked():
    inp = ol_input()
    inp.deposit.market_rate_pct = None
    with pytest.raises(LessorInputError) as exc:
        calculate_lessor(inp)
    assert any(i.code == "DEPOSIT_RATE" for i in exc.value.issues)


# --------------------------------------------------------------------------- sublease (B58) and portfolio disclosures
def test_finance_sublease_derecognises_rou_and_uses_its_own_ledger_role():
    c = date(2025, 4, 1)
    pays = generate_payments(PaymentTerms(amount=Dd("100000"), start_date=c, end_date=date(2029, 3, 31)))
    res = calculate_sublease(SubleaseInput("SUB", "HEAD", c, date(2029, 3, 31), pays, head_rou_carrying_amount=Dd("3600000"),
                                           head_lease_term_end=date(2029, 3, 31), head_lease_discount_rate_pct=Dd("9")))
    assert res.classification == "FINANCE"
    cfs = [(p.date, 100000.0) for p in pays]
    ni = pv_at([cf for cf in cfs if cf[0] > c], 0.09, c)                      # first payment (in advance) received at commencement
    assert_close(res.net_investment, ni, 0.01)
    assert_close(res.gain_loss, ni + 100000 - 3600000, 0.01)
    bal = ledger(res.postings)
    assert bal["NET_INVESTMENT_SUBLEASE"] == 0 and "NET_INVESTMENT_LEASE" not in bal
    assert balanced(res.postings)


def test_portfolio_disclosures_paras_90_to_97():
    fl = serialize_lessor(calculate_lessor(fl_input(events=[LessorEvent("ECL", date(2026, 3, 31), loss_allowance=Dd("25000"))])))
    ol = serialize_lessor(calculate_lessor(ol_input()))
    entries = [{"lease_code": "FL-A", "asset_class": "Plant and machinery", "kind": "LESSOR", "summary": fl},
               {"lease_code": "OL-B", "asset_class": "Buildings", "kind": "LESSOR", "summary": ol}]
    s, e = date(2025, 4, 1), date(2026, 3, 31)
    d = aggregate_lessor_disclosures(entries, s, e)
    inc = {(x["ref"], x["item"][:20]): Dd(x["amount"]) for x in d["income_table"]}
    fin_income = sum((Dd(r["finance_income"]) for r in fl["rows"] if s.isoformat() <= r["period_end"] <= e.isoformat()), Dd(0))
    op_income = sum((Dd(r["lease_income"]) for r in ol["rows"] if s.isoformat() <= r["period_end"] <= e.isoformat()), Dd(0))
    assert inc[("90(a)(ii)", "Finance leases — fin")] == fin_income
    assert inc[("90(b)", "Operating leases — l")] == op_income
    assert inc[("90(a)(i)", "Finance leases — sel")] == 0                       # non-dealer lessor: no selling profit
    assert [Dd(x["amount"]) for x in d["other_items"]] == [Dd("400000.00")]     # gain on derecognition shown outside para 90
    assert d["current_method"].startswith("Current portion of the net investment")
    mv = d["net_investment_movement"]
    assert Dd(mv["reconciliation_difference"]) == 0 and Dd(mv["opening"]) == 0
    assert Dd(mv["closing"]) == Dd(fl["rows"][11]["ni_close"])
    rec = d["reconciliation"]
    assert Dd(rec["net_investment"]) == Dd(mv["closing"])
    assert Dd(rec["net_investment_net_of_allowance"]) == Dd(mv["closing"]) - Dd("25000")
    assert sum(Dd(m["amount"]) for m in d["maturity_finance"]) == Dd(rec["undiscounted_lease_payments"])
    # para 97: remaining operating lease payments (Apr-26 .. Dec-29)
    remaining = sum(float(p.lease_amount) for p in pays_b() if p.date > e)
    assert_close(sum(Dd(m["amount"]) for m in d["maturity_operating"]), remaining, 0.001)
    pres = d["presentation"]
    assert Dd(pres["ni_current"]) + Dd(pres["ni_noncurrent"]) == Dd(mv["closing"])
    assert [a["lease_code"] for a in d["operating_lease_assets"]] == ["OL-B"]
