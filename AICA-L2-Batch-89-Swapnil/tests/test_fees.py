"""Golden tests 12–16 plus every fee regime."""
from dataclasses import replace
from datetime import date, timedelta

import pytest

from engine import UnverifiedRuleError, compute_fee
from engine.fees import fmt_inr, validate_fee_tables
from engine.rulepack import FeeTable
from engine.types import EntityIn

D = date
co5l = EntityIn(99, "Demo Five Lakh Pvt Ltd", "PRIVATE", D(2020, 1, 1), nominal_capital=500_000, paid_up_capital=500_000)


def fee(rp, code, due, late_days, entity=co5l, **kw):
    return compute_fee(code, entity, due, due + timedelta(days=late_days), rulepack=rp, **kw)


# --------------------------------------------------------------- golden 12
def test_g12_adt1_109_days(rp):
    f = fee(rp, "ADT1", D(2024, 1, 10), 109)
    assert (f.normal, f.additional, f.total) == (400, 4000, 4400)
    assert "10×" in f.slab


# --------------------------------------------------------------- golden 13
def test_g13_aoc4_730_days(rp):
    f = fee(rp, "AOC4", D(2024, 1, 1), 730)
    assert (f.normal, f.additional, f.total) == (400, 73000, 73400)


def test_g13_per_form_60_days(rp):
    a, m = fee(rp, "AOC4", D(2024, 1, 1), 60), fee(rp, "MGT7", D(2024, 1, 1), 60)
    assert a.additional == 6000 and m.additional == 6000


# --------------------------------------------------------------- golden 14
def test_g14_zeta_form11(rp, demo):
    zeta = demo["zeta"]["entity"]
    f = compute_fee("LLP_FORM11", zeta, D(2026, 5, 30), D(2026, 9, 20), rulepack=rp, is_small=True)
    assert f.delay_days == 113
    assert (f.normal, f.additional, f.total) == (150, 1500, 1650)
    assert f.scheme is None                                   # CCFS is for companies only


# --------------------------------------------------------------- golden 15
def test_g15_ccfs_overlay(rp, demo):
    theta = demo["theta"]["entity"]
    due = D(2024, 10, 30)
    inside = compute_fee("AOC4", theta, due, D(2026, 9, 10), rulepack=rp)
    assert inside.delay_days == 680 and inside.additional == 68000
    assert inside.scheme == "CCFS_2026" and inside.scheme_relief == 61200 and inside.total == 7200
    after = compute_fee("AOC4", theta, due, D(2026, 9, 20), rulepack=rp)
    assert after.scheme is None and after.total == 400 + 69000
    zeta = demo["zeta"]["entity"]
    llp = compute_fee("LLP_FORM11", zeta, D(2025, 5, 30), D(2026, 9, 10), rulepack=rp)
    assert llp.scheme is None and llp.scheme_relief == 0
    excluded = compute_fee("AOC4", replace(theta, ccfs_excluded=True), due, D(2026, 9, 10), rulepack=rp)
    assert excluded.scheme is None and "excluded" in excluded.explanation


# --------------------------------------------------------------- golden 16
def test_g16_unverified(rp):
    f = fee(rp, "AOC4", D(2024, 1, 1), 10)
    assert f.verified is False and f.label == "Estimate — unverified"
    assert "unverified" in f.explanation
    with pytest.raises(UnverifiedRuleError) as e:
        rp.check_exportable(["AOC4", "MGT7", "AOC4"])
    assert e.value.codes == ["AOC4", "MGT7"] and "AOC4" in str(e.value)


def test_verification_overlay(rp):
    signed = rp.with_verifications({"AOC4": ("partner", D(2026, 9, 25))})
    signed.check_exportable(["AOC4"])                         # no raise
    assert signed.rule("AOC4").content_hash == rp.rule("AOC4").content_hash
    assert fee(signed, "AOC4", D(2024, 1, 1), 10).verified is False   # fee tables still unverified


# ------------------------------------------------------------ other regimes
def test_s139_first_slab_and_on_time(rp):
    assert fee(rp, "ADT1", D(2024, 1, 10), 15).additional == 400        # 1× (correction C6)
    assert fee(rp, "ADT1", D(2024, 1, 10), 16).additional == 800
    f = fee(rp, "ADT1", D(2024, 1, 10), 0)
    assert f.total == 400 and "on time" in f.explanation


def test_general_multiplier_slabs(rp):
    for days, mult in [(1, 2), (30, 2), (31, 4), (60, 4), (90, 6), (180, 10), (181, 12)]:
        assert fee(rp, "DIR12", D(2024, 1, 10), days).additional == mult * 400, days


def test_s139_before_2022_falls_back(rp):
    assert fee(rp, "ADT1", D(2021, 1, 10), 10).additional == 800


def test_higher_additional_fee_on_repeat(rp):
    assert fee(rp, "PAS3", D(2024, 1, 10), 40).additional == 1600
    assert fee(rp, "PAS3", D(2024, 1, 10), 40, prior_defaults=1).additional == 2400
    assert fee(rp, "DIR12", D(2024, 1, 10), 40, prior_defaults=3).additional == 1600   # not a listed form


def test_charge(rp):
    big = replace(co5l, nominal_capital=50_000_000)          # ₹600 normal fee
    assert fee(rp, "CHG1", D(2024, 1, 10), 20, entity=big).additional == 3600
    assert fee(rp, "CHG1", D(2024, 1, 10), 20, entity=big, is_small=True).additional == 1800
    f = fee(rp, "CHG1", D(2024, 1, 10), 50, entity=big, charge_amount=50_000_000)
    assert f.additional == 3600 + 25000
    capped = fee(rp, "CHG1", D(2024, 1, 10), 50, entity=big, charge_amount=5_000_000_000)
    assert capped.additional == 3600 + 500_000
    assert fee(rp, "CHG1", D(2024, 1, 10), 50, entity=big).blocked            # amount missing
    f = fee(rp, "CHG1", D(2024, 1, 10), 91, entity=big)
    assert f.blocked and "s.87" in f.blocked


def test_kyc_fees(rp, demo):
    e = demo["alpha"]["entity"]
    assert compute_fee("DIR3KYC_CHANGE", e, D(2026, 9, 4), D(2026, 9, 1), rulepack=rp).total == 500   # golden 3
    assert compute_fee("DIR3KYC_TRIENNIAL", e, D(2029, 6, 30), D(2029, 6, 1), rulepack=rp).total == 0
    assert compute_fee("DIR3KYC_TRIENNIAL", e, D(2029, 6, 30), D(2029, 7, 1), rulepack=rp).total == 5000
    assert compute_fee("DIR3KYC_ANNUAL", e, D(2025, 9, 30), D(2025, 10, 5), rulepack=rp).total == 5000


def test_llp_beyond_360(rp, demo):
    zeta = demo["zeta"]["entity"]
    f = compute_fee("LLP_FORM11", zeta, D(2024, 5, 30), D(2024, 5, 30) + timedelta(days=400), rulepack=rp)
    assert f.additional == 15 * 150 + 10 * 40
    other = replace(zeta, llp_contribution=3_000_000)          # ₹400 normal fee, not small
    f = compute_fee("LLP_FORM8", other, D(2024, 10, 30), D(2024, 10, 30) + timedelta(days=365), rulepack=rp)
    assert f.normal == 400 and f.additional == 30 * 400 + 20 * 5
    f = compute_fee("LLP_FORM4", zeta, D(2024, 1, 1), D(2024, 1, 1) + timedelta(days=400), rulepack=rp)
    assert f.additional == 25 * 150                           # correction C5
    f = compute_fee("LLP_FORM4", other, D(2024, 1, 1), D(2024, 1, 1) + timedelta(days=20), rulepack=rp)
    assert f.additional == 4 * 400


def test_no_fee_and_extension_overlay(rp, demo):
    f = fee(rp, "MSME1_H1", D(2026, 10, 31), 30)
    assert f.total == 0 and "No filing fee" in f.explanation
    alpha = demo["alpha"]["entity"]                            # nominal ₹10 lakh -> ₹400
    ext = compute_fee("DPT3", alpha, D(2026, 6, 30), D(2026, 7, 20), rulepack=rp, period_key="FY2025-26")
    assert ext.additional == 800 and ext.scheme_relief == 800 and ext.total == 400
    late = compute_fee("DPT3", alpha, D(2026, 6, 30), D(2026, 8, 5), rulepack=rp, period_key="FY2025-26")
    assert late.scheme is None and late.total == 400 + 1600


def test_normal_fee_bands(rp):
    for nominal, expected in [(99_999, 200), (100_000, 300), (499_999, 300), (500_000, 400),
                              (2_499_999, 400), (2_500_000, 500), (9_999_999, 500), (10_000_000, 600)]:
        assert fee(rp, "DIR12", D(2024, 1, 1), 0, entity=replace(co5l, nominal_capital=nominal)).normal == expected
    s8 = replace(co5l, entity_type="SECTION8", has_share_capital=False)
    assert fee(rp, "DIR12", D(2024, 1, 1), 0, entity=s8).normal == 200


def test_fmt_inr():
    assert fmt_inr(123456) == "₹1,23,456"
    assert fmt_inr(73400) == "₹73,400"
    assert fmt_inr(12345678) == "₹1,23,45,678"
    assert fmt_inr(400) == "₹400"
    assert fmt_inr(-1500) == "-₹1,500"


def test_default_rulepack_loaded_when_none():
    assert compute_fee("ADT1", co5l, D(2024, 1, 10), D(2024, 1, 10)).total == 400


def test_validate_fee_tables_errors():
    base = dict(law="x", effective_from=D(2020, 1, 1))
    with pytest.raises(ValueError, match="missing fee tables"):
        validate_fee_tables([FeeTable(code="MULTIPLIER", data={"slabs": [{"upto_days": None, "multiple": 1}]}, **base)])
    good = {c: FeeTable(code=c, data={"bands": [{"fee": 1}], "slabs": [{"upto_days": None, "multiple": 1}],
                                      "annual_forms_beyond_360": {}, "other_forms_beyond_360": {}}, **base)
            for c in ("NORMAL_COMPANY", "NORMAL_LLP", "MULTIPLIER", "MULTIPLIER_S139", "HIGHER_MULTIPLIER",
                      "PER_DAY_100", "CHARGE", "FIXED_KYC", "LLP_MATRIX")}
    validate_fee_tables(list(good.values()))
    bad = dict(good)
    bad["MULTIPLIER"] = FeeTable(code="MULTIPLIER", data={"slabs": [{"upto_days": 30, "multiple": 2}]}, **base)
    with pytest.raises(ValueError, match="open-ended"):
        validate_fee_tables(list(bad.values()))
    bad["MULTIPLIER"] = FeeTable(code="MULTIPLIER", data={"slabs": [{"upto_days": 30, "multiple": 2},
                                                                    {"upto_days": 20, "multiple": 4}]}, **base)
    with pytest.raises(ValueError, match="increase"):
        validate_fee_tables(list(bad.values()))
    bad["MULTIPLIER"] = FeeTable(code="MULTIPLIER", data={"slabs": "x"}, **base)
    with pytest.raises(ValueError, match="non-empty"):
        validate_fee_tables(list(bad.values()))
    bad["MULTIPLIER"] = FeeTable(code="MULTIPLIER", data={"slabs": [{"upto_days": None}]}, **base)
    with pytest.raises(ValueError, match="missing 'multiple'"):
        validate_fee_tables(list(bad.values()))
    bad = dict(good)
    bad["NORMAL_LLP"] = FeeTable(code="NORMAL_LLP", data={}, **base)
    with pytest.raises(ValueError, match="bands"):
        validate_fee_tables(list(bad.values()))
    bad = dict(good)
    bad["LLP_MATRIX"] = FeeTable(code="LLP_MATRIX", data={"slabs": [{"upto_days": None, "see": 1}]}, **base)
    with pytest.raises(ValueError, match="annual_forms_beyond_360"):
        validate_fee_tables(list(bad.values()))
