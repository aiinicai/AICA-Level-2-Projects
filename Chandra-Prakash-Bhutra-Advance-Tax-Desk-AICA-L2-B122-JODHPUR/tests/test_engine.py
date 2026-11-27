from datetime import date

import pytest

from advtax.engine import ClientInputs, compute, compute_tax, fmt_inr, instalment_schedule, load_rules
from advtax.projection import project_business, project_presumptive

R = load_rules()


def tax(regime="new", **kw):
    return compute_tax(ClientInputs(**kw), regime, R)


# ---- new regime slabs, rebate and marginal relief ---------------------------
def test_new_regime_rebate_makes_12_lakh_tax_free():
    assert tax(business_income=1200000)["total_tax"] == 0


def test_new_regime_marginal_relief_just_above_12_lakh():
    # slab tax 61,500 limited to income above 12 lakh (10,000) + 4% cess
    assert tax(business_income=1210000)["total_tax"] == 10400


def test_new_regime_18_lakh():
    # 20,000 + 40,000 + 60,000 + 40,000 = 1,60,000 + cess 6,400
    assert tax(business_income=1800000)["total_tax"] == 166400


def test_salary_standard_deduction_new_regime():
    # 12,75,000 salary less 75,000 = 12,00,000 -> nil after rebate
    assert tax(salary_gross=1275000)["total_tax"] == 0


# ---- old regime ------------------------------------------------------------
def test_old_regime_10_lakh():
    # 12,500 + 1,00,000 = 1,12,500 + cess 4,500
    assert tax("old", business_income=1000000)["total_tax"] == 117000


def test_old_regime_rebate_up_to_5_lakh():
    assert tax("old", business_income=500000)["total_tax"] == 0


def test_old_regime_senior_exemption():
    # 3,00,000 exempt; 2,00,000 @5% + 1,00,000 @20% = 30,000 + cess 1,200
    assert tax("old", business_income=600000, age_band="senior")["total_tax"] == 31200


def test_old_regime_deductions_reduce_income():
    r = tax("old", business_income=1000000, deductions_old=200000)
    assert r["normal_income"] == 800000 and r["total_tax"] == round(72500 * 1.04)


def test_huf_gets_no_rebate():
    # 4-8 lakh @5% + 2 lakh @10% = 40,000 + cess
    assert tax(constitution="HUF", business_income=1000000)["total_tax"] == 41600


# ---- surcharge -------------------------------------------------------------
def test_surcharge_10_percent_above_50_lakh():
    # tax 13,80,000 + surcharge 1,38,000 + cess 60,720
    assert tax(business_income=6000000)["total_tax"] == 1578720


def test_surcharge_marginal_relief_at_51_lakh():
    # tax at 50 lakh 10,80,000 + excess income 1,00,000 = 11,80,000 + cess 47,200
    assert tax(business_income=5100000)["total_tax"] == 1227200


# ---- firms -----------------------------------------------------------------
def test_firm_flat_30_percent():
    assert tax(constitution="Firm", business_income=2000000)["total_tax"] == 624000


def test_llp_surcharge_above_1_crore():
    # 2 crore: 60,00,000 + 12% = 67,20,000 + cess 2,68,800
    assert tax(constitution="LLP", business_income=20000000)["total_tax"] == 6988800


# ---- capital gains ----------------------------------------------------------
def test_equity_gains_special_rates():
    r = tax(business_income=1500000, stcg_equity=100000, ltcg_equity=225000)
    # normal 15 lakh: 20,000+40,000+45,000 = 1,05,000 ; STCG 20,000 ; LTCG (2,25,000-1,25,000)*12.5% = 12,500
    assert r["tax_on_normal_income"] == 105000 and r["tax_on_capital_gains"] == 32500
    assert r["total_tax"] == round(137500 * 1.04)


def test_rebate_not_given_against_capital_gains_new_regime():
    r = tax(business_income=600000, stcg_equity=200000)
    assert r["rebate"] == 10000 and r["total_tax"] == round(40000 * 1.04)


def test_unused_basic_exemption_set_against_gains():
    # normal income 1 lakh, 3 lakh of the 4 lakh exemption unused -> STCG 5 lakh taxed on 2 lakh
    assert tax(business_income=100000, stcg_equity=500000)["tax_on_capital_gains"] == 40000


def test_non_resident_gets_no_exemption_shift_or_rebate():
    assert tax(business_income=100000, stcg_equity=500000, resident=False)["tax_on_capital_gains"] == 100000


# ---- house property ----------------------------------------------------------
def test_let_out_property_30_percent_deduction():
    r = tax(hp_let_out_rent=600000, hp_municipal_tax=20000, hp_let_out_interest=100000)
    assert r["house_property_income"] == 580000 * 0.7 - 100000


def test_self_occupied_interest_only_in_old_regime():
    new = tax("new", business_income=1500000, hp_self_occupied_interest=300000)
    old = tax("old", business_income=1500000, hp_self_occupied_interest=300000)
    assert new["house_property_income"] == 0 and old["house_property_income"] == -200000


# ---- advance tax instalments ---------------------------------------------------
def test_regime_auto_picks_lower_and_instalments():
    res = compute(ClientInputs(business_income=1800000), R, date(2026, 11, 22))
    assert res["chosen_key"] == "new" and res["net_liability"] == 166400
    nd = res["schedule"]["next_due"]
    assert nd["date"] == date(2026, 12, 15) and nd["pay_now"] == 124800 and nd["days_left"] == 23
    # nothing paid: June 15% and Sept 45% missed -> 3% each on shortfall rounded down to 100
    assert res["schedule"]["interest_incurred"] == round(24900 * 0.03) + round(74800 * 0.03)


def test_below_10000_not_liable():
    res = compute(ClientInputs(business_income=1210000, tds_tcs=1000), R, date(2026, 11, 22))
    assert res["net_liability"] == 9400 and not res["liable"]


def test_senior_without_business_not_liable():
    res = compute(ClientInputs(age_band="senior", other_interest=2500000), R, date(2026, 11, 22))
    assert not res["liable"]


def test_presumptive_single_instalment():
    res = compute(ClientInputs(business_income=1800000, presumptive=True), R, date(2026, 11, 22))
    rows = res["schedule"]["rows"]
    assert len(rows) == 1 and rows[0]["due_date"] == date(2027, 3, 15)
    assert res["schedule"]["next_due"]["pay_now"] == 166400 and res["schedule"]["interest_incurred"] == 0


def test_safe_harbour_12_percent_in_june():
    pays = [{"date": "2026-06-10", "amount": 12000}]
    s = instalment_schedule(100000, pays, date(2026, 7, 1), False, R)
    assert s["rows"][0]["shortfall"] == 3000 and s["rows"][0]["interest"] == 0


def test_payment_after_due_date_does_not_count_for_that_instalment():
    pays = [{"date": "2026-06-20", "amount": 15000}]
    s = instalment_schedule(100000, pays, date(2026, 7, 1), False, R)
    assert s["rows"][0]["interest"] == 450 and s["paid_to_date"] == 15000


def test_fully_paid_schedule_has_no_interest():
    pays = [{"date": "2026-06-15", "amount": 15000}, {"date": "2026-09-15", "amount": 30000},
            {"date": "2026-12-15", "amount": 30000}, {"date": "2027-03-15", "amount": 25000}]
    s = instalment_schedule(100000, pays, date(2027, 3, 31), False, R)
    assert s["interest_if_nothing_more_paid"] == 0 and s["next_due"] is None


def test_default_interest_per_month():
    res = compute(ClientInputs(constitution="Firm", business_income=2000000), R, date(2026, 11, 22))
    assert res["monthly_default_interest"] == 6240


# ---- projection ----------------------------------------------------------------
def test_projection_straight_line():
    # 183 days (1 Apr - 30 Sep) of a 365-day year
    p = project_business(3660000, 1830000, as_on=date(2026, 9, 30))
    assert p["days_done"] == 183 and p["ytd_profit"] == 1830000
    assert p["projected_book_profit"] == 3650000


def test_projection_one_off_and_adjustments():
    p = project_business(3660000, 1830000, one_off_income=100000, as_on=date(2026, 9, 30),
                         add_backs=50000, less_deductions=200000)
    assert p["projected_business_income"] == 3650000 + 100000 + 50000 - 200000


def test_projection_stock_adjustment():
    p = project_business(1000000, 900000, opening_stock=200000, closing_stock=300000, as_on=date(2027, 3, 31))
    assert p["projected_book_profit"] == 200000


def test_presumptive_projection():
    p = project_presumptive(1830000, 6, date(2026, 4, 1), date(2026, 9, 30), date(2027, 3, 31))
    assert p["projected_turnover"] == 3650000 and p["projected_business_income"] == 219000


@pytest.mark.parametrize("n,expected", [(0, "0"), (999, "999"), (1000, "1,000"), (123456, "1,23,456"),
                                        (12345678, "1,23,45,678"), (-250000, "-2,50,000")])
def test_indian_number_format(n, expected):
    assert fmt_inr(n) == expected


# ---- age band applies only to resident individuals --------------------------------
def test_huf_ignores_age_band():
    a = tax("old", constitution="HUF", business_income=600000, age_band="senior")
    b = tax("old", constitution="HUF", business_income=600000)
    assert a["total_tax"] == b["total_tax"] == round(32500 * 1.04)


def test_non_resident_senior_gets_normal_exemption():
    # 2.5 lakh exemption, no rebate: 12,500 + 20,000 = 32,500 + cess
    assert tax("old", business_income=600000, age_band="senior", resident=False)["total_tax"] == 33800


def test_fixed_regime_that_costs_more_reports_negative_saving():
    res = compute(ClientInputs(regime="old", business_income=1000000), R, date(2026, 11, 22))
    assert res["chosen_key"] == "old" and res["regime_saving"] < 0


# ---- client message wording ----------------------------------------------------------
def test_message_does_not_ask_for_payment_when_nothing_is_due():
    from advtax import notes
    senior = ClientInputs(name="X", age_band="senior", other_interest=2500000)
    text = notes.whatsapp_text(senior, compute(senior, R, date(2026, 11, 22)))
    assert "Please pay" not in text and "self-assessment tax" in text
    due = ClientInputs(name="Y", business_income=1800000)
    assert "Please pay" in notes.whatsapp_text(due, compute(due, R, date(2026, 11, 22)))


def test_dividend_with_surcharge_above_15_percent_is_flagged():
    # income above Rs 2 crore draws 25% surcharge; the 15% limit on dividend is not worked out, so the user is told
    flags = tax(business_income=30000000, other_dividend=500000)["flags"]
    assert any("dividend" in f.lower() for f in flags)
    assert not any("dividend" in f.lower() for f in tax(business_income=30000000)["flags"])
    assert not any("dividend" in f.lower() for f in tax(business_income=8000000, other_dividend=500000)["flags"])
