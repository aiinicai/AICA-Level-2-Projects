from datetime import date, timedelta

import pytest

from engine.dates import (FY, agm_deadline, company_first_fy_end, due_date, financial_years, fy_containing,
                          fy_key_for_end, half_years, holiday_hint, kyc_cycle_dues, kyc_cycle_key, kyc_due,
                          llp_election_available, llp_first_fy_end, march31s_after, standard_fy_end)


class TestDueDate:
    def test_days_excludes_anchor_day(self):
        assert due_date(date(2026, 1, 20), {"days": 30}) == date(2026, 2, 19)

    def test_months_keeps_day(self):
        assert due_date(date(2026, 1, 20), {"months": 2}) == date(2026, 3, 20)

    def test_months_clip_to_month_end(self):
        assert due_date(date(2026, 8, 31), {"months": 6}) == date(2027, 2, 28)
        assert due_date(date(2027, 8, 31), {"months": 6}) == date(2028, 2, 29)

    def test_months_then_days(self):
        # LLP Form 8: 30 days from the end of six months of the FY
        assert due_date(date(2026, 3, 31), {"months": 6, "days": 30}) == date(2026, 10, 30)

    def test_negative_and_empty(self):
        assert due_date(date(2026, 9, 30), {"days": -21}) == date(2026, 9, 9)
        assert due_date(date(2026, 9, 30), None) == date(2026, 9, 30)

    def test_rejects_unknown_key(self):
        with pytest.raises(ValueError):
            due_date(date(2026, 1, 1), {"weeks": 2})

    def test_leap_year_60_days(self):
        assert due_date(date(2027, 12, 31), {"days": 60}) == date(2028, 2, 29)


def test_holiday_hint():
    assert holiday_hint(date(2026, 9, 27)) == "falls on a Sunday"
    assert holiday_hint(date(2026, 9, 28)) is None
    assert "Gandhi" in holiday_hint(date(2026, 10, 2), {date(2026, 10, 2): "Gandhi Jayanti"})


class TestFinancialYear:
    def test_first_fy_invariant_every_day_of_two_years(self):
        d = date(2024, 1, 1)
        while d < date(2026, 1, 1):
            assert company_first_fy_end(d) == date(d.year + 1, 3, 31)
            d += timedelta(days=1)

    def test_examples(self):
        assert company_first_fy_end(date(2026, 1, 20)) == date(2027, 3, 31)   # ~14 months
        assert company_first_fy_end(date(2025, 5, 10)) == date(2026, 3, 31)

    def test_keys(self):
        assert fy_key_for_end(date(2027, 3, 31)) == "FY2026-27"
        assert standard_fy_end(date(2026, 4, 1)) == date(2027, 3, 31)
        assert standard_fy_end(date(2026, 3, 31)) == date(2026, 3, 31)

    def test_series(self):
        fys = financial_years(date(2026, 1, 20), date(2027, 3, 31), date(2029, 3, 31))
        assert [f.key for f in fys] == ["FY2026-27", "FY2027-28", "FY2028-29"]
        assert fys[0].is_long and not fys[1].is_long
        assert fy_containing(fys, date(2027, 6, 1)).key == "FY2027-28"
        assert fy_containing(fys, date(2025, 1, 1)) is None

    def test_llp_election(self):
        inc = date(2025, 11, 15)
        assert llp_first_fy_end(inc, False) == date(2026, 3, 31)
        assert llp_first_fy_end(inc, True) == date(2027, 3, 31)
        # registered before 1 October: election not available
        assert llp_first_fy_end(date(2025, 6, 1), True) == date(2026, 3, 31)
        assert llp_election_available(date(2026, 2, 1)) and not llp_election_available(date(2026, 9, 30))


def test_half_years():
    hys = half_years(date(2026, 1, 20), date(2027, 3, 31))
    assert [h.key for h in hys] == ["H2-FY2025-26", "H1-FY2026-27", "H2-FY2026-27"]
    assert hys[1].end == date(2026, 9, 30)
    assert half_years(date(2026, 11, 1), date(2027, 1, 1))[0].key == "H2-FY2026-27"
    assert half_years(date(2026, 5, 1), date(2026, 6, 1))[0].key == "H1-FY2026-27"


def test_march31s():
    assert march31s_after(date(2026, 1, 20), date(2028, 3, 31)) == [date(2026, 3, 31), date(2027, 3, 31), date(2028, 3, 31)]
    assert march31s_after(date(2026, 3, 31), date(2027, 3, 31)) == [date(2027, 3, 31)]


class TestAGM:
    def test_first_agm_nine_months(self):
        assert agm_deadline(FY(date(2026, 1, 20), date(2027, 3, 31)), True, None) == date(2027, 12, 31)

    def test_later_agm_earlier_of_six_and_fifteen(self):
        fy = FY(date(2026, 4, 1), date(2027, 3, 31))
        assert agm_deadline(fy, False, date(2026, 9, 26)) == date(2027, 9, 30)
        assert agm_deadline(fy, False, date(2026, 5, 15)) == date(2027, 8, 15)   # 15-month limit bites


class TestKYC:
    def test_new_din_fy_2025_26(self):
        assert kyc_due(date(2026, 1, 15)) == date(2029, 6, 30)       # partner decision Q1

    def test_legacy_din(self):
        assert kyc_due(date(2019, 7, 1), last_kyc_fy="FY2024-25") == date(2028, 6, 30)
        assert kyc_due(date(2025, 3, 31)) == date(2028, 6, 30)

    def test_din_fy_2026_27(self):
        assert kyc_due(date(2026, 4, 1)) == date(2030, 6, 30)

    def test_override(self):
        assert kyc_due(date(2026, 1, 15), override_first_due=date(2028, 6, 30)) == date(2028, 6, 30)

    def test_cycle(self):
        assert kyc_cycle_dues(date(2019, 7, 1), date(2031, 12, 31)) == [date(2028, 6, 30), date(2031, 6, 30), date(2034, 6, 30)]
        assert kyc_cycle_key(date(2029, 6, 30)) == "KYC-CYCLE-2026-27..2028-29"
        assert kyc_cycle_key(date(2028, 6, 30)) == "KYC-CYCLE-2025-26..2027-28"
