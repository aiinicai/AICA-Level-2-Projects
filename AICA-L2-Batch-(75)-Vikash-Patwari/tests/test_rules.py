"""
The twenty hand-computed cases. Runs with pytest OR standalone:  python tests/test_rules.py

These are the spec. The code exists to reproduce this file. When you disagree
with a result, argue with the case first and only then change the engine.
"""
import sys, os
from datetime import date
from decimal import Decimal

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from clock45.rules import (  # noqa: E402
    resolve_credit_period, due_date_of, appointed_day_of, assess_invoice,
    bank_rate_on, msmed_rate_on, msmed_interest, statute_for,
    ALLOWED, ALLOWED_NOT_YET_DUE, ALLOWED_LATE_INTEREST_ONLY, DISALLOWED,
)
from clock45.classify import (  # noqa: E402
    UdyamRecord, assess_coverage, MICRO, SMALL, MEDIUM,
    SRC_CERTIFICATE, GATE_ACTIVITY, GATE_CLASS, GATE_REGISTRATION, GATE_TIMING,
)
from clock45.normalise import normalise_name, cluster_vendors  # noqa: E402

FY = "2025-26"
D = date
results = []


def check(name, got, want):
    ok = got == want
    results.append((ok, name, got, want))
    assert ok, f"{name}: got {got!r}, want {want!r}"


# --- Credit period ---------------------------------------------------------
def test_01_no_agreement_is_15_days():
    check("01 no agreement -> 15d", resolve_credit_period(None).days, 15)


def test_02_agreement_30_days_honoured():
    check("02 agreement 30d", resolve_credit_period(30).days, 30)


def test_03_agreement_60_days_capped_at_45():
    c = resolve_credit_period(60)
    check("03 agreement 60d capped", (c.days, c.ceiling_applied), (45, True))


def test_04_agreement_exactly_45_not_flagged():
    c = resolve_credit_period(45)
    check("04 agreement 45d", (c.days, c.ceiling_applied), (45, False))


# --- The clock -------------------------------------------------------------
def test_05_due_date_and_appointed_day():
    c = resolve_credit_period(None)
    check("05 due date", due_date_of(D(2025, 6, 1), c), D(2025, 6, 16))
    check("05 appointed day", appointed_day_of(D(2025, 6, 1), c), D(2025, 6, 17))


# --- Verdicts --------------------------------------------------------------
def test_06_paid_within_limit_allowed():
    v = assess_invoice(amount=Decimal("100000"), acceptance_date=D(2025, 6, 1),
                       agreement_days=45, payments=[(D(2025, 7, 10), Decimal("100000"))], fy=FY)
    check("06 paid in time", v.status, ALLOWED)


def test_07_payment_on_exact_due_date_is_in_time():
    v = assess_invoice(amount=Decimal("196000"), acceptance_date=D(2025, 12, 1),
                       agreement_days=45, payments=[(D(2026, 1, 15), Decimal("196000"))], fy=FY)
    check("07 day-45 boundary", (v.status, v.due_date), (ALLOWED, D(2026, 1, 15)))


def test_08a_paid_late_within_year_interest_only():
    # Due 16 Jul; paid 30 Aug -> 44 days past the appointed day.
    v = assess_invoice(amount=Decimal("196000"), acceptance_date=D(2025, 6, 1),
                       agreement_days=45, payments=[(D(2025, 8, 30), Decimal("196000"))], fy=FY)
    check("08a late payment status", v.status, ALLOWED_LATE_INTEREST_ONLY)
    check("08a no disallowance", v.disallowance, Decimal("0.00"))
    assert v.interest > 0, "s.16 interest should accrue on a genuinely late payment"


def test_08b_payment_on_appointed_day_is_late_with_nil_interest():
    # Due 16 Jul, appointed day 17 Jul. Paying ON the appointed day breaches
    # s.15 but leaves a nil interest period. Status must still show lateness.
    v = assess_invoice(amount=Decimal("196000"), acceptance_date=D(2025, 6, 1),
                       agreement_days=45, payments=[(D(2025, 7, 17), Decimal("196000"))], fy=FY)
    check("08b appointed-day payment is late", v.status, ALLOWED_LATE_INTEREST_ONLY)
    check("08b interest is nil", v.interest, Decimal("0.00"))


def test_09_unpaid_at_year_end_disallowed():
    v = assess_invoice(amount=Decimal("155000"), acceptance_date=D(2025, 11, 12),
                       agreement_days=None, payments=[], fy=FY)
    check("09 unpaid -> disallowed", v.status, DISALLOWED)
    check("09 amount", v.disallowance, Decimal("155000.00"))


def test_10_unpaid_but_limit_not_yet_expired():
    v = assess_invoice(amount=Decimal("500000"), acceptance_date=D(2026, 3, 20),
                       agreement_days=45, payments=[], fy=FY)
    check("10 not yet due", v.status, ALLOWED_NOT_YET_DUE)
    check("10 no disallowance", v.disallowance, Decimal("0.00"))


def test_11_no_agreement_15_day_rule_bites_harder():
    # 20 Mar + 15 days = 4 Apr, i.e. AFTER year end -> not disallowable yet.
    v_late = assess_invoice(amount=Decimal("500000"), acceptance_date=D(2026, 3, 20),
                            agreement_days=None, payments=[], fy=FY)
    check("11a 20-Mar +15d falls next year", v_late.status, ALLOWED_NOT_YET_DUE)
    # 10 Mar + 15 days = 25 Mar, inside the year -> disallowed.
    v_early = assess_invoice(amount=Decimal("500000"), acceptance_date=D(2026, 3, 10),
                             agreement_days=None, payments=[], fy=FY)
    check("11b 10-Mar +15d expires in year", v_early.status, DISALLOWED)
    # Same 10 Mar date WITH a 45-day agreement -> survives the year.
    v_agr = assess_invoice(amount=Decimal("500000"), acceptance_date=D(2026, 3, 10),
                           agreement_days=45, payments=[], fy=FY)
    check("11c agreement rescues the same date", v_agr.status, ALLOWED_NOT_YET_DUE)


def test_12_part_payment_only_balance_disallowed():
    v = assess_invoice(amount=Decimal("100000"), acceptance_date=D(2025, 6, 1),
                       agreement_days=45, payments=[(D(2025, 7, 1), Decimal("60000"))], fy=FY)
    check("12 part payment", (v.status, v.disallowance), (DISALLOWED, Decimal("40000.00")))


def test_13_agreement_60_days_still_disallowed_at_46():
    v = assess_invoice(amount=Decimal("285000"), acceptance_date=D(2026, 1, 5),
                       agreement_days=60, payments=[], fy=FY)
    check("13 60d agreement no shield", v.status, DISALLOWED)
    check("13 due date is +45", v.due_date, D(2026, 2, 19))


def test_14_full_payment_after_year_end_still_disallowed():
    v = assess_invoice(amount=Decimal("120000"), acceptance_date=D(2025, 9, 1),
                       agreement_days=45, payments=[(D(2026, 6, 15), Decimal("120000"))], fy=FY)
    check("14 paid next year", v.status, DISALLOWED)


# --- Interest --------------------------------------------------------------
def test_15_bank_rate_is_550_not_675():
    check("15 bank rate Jun-26", bank_rate_on(D(2026, 6, 30)), Decimal("5.50"))
    check("15 msmed rate", msmed_rate_on(D(2026, 6, 30)), Decimal("16.50"))


def test_16_historic_bank_rate_preserved():
    check("16 rate Jan-2024", bank_rate_on(D(2024, 1, 15)), Decimal("6.75"))
    check("16 msmed then", msmed_rate_on(D(2024, 1, 15)), Decimal("20.25"))


def test_17a_interest_flat_rate_period():
    # Wholly inside the 5.50% Bank Rate window -> 16.50% p.a., monthly rests.
    # 100000 * (1 + 0.165/12)^12 - 100000 = 17,810 approx.
    r = msmed_interest(Decimal("100000"), D(2026, 1, 1), D(2027, 1, 1))
    check("17a twelve rests", len(r.segments), 12)
    assert Decimal("17700") < r.interest < Decimal("17900"), r.interest


def test_17b_interest_segments_across_rate_changes():
    # Apr-2025 to Mar-2026 spans 6.75% -> 6.00% -> 5.75% -> 5.50%, so the
    # blended cost is HIGHER than the flat 16.50% case above. If this ever
    # equals 17b's flat figure, rate segmentation has silently broken.
    r = msmed_interest(Decimal("100000"), D(2025, 4, 1), D(2026, 3, 31))
    assert Decimal("19000") < r.interest < Decimal("20000"), r.interest
    rates = {s["msmed_rate_pct"] for s in r.segments}
    assert len(rates) >= 3, f"expected multiple rates, saw {rates}"
    check("17b rate changed mid-period", len(rates) >= 3, True)


def test_18_no_interest_before_appointed_day():
    r = msmed_interest(Decimal("100000"), D(2026, 3, 1), D(2026, 2, 1))
    check("18 negative period", r.interest, Decimal("0.00"))


# --- Coverage gates --------------------------------------------------------
def test_19_gates():
    supply = D(2025, 11, 12)
    trader = UdyamRecord("T1", "UDYAM-X", SMALL, "46109", "Wholesale trade",
                         D(2022, 3, 14), SRC_CERTIFICATE)
    check("19a trader excluded", assess_coverage(trader, supply).gate_failed, GATE_ACTIVITY)

    medium = UdyamRecord("M1", "UDYAM-Y", MEDIUM, "25101", "Mfg", D(2021, 9, 2), SRC_CERTIFICATE)
    check("19b medium excluded", assess_coverage(medium, supply).gate_failed, GATE_CLASS)

    unreg = UdyamRecord("U1")
    check("19c unregistered", assess_coverage(unreg, supply).gate_failed, GATE_REGISTRATION)

    late = UdyamRecord("L1", "UDYAM-Z", SMALL, "28104", "Mfg", D(2026, 1, 20), SRC_CERTIFICATE)
    check("19d registered after supply", assess_coverage(late, supply).gate_failed, GATE_TIMING)

    good = UdyamRecord("G1", "UDYAM-A", MICRO, "25931", "Mfg", D(2021, 2, 18), SRC_CERTIFICATE)
    check("19e covered", assess_coverage(good, supply).covered, True)

    # NIC 45 (motor vehicle trade) is also a trade division
    n45 = UdyamRecord("T2", "UDYAM-B", SMALL, "45201", "Trade", D(2022, 1, 1), SRC_CERTIFICATE)
    check("19f NIC 45 excluded", assess_coverage(n45, supply).gate_failed, GATE_ACTIVITY)


# --- Normalisation and statute --------------------------------------------
def test_20_normalisation_and_statute():
    check("20a normalise M/s + abbrev", normalise_name("M/s Sharma Inds Pvt Ltd"),
          "SHARMA INDUSTRIES")
    check("20b normalise caps + suffix", normalise_name("SHARMA INDUSTRIES PVT LTD"),
          "SHARMA INDUSTRIES")
    check("20c normalise dotted abbrev", normalise_name("Sharma Ind."), "SHARMA INDUSTRIES")
    clusters, _ = cluster_vendors(
        ["Sharma Ind.", "Sharma Industries", "M/s Sharma Inds Pvt Ltd",
         "SHARMA INDUSTRIES PVT LTD", "Verma Castings"])
    biggest = max(clusters, key=lambda c: len(c.members))
    check("20d four spellings cluster", len(biggest.members), 4)
    check("20e FY25-26 statute", statute_for("2025-26")["section"], "43B(h)")
    check("20f FY26-27 statute", statute_for("2026-27")["section"], "37")
    check("20g FY26-27 act", statute_for("2026-27")["act"], "Income-tax Act, 2025")


def test_21_traders_must_not_merge_with_manufacturers():
    """
    GUARD TEST. 'Sharma Industries' and 'Sharma Traders' are different vendors
    and sit on OPPOSITE sides of the trader exclusion. An earlier normaliser
    stripped both descriptors and silently merged them, which would have put a
    wrong number into a signed audit report. Never delete this test.
    """
    assert normalise_name("Sharma Industries") != normalise_name("Sharma Traders")
    clusters, _ = cluster_vendors(["Sharma Industries", "Sharma Traders",
                                   "M/s Sharma Inds Pvt Ltd"])
    for c in clusters:
        joined = " | ".join(c.members)
        assert not ("Traders" in joined and "Industries" in joined), \
            f"trader merged with manufacturer: {joined}"
    check("21 trader/manufacturer kept apart", True, True)


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for fn in fns:
        try:
            fn()
        except AssertionError as e:
            failed += 1
            print(f"  FAIL  {fn.__name__}: {e}")
    for ok, name, got, want in results:
        print(f"  {'PASS' if ok else 'FAIL'}  {name:<34} {got}")
    print(f"\n{len(results)} assertions across {len(fns)} cases · "
          f"{'ALL PASSED' if failed == 0 else f'{failed} FAILED'}")
    sys.exit(1 if failed else 0)
