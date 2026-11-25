"""Lot anchor date: periods starting on a chosen day (month_thirds) or a chosen date (fixed_days)."""
from datetime import date

import pytest
from pydantic import ValidationError

from app.core.config import BusinessDefaults
from app.engine.forecast import build_columns
from app.engine.lots import ACTUAL, CURRENT, build_lots, forecast_lots


def _s(**kw):
    return BusinessDefaults(**kw)


def spans(lots):
    return [(lt.start.isoformat(), lt.end.isoformat(), lt.status) for lt in lots]


def test_blank_anchor_is_unchanged_calendar():
    lots = build_lots(date(2026, 11, 24), _s(horizon_months=2))
    assert spans(lots)[0] == ("2026-11-21", "2026-11-30", CURRENT)
    assert [lt.band for lt in lots] == ["November 2026"] + ["December 2026"] * 3


def test_month_thirds_anchor_day_5():
    s = _s(lot_anchor_date="2026-01-05", horizon_months=2, grid_start="month_start")
    lots = build_lots(date(2026, 11, 24), s)
    assert spans(lots) == [
        ("2026-11-05", "2026-11-14", ACTUAL), ("2026-11-15", "2026-11-24", CURRENT),
        ("2026-11-25", "2026-12-04", "forecast"),
        ("2026-12-05", "2026-12-14", "forecast"), ("2026-12-15", "2026-12-24", "forecast"),
        ("2026-12-25", "2027-01-04", "forecast")]
    assert lots[0].band == "05 Nov-04 Dec 2026"
    cols = build_columns(forecast_lots(lots), True)
    totals = [c for c in cols if c.kind == "month"]
    assert totals[0].label == "05 Nov-04 Dec 2026 total *" and totals[0].partial      # lot 1 of period is past
    assert totals[1].label == "05 Dec-04 Jan 2027 total" and not totals[1].partial


def test_month_thirds_anchor_before_anchor_day_uses_previous_period():
    lots = build_lots(date(2026, 11, 3), _s(lot_anchor_date="2026-01-05", horizon_months=1))
    assert spans(lots)[0] == ("2026-10-25", "2026-11-04", CURRENT)      # period 5 Oct-4 Nov
    assert len(lots) == 1


def test_month_thirds_anchor_covers_february():
    lots = build_lots(date(2027, 2, 20), _s(lot_anchor_date="2026-01-28", horizon_months=1))
    assert spans(lots)[-1] == ("2027-02-17", "2027-02-27", CURRENT)     # 28 Jan-27 Feb, no day lost
    lots = build_lots(date(2027, 2, 28), _s(lot_anchor_date="2026-01-28", horizon_months=1))
    assert spans(lots)[0][0] == "2027-02-28"


def test_fixed_days_anchor_repeats_from_exact_date():
    s = _s(lot_scheme="fixed_days", lot_anchor_date="2026-11-05", horizon_lots=3)
    lots = build_lots(date(2026, 11, 24), s)
    assert spans(lots) == [("2026-11-15", "2026-11-24", CURRENT), ("2026-11-25", "2026-12-04", "forecast"),
                           ("2026-12-05", "2026-12-14", "forecast")]
    # stable: the next month still uses the same 10-day rhythm
    later = build_lots(date(2027, 1, 2), s)
    assert spans(later)[0] == ("2026-12-25", "2027-01-03", CURRENT)


def test_anchor_validation():
    with pytest.raises(ValidationError):
        _s(lot_anchor_date="2026-01-30")                  # month_thirds: day must exist in every month
    with pytest.raises(ValidationError):
        _s(lot_anchor_date="5th")
    assert _s(lot_scheme="fixed_days", lot_anchor_date="2026-01-30").anchor == date(2026, 1, 30)
    assert _s(lot_anchor_date=" ").lot_anchor_date == ""


def test_anchor_setting_saved_on_settings_page(app_client):
    from tests.test_phase6_web import csrf_of, login
    c = app_client
    login(c, "admin1")
    page = c.get("/admin/settings").text
    assert 'type="date" id="lot_anchor_date"' in page
    r = c.post("/admin/settings", data={"lot_anchor_date": "2026-01-05", "csrf_token": csrf_of(page)},
               follow_redirects=True)
    assert "lot_anchor_date" in r.text and "Settings saved" in r.text
    grid = c.get("/?as_of=2026-11-24").text
    assert "15-24 Nov" in grid and "05 Nov-04 Dec 2026" in grid
    r = c.post("/admin/settings", data={"lot_anchor_date": "2026-01-31", "csrf_token": csrf_of(page)},
               follow_redirects=True)
    assert "1-28" in r.text


from tests.test_phase6_web import app_client  # noqa: E402,F401  (fixture)
