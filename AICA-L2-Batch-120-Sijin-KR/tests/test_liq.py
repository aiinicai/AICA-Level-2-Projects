from datetime import date

from auditsignoff.cli import review_liq
from auditsignoff.models import load_params, load_yaml
from auditsignoff.rules_liq import add_business_days, add_months, run_liq

TODAY = date(2026, 10, 14)


def test_business_days_skip_weekends():
    p = load_params()
    assert add_business_days(date(2026, 6, 5), 20, p) == date(2026, 7, 3)
    assert add_business_days(date(2026, 6, 5), 1, p) == date(2026, 6, 8)      # Fri -> Mon


def test_business_days_holiday_list_is_respected():
    p = dict(load_params(), holidays=["2026-06-08"])
    assert add_business_days(date(2026, 6, 5), 1, p) == date(2026, 6, 9)


def test_add_months_month_end():
    assert add_months(date(2026, 8, 31), 6) == date(2027, 2, 28)


def _ms(samples, case):
    inp = load_yaml(samples / f"liq_{case}.yaml")
    res, ms = run_liq(inp, load_params(), TODAY)
    return {m["check"]: m for m in ms}, {r.check_id: r for r in res}


def test_difc_breach_clocks(samples):
    ms, res = _ms(samples, "difc_breach")
    assert ms["LQ-03"]["due"] == "2026-07-03" and ms["LQ-03"]["status"] == "OVERDUE"
    assert ms["LQ-04"]["due"] == "2026-07-01" and ms["LQ-04"]["status"] == "LATE"
    assert ms["LQ-05"]["due"] == "2026-10-18" and ms["LQ-05"]["status"] == "TOO EARLY"
    assert res["LQ-14"].status == "EXC"
    assert res["LQ-13"].status == "EXC"


def test_dso_rules_apply_only_to_dso(samples):
    ms, res = _ms(samples, "dso_short_gap")
    assert ms["LQ-06"]["due"] == "2026-10-15" and ms["LQ-06"]["status"] == "TOO EARLY"
    assert ms["LQ-08"]["due"] == "2026-09-14"
    assert res["LQ-05"].status == "NOTRUN" and res["LQ-07"].status == "NOTRUN"
    assert res["LQ-01"].status == "EXC"          # liquidator not confirmed in BR


def test_clean_liquidation_has_no_exceptions(samples):
    ms, res = _ms(samples, "dmcc_clean")
    assert all(r.status != "EXC" for r in res.values())
    assert ms["LQ-19"]["due"] == "2027-09-15"


def test_partner_approval_suppresses_short_gap(samples):
    inp = load_yaml(samples / "liq_dso_short_gap.yaml")
    inp["partner_approval_short_gap"] = True
    res, ms = run_liq(inp, load_params(), TODAY)
    assert all(m["check"] != "LQ-06" for m in ms)


def test_paper_is_written(samples, tmp_path):
    res, ms, path = review_liq(samples / "liq_difc_breach.yaml", tmp_path, TODAY)
    assert path.exists() and path.with_suffix(".xlsx").exists() and path.with_suffix(".json").exists()
